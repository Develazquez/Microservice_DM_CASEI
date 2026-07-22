from __future__ import annotations

import hashlib
import re
import time
from typing import Any

import pandas as pd

from app.models.search_config import (
    CASEI_SEARCH_MODE,
    CASEI_SEARCH_RETRIEVAL_MODE,
    CASEI_SEMANTIC_SEARCH_ENABLED,
    CASEI_SLM_ENABLED,
    SEARCH_EXPLAIN_DEFAULT,
    SEMANTIC_TOP_K,
)
from app.models.search_query_schemas import NumericCondition, QueryCatalogs, StructuredAcademicQuery
from app.services.academic_bm25_search_service import get_cached_index, normalize_text, tokenize
from app.services.academic_semantic_embedding_service import EmbeddingUnavailableError, semantic_search_documents
from app.services.hybrid_search_ranking_service import reciprocal_rank_fusion
from app.services.ollama_query_interpretation_service import SlmUnavailableError, interpret_query
from app.services.search_conclusion_matrix_service import ConclusionMatrixBuilder


VALID_SEARCH_MODES = {"auto", "bm25", "slm"}
VALID_RETRIEVAL_MODES = {"hybrid", "bm25", "semantic"}
PII_PATTERN = re.compile(r"(?:\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|\b[a-z]{2,5}\d{6,}\b)", re.IGNORECASE)
COMPLEX_MARKERS = {
    "excepto", "sin", "mayor", "menor", "entre", "desde", "hasta",
    "superior", "inferior", "por encima", "por debajo", "y ademas", "pero", "pese a",
}
NEGATION_FILTER_MARKERS = {
    "no criticos", "no tengan", "no mostrar", "no sean", "todos menos",
}
ACADEMIC_CRITERIA = {
    "promedio", "asistencia", "rezago", "reprobadas", "programa", "carrera",
    "perfil", "estatus", "periodo", "cohorte", "cluster", "sexo", "incidencias",
    "tutorias", "seguimiento", "avance", "riesgo", "mujeres", "hombres",
}
NUMBER_WORDS = {"cero", "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"}
AMBIGUOUS_OR_UNSUPPORTED_MARKERS = {
    "muchas alertas", "varias dificultades", "los complicados", "los mejores",
    "los atrasados", "los ausentes", "los regulares", "los de seguimiento",
    "bajo avance", "mejoraron", "empeoraron", "los que preocupan", "atrasados y",
    "con beca", "que trabajan",
    "discapacidad", "viven lejos", "problemas familiares", "apoyo psicologico",
    "con deuda", "transporte escolar",
}
DIRECT_LEXICAL_PHRASES = {
    "riesgo academico", "promedio bajo", "asistencia baja", "rezago alto",
    "seguimiento preventivo", "materias reprobadas", "con tutorias",
    "con incidencias", "alto rendimiento", "sin incidencias",
    "sin materias reprobadas",
}


class UnsupportedSourceFilterError(ValueError):
    def __init__(self, filter_name: str) -> None:
        self.filter_name = filter_name
        super().__init__(f"filter_not_supported_by_source: {filter_name}")


def _unique_strings(documents: pd.DataFrame, column: str) -> list[str]:
    if column not in documents.columns:
        return []
    return sorted({str(value).strip() for value in documents[column].dropna() if str(value).strip()})


def build_query_catalogs(documents: pd.DataFrame) -> QueryCatalogs:
    payload = {
        "programas": _unique_strings(documents, "programa"),
        "perfiles": _unique_strings(documents, "perfil_sugerido"),
        "estatus": _unique_strings(documents, "estatus_academico"),
        "periodos": _unique_strings(documents, "id_periodo"),
        "cohortes": _unique_strings(documents, "cohorte"),
        "clusters": sorted({int(value) for value in documents.get("cluster", pd.Series(dtype=int)).dropna()}),
        "source_columns": sorted(str(column) for column in documents.columns),
    }
    serialized = repr(payload).encode("utf-8")
    payload["version"] = hashlib.sha256(serialized).hexdigest()[:16]
    return QueryCatalogs(**payload)


