from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import time
from typing import Any
import uuid

import numpy as np
import pandas as pd

from app.models.config import (
    ACTIVE_INFERENCE_METADATA,
    ACTIVE_INFERENCE_SNAPSHOT,
    API_HISTORY_PATH,
    ARTIFACTS_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    STUDENT_PERIOD_DATASET,
)
from app.services.academic_bm25_search_service import load_search_documents, run_search_engine
from app.services.academic_search_orchestrator_service import search_academic_documents
from app.services.academic_semantic_embedding_service import build_and_persist_semantic_index
from app.models.search_config import CASEI_SEMANTIC_SEARCH_ENABLED
from app.services.clustering_training_evaluation_service import run_phase_5_6
from app.services.exploratory_analysis_feature_engineering_pca_service import main as run_phase_2_4
from app.services.inference_persistence_service import (
    get_inference_run,
    get_student_inference_history,
    list_inference_runs,
    persist_inference_snapshot,
    persistence_summary,
)
from app.services.model_persistence_service import (
    load_persisted_model_bundle,
    persist_current_model_bundle,
    validate_loaded_contract,
)
from app.services.profile_interpretation_service import run_phase_7
from app.services.security_audit_service import SecurityContext, apply_student_scope


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
    if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
        return None
    return value


def dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.replace({np.nan: None})
    return jsonable(clean.to_dict(orient="records"))


def append_history(event: dict[str, Any]) -> None:
    API_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with API_HISTORY_PATH.open("a", encoding="utf-8") as target:
        target.write(json.dumps(jsonable(event), ensure_ascii=False) + "\n")


def read_history(limit: int = 20, student_id: str | None = None) -> list[dict[str, Any]]:
    return list_inference_runs(limit=limit, student_id=student_id)


def history_detail(execution_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any] | None:
    return get_inference_run(execution_id=execution_id, limit=limit, offset=offset)


def student_history(student_id: str, limit: int = 100) -> dict[str, Any]:
    return get_student_inference_history(student_id=student_id, limit=limit)


def history_summary() -> dict[str, Any]:
    return persistence_summary()


def current_loaded_bundle() -> dict[str, Any]:
    return load_persisted_model_bundle()


def current_manifest() -> dict[str, Any]:
    return current_loaded_bundle()["manifest"]


def health_status() -> dict[str, Any]:
    try:
        loaded = current_loaded_bundle()
        checks = validate_loaded_contract(loaded)
        checks_passed = bool(checks["passed"].all())
        manifest = loaded["manifest"]
        status = "ok" if checks_passed else "degraded"
        return {
            "status": status,
            "service": "academic-segmentation",
            "api_version": "v1",
            "model_version": manifest["model_version"],
            "selected_representation": manifest["model"]["selected_representation"],
            "selected_k": manifest["model"]["selected_k"],
            "checks_passed": checks_passed,
            "checked_at_utc": utc_now(),
        }
    except Exception as exc:  # pragma: no cover - surfaced by HTTP health.
        return {
            "status": "degraded",
            "service": "academic-segmentation",
            "api_version": "v1",
            "error": str(exc),
            "checked_at_utc": utc_now(),
        }


def profile_catalog_df(loaded: dict[str, Any]) -> pd.DataFrame:
    profiles = pd.DataFrame(loaded["profile_catalog"])
    if profiles.empty:
        return pd.DataFrame(columns=["cluster", "perfil_academico"])
    return profiles


def student_period_df() -> pd.DataFrame:
    if not STUDENT_PERIOD_DATASET.exists():
        raise FileNotFoundError(f"Student-period dataset not found: {STUDENT_PERIOD_DATASET}")
    return pd.read_csv(STUDENT_PERIOD_DATASET)


def pca_coordinates_df() -> pd.DataFrame:
    pca_path = PROCESSED_DIR / "pca_scores.csv"
    if not pca_path.exists():
        return pd.DataFrame(columns=["id_estudiante", "id_periodo", "PC1", "PC2"])
    pca = pd.read_csv(pca_path)
    columns = [column for column in ["id_estudiante", "id_periodo", "PC1", "PC2"] if column in pca.columns]
    return pca[columns]


