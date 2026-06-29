from __future__ import annotations

import math
import uuid

import numpy as np
import pandas as pd

from app.models.config import RAW_DATASET_V1, RAW_DATASET_V2, REPORTS_DIR, RANDOM_SEED
from app.views.report_view import markdown_table, write_markdown


PROGRAMS = [
    "Ingenieria en Desarrollo de Software",
    "Ingenieria Biomedica",
    "Ingenieria en Energia",
    "Ingenieria Agroindustrial",
]
PROGRAM_WEIGHTS = [0.34, 0.26, 0.22, 0.18]
PROGRAM_PLAN_CREDITS = {
    "Ingenieria en Desarrollo de Software": 270,
    "Ingenieria Biomedica": 282,
    "Ingenieria en Energia": 264,
    "Ingenieria Agroindustrial": 276,
}
PERIODS = ["2022-2", "2023-1", "2023-2", "2024-1", "2024-2", "2025-1"]
COHORTS = [2020, 2021, 2022, 2023, 2024]


def clipped_normal(rng: np.random.Generator, mean: float, std: float, low: float, high: float) -> float:
    return float(np.clip(rng.normal(mean, std), low, high))


def bounded_int(value: float, low: int, high: int) -> int:
    return int(np.clip(round(value), low, high))


def period_order(period: str) -> int:
    year, term = period.split("-")
    return int(year) * 2 + (1 if term == "1" else 2)


def choose_status(
    rng: np.random.Generator,
    promedio_general: float,
    asistencia: float,
    reprobadas_acumuladas: int,
    rezago: int,
    periodos_sin_inscripcion: int,
    evento_baja: bool,
) -> str:
    if evento_baja or periodos_sin_inscripcion >= 2:
        return "Baja Temporal"
    risk_score = (
        (70 - promedio_general) * 0.04
        + max(0, 75 - asistencia) * 0.025
        + reprobadas_acumuladas * 0.22
        + rezago * 0.18
    )
    noise = rng.normal(0, 0.35)
    if risk_score + noise > 2.0:
        return "Irregular"
    return "Regular"


