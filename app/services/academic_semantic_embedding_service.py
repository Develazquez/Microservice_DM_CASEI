from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import threading
import time
from typing import Any

import httpx
import numpy as np
import pandas as pd

from app.models.config import CURRENT_SEARCH_INDEX_POINTER, PROJECT_ROOT, SEARCH_REGISTRY_DIR
from app.models.search_config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_CACHE_MAX_SIZE,
    EMBEDDING_CACHE_TTL_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_EMBEDDING_INDEX_TIMEOUT_SECONDS,
    OLLAMA_EMBEDDING_TIMEOUT_SECONDS,
    OLLAMA_GATEWAY_API_KEY,
    OLLAMA_GATEWAY_URL,
    OLLAMA_KEEP_ALIVE,
    SEMANTIC_MIN_SIMILARITY,
    SEMANTIC_PROTOTYPE_MIN_SIMILARITY,
)
from app.models.search_query_schemas import EmbeddingRequest, SemanticHint
from app.services.academic_bm25_search_service import tokenize


SEMANTIC_CATALOG_PATH = PROJECT_ROOT / "app" / "models" / "semantic_catalog.json"
SEMANTIC_DESCRIPTOR_VERSION = "2"
_QUERY_CACHE: OrderedDict[str, tuple[float, np.ndarray]] = OrderedDict()
_INDEX_CACHE: dict[str, "SemanticIndexBundle"] = {}
_LOCK = threading.Lock()


class EmbeddingUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticIndexBundle:
    version: str
    model: str
    document_ids: list[str]
    document_embeddings: np.ndarray
    prototype_ids: list[str]
    prototype_embeddings: np.ndarray
    catalog: dict[str, Any]


def load_semantic_catalog() -> dict[str, Any]:
    return json.loads(SEMANTIC_CATALOG_PATH.read_text(encoding="utf-8"))


def semantic_descriptor(row: pd.Series) -> str:
    average_bucket = str(row.get("promedio_bucket", ""))
    attendance_bucket = str(row.get("asistencia_bucket", ""))
    lag_bucket = str(row.get("rezago_bucket", ""))
    failed_bucket = str(row.get("reprobadas_bucket", ""))
    profile = str(row.get("perfil_sugerido", ""))
    parts = [
        f"programa {row.get('programa', 'sin programa')}",
        f"estatus {row.get('estatus_academico', 'sin estatus')}",
        f"perfil {profile or 'sin perfil'}",
        average_bucket,
        attendance_bucket,
        lag_bucket,
        failed_bucket,
        str(row.get("acompanamiento_bucket", "")),
        str(row.get("incidencias_bucket", "")),
    ]
    risk_signals = 0
    if "promedio bajo" in average_bucket:
        parts.append("bajo rendimiento va mal notas bajas se le complican las materias va flojo")
        risk_signals += 1
    if "asistencia baja" in attendance_bucket:
        parts.append("baja asistencia casi no viene falta mucho ausentismo no se presenta")
        risk_signals += 1
    if "rezago" in lag_bucket and "sin rezago" not in lag_bucket:
        parts.append("rezago academico va atrasado esta atorado debe materias se esta quedando")
        risk_signals += 1
    if "reprobadas" in failed_bucket and "sin reprobadas" not in failed_bucket:
        parts.append("asignaturas pendientes dificultades para aprobar materias reprobadas")
        risk_signals += 1
    if "promedio alto" in average_bucket:
        parts.append("buen desempeno va excelente buenas notas alto rendimiento destacado va muy bien")
    if "regular" in profile.lower():
        parts.append("avance academico estable va estable sin problemas avance regular todo en orden")
    if "promedio alto" in average_bucket and "asistencia baja" in attendance_bucket:
        parts.append("buen promedio con baja asistencia saca buenas notas pero falta va bien aunque no viene")
    if risk_signals >= 2:
        parts.append("multiples senales de riesgo varias dificultades muchas alertas caso complicado")
    return " ".join(" ".join(part.strip().split()) for part in parts if part and part.strip())


