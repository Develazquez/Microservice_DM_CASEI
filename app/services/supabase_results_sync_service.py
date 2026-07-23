from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any
import uuid

import numpy as np
import pandas as pd

from app.repositories.supabase_repository import SupabaseRepository
from app.services.llm_context_service import rag_documents
from app.services.model_persistence_service import load_persisted_model_bundle
from app.services.model_bundle_inference_service import InferenceResult
from app.services.segmentation_api_service import current_manifest, jsonable, student_period_df, student_view


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sync_results_to_supabase(
    include_rag_documents: bool = True,
    max_rag_documents: int = 500,
    batch_size: int = 500,
    notes: str | None = None,
) -> dict[str, Any]:
    repository = SupabaseRepository()
    repository.require_configured()
    started_at = utc_now()
    execution_id = str(uuid.uuid4())
    batch_size = max(1, min(int(batch_size), 1000))
    max_rag_documents = max(0, min(int(max_rag_documents), 5000))

    loaded = load_persisted_model_bundle()
    manifest = loaded["manifest"]
    model = manifest["model"]
    model_version = str(manifest["model_version"])
    metrics = model.get("metrics", {})
    source_hash = build_source_hash(manifest)
    counts: dict[str, int] = {}

    try:
        repository.patch_rows("ml_model_versions", {"is_active": False}, {"is_active": "eq.true"})
        counts["ml_model_versions"] = repository.insert_rows(
            "ml_model_versions",
            [
                {
                    "model_version": model_version,
                    "algorithm": str(model.get("algorithm") or "kmeans"),
                    "selected_representation": model.get("selected_representation"),
                    "selected_k": int(model.get("selected_k")) if model.get("selected_k") is not None else None,
                    "metrics": jsonable(metrics),
                    "artifact_manifest": jsonable(manifest),
                    "is_active": True,
                }
            ],
            upsert=True,
            on_conflict="model_version",
        )

        repository.insert_rows(
            "ml_model_runs",
            [
                {
                    "execution_id": execution_id,
                    "model_version": model_version,
                    "run_type": "sync_to_supabase",
                    "status": "running",
                    "parameters": {
                        "include_rag_documents": include_rag_documents,
                        "max_rag_documents": max_rag_documents,
                        "batch_size": batch_size,
                        "notes": notes,
                    },
                    "metrics": jsonable(metrics),
                    "started_at": started_at,
                }
            ],
            upsert=True,
            on_conflict="execution_id",
        )
        counts["ml_model_runs"] = 1

        # Clean previous results so stale records (e.g. with missing names) don't persist.
        _clean_previous_results(repository, model_version, execution_id)
        counts["cleaned_previous"] = 1

        identities = repository.fetch_student_identity_lookup()
        programs = repository.fetch_program_lookup()
        features = student_period_df()
        view = student_view()

        feature_rows = build_feature_rows(
            features=features,
            execution_id=execution_id,
            source_hash=source_hash,
            identities=identities,
            programs=programs,
        )
        counts["student_period_features"] = insert_in_batches(
            repository,
            "student_period_features",
            feature_rows,
            batch_size=batch_size,
            upsert=True,
            on_conflict="execution_id,id_estudiante,id_periodo",
        )

        assignment_rows = build_assignment_rows(
            view=view,
            execution_id=execution_id,
            model_version=model_version,
            identities=identities,
            programs=programs,
        )
        counts["cluster_assignments"] = insert_in_batches(
            repository,
            "cluster_assignments",
            assignment_rows,
            batch_size=batch_size,
            upsert=True,
            on_conflict="execution_id,id_estudiante,id_periodo",
        )

        history_rows = build_profile_history_rows(
            view=view,
            execution_id=execution_id,
            model_version=model_version,
            identities=identities,
            programs=programs,
        )
        counts["student_profile_history"] = insert_in_batches(
            repository,
            "student_profile_history",
            history_rows,
            batch_size=batch_size,
        )

        rag_rows: list[dict[str, Any]] = []
        if include_rag_documents and max_rag_documents > 0:
            rag_rows = build_rag_document_rows(
                model_version=model_version,
                identities=identities,
                limit=max_rag_documents,
            )
            counts["rag_context_documents"] = insert_in_batches(
                repository,
                "rag_context_documents",
                rag_rows,
                batch_size=batch_size,
                upsert=True,
                on_conflict="document_id",
            )
        else:
            counts["rag_context_documents"] = 0

        finished_at = utc_now()
        repository.patch_rows(
            "ml_model_runs",
            {
                "status": "completed",
                "finished_at": finished_at,
                "duration_seconds": duration_seconds(started_at, finished_at),
                "parameters": {
                    "include_rag_documents": include_rag_documents,
                    "max_rag_documents": max_rag_documents,
                    "batch_size": batch_size,
                    "notes": notes,
                    "counts": counts,
                },
            },
            {"execution_id": f"eq.{execution_id}"},
        )

        return {
            "status": "completed",
            "execution_id": execution_id,
            "model_version": model_version,
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
            "duration_seconds": duration_seconds(started_at, finished_at),
            "source_hash": source_hash,
            "counts": counts,
            "active_model_version": model_version,
            "note": "Resultados ML publicados en Supabase PostgreSQL. Los artefactos locales se conservan como evidencia reproducible.",
        }
    except Exception as exc:
        try:
            repository.patch_rows(
                "ml_model_runs",
                {
                    "status": "failed",
                    "finished_at": utc_now(),
                    "error_message": str(exc),
                },
                {"execution_id": f"eq.{execution_id}"},
            )
        except Exception:
            pass
        raise