def generate_dataset_v2(n_records: int = 1000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records: list[dict[str, object]] = []

    for index in range(n_records):
        programa = str(rng.choice(PROGRAMS, p=PROGRAM_WEIGHTS))
        periodo = str(rng.choice(PERIODS, p=[0.08, 0.15, 0.18, 0.22, 0.20, 0.17]))
        cohorte = int(rng.choice(COHORTS, p=[0.15, 0.22, 0.25, 0.23, 0.15]))
        periodos_cursados = max(1, period_order(periodo) - period_order(f"{cohorte}-1") + 1)
        periodos_cursados = bounded_int(periodos_cursados + rng.normal(0, 0.6), 1, 12)

        habilidad = clipped_normal(rng, 0.62, 0.18, 0.10, 0.98)
        habito_asistencia = clipped_normal(rng, 0.76, 0.18, 0.12, 0.99)
        carga_externa = clipped_normal(rng, 0.28, 0.20, 0.0, 0.95)
        necesidad_apoyo = clipped_normal(rng, 1.0 - habilidad + rng.normal(0, 0.10), 0.15, 0.0, 1.0)
        evento_periodo = str(rng.choice(["normal", "enfermedad", "laboral", "recuperacion", "baja", "carga_extra"], p=[0.67, 0.07, 0.09, 0.08, 0.04, 0.05]))

        creditos_totales_plan = PROGRAM_PLAN_CREDITS[programa]
        avance_esperado = min(0.95, periodos_cursados / 10)
        avance_real = np.clip(
            avance_esperado
            + (habilidad - 0.55) * 0.20
            - necesidad_apoyo * 0.10
            - carga_externa * 0.06
            + rng.normal(0, 0.06),
            0.04,
            0.98,
        )
        creditos_acumulados = bounded_int(creditos_totales_plan * avance_real, 0, creditos_totales_plan)
        materias_aprobadas = bounded_int(creditos_acumulados / rng.uniform(5.0, 8.0), 0, 55)
        porcentaje_avance = round(creditos_acumulados / creditos_totales_plan * 100, 2)

        carga_base = rng.integers(4, 8)
        if evento_periodo == "carga_extra":
            carga_base += 1
        if carga_externa > 0.70:
            carga_base -= 1
        materias_en_curso_periodo = bounded_int(carga_base, 2, 8)
        creditos_inscritos_periodo = bounded_int(materias_en_curso_periodo * rng.uniform(5.0, 8.0), 8, 56)

        asistencia = 100 * np.clip(
            habito_asistencia
            - carga_externa * 0.20
            - (0.20 if evento_periodo in {"enfermedad", "laboral"} else 0)
            + (0.08 if evento_periodo == "recuperacion" else 0)
            + rng.normal(0, 0.07),
            0.05,
            0.99,
        )
        permisos_aprobados = int(rng.poisson(0.5 + 1.6 * carga_externa + (2.0 if evento_periodo in {"enfermedad", "laboral"} else 0)))
        permisos_rechazados = int(rng.poisson(0.2 + 0.8 * max(0, 0.55 - habito_asistencia)))
        faltas = bounded_int((100 - asistencia) / 100 * 32 - permisos_aprobados * 0.45 + rng.normal(0, 2.0), 0, 32)
        retardos = int(np.clip(rng.poisson(1.0 + 3.0 * (1 - habito_asistencia) + carga_externa), 0, 12))

        promedio_general = 45 + habilidad * 48 + habito_asistencia * 8 - necesidad_apoyo * 12 + rng.normal(0, 5)
        promedio_periodo = promedio_general + rng.normal(0, 8) - carga_externa * 8
        if evento_periodo == "recuperacion":
            promedio_periodo += rng.uniform(5, 12)
        if evento_periodo in {"enfermedad", "laboral"}:
            promedio_periodo -= rng.uniform(5, 14)
        promedio_general = round(float(np.clip(promedio_general, 35, 98)), 2)
        promedio_periodo = round(float(np.clip(promedio_periodo, 25, 100)), 2)

        materias_reprobadas_periodo = int(np.clip(rng.poisson(max(0.05, (70 - promedio_periodo) / 18 + (65 - asistencia) / 32)), 0, materias_en_curso_periodo))
        materias_reprobadas_acumuladas = int(np.clip(materias_reprobadas_periodo + rng.poisson(max(0.2, necesidad_apoyo * periodos_cursados / 2.2)), 0, 18))
        recursamientos = int(rng.integers(0, materias_reprobadas_acumuladas + 1)) if materias_reprobadas_acumuladas > 0 else 0
        rezago_base = max(materias_reprobadas_acumuladas - recursamientos, 0)
        periodos_sin_inscripcion = int(np.clip(rng.poisson(0.12 + 0.35 * carga_externa + (0.9 if evento_periodo == "baja" else 0)), 0, 4))
        rezago_materias = int(np.clip(rezago_base + periodos_sin_inscripcion + rng.poisson(0.25 + necesidad_apoyo * 0.6), 0, 12))

        creditos_aprobados_periodo = bounded_int(
            creditos_inscritos_periodo * max(0, 1 - materias_reprobadas_periodo / max(materias_en_curso_periodo, 1)),
            0,
            creditos_inscritos_periodo,
        )
        tendencia_promedio = round(promedio_periodo - promedio_general, 2)
        varianza_calificaciones = round(float(np.clip(rng.gamma(2.0, 10.0) + necesidad_apoyo * 25, 2, 85)), 2)

        tutorias_abiertas = int(np.clip(rng.poisson(0.3 + necesidad_apoyo * 1.8 + rezago_materias * 0.15), 0, 8))
        tutorias_cerradas = int(np.clip(rng.poisson(0.6 + (1 - necesidad_apoyo) * 1.1 + (evento_periodo == "recuperacion") * 1.2), 0, 8))
        num_tutorias = tutorias_abiertas + tutorias_cerradas
        num_asesorias = int(np.clip(rng.poisson(0.4 + materias_reprobadas_periodo * 0.9 + necesidad_apoyo), 0, 10))
        num_incidencias = int(np.clip(rng.poisson(0.15 + max(0, 60 - asistencia) / 35 + permisos_rechazados * 0.35), 0, 8))
        compromisos_pendientes = int(np.clip(rng.poisson(0.2 + tutorias_abiertas * 0.7 + num_incidencias * 0.4), 0, 10))
        compromisos_cumplidos = int(np.clip(rng.poisson(0.5 + tutorias_cerradas * 0.8 + (evento_periodo == "recuperacion") * 1.0), 0, 10))

        estatus = choose_status(
            rng,
            promedio_general,
            asistencia,
            materias_reprobadas_acumuladas,
            rezago_materias,
            periodos_sin_inscripcion,
            evento_periodo == "baja",
        )
        bandera_dato_incompleto = 0
        if estatus == "Baja Temporal":
            materias_en_curso_periodo = 0
            creditos_inscritos_periodo = 0
            creditos_aprobados_periodo = 0
            asistencia = round(float(np.clip(asistencia * rng.uniform(0.0, 0.35), 0, 25)), 2)
            faltas = bounded_int(rng.normal(24, 5), 0, 32)
            if rng.random() < 0.55:
                promedio_periodo = math.nan
                tendencia_promedio = math.nan
                bandera_dato_incompleto = 1

        record = {
            "id_estudiante": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"casei-v2-{index}")),
            "id_periodo": periodo,
            "programa": programa,
            "cohorte": cohorte,
            "promedio_general": promedio_general,
            "promedio_periodo": promedio_periodo,
            "materias_aprobadas": materias_aprobadas,
            "materias_reprobadas": materias_reprobadas_acumuladas,
            "materias_en_curso": materias_en_curso_periodo,
            "creditos_acumulados": creditos_acumulados,
            "porcentaje_avance": porcentaje_avance,
            "porcentaje_asistencia": round(float(asistencia), 2),
            "faltas": faltas,
            "retardos": retardos,
            "num_tutorias": num_tutorias,
            "num_asesorias": num_asesorias,
            "num_incidencias": num_incidencias,
            "num_permisos": permisos_aprobados + permisos_rechazados,
            "recursamientos": recursamientos,
            "rezago_materias": rezago_materias,
            "estatus_academico": estatus,
            "creditos_inscritos_periodo": creditos_inscritos_periodo,
            "creditos_aprobados_periodo": creditos_aprobados_periodo,
            "creditos_totales_plan": creditos_totales_plan,
            "periodos_cursados": periodos_cursados,
            "periodos_sin_inscripcion": periodos_sin_inscripcion,
            "materias_reprobadas_periodo": materias_reprobadas_periodo,
            "materias_reprobadas_acumuladas": materias_reprobadas_acumuladas,
            "materias_en_curso_periodo": materias_en_curso_periodo,
            "tendencia_promedio": tendencia_promedio,
            "varianza_calificaciones": varianza_calificaciones,
            "tutorias_abiertas": tutorias_abiertas,
            "tutorias_cerradas": tutorias_cerradas,
            "compromisos_pendientes": compromisos_pendientes,
            "compromisos_cumplidos": compromisos_cumplidos,
            "permisos_aprobados": permisos_aprobados,
            "permisos_rechazados": permisos_rechazados,
            "bandera_dato_incompleto": bandera_dato_incompleto,
        }
        records.append(record)

    return pd.DataFrame(records)