def student_view() -> pd.DataFrame:
    loaded = current_loaded_bundle()
    assignments = loaded["cluster_assignments"].copy()
    if ACTIVE_INFERENCE_SNAPSHOT.exists() and ACTIVE_INFERENCE_METADATA.exists():
        active_metadata = json.loads(ACTIVE_INFERENCE_METADATA.read_text(encoding="utf-8"))
        if active_metadata.get("model_version") == loaded["manifest"]["model_version"]:
            assignments = pd.read_csv(ACTIVE_INFERENCE_SNAPSHOT)
    features = student_period_df()
    keys = ["id_estudiante", "id_periodo"]
    feature_columns = keys + [column for column in features.columns if column not in assignments.columns]
    view = assignments.merge(
        features[feature_columns],
        on=keys,
        how="left",
    )

    profiles = profile_catalog_df(loaded)
    profile_columns = [
        column
        for column in [
            "cluster",
            "perfil_academico",
            "prioridad_tutorial",
            "lectura_funcional",
            "acciones_sugeridas",
            "cautela_interpretacion",
        ]
        if column in profiles.columns
    ]
    if profile_columns and "perfil_academico" not in view.columns:
        view = view.merge(profiles[profile_columns], on="cluster", how="left")

    pca = pca_coordinates_df()
    if not pca.empty and "PC1" not in view.columns:
        view = view.merge(pca, on=["id_estudiante", "id_periodo"], how="left")

    return view


def segmentation_summary(security_context: SecurityContext | None = None) -> dict[str, Any]:
    loaded = current_loaded_bundle()
    manifest = loaded["manifest"]
    students = apply_student_scope(student_view(), security_context)
    profiles = profile_catalog_df(loaded)
    metrics = manifest["model"].get("metrics", {})
    follow_up = students["prioridad_tutorial"].fillna("").str.lower().ne("baja-media")

    profile_distribution = (
        students.groupby(["cluster", "perfil_academico", "prioridad_tutorial"], dropna=False)
        .size()
        .reset_index(name="registros")
        .sort_values("cluster")
    )
    program_distribution = (
        students.groupby("programa", dropna=False)
        .agg(estudiantes=("id_estudiante", "nunique"), registros=("id_estudiante", "count"))
        .reset_index()
        .sort_values("programa")
    )

    return jsonable(
        {
            "model_version": manifest["model_version"],
            "selected_representation": manifest["model"]["selected_representation"],
            "selected_k": manifest["model"]["selected_k"],
            "metrics": metrics,
            "total_students": int(students["id_estudiante"].nunique()),
            "total_records": int(len(students)),
            "average_score": float(students["promedio_general"].mean()),
            "average_attendance": float(students["porcentaje_asistencia"].mean()),
            "students_in_follow_up": int(students.loc[follow_up, "id_estudiante"].nunique()),
            "records_in_follow_up": int(follow_up.sum()),
            "profile_distribution": dataframe_records(profile_distribution),
            "program_distribution": dataframe_records(program_distribution),
            "profiles": dataframe_records(profiles),
            "warnings": manifest.get("warnings", []),
        }
    )


def filtered_students(
    perfil: str | None = None,
    programa: str | None = None,
    cluster: int | None = None,
    student_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    security_context: SecurityContext | None = None,
) -> dict[str, Any]:
    students = apply_student_scope(student_view(), security_context)
    if perfil:
        students = students[students["perfil_academico"].fillna("").str.contains(perfil, case=False, na=False)]
    if programa:
        students = students[students["programa"].fillna("").str.contains(programa, case=False, na=False)]
    if cluster is not None:
        students = students[students["cluster"] == cluster]
    if student_id:
        students = students[students["id_estudiante"].fillna("").str.upper() == student_id.upper()]

    total = len(students)
    students = students.sort_values(["id_estudiante", "id_periodo"]).iloc[offset : offset + limit]
    return {
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
        "items": dataframe_records(students),
    }


def student_detail(student_id: str, security_context: SecurityContext | None = None) -> dict[str, Any] | None:
    result = filtered_students(student_id=student_id, limit=500, offset=0, security_context=security_context)
    if result["total"] == 0:
        return None
    items = result["items"]
    latest = items[-1] if items else None
    return {
        "id_estudiante": student_id,
        "total_records": result["total"],
        "latest_record": latest,
        "records": items,
    }


def cluster_catalog() -> dict[str, Any]:
    loaded = current_loaded_bundle()
    bundle_dir = ARTIFACTS_DIR / "model_registry" / loaded["manifest"]["model_version"]
    centroids = loaded["kmeans_centroids"]
    profiles = profile_catalog_df(loaded)
    summary_path = bundle_dir / "evaluation" / "cluster_summary.csv"
    differences_path = bundle_dir / "profiles" / "cluster_feature_differences.csv"
    summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    differences = pd.read_csv(differences_path) if differences_path.exists() else pd.DataFrame()
    if not differences.empty:
        differences["abs_diff"] = differences["diferencia_estandarizada"].abs()
        differences = differences.sort_values(["cluster", "abs_diff"], ascending=[True, False]).drop(columns="abs_diff")

    return {
        "model_version": loaded["manifest"]["model_version"],
        "profiles": dataframe_records(profiles),
        "centroids": dataframe_records(centroids),
        "summary": dataframe_records(summary),
        "top_feature_differences": dataframe_records(differences.groupby("cluster").head(8) if not differences.empty else differences),
    }


