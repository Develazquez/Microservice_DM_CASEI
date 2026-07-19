from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import math
import os
import sqlite3
import time
from typing import Any
import uuid

import numpy as np
import pandas as pd

from app.models.config import (
    INFERENCE_HISTORY_DB,
    INFERENCE_SCHEMA_PATH,
    PROCESSED_DIR,
    REPORTS_DIR,
    STORAGE_DIR,
    STUDENT_PERIOD_DATASET,
)
from app.services.model_persistence_service import load_persisted_model_bundle
from app.views.report_view import markdown_table, write_markdown


INFERENCE_PERSISTENCE_REPORT = REPORTS_DIR / "inference_persistence_report.md"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS inference_runs (
    execution_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    model_version TEXT NOT NULL,
    selected_representation TEXT,
    selected_k INTEGER,
    started_at_utc TEXT NOT NULL,
    finished_at_utc TEXT NOT NULL,
    duration_seconds REAL,
    dataset_path TEXT,
    dataset_records INTEGER,
    assignments_count INTEGER NOT NULL,
    students_count INTEGER NOT NULL,
    parameters_json TEXT,
    metrics_json TEXT,
    notes TEXT,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_inferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    id_estudiante TEXT NOT NULL,
    id_periodo TEXT NOT NULL,
    programa TEXT,
    cohorte TEXT,
    estatus_academico TEXT,
    cluster INTEGER NOT NULL,
    perfil_academico TEXT,
    prioridad_tutorial TEXT,
    distance_to_centroid REAL,
    membership_score REAL,
    promedio_general REAL,
    porcentaje_asistencia REAL,
    rezago_materias REAL,
    materias_reprobadas_periodo REAL,
    materias_reprobadas_acumuladas REAL,
    tendencia_promedio REAL,
    pc1 REAL,
    pc2 REAL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (execution_id) REFERENCES inference_runs(execution_id) ON DELETE CASCADE,
    UNIQUE (execution_id, id_estudiante, id_periodo)
);

CREATE INDEX IF NOT EXISTS idx_inference_runs_model_version
    ON inference_runs(model_version);

CREATE INDEX IF NOT EXISTS idx_inference_runs_started
    ON inference_runs(started_at_utc);

CREATE INDEX IF NOT EXISTS idx_student_inferences_student
    ON student_inferences(id_estudiante);

CREATE INDEX IF NOT EXISTS idx_student_inferences_period
    ON student_inferences(id_periodo);

CREATE INDEX IF NOT EXISTS idx_student_inferences_cluster
    ON student_inferences(cluster);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if value is pd.NA:
        return None
    return value


def to_sql_value(value: Any) -> Any:
    value = jsonable(value)
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return jsonable(df.replace({np.nan: None}).to_dict(orient="records"))


def sqlite_history_mode() -> str:
    return os.getenv("CASEI_SQLITE_HISTORY", "auto").strip().lower()


def sqlite_history_disabled() -> bool:
    return sqlite_history_mode() in {"0", "false", "off", "disabled", "none"}


def empty_history_summary(error: str | None = None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "database_path": str(INFERENCE_HISTORY_DB),
        "schema_path": str(INFERENCE_SCHEMA_PATH),
        "runs": 0,
        "student_inferences": 0,
        "students": 0,
        "latest_run": None,
    }
    if error:
        summary["warning"] = error
    return summary


