from __future__ import annotations

import hashlib
import re
import time
from typing import Any

import pandas as pd

from app.models.search_config import CASEI_SEARCH_MODE, CASEI_SLM_ENABLED
from app.models.search_query_schemas import NumericCondition, QueryCatalogs, StructuredAcademicQuery
from app.services.academic_bm25_search_service import get_cached_index, normalize_text, tokenize
from app.services.ollama_query_interpretation_service import SlmUnavailableError, interpret_query


VALID_SEARCH_MODES = {"auto", "bm25", "slm"}
PII_PATTERN = re.compile(r"(?:\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|\b[a-z]{2,5}\d{6,}\b)", re.IGNORECASE)
COMPLEX_MARKERS = {
    "excepto", "sin", "no", "mayor", "menor", "entre", "desde", "hasta",
    "superior", "inferior", "por encima", "por debajo", "y ademas", "pero",
}
ACADEMIC_CRITERIA = {
    "promedio", "asistencia", "rezago", "reprobadas", "programa", "carrera",
    "perfil", "estatus", "periodo", "cohorte", "cluster", "sexo",
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
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:a|y|-)\s*\d+(?:\.\d+)?\b", normalized):
        return True
    criteria_count = sum(1 for criterion in ACADEMIC_CRITERIA if criterion in normalized)
    if criteria_count >= 2:
        return True
    query_tokens = set(tokenize(normalized))
    if not query_tokens or documents.empty:
        return False
    vocabulary: set[str] = set()
    for text in documents["search_text"].astype(str):
        vocabulary.update(tokenize(text))
    coverage = len(query_tokens & vocabulary) / len(query_tokens)
    return coverage < 0.5


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
) -> dict[str, Any]:
    started = time.perf_counter()
    selected_mode = (mode or CASEI_SEARCH_MODE or "auto").strip().lower()
    if selected_mode not in VALID_SEARCH_MODES:
        raise ValueError(f"Modo de busqueda no soportado: {selected_mode}")
    warnings: list[str] = []
    explicit_filters = {key: value for key, value in {"programa": programa, "perfil": perfil, "sexo": sexo}.items() if value}
    if sexo and "sexo" not in documents.columns:
        raise UnsupportedSourceFilterError("sexo")

    slm_requested = selected_mode == "slm" or (selected_mode == "auto" and requires_slm(query, documents))
    pii_detected = bool(PII_PATTERN.search(query))
    if pii_detected:
        slm_requested = False
        warnings.append("La consulta contiene un identificador y se proceso localmente sin enviarlo al SLM.")

    interpretation: StructuredAcademicQuery | None = None
    cached = False
    slm_started = time.perf_counter()
    processing_mode = "direct_bm25"
    if slm_requested and CASEI_SLM_ENABLED:
        catalogs = build_query_catalogs(documents)
        try:
            interpretation, cached = interpret_query(query, catalogs)
            interpretation, validation_warnings = validate_interpretation(interpretation, catalogs, query)
            warnings.extend(validation_warnings)
            processing_mode = "slm_bm25"
        except SlmUnavailableError as exc:
            processing_mode = "fallback_bm25"
            warnings.append(str(exc))
    elif slm_requested:
        processing_mode = "fallback_bm25" if selected_mode == "slm" else "direct_bm25"
        warnings.append("SLM deshabilitado; se utilizo BM25.")
    slm_ms = (time.perf_counter() - slm_started) * 1000

    inferred_filters: dict[str, Any] = {}
    if interpretation is not None:
        for field in [
            "programa", "perfil", "estatus", "periodo", "cohorte", "sexo", "cluster",
            "promedio", "asistencia", "rezago", "materias_reprobadas",
        ]:
            value = getattr(interpretation, field)
            if value is not None:
                inferred_filters[field] = value
    for key, explicit_value in explicit_filters.items():
        if key in inferred_filters and normalize_text(inferred_filters[key]) != normalize_text(explicit_value):
            warnings.append(f"El filtro explicito '{key}' prevalecio sobre el valor inferido por el SLM.")
        inferred_filters[key] = explicit_value
    if inferred_filters.get("sexo") and "sexo" not in documents.columns:
        raise UnsupportedSourceFilterError("sexo")

    filter_started = time.perf_counter()
    candidates = apply_search_filters(documents, inferred_filters)
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
    if candidates.empty:
        results = candidates.copy()
    else:
        results = get_cached_index(candidates).search(normalized_query, top_k=top_k, weighted_terms=weighted_terms)
    bm25_ms = (time.perf_counter() - bm25_started) * 1000
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
            "timings_ms": {
                "slm": round(slm_ms, 3),
                "filters": round(filter_ms, 3),
                "bm25": round(bm25_ms, 3),
                "total": round((time.perf_counter() - started) * 1000, 3),
            },
            "warnings": warnings,
        },
    }