def requires_slm(query: str, documents: pd.DataFrame) -> bool:
    normalized = normalize_text(query)
    if PII_PATTERN.search(normalized):
        return False
    if any(marker in normalized for marker in COMPLEX_MARKERS):
        return True
    if any(marker in normalized for marker in NEGATION_FILTER_MARKERS):
        return True
    if any(marker in normalized for marker in AMBIGUOUS_OR_UNSUPPORTED_MARKERS):
        return True
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:a|y|-)\s*\d+(?:\.\d+)?\b", normalized):
        return True
    query_tokens = set(tokenize(normalized))
    if re.search(r"\d", normalized) and any(criterion in normalized for criterion in ACADEMIC_CRITERIA):
        return True
    if query_tokens & NUMBER_WORDS and any(criterion in normalized for criterion in ACADEMIC_CRITERIA):
        return True
    criteria_count = sum(1 for criterion in ACADEMIC_CRITERIA if criterion in normalized)
    if criteria_count >= 2:
        return True
    if " con " in f" {normalized} " and criteria_count:
        program_tokens = {
            token
            for value in documents.get("programa", pd.Series(dtype=str)).dropna().astype(str)
            for token in tokenize(value)
            if len(token) >= 6
        }
        if query_tokens & program_tokens:
            return True
    return False


def lexical_coverage(query: str, documents: pd.DataFrame) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens or documents.empty or "search_text" not in documents.columns:
        return 0.0
    vocabulary = set(get_cached_index(documents).idf)
    return len(query_tokens & vocabulary) / len(query_tokens)


def requires_semantic(query: str, documents: pd.DataFrame) -> bool:
    normalized = normalize_text(query)
    if PII_PATTERN.search(normalized):
        return False
    query_tokens = set(tokenize(normalized))
    has_numeric_value = bool(re.search(r"\d", normalized)) or bool(query_tokens & NUMBER_WORDS)
    if has_numeric_value and any(criterion in normalized for criterion in ACADEMIC_CRITERIA):
        return False
    if normalized in DIRECT_LEXICAL_PHRASES:
        return False
    if any(marker in normalized for marker in AMBIGUOUS_OR_UNSUPPORTED_MARKERS):
        return True
    if " con " in f" {normalized} ":
        criteria_count = sum(1 for criterion in ACADEMIC_CRITERIA if criterion in normalized)
        program_tokens = {
            token
            for value in documents.get("programa", pd.Series(dtype=str)).dropna().astype(str)
            for token in tokenize(value)
            if len(token) >= 6
        }
        if criteria_count >= 2 or (criteria_count and query_tokens & program_tokens):
            return True
    if not query_tokens:
        return False
    coverage = lexical_coverage(normalized, documents)
    if len(query_tokens) <= 3 and coverage >= 0.75:
        return False
    return coverage < 0.75 or len(query_tokens) >= 4


def requires_structured_reasoning(query: str) -> bool:
    normalized = normalize_text(query)
    if any(marker in normalized for marker in COMPLEX_MARKERS):
        return True
    if re.search(r"\b\d+(?:\.\d+)?\b", normalized):
        return True
    return sum(1 for criterion in ACADEMIC_CRITERIA if criterion in normalized) >= 2


def _canonical(value: str | None, allowed: list[str]) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value).strip()
    matches = [item for item in allowed if normalize_text(item).strip() == normalized]
    return matches[0] if len(matches) == 1 else None


def validate_interpretation(
    interpretation: StructuredAcademicQuery,
    catalogs: QueryCatalogs,
    original_query: str,
) -> tuple[StructuredAcademicQuery, list[str]]:
    warnings: list[str] = []
    categorical = {
        "programa": catalogs.programas,
        "perfil": catalogs.perfiles,
        "estatus": catalogs.estatus,
        "periodo": catalogs.periodos,
        "cohorte": catalogs.cohortes,
    }
    updates: dict[str, Any] = {}
    for field, allowed in categorical.items():
        value = getattr(interpretation, field)
        if value is None:
            continue
        canonical = _canonical(str(value), allowed)
        if canonical is None:
            updates[field] = None
            warnings.append(f"Filtro inferido '{field}' descartado por no pertenecer al catalogo actual.")
        else:
            updates[field] = canonical
    if interpretation.cluster is not None and interpretation.cluster not in catalogs.clusters:
        updates["cluster"] = None
        warnings.append("Filtro inferido 'cluster' descartado por no pertenecer al catalogo actual.")
    normalized_query = normalize_text(original_query)
    clauses = re.split(r"\s+y\s+|[,;]", normalized_query)
    numeric_terms = {
        "promedio": ("promedio", "calificacion"),
        "asistencia": ("asistencia", "asistencias"),
        "rezago": ("rezago", "atraso"),
        "materias_reprobadas": ("reprobadas", "reprobacion"),
    }
    for field, terms in numeric_terms.items():
        if getattr(interpretation, field) is None:
            continue
        supported = any(any(term in clause for term in terms) and bool(re.search(r"\d", clause)) for clause in clauses)
        if not supported:
            updates[field] = None
            warnings.append(f"Condicion numerica '{field}' descartada porque la consulta no proporciona una cifra.")
    return interpretation.model_copy(update=updates), warnings