def prototype_text(concept: dict[str, Any]) -> str:
    phrases = ". ".join(str(value) for value in concept.get("phrases", []))
    return f"{concept.get('label', '')}. {concept.get('description', '')}. Expresiones: {phrases}".strip()


def _semantic_stems(text: str) -> set[str]:
    stems: set[str] = set()
    for token in tokenize(text):
        value = "va" if token == "van" else token
        if len(value) > 4 and value.endswith("s"):
            value = value[:-1]
        if len(value) > 4 and value.endswith("n"):
            value = value[:-1]
        stems.add(value)
    return stems


def _matching_catalog_concepts(query: str, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    query_stems = _semantic_stems(query)
    matches: list[dict[str, Any]] = []
    for concept in catalog.get("concepts", []):
        required_terms = concept.get("required_query_terms", [])
        if required_terms and not any(
            _semantic_stems(str(term)) <= query_stems
            for term in required_terms
        ):
            continue
        for phrase in concept.get("phrases", []):
            phrase_stems = _semantic_stems(str(phrase))
            if phrase_stems and len(query_stems & phrase_stems) / len(phrase_stems) >= 0.6:
                matches.append(concept)
                break
    return matches


def semantic_query_text(query: str, catalog: dict[str, Any]) -> tuple[str, list[str]]:
    matches = _matching_catalog_concepts(query, catalog)
    expanded = " ".join([query, *[prototype_text(concept) for concept in matches]])
    return expanded.strip(), [str(concept["id"]) for concept in matches]


def select_semantic_hints(
    catalog: dict[str, Any],
    prototype_ids: list[str],
    prototype_scores: np.ndarray,
    expanded_concepts: list[str],
) -> list[SemanticHint]:
    concept_by_id = {str(item["id"]): item for item in catalog.get("concepts", [])}
    score_by_id = {
        str(concept_id): float(prototype_scores[position])
        for position, concept_id in enumerate(prototype_ids)
    }
    explicit_ids = [concept_id for concept_id in expanded_concepts if concept_id in concept_by_id]
    ordered_ids = [
        *explicit_ids,
        *[
            prototype_ids[int(position)]
            for position in np.argsort(-prototype_scores)
            if prototype_ids[int(position)] not in explicit_ids
        ],
    ]
    blocked_ids = {
        str(conflict)
        for concept_id in explicit_ids
        for conflict in concept_by_id[concept_id].get("conflicts_with", [])
        if str(conflict) not in explicit_ids
    }
    hints: list[SemanticHint] = []
    for concept_id in ordered_ids:
        concept_id = str(concept_id)
        concept = concept_by_id[concept_id]
        score = score_by_id[concept_id]
        is_explicit = concept_id in explicit_ids
        if concept_id in blocked_ids:
            continue
        if concept.get("requires_catalog_match") and not is_explicit:
            continue
        if not is_explicit and score < SEMANTIC_PROTOTYPE_MIN_SIMILARITY:
            continue
        hints.append(
            SemanticHint(
                concept_id=concept_id,
                label=str(concept.get("label", concept_id)),
                similarity=score,
                allowed_effect=str(concept.get("allowed_effect", "ranking")),
            )
        )
        if len(hints) >= 8:
            break
    return hints


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise EmbeddingUnavailableError("Ollama devolvio una matriz de embeddings invalida.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise EmbeddingUnavailableError("Ollama devolvio un embedding con norma cero.")
    return matrix / norms


def request_direct_embeddings(
    texts: list[str],
    *,
    base_url: str = OLLAMA_BASE_URL,
    model: str = OLLAMA_EMBEDDING_MODEL,
    timeout: float = OLLAMA_EMBEDDING_TIMEOUT_SECONDS,
) -> np.ndarray:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{base_url.rstrip('/')}/api/embed",
            json={
                "model": model,
                "input": texts,
                "truncate": True,
                "keep_alive": OLLAMA_KEEP_ALIVE,
            },
        )
        response.raise_for_status()
    embeddings = response.json().get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise EmbeddingUnavailableError("Ollama no devolvio un embedding por cada texto.")
    return _normalize_rows(np.asarray(embeddings, dtype=np.float32))


def request_gateway_embeddings(
    texts: list[str],
    *,
    timeout: float = OLLAMA_EMBEDDING_TIMEOUT_SECONDS,
) -> np.ndarray:
    headers = {"X-CASEI-SLM-KEY": OLLAMA_GATEWAY_API_KEY} if OLLAMA_GATEWAY_API_KEY else {}
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{OLLAMA_GATEWAY_URL}/embed",
            json=EmbeddingRequest(texts=texts).model_dump(mode="json"),
            headers=headers,
        )
        response.raise_for_status()
    payload = response.json()
    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise EmbeddingUnavailableError("El gateway no devolvio un embedding por cada texto.")
    return _normalize_rows(np.asarray(embeddings, dtype=np.float32))