def validate_dataset(df: pd.DataFrame, version: str) -> pd.DataFrame:
    checks: list[dict[str, object]] = []

    def add(name: str, passed: bool, failing_rows: int, severity: str, detail: str) -> None:
        checks.append(
            {
                "check": name,
                "passed": bool(passed),
                "failing_rows": int(failing_rows),
                "severity": severity,
                "detail": detail,
            }
        )

    duplicated = int(df.duplicated(["id_estudiante", "id_periodo"]).sum())
    add("unique_student_period", duplicated == 0, duplicated, "alta", "La llave id_estudiante + id_periodo debe ser unica.")

    required = {"id_estudiante", "id_periodo", "programa", "cohorte", "promedio_general", "porcentaje_asistencia", "estatus_academico"}
    missing = sorted(required - set(df.columns))
    add("required_columns", not missing, len(missing), "alta", f"Columnas faltantes: {missing}")

    for column in ["promedio_general", "promedio_periodo", "porcentaje_asistencia", "porcentaje_avance"]:
        if column in df.columns:
            invalid = int((df[column].dropna().lt(0) | df[column].dropna().gt(100)).sum())
            add(f"range_0_100_{column}", invalid == 0, invalid, "alta", f"{column} debe estar entre 0 y 100 cuando aplica.")

    count_columns = [
        col
        for col in df.columns
        if col.startswith("num_")
        or col.startswith("materias_")
        or col in {"faltas", "retardos", "recursamientos", "rezago_materias", "periodos_cursados", "periodos_sin_inscripcion"}
    ]
    for column in count_columns:
        invalid = int(df[column].dropna().lt(0).sum())
        add(f"non_negative_{column}", invalid == 0, invalid, "alta", f"{column} no debe tener valores negativos.")

    if {"creditos_aprobados_periodo", "creditos_inscritos_periodo"} <= set(df.columns):
        invalid = int((df["creditos_aprobados_periodo"] > df["creditos_inscritos_periodo"]).sum())
        add("period_credits_consistency", invalid == 0, invalid, "alta", "Creditos aprobados del periodo no debe exceder creditos inscritos.")

    if {"creditos_acumulados", "creditos_totales_plan", "porcentaje_avance"} <= set(df.columns):
        expected = df["creditos_acumulados"] / df["creditos_totales_plan"] * 100
        invalid = int((expected.sub(df["porcentaje_avance"]).abs() > 0.75).sum())
        add("progress_matches_credits", invalid == 0, invalid, "alta", "porcentaje_avance debe ser compatible con creditos acumulados / creditos del plan.")

    if {"estatus_academico", "materias_en_curso_periodo"} <= set(df.columns):
        invalid = int(((df["estatus_academico"] == "Baja Temporal") & (df["materias_en_curso_periodo"] > 0)).sum())
        add("baja_temporal_without_active_load", invalid == 0, invalid, "alta", "Baja Temporal no debe tener materias activas en snapshot v2.")
    elif {"estatus_academico", "materias_en_curso"} <= set(df.columns):
        invalid = int(((df["estatus_academico"] == "Baja Temporal") & (df["materias_en_curso"] > 0)).sum())
        add("baja_temporal_without_active_load", invalid == 0, invalid, "alta", "Baja Temporal no debe tener materias activas si representa baja durante periodo.")

    if {"recursamientos", "materias_reprobadas_acumuladas"} <= set(df.columns):
        invalid = int((df["recursamientos"] > df["materias_reprobadas_acumuladas"]).sum())
        add("recursamientos_not_greater_than_failed_accumulated", invalid == 0, invalid, "alta", "Recursamientos no debe exceder reprobadas acumuladas.")
    elif {"recursamientos", "materias_reprobadas"} <= set(df.columns):
        invalid = int((df["recursamientos"] > df["materias_reprobadas"]).sum())
        add("recursamientos_not_greater_than_failed", invalid == 0, invalid, "alta", "Recursamientos no debe exceder materias reprobadas si ambas son acumuladas.")

    if {"rezago_materias", "materias_reprobadas_acumuladas", "recursamientos"} <= set(df.columns):
        expected_min = (df["materias_reprobadas_acumuladas"] - df["recursamientos"]).clip(lower=0)
        invalid = int((df["rezago_materias"] < expected_min).sum())
        add("lag_not_below_failed_minus_retake", invalid == 0, invalid, "media", "Rezago debe cubrir reprobadas acumuladas no regularizadas.")
    elif {"rezago_materias", "materias_reprobadas", "recursamientos"} <= set(df.columns):
        expected_min = (df["materias_reprobadas"] - df["recursamientos"]).clip(lower=0)
        invalid = int((df["rezago_materias"] < expected_min).sum())
        add("lag_not_below_failed_minus_retake", invalid == 0, invalid, "media", "Rezago debe cubrir reprobadas no regularizadas.")

    if version == "v2":
        allowed_nulls = {"promedio_periodo", "tendencia_promedio"}
        disallowed_null_columns = [col for col in df.columns if col not in allowed_nulls]
        invalid = int(df[disallowed_null_columns].isna().sum().sum())
        add("controlled_missing_values", invalid == 0, invalid, "media", "Solo se permiten nulos controlados en variables no aplicables por baja.")

    return pd.DataFrame(checks)


