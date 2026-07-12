from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in managed runtimes
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.segmentation_api_controller import router as segmentation_router
from app.models.api_schemas import HealthResponse, RootResponse
from app.services.segmentation_api_service import health_status


OPENAPI_DESCRIPTION = """
API local para segmentacion academica no supervisada de CASEI.

El servicio carga artefactos locales versionados, expone perfiles K-Means, consultas BM25,
historial de inferencias y operaciones de ejecucion local del pipeline.

Aviso academico: los clusters son apoyo tutorial y analitico. No representan un diagnostico
automatico definitivo ni sustituyen la validacion de tutores o coordinadores.
"""

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Estado general del microservicio y enlaces de documentacion.",
    },
    {
        "name": "Segmentacion academica",
        "description": "Endpoints versionados para resumen, alumnos, clusters, busqueda, ejecucion e historial.",
    },
    {
        "name": "LLM y RAG",
        "description": "Contrato de contexto academico controlado para futura integracion con tutor inteligente.",
    },
    {
        "name": "Sincronizacion Supabase",
        "description": "Lectura controlada de datos academicos reales desde Supabase PostgreSQL.",
    },
]

LOCAL_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]


def _csv_env(name: str) -> list[str]:
    raw_value = os.getenv(name, "")
    return [value.strip().rstrip("/") for value in raw_value.split(",") if value.strip()]


def _normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    url = value.strip().rstrip("/")
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def _cors_origins() -> list[str]:
    configured = _csv_env("CASEI_CORS_ORIGINS")
    if configured:
        return configured
    origins = [*LOCAL_CORS_ORIGINS]
    web_url = _normalize_url(os.getenv("CASEI_WEB_URL") or os.getenv("NEXT_PUBLIC_SITE_URL"))
    if web_url and web_url not in origins:
        origins.append(web_url)
    return origins


def _openapi_servers() -> list[dict[str, str]]:
    servers = [
        {"url": "http://127.0.0.1:8000", "description": "Servidor local por defecto"},
        {"url": "http://localhost:8000", "description": "Alias local"},
    ]
    public_url = _normalize_url(os.getenv("CASEI_API_PUBLIC_URL") or os.getenv("VERCEL_URL"))
    if public_url:
        servers.insert(0, {"url": public_url, "description": "Despliegue publico"})
    return servers


app = FastAPI(
    title="CASEI Academic Segmentation API",
    summary="Microservicio local de mineria de datos y segmentacion academica.",
    description=OPENAPI_DESCRIPTION,
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
    servers=_openapi_servers(),
    contact={
        "name": "CASEI local academic analytics",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=os.getenv("CASEI_CORS_ORIGIN_REGEX"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(segmentation_router)


@app.get(
    "/health",
    tags=["Health"],
    response_model=HealthResponse,
    summary="Verificar salud general del servicio",
    description="Health check general; valida disponibilidad del bundle activo y contrato de carga.",
)
def health() -> HealthResponse:
    return health_status()


@app.get(
    "/",
    tags=["Health"],
    response_model=RootResponse,
    summary="Mostrar enlaces principales del servicio",
    description="Devuelve rutas utiles para Swagger, OpenAPI y prefijo versionado de la API.",
)
def root() -> RootResponse:
    status = health_status()
    return {
        "service": status.get("service", "academic-segmentation"),
        "status": status.get("status"),
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api_prefix": "/api/v1/segmentation",
    }