def _cache_key(text: str) -> str:
    normalized = " ".join(text.lower().strip().split())
    catalog_version = load_semantic_catalog().get("version", "unknown")
    return json.dumps(
        {
            "text": normalized,
            "model": OLLAMA_EMBEDDING_MODEL,
            "catalog_version": catalog_version,
            "descriptor_version": SEMANTIC_DESCRIPTOR_VERSION,
        },
        sort_keys=True,
    )


def _cached_embedding(text: str) -> np.ndarray | None:
    key = _cache_key(text)
    now = time.monotonic()
    with _LOCK:
        item = _QUERY_CACHE.get(key)
        if item is None:
            return None
        created_at, vector = item
        if now - created_at > EMBEDDING_CACHE_TTL_SECONDS:
            _QUERY_CACHE.pop(key, None)
            return None
        _QUERY_CACHE.move_to_end(key)
        return vector.copy()


def _store_embedding(text: str, vector: np.ndarray) -> None:
    key = _cache_key(text)
    with _LOCK:
        _QUERY_CACHE[key] = (time.monotonic(), np.asarray(vector, dtype=np.float32).copy())
        _QUERY_CACHE.move_to_end(key)
        while len(_QUERY_CACHE) > EMBEDDING_CACHE_MAX_SIZE:
            _QUERY_CACHE.popitem(last=False)


def _request_embedding_batch(texts: list[str], timeout: float) -> np.ndarray:
    return (
        request_gateway_embeddings(texts, timeout=timeout)
        if OLLAMA_GATEWAY_URL
        else request_direct_embeddings(texts, timeout=timeout)
    )


def _embed_batch_with_split(texts: list[str], timeout: float) -> np.ndarray:
    try:
        return _request_embedding_batch(texts, timeout)
    except (httpx.HTTPError, ValueError, EmbeddingUnavailableError):
        if len(texts) <= 1:
            raise
        midpoint = len(texts) // 2
        left = _embed_batch_with_split(texts[:midpoint], timeout)
        right = _embed_batch_with_split(texts[midpoint:], timeout)
        return np.vstack([left, right]).astype(np.float32)