def describe_dataset(df: pd.DataFrame, label: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset": label,
                "records": len(df),
                "columns": len(df.columns),
                "null_cells": int(df.isna().sum().sum()),
                "programs": int(df["programa"].nunique()),
                "periods": int(df["id_periodo"].nunique()),
                "cohorts": int(df["cohorte"].nunique()),
                "avg_grade": float(df["promedio_general"].mean()),
                "avg_attendance": float(df["porcentaje_asistencia"].mean()),
                "avg_lag": float(df["rezago_materias"].mean()),
            }
        ]
    )


def write_dataset_documents(v1: pd.DataFrame, v2: pd.DataFrame, validation_v1: pd.DataFrame, validation_v2: pd.DataFrame) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    validation_v1.to_csv(REPORTS_DIR / "dataset_validation_v1.csv", index=False)
    validation_v2.to_csv(REPORTS_DIR / "dataset_validation_v2.csv", index=False)

    comparison = pd.concat([describe_dataset(v1, "v1"), describe_dataset(v2, "v2")], ignore_index=True)
    comparison.to_csv(REPORTS_DIR / "dataset_v1_vs_v2.csv", index=False)

    write_markdown(
        REPORTS_DIR / "criterios_realismo_dataset.md",
        """
# Criterios de Realismo del Dataset

## Snapshot

La unidad analitica es estudiante-periodo. El dataset v2 representa un corte durante o al cierre del periodo academico. Si `estatus_academico` es `Baja Temporal`, se interpreta como baja efectiva durante el periodo y por eso no debe tener carga activa.

## Reglas verificables

- Llave unica por `id_estudiante` + `id_periodo`.
- Calificaciones, asistencia y avance entre 0 y 100.
- Conteos academicos y operativos no negativos.
- `porcentaje_avance` compatible con creditos acumulados sobre creditos del plan.
- `creditos_aprobados_periodo <= creditos_inscritos_periodo`.
- `Baja Temporal` sin materias activas en el periodo.
- `recursamientos <= materias_reprobadas_acumuladas`.
- `rezago_materias >= max(materias_reprobadas_acumuladas - recursamientos, 0)`.
- Nulos permitidos solo en variables no aplicables por baja temporal.

## Variables latentes usadas

El dataset v2 se genera desde senales no visibles directamente: habilidad academica, habito de asistencia, carga externa, necesidad de apoyo, avance esperado por cohorte y evento del periodo.
""",
    )

    dictionary = pd.DataFrame(
        [
            ("creditos_inscritos_periodo", "Carga academica real inscrita en el periodo.", "periodo"),
            ("creditos_aprobados_periodo", "Creditos aprobados en el periodo.", "periodo"),
            ("creditos_totales_plan", "Total de creditos del plan sintetico por programa.", "plan"),
            ("periodos_cursados", "Periodos estimados desde cohorte hasta periodo.", "trayectoria"),
            ("periodos_sin_inscripcion", "Periodos con interrupcion de inscripcion.", "trayectoria"),
            ("materias_reprobadas_periodo", "Materias reprobadas en el periodo.", "periodo"),
            ("materias_reprobadas_acumuladas", "Materias reprobadas historicas acumuladas.", "historico"),
            ("materias_en_curso_periodo", "Materias activas del periodo.", "periodo"),
            ("tendencia_promedio", "Promedio del periodo menos promedio general.", "derivada"),
            ("varianza_calificaciones", "Variabilidad sintetica de desempeno por materias.", "derivada"),
            ("tutorias_abiertas", "Tutorias pendientes o en seguimiento.", "operativa"),
            ("tutorias_cerradas", "Tutorias atendidas/cerradas.", "operativa"),
            ("compromisos_pendientes", "Compromisos tutoriales no resueltos.", "operativa"),
            ("compromisos_cumplidos", "Compromisos tutoriales cumplidos.", "operativa"),
            ("permisos_aprobados", "Permisos aceptados que contextualizan ausencias.", "operativa"),
            ("permisos_rechazados", "Permisos no aceptados.", "operativa"),
            ("bandera_dato_incompleto", "Indica faltantes controlados por no aplicabilidad.", "calidad"),
        ],
        columns=["variable", "descripcion", "semantica"],
    )
    write_markdown(
        REPORTS_DIR / "diccionario_variables_v2.md",
        f"""
# Diccionario de Variables v2

{markdown_table(dictionary, max_rows=40)}

## Variables heredadas

El dataset conserva variables v1 para compatibilidad de reportes, pero el pipeline v2 prioriza las variables nuevas o corregidas definidas en `app/models/config.py`.
""",
    )

    write_markdown(
        REPORTS_DIR / "dataset_validation_v1.md",
        f"""
# Diagnostico Dataset v1

## Resumen

{markdown_table(describe_dataset(v1, "v1"))}

## Reglas evaluadas

{markdown_table(validation_v1, max_rows=40)}
""",
    )
    write_markdown(
        REPORTS_DIR / "dataset_validation_v2.md",
        f"""
# Validacion Dataset v2

## Resumen

{markdown_table(describe_dataset(v2, "v2"))}

## Reglas evaluadas

{markdown_table(validation_v2, max_rows=40)}
""",
    )
    write_markdown(
        REPORTS_DIR / "dataset_v1_vs_v2.md",
        f"""
# Comparacion Dataset v1 vs v2

## Resumen comparativo

{markdown_table(comparison)}

## Lectura tecnica

El dataset v2 mantiene 1000 registros sinteticos, amplia periodos y variables, separa variables de periodo e historicas, elimina contradicciones criticas de baja temporal con carga activa y documenta nulos controlados en variables no aplicables.
""",
    )


def run_dataset_v2_pipeline() -> None:
    if not RAW_DATASET_V1.exists():
        raise FileNotFoundError(f"Dataset v1 not found: {RAW_DATASET_V1}")
    v1 = pd.read_csv(RAW_DATASET_V1)
    v2 = generate_dataset_v2()
    RAW_DATASET_V2.parent.mkdir(parents=True, exist_ok=True)
    v2.to_csv(RAW_DATASET_V2, index=False)

    validation_v1 = validate_dataset(v1, "v1")
    validation_v2 = validate_dataset(v2, "v2")
    write_dataset_documents(v1, v2, validation_v1, validation_v2)

    print("Dataset v2 generado y validado.")
    print(f"Dataset: {RAW_DATASET_V2}")
    print(f"Reportes: {REPORTS_DIR}")

