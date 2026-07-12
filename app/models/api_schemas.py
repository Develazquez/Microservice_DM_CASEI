from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ErrorResponse(ApiModel):
    detail: str = Field(description="Descripcion legible del error.")


class RootResponse(ApiModel):
    service: str
    status: str | None = None
    docs: str
    openapi: str
    api_prefix: str


class HealthResponse(ApiModel):
    status: Literal["ok", "degraded"]
    service: str
    api_version: str
    model_version: str | None = None
    selected_representation: str | None = None
    selected_k: int | None = None
    checks_passed: bool | None = None
    checked_at_utc: str
    error: str | None = None


class RunSegmentationRequest(BaseModel):
    mode: Literal["load_existing", "retrain_local"] = Field(
        default="load_existing",
        description="load_existing valida y carga el bundle actual; retrain_local regenera fases 2-8.",
    )
    persist_model: bool = Field(
        default=True,
        description="Cuando mode=retrain_local, registra un nuevo bundle versionado en Fase 8.",
    )
    refresh_search_index: bool = Field(
        default=False,
        description="Regenera artefactos BM25 despues de cargar o entrenar.",
    )
    notes: str | None = Field(default=None, max_length=500)


class RunSegmentationResponse(ApiModel):
    execution_id: str
    status: Literal["completed"]
    mode: Literal["load_existing", "retrain_local"]
    steps: list[str]
    started_at_utc: str
    finished_at_utc: str
    duration_seconds: float
    model_version: str
    inference_persistence: dict[str, Any]
    summary: dict[str, Any]


class AcademicProfile(ApiModel):
    cluster: int
    perfil_academico: str
    prioridad_tutorial: str | None = None
    registros: int | None = None
    porcentaje_registros: float | None = None
    rasgos_dominantes: str | None = None
    lectura_funcional: str | None = None
    acciones_sugeridas: str | None = None
    cautela_interpretacion: str | None = None


class ProfileDistributionItem(ApiModel):
    cluster: int
    perfil_academico: str | None = None
    prioridad_tutorial: str | None = None
    registros: int


class ProgramDistributionItem(ApiModel):
    programa: str
    estudiantes: int
    registros: int


class SegmentationSummaryResponse(ApiModel):
    model_version: str
    selected_representation: str
    selected_k: int
    metrics: dict[str, Any]
    total_students: int
    total_records: int
    average_score: float
    average_attendance: float
    students_in_follow_up: int
    records_in_follow_up: int
    profile_distribution: list[ProfileDistributionItem]
    program_distribution: list[ProgramDistributionItem]
    profiles: list[AcademicProfile]
    warnings: list[str]


class StudentListResponse(ApiModel):
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]


class StudentDetailResponse(ApiModel):
    id_estudiante: str
    total_records: int
    latest_record: dict[str, Any] | None
    records: list[dict[str, Any]]


class SearchResponse(ApiModel):
    query: str
    top_k: int
    total_indexed: int
    items: list[dict[str, Any]]


class ClusterCatalogResponse(ApiModel):
    model_version: str
    profiles: list[dict[str, Any]]
    centroids: list[dict[str, Any]]
    summary: list[dict[str, Any]]
    top_feature_differences: list[dict[str, Any]]


class HistorySummary(ApiModel):
    database_path: str
    schema_path: str
    runs: int
    student_inferences: int
    students: int
    latest_run: dict[str, Any] | None = None


class HistoryResponse(ApiModel):
    summary: HistorySummary
    items: list[dict[str, Any]]


class HistoryRunResponse(ApiModel):
    run: dict[str, Any]
    total_inferences: int
    limit: int
    offset: int
    items: list[dict[str, Any]]


class StudentHistoryResponse(ApiModel):
    id_estudiante: str
    total: int
    items: list[dict[str, Any]]


class LlmContextContractResponse(ApiModel):
    context_version: str
    generated_at_utc: str
    purpose: str
    source: dict[str, Any]
    roles: list[dict[str, Any]]
    field_groups: dict[str, list[str]]
    required_upstream_controls: list[str]
    safety_rules: list[str]
    data_warnings: list[str]
    endpoints: list[str]


class StudentLlmContextResponse(ApiModel):
    context_version: str
    generated_at_utc: str
    model_version: str
    role: Literal["director", "coordinador", "tutor", "analista"]
    student_reference: str
    access_control: dict[str, Any]
    academic_summary: dict[str, Any]
    compact_profile_history: list[dict[str, Any]]
    persisted_profile_history: list[dict[str, Any]]
    rag_context: dict[str, Any]
    safety: dict[str, Any]
    data_warnings: list[str]


class RagDocumentsResponse(ApiModel):
    context_version: str
    generated_at_utc: str
    role: Literal["director", "coordinador", "tutor", "analista"]
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]
    data_warnings: list[str]


class SupabaseSyncStatusResponse(ApiModel):
    status: Literal["configured", "missing_configuration"]
    repository: dict[str, Any]
    repository_selection: dict[str, Any] | None = None
    snapshot_path: str
    preview_path: str
    validation_report_path: str | None = None


class SupabaseSyncRequest(BaseModel):
    limit: int = Field(default=1000, ge=1, le=10000)
    write_preview: bool = True


class SupabaseSyncResponse(ApiModel):
    status: Literal["completed"]
    started_at_utc: str
    finished_at_utc: str
    source_hash: str
    counts: dict[str, int]
    preview_records: int
    snapshot_path: str
    preview_path: str | None
    validation_report_path: str | None = None
    validation: dict[str, Any] | None = None
    active_dataset_replaced: bool
    note: str

class SupabaseResultsSyncRequest(BaseModel):
    include_rag_documents: bool = Field(
        default=True,
        description="Incluye documentos RAG derivados del snapshot local actual.",
    )
    max_rag_documents: int = Field(default=500, ge=0, le=5000)
    batch_size: int = Field(default=500, ge=1, le=1000)
    notes: str | None = Field(default=None, max_length=500)


class SupabaseResultsSyncResponse(ApiModel):
    status: Literal["completed"]
    execution_id: str
    model_version: str
    started_at_utc: str
    finished_at_utc: str
    duration_seconds: float
    source_hash: str
    counts: dict[str, int]
    active_model_version: str
    note: str