def search_students(
    query: str,
    top_k: int = 10,
    security_context: SecurityContext | None = None,
    mode: str | None = None,
    programa: str | None = None,
    perfil: str | None = None,
    sexo: str | None = None,
    retrieval: str | None = None,
    explain: bool | None = None,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("La consulta no puede estar vacia.")
    documents = apply_student_scope(load_search_documents(), security_context)
    search_result = search_academic_documents(
        documents=documents,
        query=query,
        top_k=top_k,
        mode=mode,
        programa=programa,
        perfil=perfil,
        sexo=sexo,
        retrieval=retrieval,
        explain=explain,
    )
    return {
        "query": query,
        "top_k": int(top_k),
        "total_indexed": int(len(documents)),
        "items": dataframe_records(search_result["results"]),
        "search_metadata": search_result["metadata"],
    }


def run_segmentation(mode: str, persist_model: bool = True, refresh_search_index: bool = False, notes: str | None = None) -> dict[str, Any]:
    execution_id = str(uuid.uuid4())
    started_at = utc_now()
    start = time.perf_counter()
    steps: list[str] = []
    status = "completed"
    error: str | None = None

    try:
        if mode == "retrain_local":
            run_phase_2_4()
            steps.append("phase_2_4")
            run_phase_5_6()
            steps.append("phase_5_6")
            run_phase_7()
            steps.append("phase_7")
            if persist_model:
                persist_current_model_bundle()
                steps.append("phase_8_persist")
        elif mode == "load_existing":
            loaded = current_loaded_bundle()
            checks = validate_loaded_contract(loaded)
            if not checks["passed"].all():
                raise ValueError("El bundle activo no paso la validacion de carga.")
            steps.append("load_current_model")
        else:
            raise ValueError(f"Modo no soportado: {mode}")

        if refresh_search_index:
            run_search_engine()
            steps.append("refresh_search_index")
            if CASEI_SEMANTIC_SEARCH_ENABLED:
                build_and_persist_semantic_index(load_search_documents())
                steps.append("refresh_semantic_search_index")

        manifest = current_manifest()
        summary = segmentation_summary()
        finished_at = utc_now()
        persistence = persist_inference_snapshot(
            execution_id=execution_id,
            run_type=f"api_{mode}",
            status=status,
            parameters={
                "mode": mode,
                "persist_model": persist_model,
                "refresh_search_index": refresh_search_index,
                "steps": steps,
            },
            notes=notes,
            started_at_utc=started_at,
            finished_at_utc=finished_at,
            duration_seconds=round(time.perf_counter() - start, 3),
        )
        steps.append("phase_10_inference_persist")
        output = {
            "execution_id": execution_id,
            "status": status,
            "mode": mode,
            "steps": steps,
            "started_at_utc": started_at,
            "finished_at_utc": utc_now(),
            "duration_seconds": round(time.perf_counter() - start, 3),
            "model_version": manifest["model_version"],
            "inference_persistence": persistence,
            "summary": {
                "total_students": summary["total_students"],
                "total_records": summary["total_records"],
                "selected_k": summary["selected_k"],
                "selected_representation": summary["selected_representation"],
            },
        }
    except Exception as exc:
        status = "failed"
        error = str(exc)
        output = {
            "execution_id": execution_id,
            "status": status,
            "mode": mode,
            "steps": steps,
            "started_at_utc": started_at,
            "finished_at_utc": utc_now(),
            "duration_seconds": round(time.perf_counter() - start, 3),
            "error": error,
        }

    append_history(
        {
            "execution_id": execution_id,
            "event": "segmentation_run",
            "status": status,
            "mode": mode,
            "steps": steps,
            "notes": notes,
            "persist_model": persist_model,
            "refresh_search_index": refresh_search_index,
            "started_at_utc": started_at,
            "finished_at_utc": output["finished_at_utc"],
            "duration_seconds": output["duration_seconds"],
            "model_version": output.get("model_version"),
            "error": error,
        }
    )
    if status == "failed":
        raise RuntimeError(error)
    return jsonable(output)
