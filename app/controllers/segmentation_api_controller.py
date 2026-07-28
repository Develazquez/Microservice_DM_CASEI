from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.api_schemas import (
    ClusterCatalogResponse,
    ActiveModelResponse,
    ErrorResponse,
    HealthResponse,
    HistoryResponse,
    HistoryRunResponse,
    LlmContextContractResponse,
    MlJobCreateRequest,
    MlJobResponse,
    ModelActivationResponse,
    RagDocumentsResponse,
    RunSegmentationRequest,
    RunSegmentationResponse,
    SearchResponse,
    SegmentationSummaryResponse,
    StudentDetailResponse,
    StudentHistoryResponse,
    StudentLlmContextResponse,
    StudentListResponse,
    SupabaseResultsSyncRequest,
    SupabaseResultsSyncResponse,
    SupabasePromoteRequest,
    SupabasePromoteResponse,
    SupabaseSyncRequest,
    SupabaseSyncResponse,
    SupabaseSyncStatusResponse,
)
from app.services.llm_context_service import (
    context_contract,
    rag_documents,
    student_llm_context,
)
from app.services.ml_job_service import active_model, cancel_job, enqueue_job, get_job
from app.services.candidate_model_service import activate_candidate_model
from app.services.academic_search_orchestrator_service import UnsupportedSourceFilterError
from app.services.security_audit_service import (
    AuthorizationError,
    audit_context_access,
    audit_items_access,
    require_student_access,
)
from app.services.supabase_auth_service import (
    AuthenticationError,
    require_roles,
    security_context_from_request,
)
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
from app.services.supabase_results_sync_service import sync_results_to_supabase
from app.services.supabase_sync_service import (
    promote_supabase_preview,
    supabase_sync_status,
    sync_from_supabase,
)


ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Solicitud invalida o parametros no soportados."},
    404: {"model": ErrorResponse, "description": "Recurso no encontrado."},
    422: {"model": ErrorResponse, "description": "Filtro no disponible en la fuente de datos activa."},
    503: {"model": ErrorResponse, "description": "Artefactos locales requeridos no disponibles."},
}


router = APIRouter(prefix="/cacei/segmentation", tags=["Segmentacion academica"])


def http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, AuthorizationError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, UnsupportedSourceFilterError):
        return HTTPException(
            status_code=422,
            detail={"code": "filter_not_supported_by_source", "filter": exc.filter_name},
        )
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar salud del bundle de segmentacion",
    description="Valida que el bundle activo pueda cargarse desde `artifacts/current_model.json` y que sus archivos pasen el contrato de carga.",
    responses={503: {"model": ErrorResponse, "description": "No se pudo cargar el bundle local."}},
)
def api_health() -> HealthResponse:
    return health_status()


@router.post(
    "/run",
    response_model=RunSegmentationResponse,
    summary="Ejecutar o validar segmentacion local",
    description=(
        "`load_existing` valida el modelo persistido y registra una corrida de inferencia. "
        "`retrain_local` recalcula fases 2-8 con archivos locales y despues persiste inferencias."
    ),
    responses=ERROR_RESPONSES,
)
def run(payload: RunSegmentationRequest, request: Request) -> RunSegmentationResponse:
    try:
        context = security_context_from_request(request)
        require_roles(context, "director")
        return run_segmentation(
            mode=payload.mode,
            persist_model=payload.persist_model,
            refresh_search_index=payload.refresh_search_index,
            notes=payload.notes,
        )
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/summary",
    response_model=SegmentationSummaryResponse,
    summary="Obtener resumen institucional de segmentacion",
    description="Devuelve metricas del modelo, distribucion de perfiles, programas y conteos de seguimiento.",
    responses=ERROR_RESPONSES,
)
def summary(request: Request) -> SegmentationSummaryResponse:
    try:
        context = security_context_from_request(request)
        return segmentation_summary(security_context=context)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/context/contract",
    response_model=LlmContextContractResponse,
    tags=["LLM y RAG"],
    summary="Consultar contrato de contexto para LLM/RAG",
    description=(
        "Describe campos, roles, limites de uso y controles esperados para que un futuro tutor "
        "inteligente use el perfil academico como contexto controlado."
    ),
    responses=ERROR_RESPONSES,
)
def llm_context_contract(request: Request) -> LlmContextContractResponse:
    try:
        security_context_from_request(request)
        return context_contract()
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/sync/status",
    response_model=SupabaseSyncStatusResponse,
    tags=["Sincronizacion Supabase"],
    summary="Consultar configuracion de sincronizacion Supabase",
    description="Indica si el microservicio tiene variables suficientes para leer datos academicos desde Supabase.",
    responses=ERROR_RESPONSES,
)
def sync_status(request: Request) -> SupabaseSyncStatusResponse:
    try:
        context = security_context_from_request(request)
        require_roles(context, "director")
        return supabase_sync_status()
    except Exception as exc:
        raise http_error(exc) from exc


