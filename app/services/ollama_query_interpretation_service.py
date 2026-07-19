from __future__ import annotations

from collections import OrderedDict
import json
import threading
import time

import httpx

from app.models.search_config import (
    OLLAMA_BASE_URL,
    OLLAMA_GATEWAY_API_KEY,
    OLLAMA_GATEWAY_URL,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TIMEOUT_SECONDS,
    SLM_CACHE_MAX_SIZE,
    SLM_CACHE_TTL_SECONDS,
    SLM_COOLDOWN_SECONDS,
    SLM_FAILURE_THRESHOLD,
)
from app.models.search_query_schemas import InterpretationRequest, QueryCatalogs, StructuredAcademicQuery


SYSTEM_PROMPT = """Eres un analizador de consultas academicas en espanol.
Devuelve exclusivamente el objeto definido por el JSON Schema.
Usa solo valores presentes en los catalogos. No inventes alumnos, columnas, programas o perfiles.
No generes SQL, codigo, operadores simbolicos, nombres de columnas ni diagnosticos.
normalized_query debe ser una frase natural corta y conservar la intencion original.
Las comparaciones numericas deben ir en promedio, asistencia, rezago o materias_reprobadas.
Ejemplo: "promedio menor a 70" usa promedio={"operator":"lt","value":70,"max_value":null}.
Un adjetivo sin cifra, como "rezago alto", se conserva como keyword y no inventa un umbral.
Extrae filtros solo cuando la consulta los expresa. Limita keywords y synonyms a ocho elementos cada uno."""


class SlmUnavailableError(RuntimeError):
    pass


_CACHE: OrderedDict[str, tuple[float, StructuredAcademicQuery]] = OrderedDict()
_LOCK = threading.Lock()
_CONSECUTIVE_FAILURES = 0
_COOLDOWN_UNTIL = 0.0


def _cache_key(query: str, catalogs: QueryCatalogs) -> str:
    return json.dumps(
        {"query": query.strip().lower(), "model": OLLAMA_MODEL, "catalog_version": catalogs.version},
        sort_keys=True,
        ensure_ascii=True,
    )


def _cached(key: str) -> StructuredAcademicQuery | None:
    now = time.monotonic()
    with _LOCK:
        item = _CACHE.get(key)
        if item is None:
            return None
        created_at, interpretation = item
        if now - created_at > SLM_CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        _CACHE.move_to_end(key)
        return interpretation.model_copy(deep=True)


def _store(key: str, interpretation: StructuredAcademicQuery) -> None:
    with _LOCK:
        _CACHE[key] = (time.monotonic(), interpretation.model_copy(deep=True))
        _CACHE.move_to_end(key)
        while len(_CACHE) > SLM_CACHE_MAX_SIZE:
            _CACHE.popitem(last=False)


def _ensure_circuit_available() -> None:
    if time.monotonic() < _COOLDOWN_UNTIL:
        remaining = max(1, round(_COOLDOWN_UNTIL - time.monotonic()))
        raise SlmUnavailableError(f"SLM temporalmente en cooldown ({remaining}s).")


def _record_success() -> None:
    global _CONSECUTIVE_FAILURES, _COOLDOWN_UNTIL
    with _LOCK:
        _CONSECUTIVE_FAILURES = 0
        _COOLDOWN_UNTIL = 0.0


def _record_failure(auth_failure: bool = False) -> None:
    global _CONSECUTIVE_FAILURES, _COOLDOWN_UNTIL
    with _LOCK:
        _CONSECUTIVE_FAILURES += 1
        if auth_failure:
            _COOLDOWN_UNTIL = time.monotonic() + 300
        elif _CONSECUTIVE_FAILURES >= SLM_FAILURE_THRESHOLD:
            _COOLDOWN_UNTIL = time.monotonic() + SLM_COOLDOWN_SECONDS


def build_prompt(request: InterpretationRequest) -> str:
    public_catalogs = request.catalogs.model_dump(exclude={"source_columns"})
    return (
        "Interpreta la consulta usando estos catalogos permitidos.\n"
        f"CATALOGOS={json.dumps(public_catalogs, ensure_ascii=True)}\n"
        f"CONSULTA={request.query.strip()}"
    )


def request_direct_ollama(
    request: InterpretationRequest,
    base_url: str = OLLAMA_BASE_URL,
    model: str = OLLAMA_MODEL,
    timeout: float = OLLAMA_TIMEOUT_SECONDS,
) -> StructuredAcademicQuery:
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": build_prompt(request),
        "stream": False,
        "think": False,
        "format": StructuredAcademicQuery.model_json_schema(),
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{base_url.rstrip('/')}/api/generate", json=payload)
        response.raise_for_status()
    content = response.json().get("response")
    if not content:
        raise SlmUnavailableError("Ollama devolvio una respuesta vacia.")
    return StructuredAcademicQuery.model_validate_json(content)


def request_gateway(request: InterpretationRequest) -> StructuredAcademicQuery:
    headers = {"X-CASEI-SLM-KEY": OLLAMA_GATEWAY_API_KEY} if OLLAMA_GATEWAY_API_KEY else {}
    with httpx.Client(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
        response = client.post(
            f"{OLLAMA_GATEWAY_URL}/interpret",
            json=request.model_dump(mode="json"),
            headers=headers,
        )
        response.raise_for_status()
    payload = response.json()
    return StructuredAcademicQuery.model_validate(payload.get("interpretation", payload))


def interpret_query(query: str, catalogs: QueryCatalogs) -> tuple[StructuredAcademicQuery, bool]:
    global _COOLDOWN_UNTIL
    key = _cache_key(query, catalogs)
    cached = _cached(key)
    if cached is not None:
        return cached, True
    _ensure_circuit_available()
    request = InterpretationRequest(query=query, catalogs=catalogs)
    try:
        interpretation = request_gateway(request) if OLLAMA_GATEWAY_URL else request_direct_ollama(request)
    except httpx.HTTPStatusError as exc:
        auth_failure = exc.response.status_code in {401, 403}
        _record_failure(auth_failure=auth_failure)
        raise SlmUnavailableError(f"Gateway SLM respondio HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, ValueError, SlmUnavailableError) as exc:
        _record_failure()
        raise SlmUnavailableError(f"No fue posible interpretar la consulta con el SLM: {exc}") from exc
    _record_success()
    _store(key, interpretation)
    return interpretation, False


def reset_runtime_state() -> None:
    global _CONSECUTIVE_FAILURES, _COOLDOWN_UNTIL
    with _LOCK:
        _CACHE.clear()
        _CONSECUTIVE_FAILURES = 0
        _COOLDOWN_UNTIL = 0.0