def ensure_model_version_registered(
    repository: SupabaseRepository,
    model_version: str,
    activate_if_missing: bool = True,
) -> dict[str, Any]:
    loaded = load_persisted_model_bundle(model_version)
    manifest = loaded["manifest"]
    model = manifest["model"]
    active_rows = repository.fetch_table(
        "ml_model_versions",
        select="model_version",
        filters={"is_active": "eq.true"},
        limit=1,
    )
    existing_rows = repository.fetch_table(
        "ml_model_versions",
        select="model_version,is_active",
        filters={"model_version": f"eq.{model_version}"},
        limit=1,
    )
    already_active = bool(existing_rows and existing_rows[0].get("is_active"))
    should_activate = activate_if_missing and not active_rows
    repository.insert_rows(
        "ml_model_versions",
        [
            {
                "model_version": model_version,
                "algorithm": str(model.get("algorithm") or "kmeans"),
                "selected_representation": model.get("selected_representation"),
                "selected_k": model.get("selected_k"),
                "metrics": jsonable(model.get("metrics") or {}),
                "artifact_manifest": jsonable(manifest),
                "is_active": already_active or should_activate,
            }
        ],
        upsert=True,
        on_conflict="model_version",
    )
    return {
        "model_version": model_version,
        "activated": already_active or should_activate,
        "active_model_version": (
            model_version
            if already_active or should_activate
            else str(active_rows[0]["model_version"]) if active_rows else None
        ),
    }


def publish_inference_result(
    result: InferenceResult,
    execution_id: str,
    source_hash: str,
) -> dict[str, int]:
    repository = SupabaseRepository()
    repository.require_configured()
    ensure_model_version_registered(repository, result.model_version)

    # Clean previous results so stale records don't persist across runs.
    _clean_previous_results(repository, result.model_version, execution_id)

    identities = repository.fetch_student_identity_lookup()
    programs = repository.fetch_program_lookup()
    feature_rows = build_feature_rows(
        features=result.features,
        execution_id=execution_id,
        source_hash=source_hash,
        identities=identities,
        programs=programs,
    )
    assignment_rows = build_assignment_rows(
        view=result.assignments,
        execution_id=execution_id,
        model_version=result.model_version,
        identities=identities,
        programs=programs,
    )
    history_rows = build_profile_history_rows(
        view=result.assignments,
        execution_id=execution_id,
        model_version=result.model_version,
        identities=identities,
        programs=programs,
    )
    counts = repository.rpc(
        "publish_ml_inference_results",
        {
            "target_execution_id": execution_id,
            "target_model_version": result.model_version,
            "feature_rows": feature_rows,
            "assignment_rows": assignment_rows,
            "history_rows": history_rows,
        },
    )
    return {key: int(value) for key, value in (counts or {}).items()}