@router.post(
    "/sync/from-supabase",
    response_model=SupabaseSyncResponse,
    tags=["Sincronizacion Supabase"],
    summary="Sincronizar datos academicos desde Supabase",
    description=(
        "Lee tablas academicas de Supabase con service role, genera un snapshot local y una vista "
        "alumno-periodo preliminar. No reemplaza el dataset activo hasta validacion."
    ),
    responses=ERROR_RESPONSES,
)
def sync_from_supabase_endpoint(payload: SupabaseSyncRequest, request: Request) -> SupabaseSyncResponse:
    try:
        context = security_context_from_request(request)
        require_roles(context, "director")
        return sync_from_supabase(limit=payload.limit, write_preview=payload.write_preview, tenant_id=context.tenant_id)
    except Exception as exc:
        raise http_error(exc) from exc


@router.post("/jobs", response_model=MlJobResponse, summary="Encolar procesamiento de segmentacion")
def create_ml_job(payload: MlJobCreateRequest, request: Request) -> MlJobResponse:
    try:
        context = security_context_from_request(request)
        return enqueue_job(
            context=context,
            operation=payload.operation,
            trigger_source=payload.trigger_source,
            source_hash=payload.source_hash,
            scope=payload.scope,
            source_batch_id=payload.source_batch_id,
            student_profile_ids=payload.student_profile_ids,
            notes=payload.notes,
        )
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/jobs/{execution_id}", response_model=MlJobResponse, summary="Consultar estado de trabajo ML")
def ml_job(execution_id: str, request: Request) -> MlJobResponse:
    try:
        return get_job(execution_id, security_context_from_request(request))
    except Exception as exc:
        raise http_error(exc) from exc


@router.post("/jobs/{execution_id}/cancel", response_model=MlJobResponse, summary="Cancelar trabajo ML pendiente")
def cancel_ml_job(execution_id: str, request: Request) -> MlJobResponse:
    try:
        return cancel_job(execution_id, security_context_from_request(request))
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/models/active", response_model=ActiveModelResponse, summary="Consultar modelo activo")
def active_model_endpoint(request: Request) -> ActiveModelResponse:
    try:
        security_context_from_request(request)
        return active_model()
    except Exception as exc:
        raise http_error(exc) from exc


@router.post(
    "/models/{model_version}/activate",
    response_model=ModelActivationResponse,
    summary="Activar modelo candidato y encolar reinferencia",
)
def activate_model_endpoint(model_version: str, request: Request) -> ModelActivationResponse:
    try:
        context = security_context_from_request(request)
        require_roles(context, "director")
        activation = activate_candidate_model(model_version)
        try:
            job = enqueue_job(
                context=context,
                operation="inference",
                trigger_source="model_activation",
                scope={"model_version": model_version, "full_population": True},
                notes=f"Reinferencia posterior a activacion de {model_version}",
            )
        except Exception:
            previous = activation.get("previous_model_version")
            if previous and previous != model_version:
                activate_candidate_model(str(previous))
            raise
        return {**activation, "inference_job": job}
    except Exception as exc:
        raise http_error(exc) from exc


@router.post(
    "/sync/promote",
    response_model=SupabasePromoteResponse,
    tags=["Sincronizacion Supabase"],
    summary="Promover snapshot validado como dataset activo",
    responses=ERROR_RESPONSES,
)
def promote_supabase_endpoint(payload: SupabasePromoteRequest, request: Request) -> SupabasePromoteResponse:
    try:
        context = security_context_from_request(request)
        require_roles(context, "director")
        return promote_supabase_preview(payload.source_hash, reviewed_by=context.user_id)
    except Exception as exc:
        raise http_error(exc) from exc




@router.post(
    "/sync/to-supabase",
    response_model=SupabaseResultsSyncResponse,
    tags=["Sincronizacion Supabase"],
    summary="Publicar resultados ML en Supabase",
    description=(
        "Guarda version de modelo, corrida, features alumno-periodo, asignaciones de cluster, "
        "historial de perfiles y documentos RAG en Supabase PostgreSQL. No usa Supabase Storage."
    ),
    responses=ERROR_RESPONSES,
)
def sync_to_supabase_endpoint(payload: SupabaseResultsSyncRequest, request: Request) -> SupabaseResultsSyncResponse:
    try:
        context = security_context_from_request(request)
        require_roles(context, "director")
        return sync_results_to_supabase(
            include_rag_documents=payload.include_rag_documents,
            max_rag_documents=payload.max_rag_documents,
            batch_size=payload.batch_size,
            notes=payload.notes,
            tenant_id=context.tenant_id,
        )
    except Exception as exc:
        raise http_error(exc) from exc

