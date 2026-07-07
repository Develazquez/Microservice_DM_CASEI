from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.segmentation_api_controller import router as segmentation_router
from app.services.segmentation_api_service import health_status


app = FastAPI(
    title="CASEI Academic Segmentation API",
    description=(
        "Microservicio local para segmentacion academica no supervisada. "
        "Los perfiles son apoyo tutorial y analitico, no diagnostico automatico definitivo."
    ),
    version="0.9.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(segmentation_router)


@app.get("/health", tags=["Health"])
def health() -> dict:
    return health_status()


@app.get("/", tags=["Health"])
def root() -> dict:
    status = health_status()
    return {
        "service": status.get("service", "academic-segmentation"),
        "status": status.get("status"),
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api_prefix": "/api/v1/segmentation",
    }