def embed_texts(
    texts: list[str],
    *,
    use_cache: bool = True,
    timeout: float = OLLAMA_EMBEDDING_TIMEOUT_SECONDS,
) -> tuple[np.ndarray, bool]:
    cleaned = [" ".join(str(text).strip().split()) for text in texts]
    if not cleaned or any(not text for text in cleaned):
        raise ValueError("Los textos para embeddings no pueden estar vacios.")

    vectors: list[np.ndarray | None] = [None] * len(cleaned)
    missing_indexes: list[int] = []
    cache_hits = 0
    if use_cache:
        for index, text in enumerate(cleaned):
            cached = _cached_embedding(text)
            if cached is None:
                missing_indexes.append(index)
            else:
                vectors[index] = cached
                cache_hits += 1
    else:
        missing_indexes = list(range(len(cleaned)))

    try:
        for offset in range(0, len(missing_indexes), max(1, EMBEDDING_BATCH_SIZE)):
            batch_indexes = missing_indexes[offset : offset + max(1, EMBEDDING_BATCH_SIZE)]
            batch_texts = [cleaned[index] for index in batch_indexes]
            embedded = _embed_batch_with_split(batch_texts, timeout)
            for row_index, source_index in enumerate(batch_indexes):
                vector = embedded[row_index]
                vectors[source_index] = vector
                if use_cache:
                    _store_embedding(cleaned[source_index], vector)
    except (httpx.HTTPError, ValueError, EmbeddingUnavailableError) as exc:
        raise EmbeddingUnavailableError(f"No fue posible generar embeddings: {exc}") from exc

    if any(vector is None for vector in vectors):
        raise EmbeddingUnavailableError("No se completaron todos los embeddings solicitados.")
    matrix = np.vstack([vector for vector in vectors if vector is not None]).astype(np.float32)
    return matrix, cache_hits == len(cleaned)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_checksum_matches(path: Path, expected_sha256: str) -> bool:
    if _sha256(path) == expected_sha256:
        return True
    if path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
        return False

    raw = path.read_bytes()
    normalized_lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    variants = {
        hashlib.sha256(normalized_lf).hexdigest(),
        hashlib.sha256(normalized_lf.replace(b"\n", b"\r\n")).hexdigest(),
    }
    return expected_sha256 in variants


def _descriptor_hash(descriptor: str) -> str:
    value = f"{SEMANTIC_DESCRIPTOR_VERSION}:{descriptor}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reusable_document_embeddings() -> dict[str, tuple[str, np.ndarray]]:
    if not CURRENT_SEARCH_INDEX_POINTER.exists():
        return {}
    try:
        pointer = json.loads(CURRENT_SEARCH_INDEX_POINTER.read_text(encoding="utf-8"))
        target = PROJECT_ROOT / str(pointer.get("bundle_dir", ""))
        manifest_path = PROJECT_ROOT / str(pointer.get("manifest_path", ""))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("model") != OLLAMA_EMBEDDING_MODEL
            or str(manifest.get("descriptor_version")) != SEMANTIC_DESCRIPTOR_VERSION
        ):
            return {}
        for name, expected in manifest.get("files", {}).items():
            path = target / name
            if not path.exists() or not file_checksum_matches(path, expected):
                return {}
        identifiers = pd.read_csv(target / "semantic_document_ids.csv", dtype=str)
        vectors = _normalize_rows(np.load(target / "semantic_embeddings.npy", allow_pickle=False))
        if len(identifiers) != len(vectors):
            return {}
        return {
            str(row.document_id): (str(row.descriptor_hash), vectors[index].copy())
            for index, row in enumerate(identifiers.itertuples(index=False))
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError, EmbeddingUnavailableError):
        return {}


