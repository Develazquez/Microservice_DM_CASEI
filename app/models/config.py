from __future__ import annotations

import os
from pathlib import Path


def _strip_inline_comment(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
            continue
        if char == "#" and quote is None:
            return value[:index].strip()
    return value.strip().strip('"').strip("'")


def _load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_inline_comment(value)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASEI_ROOT = PROJECT_ROOT.parent

_env_candidates = []
if os.getenv("CASEI_ENV_FILE"):
    _env_candidates.append(Path(os.getenv("CASEI_ENV_FILE", "")))
_env_candidates.extend(
    [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".env.local",
        CASEI_ROOT / "NuevostestsWeb" / "CASEI_Tests" / ".env.local",
        CASEI_ROOT / "NuevostestsWeb" / "CASEI_Tests" / ".env",
        CASEI_ROOT / "CACEIv2" / ".env",
        CASEI_ROOT / "CACEIv2" / ".env.local",
    ]
)
for _env_file in _env_candidates:
    _load_env_file(_env_file)

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
STORAGE_DIR = DATA_DIR / "storage"
FIGURES_DIR = REPORTS_DIR / "figures"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODEL_REGISTRY_DIR = ARTIFACTS_DIR / "model_registry"
MODEL_REGISTRY_INDEX = MODEL_REGISTRY_DIR / "registry_index.csv"
CURRENT_MODEL_POINTER = ARTIFACTS_DIR / "current_model.json"


def tenant_artifacts_dir(tenant_slug: str | None = None) -> Path:
    """Return the artifacts directory for a specific tenant.

    When *tenant_slug* is ``None`` the global ``ARTIFACTS_DIR`` is returned so
    that existing single-tenant code keeps working without changes.
    """
    if not tenant_slug:
        return ARTIFACTS_DIR
    tenant_dir = ARTIFACTS_DIR / tenant_slug
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return tenant_dir


def tenant_model_pointer(tenant_slug: str | None = None) -> Path:
    return tenant_artifacts_dir(tenant_slug) / "current_model.json"


def tenant_model_registry_dir(tenant_slug: str | None = None) -> Path:
    registry = tenant_artifacts_dir(tenant_slug) / "model_registry"
    registry.mkdir(parents=True, exist_ok=True)
    return registry
API_HISTORY_PATH = REPORTS_DIR / "api_execution_history.jsonl"
INFERENCE_HISTORY_DB = STORAGE_DIR / "segmentation_inference_history.sqlite"
INFERENCE_SCHEMA_PATH = STORAGE_DIR / "segmentation_inference_schema.sql"
SUPABASE_SOURCE_SNAPSHOT = STORAGE_DIR / "supabase_academic_source_snapshot.json"
SUPABASE_STUDENT_PERIOD_PREVIEW = PROCESSED_DIR / "supabase_student_period_features_preview.csv"
SUPABASE_SYNC_VALIDATION_REPORT = REPORTS_DIR / "supabase_sync_validation_report.md"
SUPABASE_SNAPSHOT_REGISTRY_DIR = STORAGE_DIR / "supabase_snapshots"
DATASET_VERSION_DIR = STORAGE_DIR / "dataset_versions"
ACTIVE_DATASET_POINTER = STORAGE_DIR / "active_dataset.json"
ACTIVE_INFERENCE_SNAPSHOT = PROCESSED_DIR / "active_inference_assignments.csv"
ACTIVE_INFERENCE_METADATA = STORAGE_DIR / "active_inference_metadata.json"
SEARCH_INDEX_STATE = STORAGE_DIR / "search_index_state.json"
SEARCH_REGISTRY_DIR = ARTIFACTS_DIR / "search_registry"
CURRENT_SEARCH_INDEX_POINTER = ARTIFACTS_DIR / "current_search_index.json"

CASEI_SUPABASE_URL = os.getenv("CASEI_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
CASEI_SUPABASE_SERVICE_ROLE_KEY = os.getenv("CASEI_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CASEI_SUPABASE_ANON_KEY = os.getenv("CASEI_SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
CASEI_DB_MODE = os.getenv("CASEI_DB_MODE", "local").strip().lower()
CASEI_ARTIFACT_MODE = os.getenv("CASEI_ARTIFACT_MODE", "local").strip().lower()
CASEI_ALLOW_STORAGE_ARTIFACT_BACKUP = os.getenv("CASEI_ALLOW_STORAGE_ARTIFACT_BACKUP", "false").lower() == "true"
CASEI_ENVIRONMENT = os.getenv("CASEI_ENVIRONMENT", "development").strip().lower()
CASEI_ALLOW_DEV_IDENTITY_HEADERS = os.getenv(
    "CASEI_ALLOW_DEV_IDENTITY_HEADERS",
    "false" if CASEI_ENVIRONMENT == "production" else "true",
).lower() == "true"
CASEI_AUTH_TIMEOUT_SECONDS = float(os.getenv("CASEI_AUTH_TIMEOUT_SECONDS", "5"))
CASEI_PIPELINE_DATA_SOURCE = os.getenv("CASEI_PIPELINE_DATA_SOURCE", "auto").strip().lower()
CASEI_AUTO_INFERENCE_ENABLED = os.getenv("CASEI_AUTO_INFERENCE_ENABLED", "false").lower() == "true"
CASEI_ML_WORKER_ENABLED = os.getenv("CASEI_ML_WORKER_ENABLED", "true").lower() == "true"
CASEI_ML_WORKER_ID = os.getenv("CASEI_ML_WORKER_ID", "worker-local-1").strip()
CASEI_ML_POLL_SECONDS = float(os.getenv("CASEI_ML_POLL_SECONDS", "5"))
CASEI_ML_JOB_TIMEOUT_SECONDS = int(os.getenv("CASEI_ML_JOB_TIMEOUT_SECONDS", "900"))
CASEI_ML_EVENT_DEBOUNCE_SECONDS = int(os.getenv("CASEI_ML_EVENT_DEBOUNCE_SECONDS", "60"))
CASEI_MODEL_ACTIVATION_MODE = os.getenv("CASEI_MODEL_ACTIVATION_MODE", "manual").strip().lower()

RAW_DATASET_V1 = RAW_DIR / "dataset_sintetico_alumnos.csv"
RAW_DATASET_V2 = RAW_DIR / "dataset_sintetico_alumnos_v2.csv"
RAW_CARDEX_DATASET = RAW_DIR / "dataset_crudo_2000_estudiantes.csv"
RAW_DATASET = RAW_CARDEX_DATASET
STUDENT_PERIOD_DATASET = PROCESSED_DIR / "student_period_features.csv"

CARDEX_COLUMNS = [
    "Matricula",
    "Nombre",
    "Carrera",
    "EstatusAlumno",
    "CuatrimestreActual",
    "Materia",
    "Periodo",
    "EstatusMateria",
    "Final",
    "Extr",
    "EstatusCardex",
    "PeriodoCursado",
    "PlanEstudiosClave",
    "Credito",
]

METADATA_COLUMNS = ["id_estudiante", "id_periodo", "programa", "cohorte", "estatus_academico"]

NUMERIC_COLUMNS = [
    "promedio_general",
    "promedio_periodo",
    "materias_aprobadas",
    "materias_reprobadas",
    "materias_en_curso",
    "creditos_acumulados",
    "porcentaje_avance",
    "porcentaje_asistencia",
    "faltas",
    "retardos",
    "num_tutorias",
    "num_asesorias",
    "num_incidencias",
    "num_permisos",
    "recursamientos",
    "rezago_materias",
    "creditos_inscritos_periodo",
    "creditos_aprobados_periodo",
    "creditos_totales_plan",
    "periodos_cursados",
    "periodos_sin_inscripcion",
    "materias_reprobadas_periodo",
    "materias_reprobadas_acumuladas",
    "materias_en_curso_periodo",
    "tendencia_promedio",
    "varianza_calificaciones",
    "tutorias_abiertas",
    "tutorias_cerradas",
    "compromisos_pendientes",
    "compromisos_cumplidos",
    "permisos_aprobados",
    "permisos_rechazados",
    "bandera_dato_incompleto",
]

FEATURE_DECISIONS = {
    "promedio_general": ("include", "Desempeno acumulado del estudiante."),
    "promedio_periodo": ("include", "Desempeno reciente; se imputa cuando no aplica por baja temporal."),
    "materias_aprobadas": ("exclude", "Variable heredada; en v2 se usa creditos aprobados y avance."),
    "materias_reprobadas": ("exclude", "Alias heredado; se reemplaza por periodo y acumulado."),
    "materias_en_curso": ("exclude", "Alias heredado; se reemplaza por materias_en_curso_periodo."),
    "creditos_acumulados": ("exclude", "Variable heredada; se reemplaza por creditos_aprobados_periodo y porcentaje_avance."),
    "porcentaje_avance": ("include", "Lectura academica clara del progreso curricular."),
    "porcentaje_asistencia": ("include", "Indicador normalizado de compromiso/asistencia."),
    "faltas": ("exclude", "Altamente inverso a porcentaje_asistencia; se mantiene el indicador normalizado."),
    "retardos": ("include", "Senal operativa distinta a la asistencia acumulada."),
    "num_tutorias": ("exclude", "Alias heredado; en v2 se separa en abiertas y cerradas."),
    "num_asesorias": ("include", "Mide apoyo academico complementario."),
    "num_incidencias": ("include", "Senal de eventos que pueden afectar trayectoria."),
    "num_permisos": ("exclude", "Alias heredado; en v2 se separa en permisos aprobados y rechazados."),
    "recursamientos": ("include", "Historial acumulado de repeticion de materias."),
    "rezago_materias": ("include", "Indicador central de atraso academico."),
    "creditos_inscritos_periodo": ("include", "Carga academica real del periodo."),
    "creditos_aprobados_periodo": ("include", "Desempeno reciente en creditos, no solo materias."),
    "creditos_totales_plan": ("exclude", "Constante por plan/programa; descriptiva, no debe dominar clustering."),
    "periodos_cursados": ("include", "Contexto temporal de avance academico."),
    "periodos_sin_inscripcion": ("include", "Explica rezago y bajas de forma academica."),
    "materias_reprobadas_periodo": ("include", "Dificultad reciente del periodo."),
    "materias_reprobadas_acumuladas": ("include", "Dificultad historica acumulada."),
    "materias_en_curso_periodo": ("include", "Carga actual validada contra estatus."),
    "tendencia_promedio": ("include", "Diferencia recuperacion, deterioro y estabilidad."),
    "varianza_calificaciones": ("include", "Distingue desempeno estable de desempeno irregular."),
    "tutorias_abiertas": ("include", "Seguimiento tutorial pendiente."),
    "tutorias_cerradas": ("include", "Acompanamiento tutorial completado."),
    "compromisos_pendientes": ("include", "Accionabilidad tutorial no resuelta."),
    "compromisos_cumplidos": ("include", "Respuesta del alumno al seguimiento."),
    "permisos_aprobados": ("include", "Contextualiza baja asistencia sin asumir abandono."),
    "permisos_rechazados": ("include", "Senal operativa de ausencias sin soporte."),
    "bandera_dato_incompleto": ("include", "Permite que el modelo capture incertidumbre controlada."),
}

FINAL_FEATURES = [
    column for column, (decision, _) in FEATURE_DECISIONS.items() if decision == "include"
]

RANDOM_SEED = 42
K_MIN = 2
K_MAX = 8
N_INIT = 20
MAX_ITER = 300
TOL = 1e-4