def _numeric_mask(series: pd.Series, condition: NumericCondition) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    operations = {
        "lt": numeric < condition.value,
        "lte": numeric <= condition.value,
        "eq": numeric == condition.value,
        "gte": numeric >= condition.value,
        "gt": numeric > condition.value,
    }
    if condition.operator == "between":
        return numeric.between(condition.value, float(condition.max_value), inclusive="both")
    return operations[condition.operator]


def apply_search_filters(documents: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    result = documents
    column_map = {
        "programa": "programa",
        "perfil": "perfil_sugerido",
        "estatus": "estatus_academico",
        "periodo": "id_periodo",
        "cohorte": "cohorte",
        "sexo": "sexo",
        "cluster": "cluster",
    }
    for name, column in column_map.items():
        value = filters.get(name)
        if value is None:
            continue
        if column not in result.columns:
            raise UnsupportedSourceFilterError(name)
        if name == "cluster":
            result = result[pd.to_numeric(result[column], errors="coerce") == int(value)]
        elif name == "sexo":
            result = result[result[column].fillna("").astype(str).str.upper() == str(value).upper()]
        else:
            target = normalize_text(value)
            result = result[result[column].fillna("").astype(str).map(normalize_text).str.contains(target, regex=False)]
    numeric_map = {
        "promedio": "promedio_general",
        "asistencia": "porcentaje_asistencia",
        "rezago": "rezago_materias",
        "materias_reprobadas": "materias_reprobadas",
    }
    for name, column in numeric_map.items():
        condition = filters.get(name)
        if condition is not None:
            if column not in result.columns:
                raise UnsupportedSourceFilterError(name)
            result = result[_numeric_mask(result[column], condition)]
    return result


def search_academic_documents(
    documents: pd.DataFrame,
    query: str,
    top_k: int,
    mode: str | None = None,
    programa: str | None = None,
    perfil: str | None = None,
    sexo: str | None = None,
    retrieval: str | None = None,
    explain: bool | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    selected_mode = (mode or CASEI_SEARCH_MODE or "auto").strip().lower()
    if selected_mode not in VALID_SEARCH_MODES:
        raise ValueError(f"Modo de busqueda no soportado: {selected_mode}")
    selected_retrieval = (retrieval or CASEI_SEARCH_RETRIEVAL_MODE or "hybrid").strip().lower()
    if selected_retrieval not in VALID_RETRIEVAL_MODES:
        raise ValueError(f"Recuperacion no soportada: {selected_retrieval}")
    if selected_mode == "bm25":
        selected_retrieval = "bm25"
    explain_enabled = SEARCH_EXPLAIN_DEFAULT if explain is None else bool(explain)
    matrix = ConclusionMatrixBuilder(enabled=True)
    warnings: list[str] = []
    explicit_filters = {key: value for key, value in {"programa": programa, "perfil": perfil, "sexo": sexo}.items() if value}
    if sexo and "sexo" not in documents.columns:
        raise UnsupportedSourceFilterError("sexo")

    pii_detected = bool(PII_PATTERN.search(query))
    matrix.add(
        "authorized_scope",
        "Alcance aplicado por el servicio antes de la recuperacion.",
        "access_control",
        "apply",
        confidence=1.0,
        candidates_before=len(documents),
        candidates_after=len(documents),
    )

    semantic_requested = (
        selected_retrieval != "bm25"
        and CASEI_SEMANTIC_SEARCH_ENABLED
        and (selected_retrieval == "semantic" or requires_semantic(query, documents))
    )
    semantic_result: dict[str, Any] | None = None
    semantic_hints = []
    semantic_cache_hit = False
    semantic_failed = False
    semantic_started = time.perf_counter()
    if pii_detected:
        semantic_requested = False
    if semantic_requested:
        try:
            semantic_result = semantic_search_documents(documents, query)
            semantic_hints = semantic_result["hints"]
            semantic_cache_hit = bool(semantic_result["metadata"].get("cache_hit"))
            for hint in semantic_hints:
                matrix.add(
                    hint.concept_id,
                    hint.label,
                    "semantic_similarity",
                    "rank",
                    confidence=hint.similarity,
                    catalog_match=True,
                    candidates_before=len(documents),
                    candidates_after=len(documents),
                )
        except EmbeddingUnavailableError as exc:
            semantic_result = None
            semantic_failed = True
            warnings.append(str(exc))
    elif selected_retrieval == "semantic" and not CASEI_SEMANTIC_SEARCH_ENABLED:
        warnings.append("Busqueda semantica deshabilitada; se utilizo BM25.")
    semantic_prepare_ms = (time.perf_counter() - semantic_started) * 1000

    slm_requested = selected_mode == "slm" or (selected_mode == "auto" and requires_slm(query, documents))
    if selected_mode == "auto" and semantic_result is not None and semantic_hints and not requires_structured_reasoning(query):
        slm_requested = False
    if pii_detected:
        slm_requested = False
        warnings.append("La consulta contiene un identificador y se proceso localmente sin enviarlo a modelos.")

    interpretation: StructuredAcademicQuery | None = None
    cached = False
    slm_started = time.perf_counter()
    slm_failed = False
    if slm_requested and CASEI_SLM_ENABLED:
        catalogs = build_query_catalogs(documents)
        try:
            interpretation, cached = interpret_query(query, catalogs, semantic_hints=semantic_hints)
            interpretation, validation_warnings = validate_interpretation(interpretation, catalogs, query)
            warnings.extend(validation_warnings)
        except SlmUnavailableError as exc:
            slm_failed = True
            warnings.append(str(exc))
    elif slm_requested:
        slm_failed = selected_mode == "slm"
        warnings.append("SLM deshabilitado; se utilizo BM25.")
    slm_ms = (time.perf_counter() - slm_started) * 1000

    inferred_filters: dict[str, Any] = {}
    filter_sources: dict[str, str] = {}
    if interpretation is not None:
        for field in [
            "programa", "perfil", "estatus", "periodo", "cohorte", "sexo", "cluster",
            "promedio", "asistencia", "rezago", "materias_reprobadas",
        ]:
            value = getattr(interpretation, field)
            if value is not None:
                inferred_filters[field] = value
                filter_sources[field] = "qwen"
    for key, explicit_value in explicit_filters.items():
        if key in inferred_filters and normalize_text(inferred_filters[key]) != normalize_text(explicit_value):
            warnings.append(f"El filtro explicito '{key}' prevalecio sobre el valor inferido por el SLM.")
        inferred_filters[key] = explicit_value
        filter_sources[key] = "explicit_endpoint"
    if inferred_filters.get("sexo") and "sexo" not in documents.columns:
        raise UnsupportedSourceFilterError("sexo")

    filter_started = time.perf_counter()
    candidates = documents.copy()
    filter_order = [
        "programa", "perfil", "estatus", "periodo", "cohorte", "sexo", "cluster",
        "promedio", "asistencia", "rezago", "materias_reprobadas",
    ]
    for filter_name in filter_order:
        if filter_name not in inferred_filters:
            continue
        before = len(candidates)
        value = inferred_filters[filter_name]
        candidates = apply_search_filters(candidates, {filter_name: value})
        matrix.add(
            filter_name,
            str(value.model_dump() if isinstance(value, NumericCondition) else value),
            filter_sources.get(filter_name, "qwen"),
            "apply",
            confidence=(interpretation.confidence_by_field.get(filter_name) if interpretation else None),
            catalog_match=not isinstance(value, NumericCondition),
            candidates_before=before,
            candidates_after=len(candidates),
        )
    filter_ms = (time.perf_counter() - filter_started) * 1000
    normalized_query = interpretation.normalized_query if interpretation else query.strip()
    weighted_terms: dict[str, float] = {}
    expansion_terms: list[str] = []
    if interpretation is not None:
        for term in interpretation.keywords[:8]:
            weighted_terms[term] = 1.5
            expansion_terms.append(term)
        for term in interpretation.synonyms[:8]:
            weighted_terms[term] = 0.75
            expansion_terms.append(term)
        for field in ["programa", "perfil", "estatus"]:
            value = inferred_filters.get(field)
            if value:
                weighted_terms[str(value)] = 2.0

    bm25_started = time.perf_counter()
    bm25_results = candidates.iloc[0:0].copy()
    bm25_enabled = selected_retrieval != "semantic" or semantic_result is None
    if not candidates.empty and bm25_enabled:
        bm25_results = get_cached_index(candidates).search(
            normalized_query,
            top_k=max(top_k, SEMANTIC_TOP_K),
            weighted_terms=weighted_terms,
        )
    bm25_ms = (time.perf_counter() - bm25_started) * 1000

    semantic_rank_started = time.perf_counter()
    semantic_results = candidates.iloc[0:0].copy()
    if semantic_result is not None and not candidates.empty:
        candidate_ids = set(candidates["document_id"].astype(str))
        semantic_results = semantic_result["results"]
        semantic_results = semantic_results[semantic_results["document_id"].astype(str).isin(candidate_ids)].copy()
        semantic_results = semantic_results.sort_values(
            ["score_semantic", "document_id"], ascending=[False, True]
        ).reset_index(drop=True)
        if "rank_semantic" in semantic_results.columns:
            semantic_results = semantic_results.drop(columns="rank_semantic")
        semantic_results.insert(0, "rank_semantic", range(1, len(semantic_results) + 1))
    semantic_rank_ms = (time.perf_counter() - semantic_rank_started) * 1000

    fusion_started = time.perf_counter()
    if selected_retrieval == "semantic" and not semantic_results.empty:
        results = reciprocal_rank_fusion(candidates, candidates.iloc[0:0], semantic_results, top_k)
    elif not semantic_results.empty:
        results = reciprocal_rank_fusion(candidates, bm25_results, semantic_results, top_k)
    else:
        results = bm25_results.head(top_k).copy()
    fusion_ms = (time.perf_counter() - fusion_started) * 1000

    if interpretation is not None and semantic_result is not None:
        processing_mode = "slm_semantic_bm25"
    elif interpretation is not None:
        processing_mode = "slm_bm25"
    elif semantic_result is not None:
        processing_mode = "fallback_semantic_bm25" if slm_failed else "semantic_bm25"
    elif semantic_failed or slm_failed or (slm_requested and not CASEI_SLM_ENABLED):
        processing_mode = "fallback_bm25"
    else:
        processing_mode = "direct_bm25"

    routing_reasons = []
    if pii_detected:
        routing_reasons.append("identifier_detected")
    if requires_structured_reasoning(query):
        routing_reasons.append("structured_criteria")
    if requires_semantic(query, documents):
        routing_reasons.append("semantic_or_low_lexical_coverage")
    semantic_metadata = semantic_result["metadata"] if semantic_result is not None else {
        "model": None,
        "index_version": None,
        "cache_hit": semantic_cache_hit,
    }
    return {
        "results": results,
        "metadata": {
            "processing_mode": processing_mode,
            "normalized_query": normalized_query,
            "applied_filters": {
                key: value.model_dump() if isinstance(value, NumericCondition) else value
                for key, value in inferred_filters.items()
            },
            "expansion_terms": list(dict.fromkeys(expansion_terms))[:16],
            "candidate_count": int(len(candidates)),
            "slm_cache_hit": cached,
            "routing": {
                "requires_slm": bool(slm_requested),
                "requires_semantic": bool(semantic_requested),
                "retrieval": selected_retrieval,
                "reasons": routing_reasons,
            },
            "retrieval_mode": selected_retrieval,
            "semantic_metadata": semantic_metadata,
            "semantic_hints": [item.model_dump() for item in semantic_hints],
            "conclusion_matrix": matrix.export() if explain_enabled else [],
            "timings_ms": {
                "routing_and_embedding": round(semantic_prepare_ms, 3),
                "slm": round(slm_ms, 3),
                "filters": round(filter_ms, 3),
                "bm25": round(bm25_ms, 3),
                "semantic": round(semantic_rank_ms, 3),
                "fusion": round(fusion_ms, 3),
                "total": round((time.perf_counter() - started) * 1000, 3),
            },
            "warnings": warnings,
        },
    }
