from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.api_schemas import RunSegmentationRequest
from app.services.segmentation_api_service import (
    cluster_catalog,
    filtered_students,
    history_detail,
    history_summary,
    health_status,
    read_history,
    run_segmentation,
    search_students,
    segmentation_summary,
    student_detail,
    student_history,
)


router = APIRouter(prefix="/api/v1/segmentation", tags=["Segmentation"])


def http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
def api_health() -> dict:
    return health_status()


@router.post("/run")
def run(request: RunSegmentationRequest) -> dict:
    try:
        return run_segmentation(
            mode=request.mode,
            persist_model=request.persist_model,
            refresh_search_index=request.refresh_search_index,
            notes=request.notes,
        )
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/summary")
def summary() -> dict:
    try:
        return segmentation_summary()
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/students")
def students(
    perfil: str | None = Query(default=None),
    programa: str | None = Query(default=None),
    cluster: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        return filtered_students(
            perfil=perfil,
            programa=programa,
            cluster=cluster,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/students/{student_id}/history")
def student_inference_history(
    student_id: str,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    try:
        return student_history(student_id, limit=limit)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/students/{student_id}")
def student(student_id: str) -> dict:
    try:
        result = student_detail(student_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Student not found: {student_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Consulta BM25 por keywords academicas."),
    top_k: int = Query(default=10, ge=1, le=50),
) -> dict:
    try:
        return search_students(q, top_k=top_k)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/clusters")
def clusters() -> dict:
    try:
        return cluster_catalog()
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/history")
def history(
    limit: int = Query(default=20, ge=1, le=100),
    student_id: str | None = Query(default=None),
) -> dict:
    return {
        "summary": history_summary(),
        "items": read_history(limit=limit, student_id=student_id),
    }


@router.get("/history/{execution_id}")
def history_run(
    execution_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        result = history_detail(execution_id=execution_id, limit=limit, offset=offset)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Inference run not found: {execution_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(exc) from exc