def build_feature_rows(
    features: pd.DataFrame,
    execution_id: str,
    source_hash: str,
    identities: dict[str, dict[str, Any]],
    programs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scalar_columns = {
        "id_estudiante",
        "id_periodo",
        "programa",
        "cohorte",
        "estatus_academico",
        "promedio_general",
        "promedio_periodo",
        "porcentaje_avance",
        "porcentaje_asistencia",
        "rezago_materias",
    }
    for row in dataframe_rows(features):
        student_id = str(row.get("id_estudiante") or "")
        identity = identities.get(student_id, {})
        program_name = row.get("programa") or identity.get("carrera")
        program = programs.get(str(program_name), {})
        rows.append(
            clean_row(
                {
                    "execution_id": execution_id,
                    "student_profile_id": identity.get("id"),
                    "id_estudiante": student_id,
                    "id_periodo": row.get("id_periodo"),
                    "programa": program_name,
                    "program_id": identity.get("program_id") or program.get("id"),
                    "cohorte": row.get("cohorte"),
                    "estatus_academico": row.get("estatus_academico"),
                    "promedio_general": row.get("promedio_general"),
                    "promedio_periodo": row.get("promedio_periodo"),
                    "porcentaje_avance": row.get("porcentaje_avance"),
                    "porcentaje_asistencia": row.get("porcentaje_asistencia"),
                    "rezago_materias": row.get("rezago_materias"),
                    "sexo": normalize_sex(identity.get("sexo") or row.get("sexo")),
                    "features": {key: value for key, value in row.items() if key not in scalar_columns},
                    "source_hash": source_hash,
                }
            )
        )
    return rows


def build_assignment_rows(
    view: pd.DataFrame,
    execution_id: str,
    model_version: str,
    identities: dict[str, dict[str, Any]],
    programs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in dataframe_rows(view):
        student_id = str(row.get("id_estudiante") or "")
        identity = identities.get(student_id, {})
        program_name = row.get("programa") or identity.get("carrera")
        program = programs.get(str(program_name), {})
        rows.append(
            clean_row(
                {
                    "execution_id": execution_id,
                    "model_version": model_version,
                    "student_profile_id": identity.get("id"),
                    "id_estudiante": student_id,
                    "id_periodo": row.get("id_periodo"),
                    "programa": program_name,
                    "program_id": identity.get("program_id") or program.get("id"),
                    "sexo": normalize_sex(identity.get("sexo") or row.get("sexo")),
                    "cluster": row.get("cluster"),
                    "perfil_academico": row.get("perfil_academico"),
                    "prioridad_tutorial": row.get("prioridad_tutorial"),
                    "membership_score": row.get("membership_score"),
                    "distance_to_centroid": row.get("distance_to_centroid"),
                    "pc1": row.get("PC1") or row.get("pc1"),
                    "pc2": row.get("PC2") or row.get("pc2"),
                }
            )
        )
    return rows


def build_profile_history_rows(
    view: pd.DataFrame,
    execution_id: str,
    model_version: str,
    identities: dict[str, dict[str, Any]],
    programs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in dataframe_rows(view):
        student_id = str(row.get("id_estudiante") or "")
        identity = identities.get(student_id, {})
        program_name = row.get("programa") or identity.get("carrera")
        program = programs.get(str(program_name), {})
        summary = {
            "promedio_general": row.get("promedio_general"),
            "promedio_periodo": row.get("promedio_periodo"),
            "porcentaje_asistencia": row.get("porcentaje_asistencia"),
            "porcentaje_avance": row.get("porcentaje_avance"),
            "materias_reprobadas_periodo": row.get("materias_reprobadas_periodo"),
            "materias_reprobadas_acumuladas": row.get("materias_reprobadas_acumuladas"),
            "rezago_materias": row.get("rezago_materias"),
            "membership_score": row.get("membership_score"),
            "distance_to_centroid": row.get("distance_to_centroid"),
            "lectura_funcional": row.get("lectura_funcional"),
            "acciones_sugeridas": row.get("acciones_sugeridas"),
            "cautela_interpretacion": row.get("cautela_interpretacion"),
        }
        rows.append(
            clean_row(
                {
                    "execution_id": execution_id,
                    "model_version": model_version,
                    "student_profile_id": identity.get("id"),
                    "id_estudiante": student_id,
                    "id_periodo": row.get("id_periodo"),
                    "programa": program_name,
                    "program_id": identity.get("program_id") or program.get("id"),
                    "sexo": normalize_sex(identity.get("sexo") or row.get("sexo")),
                    "cluster": row.get("cluster"),
                    "perfil_academico": row.get("perfil_academico"),
                    "prioridad_tutorial": row.get("prioridad_tutorial"),
                    "summary": clean_row(summary),
                }
            )
        )
    return rows


def build_rag_document_rows(
    model_version: str,
    identities: dict[str, dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    response = rag_documents(role="director", limit=limit, offset=0)
    rows: list[dict[str, Any]] = []
    for item in response.get("items", []):
        metadata = item.get("metadata", {}) or {}
        student_id = metadata.get("student_reference")
        identity = identities.get(str(student_id), {})
        rows.append(
            clean_row(
                {
                    "document_id": item.get("document_id"),
                    "student_reference": item.get("metadata", {}).get("student_reference") or str(student_id),
                    "student_profile_id": identity.get("id"),
                    "id_estudiante": student_id,
                    "id_periodo": metadata.get("latest_period"),
                    "model_version": metadata.get("model_version") or model_version,
                    "retrieval_title": item.get("retrieval_title"),
                    "retrieval_text": item.get("retrieval_text"),
                    "metadata": metadata,
                    "allowed_use": item.get("allowed_use", []),
                    "forbidden_use": item.get("forbidden_use", []),
                }
            )
        )
    return rows


def insert_in_batches(
    repository: SupabaseRepository,
    table: str,
    rows: list[dict[str, Any]],
    batch_size: int,
    upsert: bool = False,
    on_conflict: str | None = None,
) -> int:
    inserted = 0
    for index in range(0, len(rows), batch_size):
        inserted += repository.insert_rows(
            table,
            rows[index : index + batch_size],
            upsert=upsert,
            on_conflict=on_conflict,
        )
    return inserted


def dataframe_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    return jsonable(df.replace({np.nan: None}).to_dict(orient="records"))


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: clean_value(value) for key, value in row.items()}


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    if isinstance(value, np.generic):
        return clean_value(value.item())
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return value


def _clean_previous_results(
    repository: SupabaseRepository,
    model_version: str,
    current_execution_id: str,
) -> None:
    """Delete stale segmentation results from previous runs of the same model version."""
    old_runs = repository.fetch_table(
        "ml_model_runs",
        select="execution_id",
        filters={
            "model_version": f"eq.{model_version}",
            "execution_id": f"neq.{current_execution_id}",
        },
        limit=1000,
    )
    repository.delete_rows("cluster_assignments", {"model_version": f"eq.{model_version}"})
    repository.delete_rows("student_profile_history", {"model_version": f"eq.{model_version}"})
    for old_run in (old_runs or []):
        old_eid = old_run.get("execution_id")
        if old_eid:
            repository.delete_rows("student_period_features", {"execution_id": f"eq.{old_eid}"})


def normalize_sex(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    return text if text in {"M", "F"} else None


def build_source_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(jsonable(manifest), ensure_ascii=False, sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def duration_seconds(started_at: str, finished_at: str) -> float:
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    return round((finish - start).total_seconds(), 3)
