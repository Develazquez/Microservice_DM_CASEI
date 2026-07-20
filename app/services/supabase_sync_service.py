from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import shutil
from typing import Any

import pandas as pd

from app.models.config import (
    ACTIVE_DATASET_POINTER,
    DATASET_VERSION_DIR,
    FINAL_FEATURES,
    RAW_CARDEX_DATASET,
    STUDENT_PERIOD_DATASET,
    SUPABASE_SNAPSHOT_REGISTRY_DIR,
    SUPABASE_SOURCE_SNAPSHOT,
    SUPABASE_STUDENT_PERIOD_PREVIEW,
    SUPABASE_SYNC_VALIDATION_REPORT,
)
from app.repositories.factory import repository_status
from app.repositories.supabase_repository import SupabaseRepository
from app.services.cardex_student_period_feature_service import build_student_period_features
from app.services.model_persistence_service import load_persisted_model_bundle
from app.services.segmentation_api_service import jsonable


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def supabase_sync_status() -> dict[str, Any]:
    repository = SupabaseRepository()
    return {
        "status": "configured" if repository.configured else "missing_configuration",
        "repository": repository.configuration_status(),
        "repository_selection": repository_status(),
        "snapshot_path": str(SUPABASE_SOURCE_SNAPSHOT),
        "preview_path": str(SUPABASE_STUDENT_PERIOD_PREVIEW),
        "validation_report_path": str(SUPABASE_SYNC_VALIDATION_REPORT),
    }


