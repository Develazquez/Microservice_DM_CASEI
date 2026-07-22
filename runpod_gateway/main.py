from __future__ import annotations

import hmac
import os

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException

from app.models.search_config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
    OLLAMA_WARMUP_TIMEOUT_SECONDS,
)
from app.models.search_query_schemas import EmbeddingRequest, EmbeddingResponse, InterpretationRequest, InterpretationResponse
from app.services.academic_semantic_embedding_service import request_direct_embeddings
from app.services.ollama_query_interpretation_service import request_direct_ollama


app = FastAPI(
    title="CASEI SLM Gateway",
    version="1.0.0",
    description="Gateway minimo y autenticado entre CASEI y Ollama. No recibe expedientes academicos.",
)


def require_gateway_key(x_casei_slm_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("CASEI_SLM_GATEWAY_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="CASEI_SLM_GATEWAY_API_KEY no configurada.")
    if not x_casei_slm_key or not hmac.compare_digest(x_casei_slm_key, expected):
        raise HTTPException(status_code=401, detail="Credencial SLM invalida.")


def ollama_models() -> list[str]:
    with httpx.Client(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
        response = client.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
    return [str(item.get("name")) for item in response.json().get("models", []) if item.get("name")]


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "casei-slm-gateway",
        "authentication_configured": bool(os.getenv("CASEI_SLM_GATEWAY_API_KEY", "").strip()),
    }


@app.get("/ready", dependencies=[Depends(require_gateway_key)])
def ready() -> dict[str, object]:
    try:
        models = ollama_models()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama no disponible: {exc}") from exc
    def available(required: str) -> bool:
        if required in models:
            return True
        return ":" not in required and any(name.split(":")[0] == required for name in models)

    missing = [model for model in [OLLAMA_MODEL, OLLAMA_EMBEDDING_MODEL] if not available(model)]
    if missing:
        raise HTTPException(status_code=503, detail=f"Modelos no disponibles: {', '.join(missing)}")
    return {"status": "ready", "models": [OLLAMA_MODEL, OLLAMA_EMBEDDING_MODEL]}


@app.post("/warmup", dependencies=[Depends(require_gateway_key)])
def warmup() -> dict[str, object]:
    request = InterpretationRequest(
        query="estudiantes con riesgo academico",
        catalogs={
            "programas": [],
            "perfiles": ["Riesgo academico moderado"],
            "estatus": [],
            "periodos": [],
            "cohortes": [],
            "clusters": [],
            "source_columns": [],
            "version": "warmup-v1",
        },
    )
    try:
        request_direct_ollama(request, timeout=OLLAMA_WARMUP_TIMEOUT_SECONDS)
        request_direct_embeddings(["busqueda academica semantica"], timeout=OLLAMA_WARMUP_TIMEOUT_SECONDS)
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"No fue posible calentar el modelo: {exc}") from exc
    return {"status": "ready", "models": [OLLAMA_MODEL, OLLAMA_EMBEDDING_MODEL]}


@app.post(
    "/interpret",
    response_model=InterpretationResponse,
    dependencies=[Depends(require_gateway_key)],
)
def interpret(request: InterpretationRequest) -> InterpretationResponse:
    try:
        interpretation = request_direct_ollama(request)
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Fallo de interpretacion SLM: {exc}") from exc
    return InterpretationResponse(interpretation=interpretation, model=OLLAMA_MODEL)


@app.post(
    "/embed",
    response_model=EmbeddingResponse,
    dependencies=[Depends(require_gateway_key)],
)
def embed(request: EmbeddingRequest) -> EmbeddingResponse:
    try:
        embeddings = request_direct_embeddings(request.texts)
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Fallo de embeddings: {exc}") from exc
    return EmbeddingResponse(model=OLLAMA_EMBEDDING_MODEL, embeddings=embeddings.tolist())
