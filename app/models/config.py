from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

RAW_DATASET_V1 = RAW_DIR / "dataset_sintetico_alumnos.csv"
RAW_DATASET_V2 = RAW_DIR / "dataset_sintetico_alumnos_v2.csv"
RAW_DATASET = RAW_DATASET_V2

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