def build_and_persist_semantic_index(
    documents: pd.DataFrame,
    *,
    require_full_document_reuse: bool = False,
) -> dict[str, Any]:
    if documents.empty:
        raise ValueError("No hay documentos para construir el indice semantico.")
    if "document_id" not in documents.columns:
        raise ValueError("El corpus semantico requiere document_id.")

    unique = documents.drop_duplicates("document_id").reset_index(drop=True)
    descriptors = [semantic_descriptor(row) for _, row in unique.iterrows()]
    catalog = load_semantic_catalog()
    catalog_version = str(catalog.get("version", "unknown"))
    catalog_fingerprint = hashlib.sha256(
        json.dumps(catalog, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    descriptor_hashes = [_descriptor_hash(value) for value in descriptors]
    reusable = _reusable_document_embeddings()
    document_vectors: list[np.ndarray | None] = [None] * len(unique)
    changed_indexes: list[int] = []
    reused_documents = 0
    for index, document_id in enumerate(unique["document_id"].astype(str)):
        previous = reusable.get(document_id)
        if previous is not None and previous[0] == descriptor_hashes[index]:
            document_vectors[index] = previous[1]
            reused_documents += 1
        else:
            changed_indexes.append(index)
    if require_full_document_reuse and changed_indexes:
        raise EmbeddingUnavailableError(
            "El modo prototypes-only requiere reutilizar todos los embeddings documentales; "
            f"{len(changed_indexes)} documentos necesitarian recalcularse."
        )
    if changed_indexes:
        changed_embeddings, _ = embed_texts(
            [descriptors[index] for index in changed_indexes],
            use_cache=False,
            timeout=OLLAMA_EMBEDDING_INDEX_TIMEOUT_SECONDS,
        )
        for result_index, document_index in enumerate(changed_indexes):
            document_vectors[document_index] = changed_embeddings[result_index]
    if any(vector is None for vector in document_vectors):
        raise EmbeddingUnavailableError("La actualizacion incremental dejo documentos sin vector.")
    document_embeddings = np.vstack(
        [vector for vector in document_vectors if vector is not None]
    ).astype(np.float32)
    concepts = list(catalog.get("concepts", []))
    prototype_embeddings, _ = embed_texts(
        [prototype_text(item) for item in concepts],
        use_cache=False,
        timeout=OLLAMA_EMBEDDING_INDEX_TIMEOUT_SECONDS,
    )
    source_fingerprint = hashlib.sha256(
        json.dumps(
            list(zip(unique["document_id"].astype(str), descriptors)),
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    version_seed = (
        f"{source_fingerprint}:{OLLAMA_EMBEDDING_MODEL}:{catalog_version}:"
        f"{catalog_fingerprint}:{SEMANTIC_DESCRIPTOR_VERSION}"
    )
    search_version = f"casei-semantic-{hashlib.sha256(version_seed.encode('utf-8')).hexdigest()[:12]}"
    target = SEARCH_REGISTRY_DIR / search_version
    target.mkdir(parents=True, exist_ok=True)

    np.save(target / "semantic_embeddings.npy", document_embeddings, allow_pickle=False)
    np.save(target / "semantic_filter_prototypes.npy", prototype_embeddings, allow_pickle=False)
    pd.DataFrame(
        {
            "document_id": unique["document_id"].astype(str),
            "descriptor_hash": descriptor_hashes,
        }
    ).to_csv(target / "semantic_document_ids.csv", index=False)
    shutil.copyfile(SEMANTIC_CATALOG_PATH, target / "semantic_catalog.json")
    metadata = {
        "search_version": search_version,
        "model": OLLAMA_EMBEDDING_MODEL,
        "dimension": int(document_embeddings.shape[1]),
        "documents": int(len(unique)),
        "prototypes": int(len(concepts)),
        "source_fingerprint": source_fingerprint,
        "catalog_version": catalog_version,
        "catalog_fingerprint": catalog_fingerprint,
        "descriptor_version": SEMANTIC_DESCRIPTOR_VERSION,
        "build_mode": "incremental" if reusable else "full",
        "reused_documents": reused_documents,
        "embedded_documents": len(changed_indexes),
    }
    (target / "semantic_index_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    manifest_files = [
        "semantic_embeddings.npy",
        "semantic_filter_prototypes.npy",
        "semantic_document_ids.csv",
        "semantic_catalog.json",
        "semantic_index_metadata.json",
    ]
    manifest = {
        **metadata,
        "files": {name: _sha256(target / name) for name in manifest_files},
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    CURRENT_SEARCH_INDEX_POINTER.write_text(
        json.dumps(
            {
                "current_search_version": search_version,
                "bundle_dir": str(target.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "manifest_path": str((target / "manifest.json").relative_to(PROJECT_ROOT)).replace("\\", "/"),
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    _INDEX_CACHE.pop(search_version, None)
    return manifest


def load_current_semantic_index() -> SemanticIndexBundle:
    if not CURRENT_SEARCH_INDEX_POINTER.exists():
        raise EmbeddingUnavailableError("No existe un indice semantico activo; debe generarse primero.")
    pointer = json.loads(CURRENT_SEARCH_INDEX_POINTER.read_text(encoding="utf-8"))
    version = str(pointer.get("current_search_version", ""))
    if not version:
        raise EmbeddingUnavailableError("El puntero del indice semantico es invalido.")
    cached = _INDEX_CACHE.get(version)
    if cached is not None:
        return cached

    target = PROJECT_ROOT / str(pointer.get("bundle_dir", ""))
    manifest_path = PROJECT_ROOT / str(pointer.get("manifest_path", ""))
    if not target.is_dir() or not manifest_path.exists():
        raise EmbeddingUnavailableError("El bundle del indice semantico no existe.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("model") != OLLAMA_EMBEDDING_MODEL:
        raise EmbeddingUnavailableError("El indice semantico activo usa otro modelo de embeddings.")
    for name, expected in manifest.get("files", {}).items():
        path = target / name
        if not path.exists() or not file_checksum_matches(path, expected):
            raise EmbeddingUnavailableError(f"Checksum invalido en el indice semantico: {name}")

    identifiers = pd.read_csv(target / "semantic_document_ids.csv")["document_id"].astype(str).tolist()
    document_embeddings = _normalize_rows(np.load(target / "semantic_embeddings.npy", allow_pickle=False))
    prototype_embeddings = _normalize_rows(np.load(target / "semantic_filter_prototypes.npy", allow_pickle=False))
    catalog = json.loads((target / "semantic_catalog.json").read_text(encoding="utf-8"))
    prototype_ids = [str(item["id"]) for item in catalog.get("concepts", [])]
    if len(identifiers) != len(document_embeddings) or len(prototype_ids) != len(prototype_embeddings):
        raise EmbeddingUnavailableError("El bundle semantico tiene IDs y vectores desalineados.")
    bundle = SemanticIndexBundle(
        version=version,
        model=str(manifest["model"]),
        document_ids=identifiers,
        document_embeddings=document_embeddings,
        prototype_ids=prototype_ids,
        prototype_embeddings=prototype_embeddings,
        catalog=catalog,
    )
    _INDEX_CACHE[version] = bundle
    return bundle


def semantic_search_documents(documents: pd.DataFrame, query: str) -> dict[str, Any]:
    bundle = load_current_semantic_index()
    expanded_query, expanded_concepts = semantic_query_text(query, bundle.catalog)
    query_matrix, cache_hit = embed_texts([expanded_query], use_cache=True)
    query_vector = query_matrix[0]
    index_by_id = {document_id: index for index, document_id in enumerate(bundle.document_ids)}
    available = documents[documents["document_id"].astype(str).isin(index_by_id)].drop_duplicates("document_id").copy()
    missing_count = int(documents["document_id"].nunique() - available["document_id"].nunique())
    if available.empty:
        raise EmbeddingUnavailableError("El indice semantico no contiene documentos del alcance autorizado.")

    positions = [index_by_id[str(value)] for value in available["document_id"]]
    scores = bundle.document_embeddings[positions] @ query_vector
    available["score_semantic"] = scores.astype(float)
    available = available[available["score_semantic"] >= SEMANTIC_MIN_SIMILARITY]
    available = available.sort_values(["score_semantic", "document_id"], ascending=[False, True]).reset_index(drop=True)
    available.insert(0, "rank_semantic", range(1, len(available) + 1))

    prototype_scores = bundle.prototype_embeddings @ query_vector
    hints = select_semantic_hints(
        bundle.catalog,
        bundle.prototype_ids,
        prototype_scores,
        expanded_concepts,
    )
    return {
        "results": available,
        "hints": hints,
        "metadata": {
            "model": bundle.model,
            "index_version": bundle.version,
            "cache_hit": cache_hit,
            "missing_documents": missing_count,
            "matches_above_threshold": int(len(available)),
            "query_expansion_concepts": expanded_concepts,
        },
    }


def reset_semantic_runtime_state() -> None:
    with _LOCK:
        _QUERY_CACHE.clear()
    _INDEX_CACHE.clear()