def sync_from_supabase(limit: int = 1000, write_preview: bool = True) -> dict[str, Any]:
    repository = SupabaseRepository()
    started_at = utc_now()
    source = repository.fetch_academic_source_data(limit=limit)
    snapshot_hash = source_hash(source)
    preview = build_student_period_preview(source)
    validation = validate_against_local_sources(source=source, preview=preview, source_hash=snapshot_hash)

    SUPABASE_SOURCE_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SUPABASE_SOURCE_SNAPSHOT.write_text(
        json.dumps(
            jsonable(
                {
                    "generated_at_utc": started_at,
                    "source_hash": snapshot_hash,
                    "counts": {name: len(rows) for name, rows in source.items()},
                    "source": source,
                    "validation": validation,
                }
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if write_preview:
        SUPABASE_STUDENT_PERIOD_PREVIEW.parent.mkdir(parents=True, exist_ok=True)
        preview.to_csv(SUPABASE_STUDENT_PERIOD_PREVIEW, index=False)

    version_dir = SUPABASE_SNAPSHOT_REGISTRY_DIR / snapshot_hash
    version_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SUPABASE_SOURCE_SNAPSHOT, version_dir / "source.json")
    if write_preview:
        shutil.copy2(SUPABASE_STUDENT_PERIOD_PREVIEW, version_dir / "student_period_features.csv")

    write_validation_report(validation, started_at=started_at)

    return {
        "status": "completed",
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "source_hash": snapshot_hash,
        "counts": {name: len(rows) for name, rows in source.items()},
        "preview_records": int(len(preview)),
        "snapshot_path": str(SUPABASE_SOURCE_SNAPSHOT),
        "preview_path": str(SUPABASE_STUDENT_PERIOD_PREVIEW) if write_preview else None,
        "validation_report_path": str(SUPABASE_SYNC_VALIDATION_REPORT),
        "validation": validation,
        "versioned_snapshot_path": str(version_dir),
        "active_dataset_replaced": False,
        "note": (
            "La sincronizacion genera una vista preliminar desde Supabase; "
            "no reemplaza data/processed/student_period_features.csv hasta validacion academica."
        ),
    }


def source_hash(source: dict[str, list[dict[str, Any]]]) -> str:
    payload = json.dumps(jsonable(source), ensure_ascii=False, sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def build_student_period_preview(source: dict[str, list[dict[str, Any]]]) -> pd.DataFrame:
    cardex = build_cardex_from_supabase(source)
    if cardex.empty:
        return empty_preview()
    grouped = build_student_period_features(cardex)
    identities = {
        str(row.get("matricula")): row
        for row in source.get("profiles", [])
        if row.get("matricula")
    }
    grouped["student_profile_id"] = grouped["id_estudiante"].map(
        lambda value: identities.get(str(value), {}).get("id")
    )
    grouped["program_id"] = grouped["id_estudiante"].map(
        lambda value: identities.get(str(value), {}).get("program_id")
    )
    grouped["sexo"] = grouped["id_estudiante"].map(
        lambda value: identities.get(str(value), {}).get("sexo")
    )
    return grouped


def build_cardex_from_supabase(source: dict[str, list[dict[str, Any]]]) -> pd.DataFrame:
    profiles = {row["id"]: row for row in source.get("profiles", []) if row.get("id")}
    periodos = {row["id"]: row for row in source.get("periodos", []) if row.get("id")}
    materias = {row["id"]: row for row in source.get("materias", []) if row.get("id")}
    programs = {row["id"]: row for row in source.get("academic_programs", []) if row.get("id")}
    records: list[dict[str, Any]] = []

    academic_rows = list(source.get("historial_academico", []))
    if not academic_rows:
        academic_rows = [
            {
                "student_id": row.get("alumno_id"),
                "subject_id": row.get("materia_id"),
                "period_id": row.get("periodo_id"),
                "grade": row.get("calificacion_final"),
                "calificacion_extra": row.get("calificacion_extraordinario"),
                "status": row.get("estatus"),
                "attempt_type": "carga_academica",
            }
            for row in source.get("carga_academica", [])
        ]

    for item in academic_rows:
        student = profiles.get(item.get("student_id"))
        if not student or not student.get("matricula"):
            continue
        materia = materias.get(item.get("subject_id")) or {}
        periodo = periodos.get(item.get("period_id")) or {}
        program = programs.get(student.get("program_id")) or {}
        period_key = periodo.get("clave") or periodo.get("nombre") or item.get("period_id") or "SIN_PERIODO"
        status = str(item.get("status") or "").lower()
        if "reprob" in status:
            subject_status = "Reprobada"
        elif "curs" in status:
            subject_status = "Cursando"
        elif "baja" in status:
            subject_status = "Baja"
        else:
            subject_status = "Aprobada"
        records.append(
            {
                "Matricula": student.get("matricula"),
                "Carrera": student.get("carrera") or program.get("nombre") or "SIN_PROGRAMA",
                "EstatusAlumno": student.get("estatus_academico") or "Regular",
                "CuatrimestreActual": student.get("cuatrimestre_actual") or 1,
                "Materia": materia.get("nombre") or materia.get("clave") or item.get("subject_id"),
                "Periodo": period_key,
                "EstatusMateria": subject_status,
                "Final": item.get("grade"),
                "Extr": item.get("calificacion_extra"),
                "EstatusCardex": item.get("attempt_type") or "ordinario",
                "PeriodoCursado": period_key,
                "PlanEstudiosClave": program.get("clave") or "PLAN-INSTITUCIONAL",
                "Credito": materia.get("creditos") or 0,
            }
        )
    return pd.DataFrame(records)


def promote_supabase_preview(expected_source_hash: str, reviewed_by: str | None = None) -> dict[str, Any]:
    if not SUPABASE_SOURCE_SNAPSHOT.exists() or not SUPABASE_STUDENT_PERIOD_PREVIEW.exists():
        raise FileNotFoundError("No existe un snapshot Supabase pendiente de promocion.")
    snapshot = json.loads(SUPABASE_SOURCE_SNAPSHOT.read_text(encoding="utf-8"))
    actual_hash = str(snapshot.get("source_hash") or "")
    if not expected_source_hash or expected_source_hash != actual_hash:
        raise ValueError("El source_hash solicitado no coincide con el ultimo snapshot validado.")
    validation = snapshot.get("validation") or {}
    decision = validation.get("decision") or {}
    if not decision.get("ready_to_replace_active_dataset"):
        warnings = validation.get("warnings") or []
        raise ValueError("El snapshot tiene errores bloqueantes y no puede promoverse: " + "; ".join(warnings))

    preview = pd.read_csv(SUPABASE_STUDENT_PERIOD_PREVIEW)
    loaded = load_persisted_model_bundle()
    required_features = list(loaded["manifest"]["preprocessing"]["input_features"])
    missing_features = sorted(set(required_features) - set(preview.columns))
    if missing_features:
        raise ValueError("El snapshot no cumple el contrato del modelo activo. Faltan: " + ", ".join(missing_features))
    if preview.empty:
        raise ValueError("No se puede promover un snapshot vacio.")

    DATASET_VERSION_DIR.mkdir(parents=True, exist_ok=True)
    previous_backup = None
    if STUDENT_PERIOD_DATASET.exists():
        previous_hash = sha256(STUDENT_PERIOD_DATASET.read_bytes()).hexdigest()
        previous_backup = DATASET_VERSION_DIR / f"{previous_hash}.csv"
        if not previous_backup.exists():
            shutil.copy2(STUDENT_PERIOD_DATASET, previous_backup)

    temporary = STUDENT_PERIOD_DATASET.with_suffix(".promoting.csv")
    preview.to_csv(temporary, index=False)
    os.replace(temporary, STUDENT_PERIOD_DATASET)
    pointer = {
        "source": "supabase",
        "source_hash": actual_hash,
        "promoted_at_utc": utc_now(),
        "reviewed_by": reviewed_by,
        "dataset_path": str(STUDENT_PERIOD_DATASET),
        "snapshot_path": str(SUPABASE_SNAPSHOT_REGISTRY_DIR / actual_hash),
        "previous_dataset_backup": str(previous_backup) if previous_backup else None,
        "records": int(len(preview)),
    }
    ACTIVE_DATASET_POINTER.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_DATASET_POINTER.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "promoted", **pointer}


def detail_rows_from_historial(
    source: dict[str, list[dict[str, Any]]],
    profiles: dict[str, dict[str, Any]],
    periodos: dict[str, dict[str, Any]],
    materias: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in source.get("historial_academico", []):
        student = profiles.get(item.get("student_id"))
        if not student:
            continue
        materia = materias.get(item.get("subject_id")) or {}
        grade = numeric(item.get("grade"))
        extra = numeric(item.get("calificacion_extra"))
        final_grade = extra if extra is not None and extra >= 70 else grade
        rows.append(source_detail_row(student, periodos.get(item.get("period_id")) or {}, materia, item, final_grade))
    return rows


def detail_rows_from_carga(
    source: dict[str, list[dict[str, Any]]],
    profiles: dict[str, dict[str, Any]],
    periodos: dict[str, dict[str, Any]],
    materias: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in source.get("carga_academica", []):
        student = profiles.get(item.get("alumno_id"))
        if not student:
            continue
        materia = materias.get(item.get("materia_id")) or {}
        grade = numeric(item.get("calificacion_final"))
        extra = numeric(item.get("calificacion_extraordinario"))
        final_grade = extra if extra is not None and extra >= 70 else grade
        normalized = {
            "period_id": item.get("periodo_id"),
            "subject_id": item.get("materia_id"),
            "status": item.get("estatus"),
            "attempt_type": "carga_academica",
        }
        rows.append(source_detail_row(student, periodos.get(item.get("periodo_id")) or {}, materia, normalized, final_grade))
    return rows


def source_detail_row(
    student: dict[str, Any],
    periodo: dict[str, Any],
    materia: dict[str, Any],
    item: dict[str, Any],
    final_grade: float | None,
) -> dict[str, Any]:
    return {
        "id_estudiante": student.get("matricula") or student.get("id"),
        "student_profile_id": student.get("id"),
        "id_periodo": periodo.get("clave") or periodo.get("nombre") or item.get("period_id") or "SIN_PERIODO",
        "programa": student.get("carrera"),
        "program_id": student.get("program_id"),
        "sexo": student.get("sexo"),
        "cohorte": infer_cohort(student.get("matricula")),
        "estatus_academico": student.get("estatus_academico"),
        "materia_id": item.get("subject_id"),
        "materia": materia.get("nombre"),
        "creditos": numeric(materia.get("creditos")) or 0,
        "calificacion": final_grade,
        "estatus_materia": item.get("status"),
        "attempt_type": item.get("attempt_type"),
    }


def empty_preview() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "id_estudiante",
            "id_periodo",
            "programa",
            "student_profile_id",
            "program_id",
            "sexo",
            "cohorte",
            "estatus_academico",
            "promedio_general",
            "promedio_periodo",
            "materias_aprobadas",
            "materias_reprobadas_periodo",
            "materias_reprobadas_acumuladas",
            "creditos_aprobados_periodo",
            "creditos_inscritos_periodo",
            "porcentaje_avance",
            "bandera_dato_incompleto",
        ]
    )


def validate_against_local_sources(
    source: dict[str, list[dict[str, Any]]],
    preview: pd.DataFrame,
    source_hash: str,
) -> dict[str, Any]:
    active = pd.read_csv(STUDENT_PERIOD_DATASET) if STUDENT_PERIOD_DATASET.exists() else pd.DataFrame()
    raw = pd.read_csv(RAW_CARDEX_DATASET) if RAW_CARDEX_DATASET.exists() else pd.DataFrame()

    active_columns = set(active.columns)
    preview_columns = set(preview.columns)
    active_students = normalized_unique(active, "id_estudiante")
    preview_students = normalized_unique(preview, "id_estudiante")
    overlap_students = active_students & preview_students

    required_preview_columns = {
        "id_estudiante",
        "id_periodo",
        "programa",
        "sexo",
        "student_profile_id",
        "program_id",
        "promedio_general",
        "promedio_periodo",
        "materias_reprobadas_periodo",
        "materias_reprobadas_acumuladas",
        "creditos_inscritos_periodo",
        "creditos_aprobados_periodo",
        "bandera_dato_incompleto",
        *FINAL_FEATURES,
    }
    warnings = sync_warnings(source=source, preview=preview)

    validation = {
        "generated_at_utc": utc_now(),
        "source_hash": source_hash,
        "source_counts": {name: len(rows) for name, rows in source.items()},
        "local_raw_cardex": {
            "path": str(RAW_CARDEX_DATASET),
            "exists": RAW_CARDEX_DATASET.exists(),
            "rows": int(len(raw)),
            "students": int(raw["Matricula"].nunique()) if "Matricula" in raw.columns else 0,
        },
        "active_student_period_dataset": {
            "path": str(STUDENT_PERIOD_DATASET),
            "exists": STUDENT_PERIOD_DATASET.exists(),
            "rows": int(len(active)),
            "students": int(len(active_students)),
            "columns": sorted(active_columns),
        },
        "supabase_preview": {
            "path": str(SUPABASE_STUDENT_PERIOD_PREVIEW),
            "rows": int(len(preview)),
            "students": int(len(preview_students)),
            "columns": sorted(preview_columns),
            "missing_required_columns": sorted(required_preview_columns - preview_columns),
            "null_rates": null_rates(preview),
        },
        "comparison": {
            "student_overlap": int(len(overlap_students)),
            "student_overlap_ratio_vs_active": ratio(len(overlap_students), len(active_students)),
            "student_overlap_ratio_vs_preview": ratio(len(overlap_students), len(preview_students)),
            "columns_missing_vs_active": sorted(active_columns - preview_columns),
            "extra_columns_vs_active": sorted(preview_columns - active_columns),
            "record_delta_vs_active": int(len(preview) - len(active)),
        },
        "warnings": warnings,
        "decision": {
            "active_dataset_replaced": False,
            "ready_to_replace_active_dataset": bool(len(preview) > 0 and not (required_preview_columns - preview_columns) and not warnings),
            "requires_academic_review": True,
        },
    }
    return jsonable(validation)


def sync_warnings(source: dict[str, list[dict[str, Any]]], preview: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    role_counts = source.get("profile_role_counts", [])
    alumno_count = sum(int(row.get("profiles") or 0) for row in role_counts if str(row.get("rol")) == "alumno")
    if alumno_count == 0:
        warnings.append("Supabase no devolvio perfiles con rol=alumno; no se puede construir una vista alumno-periodo real.")
    if not source.get("historial_academico") and not source.get("carga_academica"):
        warnings.append("Supabase no devolvio historial_academico ni carga_academica; faltan registros academicos base.")
    if not source.get("materias"):
        warnings.append("Supabase no devolvio materias; creditos y nombres de asignatura quedan incompletos.")
    if not source.get("periodos"):
        warnings.append("Supabase no devolvio periodos; los IDs de periodo no pueden normalizarse.")
    if preview.empty:
        warnings.append("El preview alumno-periodo quedo vacio; el dataset local activo se conserva sin cambios.")
    return warnings


def write_validation_report(validation: dict[str, Any], started_at: str) -> None:
    SUPABASE_SYNC_VALIDATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    source_counts = validation["source_counts"]
    comparison = validation["comparison"]
    preview = validation["supabase_preview"]
    active = validation["active_student_period_dataset"]
    raw = validation["local_raw_cardex"]
    lines = [
        "# Reporte de validacion de sincronizacion Supabase",
        "",
        f"Generado: {started_at}",
        f"Hash de fuente: `{validation['source_hash']}`",
        "",
        "## Conteos de fuente Supabase",
        "",
    ]
    lines.extend(f"- {name}: {count}" for name, count in sorted(source_counts.items()))
    lines.extend(
        [
            "",
            "## Comparacion local",
            "",
            f"- Dataset cardex local: {raw['rows']} filas, {raw['students']} estudiantes.",
            f"- Dataset alumno-periodo activo: {active['rows']} registros, {active['students']} estudiantes.",
            f"- Preview Supabase alumno-periodo: {preview['rows']} registros, {preview['students']} estudiantes.",
            f"- Traslape de estudiantes contra activo: {comparison['student_overlap']} ({comparison['student_overlap_ratio_vs_active']}).",
            f"- Diferencia de registros preview - activo: {comparison['record_delta_vs_active']}.",
            "",
            "## Columnas",
            "",
            f"- Columnas requeridas faltantes en preview: {', '.join(preview['missing_required_columns']) or 'ninguna'}.",
            f"- Columnas del activo que aun no existen en preview: {', '.join(comparison['columns_missing_vs_active']) or 'ninguna'}.",
            f"- Columnas extra del preview: {', '.join(comparison['extra_columns_vs_active']) or 'ninguna'}.",
            "",
            "## Advertencias",
            "",
            *(f"- {warning}" for warning in validation.get("warnings", [])),
            "" if validation.get("warnings") else "- ninguna",
            "",
            "## Decision operativa",
            "",
            "El dataset activo no fue reemplazado. La salida de Supabase queda como preview hasta validacion academica.",
        ]
    )
    SUPABASE_SYNC_VALIDATION_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalized_unique(df: pd.DataFrame, column: str) -> set[str]:
    if df.empty or column not in df.columns:
        return set()
    return {str(value).strip().upper() for value in df[column].dropna().unique() if str(value).strip()}


def null_rates(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {}
    interesting = [
        "id_estudiante",
        "id_periodo",
        "programa",
        "sexo",
        "student_profile_id",
        "program_id",
        "promedio_periodo",
    ]
    return {
        column: round(float(df[column].isna().mean()), 4)
        for column in interesting
        if column in df.columns
    }


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_cohort(matricula: Any) -> str | None:
    text = str(matricula or "")
    for index in range(0, max(len(text) - 3, 0)):
        candidate = text[index : index + 4]
        if candidate.isdigit() and candidate.startswith("20"):
            return candidate
    return None