@router.get(
    "/students",
    response_model=StudentListResponse,
    summary="Listar estudiantes-periodo segmentados",
    description="Lista registros alumno-periodo con filtros por perfil academico, programa y cluster.",
    responses=ERROR_RESPONSES,
)
def students(
    request: Request,
    perfil: str | None = Query(default=None, description="Filtro parcial por nombre de perfil academico."),
    programa: str | None = Query(default=None, description="Filtro parcial por programa/carrera."),
    cluster: int | None = Query(default=None, description="Cluster numerico asignado por K-Means."),
    role: Literal["director", "coordinador", "tutor", "analista"] | None = Query(
        default=None,
        description="Compatibilidad local; con JWT el rol se deriva del perfil autenticado.",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Cantidad maxima de registros."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento para paginacion."),
) -> StudentListResponse:
    try:
        context = security_context_from_request(request, requested_role=role)
        result = filtered_students(
            perfil=perfil,
            programa=programa,
            cluster=cluster,
            limit=limit,
            offset=offset,
            security_context=context,
        )
        audit_items_access(context, endpoint="GET /cacei/segmentation/students", items=result["items"])
        return result
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/students/{student_id}/llm-context",
    response_model=StudentLlmContextResponse,
    tags=["LLM y RAG"],
    summary="Consultar contexto academico estructurado para LLM",
    description=(
        "Devuelve resumen academico, historial compacto, documento RAG y reglas de seguridad. "
        "El rol controla limite de historial y visibilidad de identificador; la autenticacion real "
        "debe aplicarse en CASEI antes de invocar el microservicio."
    ),
    responses=ERROR_RESPONSES,
)
def student_context_for_llm(
    request: Request,
    student_id: str,
    role: Literal["director", "coordinador", "tutor", "analista"] | None = Query(
        default=None,
        description="Compatibilidad local; con JWT el rol se deriva del perfil autenticado.",
    ),
    max_history: int = Query(default=6, ge=1, le=12, description="Periodos/corridas maximas a incluir."),
) -> StudentLlmContextResponse:
    try:
        context = security_context_from_request(request, requested_role=role)
        result = student_llm_context(
            student_id=student_id,
            role=context.role,
            max_history=max_history,
            security_context=context,
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Student not found: {student_id}")
        audit_context_access(
            context,
            endpoint="GET /cacei/segmentation/students/{student_id}/llm-context",
            student_id=student_id,
            model_version=result.get("model_version"),
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/students/{student_id}/history",
    response_model=StudentHistoryResponse,
    summary="Consultar historial persistido de un estudiante",
    description="Devuelve inferencias guardadas en SQLite para un estudiante a traves de corridas y periodos.",
    responses=ERROR_RESPONSES,
)
def student_inference_history(
    request: Request,
    student_id: str,
    role: Literal["director", "coordinador", "tutor", "analista"] | None = Query(
        default=None,
        description="Compatibilidad local; con JWT el rol se deriva del perfil autenticado.",
    ),
    limit: int = Query(default=100, ge=1, le=500, description="Cantidad maxima de inferencias historicas."),
) -> StudentHistoryResponse:
    try:
        context = security_context_from_request(request, requested_role=role)
        require_student_access(student_id, context)
        result = student_history(student_id, limit=limit)
        audit_context_access(
            context,
            endpoint="GET /cacei/segmentation/students/{student_id}/history",
            student_id=student_id,
        )
        return result
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/students/{student_id}",
    response_model=StudentDetailResponse,
    summary="Consultar detalle actual de un estudiante",
    description="Devuelve la trayectoria alumno-periodo disponible en el snapshot activo de segmentacion.",
    responses=ERROR_RESPONSES,
)
def student(
    request: Request,
    student_id: str,
    role: Literal["director", "coordinador", "tutor", "analista"] | None = Query(
        default=None,
        description="Compatibilidad local; con JWT el rol se deriva del perfil autenticado.",
    ),
) -> StudentDetailResponse:
    try:
        context = security_context_from_request(request, requested_role=role)
        result = student_detail(student_id, security_context=context)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Student not found: {student_id}")
        audit_context_access(
            context,
            endpoint="GET /cacei/segmentation/students/{student_id}",
            student_id=student_id,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Buscar alumnos segmentados con recuperacion lexica o semantica",
    description="Interpreta filtros autorizados y ejecuta BM25, busqueda semantica o una fusion hibrida.",
    responses=ERROR_RESPONSES,
)
def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Consulta BM25 por keywords academicas."),
    top_k: int = Query(default=10, ge=1, le=50, description="Numero de resultados a devolver."),
    mode: Literal["auto", "bm25", "slm"] = Query(
        default="auto",
        description="auto interpreta solo consultas complejas; bm25 omite el SLM; slm fuerza interpretacion con fallback.",
    ),
    retrieval: Literal["hybrid", "bm25", "semantic"] = Query(
        default="hybrid",
        description="Motor de recuperacion. Si la rama semantica no esta disponible, conserva fallback a BM25.",
    ),
    explain: bool = Query(
        default=False,
        description="Incluye la matriz de conclusion y evidencia de filtros en search_metadata.",
    ),
    programa: str | None = Query(default=None, description="Filtro explicito por programa o carrera."),
    perfil: str | None = Query(default=None, description="Filtro explicito por perfil academico."),
    sexo: Literal["F", "M"] | None = Query(
        default=None,
        description="Filtro opcional; devuelve 422 si la fuente activa no contiene sexo.",
    ),
    role: Literal["director", "coordinador", "tutor", "analista"] | None = Query(
        default=None,
        description="Compatibilidad local; con JWT el rol se deriva del perfil autenticado.",
    ),
) -> SearchResponse:
    try:
        context = security_context_from_request(request, requested_role=role)
        result = search_students(
            q,
            top_k=top_k,
            security_context=context,
            mode=mode,
            programa=programa,
            perfil=perfil,
            sexo=sexo,
            retrieval=retrieval,
            explain=explain,
        )
        audit_items_access(context, endpoint="GET /cacei/segmentation/search", items=result["items"])
        return result
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/rag/documents",
    response_model=RagDocumentsResponse,
    tags=["LLM y RAG"],
    summary="Listar documentos base para RAG academico",
    description=(
        "Genera documentos compactos por alumno a partir del snapshot local actual. "
        "Incluye texto de recuperacion, metadata filtrable, usos permitidos y usos prohibidos."
    ),
    responses=ERROR_RESPONSES,
)
def rag_document_list(
    request: Request,
    role: Literal["director", "coordinador", "tutor", "analista"] | None = Query(
        default=None,
        description="Compatibilidad local; con JWT el rol se deriva del perfil autenticado.",
    ),
    perfil: str | None = Query(default=None, description="Filtro parcial por perfil academico."),
    programa: str | None = Query(default=None, description="Filtro parcial por programa/carrera."),
    cluster: int | None = Query(default=None, description="Cluster numerico asignado por K-Means."),
    student_id: str | None = Query(default=None, description="Filtro por matricula/id de estudiante."),
    limit: int = Query(default=20, ge=1, le=100, description="Cantidad maxima de documentos."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento para paginacion."),
) -> RagDocumentsResponse:
    try:
        context = security_context_from_request(request, requested_role=role)
        result = rag_documents(
            role=context.role,
            perfil=perfil,
            programa=programa,
            cluster=cluster,
            student_id=student_id,
            limit=limit,
            offset=offset,
            security_context=context,
        )
        for item in result.get("items", []):
            metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
            audit_context_access(
                context,
                endpoint="GET /cacei/segmentation/rag/documents",
                student_id=metadata.get("student_reference"),
                model_version=metadata.get("model_version"),
            )
        return result
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/clusters",
    response_model=ClusterCatalogResponse,
    summary="Consultar catalogo de clusters y perfiles",
    description="Devuelve perfiles academicos, centroides, resumen de clusters y variables mas distintivas.",
    responses=ERROR_RESPONSES,
)
def clusters(request: Request) -> ClusterCatalogResponse:
    try:
        security_context_from_request(request)
        return cluster_catalog()
    except Exception as exc:
        raise http_error(exc) from exc


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Listar corridas persistidas",
    description="Consulta la base SQLite local de inferencias, opcionalmente filtrada por estudiante.",
    responses=ERROR_RESPONSES,
)
def history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100, description="Cantidad maxima de corridas."),
    student_id: str | None = Query(default=None, description="Filtra corridas donde aparece el estudiante."),
) -> HistoryResponse:
    security_context_from_request(request)
    return {
        "summary": history_summary(),
        "items": read_history(limit=limit, student_id=student_id),
    }


@router.get(
    "/history/{execution_id}",
    response_model=HistoryRunResponse,
    summary="Consultar inferencias de una corrida",
    description="Devuelve metadatos de la corrida y una pagina de inferencias estudiante-periodo asociadas.",
    responses=ERROR_RESPONSES,
)
def history_run(
    request: Request,
    execution_id: str,
    limit: int = Query(default=100, ge=1, le=500, description="Cantidad maxima de inferencias."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento para paginacion."),
) -> HistoryRunResponse:
    try:
        security_context_from_request(request)
        result = history_detail(execution_id=execution_id, limit=limit, offset=offset)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Inference run not found: {execution_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(exc) from exc