def ensure_schema() -> None:
    if sqlite_history_disabled():
        raise RuntimeError("SQLite inference history is disabled by CASEI_SQLITE_HISTORY.")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    INFERENCE_SCHEMA_PATH.write_text(SCHEMA_SQL.strip() + "\n", encoding="utf-8")
    with closing(sqlite3.connect(INFERENCE_HISTORY_DB)) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def connect() -> sqlite3.Connection:
    ensure_schema()
    conn = sqlite3.connect(INFERENCE_HISTORY_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def current_inference_view() -> tuple[pd.DataFrame, dict[str, Any]]:
    loaded = load_persisted_model_bundle()
    manifest = loaded["manifest"]
    assignments = loaded["cluster_assignments"].copy()
    features = pd.read_csv(STUDENT_PERIOD_DATASET)
    view = assignments.merge(
        features,
        on=["id_estudiante", "id_periodo", "programa", "cohorte", "estatus_academico"],
        how="left",
    )

    profiles = pd.DataFrame(loaded["profile_catalog"])
    profile_columns = [
        column
        for column in ["cluster", "perfil_academico", "prioridad_tutorial"]
        if column in profiles.columns
    ]
    if profile_columns:
        view = view.merge(profiles[profile_columns], on="cluster", how="left")

    pca_path = PROCESSED_DIR / "pca_scores.csv"
    if pca_path.exists():
        pca = pd.read_csv(pca_path)
        pca_columns = [column for column in ["id_estudiante", "id_periodo", "PC1", "PC2"] if column in pca.columns]
        if pca_columns:
            view = view.merge(pca[pca_columns], on=["id_estudiante", "id_periodo"], how="left")

    return view, manifest


def persist_inference_snapshot(
    execution_id: str | None = None,
    run_type: str = "manual_snapshot",
    status: str = "completed",
    parameters: dict[str, Any] | None = None,
    notes: str | None = None,
    started_at_utc: str | None = None,
    finished_at_utc: str | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    ensure_schema()
    start = time.perf_counter()
    execution_id = execution_id or str(uuid.uuid4())
    started_at_utc = started_at_utc or utc_now()
    view, manifest = current_inference_view()
    finished_at_utc = finished_at_utc or utc_now()
    if duration_seconds is None:
        duration_seconds = round(time.perf_counter() - start, 3)

    model = manifest["model"]
    metrics = model.get("metrics", {})
    run_values = {
        "execution_id": execution_id,
        "run_type": run_type,
        "status": status,
        "model_version": manifest["model_version"],
        "selected_representation": model.get("selected_representation"),
        "selected_k": model.get("selected_k"),
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "duration_seconds": duration_seconds,
        "dataset_path": manifest.get("student_period_dataset"),
        "dataset_records": int(len(pd.read_csv(STUDENT_PERIOD_DATASET))),
        "assignments_count": int(len(view)),
        "students_count": int(view["id_estudiante"].nunique()),
        "parameters_json": json.dumps(jsonable(parameters or {}), ensure_ascii=False),
        "metrics_json": json.dumps(jsonable(metrics), ensure_ascii=False),
        "notes": notes,
        "created_at_utc": utc_now(),
    }

    columns = [
        "execution_id",
        "id_estudiante",
        "id_periodo",
        "programa",
        "cohorte",
        "estatus_academico",
        "cluster",
        "perfil_academico",
        "prioridad_tutorial",
        "distance_to_centroid",
        "membership_score",
        "promedio_general",
        "porcentaje_asistencia",
        "rezago_materias",
        "materias_reprobadas_periodo",
        "materias_reprobadas_acumuladas",
        "tendencia_promedio",
        "pc1",
        "pc2",
        "created_at_utc",
    ]
    inference_rows = []
    created_at = utc_now()
    for _, row in view.iterrows():
        inference_rows.append(
            (
                execution_id,
                to_sql_value(row.get("id_estudiante")),
                to_sql_value(row.get("id_periodo")),
                to_sql_value(row.get("programa")),
                to_sql_value(row.get("cohorte")),
                to_sql_value(row.get("estatus_academico")),
                to_sql_value(row.get("cluster")),
                to_sql_value(row.get("perfil_academico")),
                to_sql_value(row.get("prioridad_tutorial")),
                to_sql_value(row.get("distance_to_centroid")),
                to_sql_value(row.get("membership_score")),
                to_sql_value(row.get("promedio_general")),
                to_sql_value(row.get("porcentaje_asistencia")),
                to_sql_value(row.get("rezago_materias")),
                to_sql_value(row.get("materias_reprobadas_periodo")),
                to_sql_value(row.get("materias_reprobadas_acumuladas")),
                to_sql_value(row.get("tendencia_promedio")),
                to_sql_value(row.get("PC1")),
                to_sql_value(row.get("PC2")),
                created_at,
            )
        )

    with closing(connect()) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO inference_runs (
                execution_id, run_type, status, model_version, selected_representation,
                selected_k, started_at_utc, finished_at_utc, duration_seconds,
                dataset_path, dataset_records, assignments_count, students_count,
                parameters_json, metrics_json, notes, created_at_utc
            ) VALUES (
                :execution_id, :run_type, :status, :model_version, :selected_representation,
                :selected_k, :started_at_utc, :finished_at_utc, :duration_seconds,
                :dataset_path, :dataset_records, :assignments_count, :students_count,
                :parameters_json, :metrics_json, :notes, :created_at_utc
            )
            """,
            run_values,
        )
        conn.execute("DELETE FROM student_inferences WHERE execution_id = ?", (execution_id,))
        placeholders = ", ".join(["?"] * len(columns))
        conn.executemany(
            f"INSERT INTO student_inferences ({', '.join(columns)}) VALUES ({placeholders})",
            inference_rows,
        )
        conn.commit()

    return {
        "execution_id": execution_id,
        "run_type": run_type,
        "status": status,
        "model_version": manifest["model_version"],
        "assignments_count": len(inference_rows),
        "students_count": run_values["students_count"],
        "database_path": str(INFERENCE_HISTORY_DB),
    }


def list_inference_runs(limit: int = 20, student_id: str | None = None) -> list[dict[str, Any]]:
    try:
        with closing(connect()) as conn:
            if student_id:
                rows = conn.execute(
                    """
                    SELECT DISTINCT r.*
                    FROM inference_runs r
                    INNER JOIN student_inferences s ON s.execution_id = r.execution_id
                    WHERE UPPER(s.id_estudiante) = UPPER(?)
                    ORDER BY r.started_at_utc DESC
                    LIMIT ?
                    """,
                    (student_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM inference_runs
                    ORDER BY started_at_utc DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [decode_run(row) for row in rows]
    except (OSError, PermissionError, RuntimeError, sqlite3.Error):
        return []


def decode_run(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["parameters"] = json.loads(result.pop("parameters_json") or "{}")
    result["metrics"] = json.loads(result.pop("metrics_json") or "{}")
    return jsonable(result)


def get_inference_run(execution_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any] | None:
    try:
        with closing(connect()) as conn:
            run_row = conn.execute("SELECT * FROM inference_runs WHERE execution_id = ?", (execution_id,)).fetchone()
            if run_row is None:
                return None
            total = conn.execute(
                "SELECT COUNT(*) AS count FROM student_inferences WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()["count"]
            rows = conn.execute(
                """
                SELECT *
                FROM student_inferences
                WHERE execution_id = ?
                ORDER BY id_estudiante, id_periodo
                LIMIT ? OFFSET ?
                """,
                (execution_id, limit, offset),
            ).fetchall()
        return {
            "run": decode_run(run_row),
            "total_inferences": int(total),
            "limit": int(limit),
            "offset": int(offset),
            "items": dataframe_records(pd.DataFrame([dict(row) for row in rows])),
        }
    except (OSError, PermissionError, RuntimeError, sqlite3.Error):
        return None


def get_student_inference_history(student_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        with closing(connect()) as conn:
            rows = conn.execute(
                """
                SELECT
                    s.*,
                    r.run_type,
                    r.status,
                    r.model_version,
                    r.selected_representation,
                    r.selected_k,
                    r.started_at_utc,
                    r.finished_at_utc
                FROM student_inferences s
                INNER JOIN inference_runs r ON r.execution_id = s.execution_id
                WHERE UPPER(s.id_estudiante) = UPPER(?)
                ORDER BY r.started_at_utc DESC, s.id_periodo DESC
                LIMIT ?
                """,
                (student_id, limit),
            ).fetchall()
        return {
            "id_estudiante": student_id,
            "total": len(rows),
            "items": dataframe_records(pd.DataFrame([dict(row) for row in rows])),
        }
    except (OSError, PermissionError, RuntimeError, sqlite3.Error):
        return {"id_estudiante": student_id, "total": 0, "items": []}


def persistence_summary() -> dict[str, Any]:
    try:
        with closing(connect()) as conn:
            runs = conn.execute("SELECT COUNT(*) AS count FROM inference_runs").fetchone()["count"]
            inferences = conn.execute("SELECT COUNT(*) AS count FROM student_inferences").fetchone()["count"]
            students = conn.execute(
                "SELECT COUNT(DISTINCT id_estudiante) AS count FROM student_inferences"
            ).fetchone()["count"]
            latest = conn.execute(
                "SELECT * FROM inference_runs ORDER BY started_at_utc DESC LIMIT 1"
            ).fetchone()
        return {
            "database_path": str(INFERENCE_HISTORY_DB),
            "schema_path": str(INFERENCE_SCHEMA_PATH),
            "runs": int(runs),
            "student_inferences": int(inferences),
            "students": int(students),
            "latest_run": decode_run(latest) if latest else None,
        }
    except (OSError, PermissionError, RuntimeError, sqlite3.Error) as exc:
        return empty_history_summary(f"Historial SQLite no disponible en este entorno: {exc}")


def build_report(summary: dict[str, Any], latest_run: dict[str, Any] | None) -> str:
    schema_tables = pd.DataFrame(
        [
            {
                "tabla": "inference_runs",
                "proposito": "Una fila por corrida identificable de inferencia/segmentacion.",
                "llave": "execution_id",
            },
            {
                "tabla": "student_inferences",
                "proposito": "Asignaciones cluster por estudiante-periodo para cada corrida.",
                "llave": "id autoincremental; unique(execution_id, id_estudiante, id_periodo)",
            },
        ]
    )
    latest = pd.DataFrame([latest_run]) if latest_run else pd.DataFrame()

    return f"""
# Fase 10 - Persistencia de inferencias

## Objetivo

Guardar cada corrida de inferencia y conservar trazabilidad por estudiante, periodo, version de modelo y parametros de ejecucion.

## Almacenamiento local

- Motor: SQLite (`sqlite3`, libreria estandar de Python).
- Base local: `data/storage/segmentation_inference_history.sqlite`
- Esquema SQL: `data/storage/segmentation_inference_schema.sql`

## Esquema

{markdown_table(schema_tables)}

## Estado actual

- Corridas registradas: {summary['runs']}
- Inferencias estudiante-periodo registradas: {summary['student_inferences']}
- Estudiantes con historial: {summary['students']}

## Ultima corrida registrada

{markdown_table(latest)}

## Consulta historica

La API expone:

- `GET /cacei/segmentation/history`
- `GET /cacei/segmentation/history/{{execution_id}}`
- `GET /cacei/segmentation/students/{{id}}/history`

## Reglas de trazabilidad

- Cada corrida queda identificada por `execution_id`.
- Cada inferencia queda asociada a `execution_id`, `id_estudiante`, `id_periodo`, cluster, perfil y version de modelo.
- Se registra `model_version`, representacion, K, fechas UTC, parametros y metricas.
- Los perfiles siguen siendo apoyo tutorial/analitico, no diagnostico automatico definitivo.
"""


def run_phase_10() -> dict[str, Any]:
    result = persist_inference_snapshot(
        run_type="phase_10_snapshot",
        parameters={"source": "current_model_bundle", "phase": 10},
        notes="Snapshot inicial de persistencia formal de inferencias.",
    )
    summary = persistence_summary()
    report = build_report(summary, summary.get("latest_run"))
    write_markdown(INFERENCE_PERSISTENCE_REPORT, report)
    print("Fase 10 completada.")
    print(f"Execution ID: {result['execution_id']}")
    print(f"Inferencias registradas: {result['assignments_count']}")
    print(f"Base SQLite: {INFERENCE_HISTORY_DB}")
    print(f"Reporte: {INFERENCE_PERSISTENCE_REPORT}")
    return result


if __name__ == "__main__":
    run_phase_10()
