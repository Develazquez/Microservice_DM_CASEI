from __future__ import annotations

from typing import Any

from app.repositories.supabase_repository import SupabaseRepository
from app.services.clustering_training_evaluation_service import run_phase_5_6
from app.services.exploratory_analysis_feature_engineering_pca_service import main as run_phase_2_4
from app.services.model_persistence_service import (
    activate_persisted_model_bundle,
    load_persisted_model_bundle,
    persist_current_model_bundle,
)
from app.services.profile_interpretation_service import run_phase_7
from app.services.segmentation_api_service import jsonable
from app.services.supabase_results_sync_service import ensure_model_version_registered


def train_candidate_model(tenant_id: str | None = None) -> dict[str, Any]:
    active = load_persisted_model_bundle()["manifest"]
    active_version = str(active["model_version"])
    active_metrics = dict(active["model"].get("metrics") or {})

    run_phase_2_4()
    run_phase_5_6()
    run_phase_7()
    persisted = persist_current_model_bundle(activate=False)
    candidate = persisted["manifest"]
    candidate_version = str(candidate["model_version"])
    candidate_metrics = dict(candidate["model"].get("metrics") or {})
    comparison = compare_metrics(active_metrics, candidate_metrics)

    repository = SupabaseRepository()
    if repository.configured:
        ensure_model_version_registered(
            repository,
            candidate_version,
            activate_if_missing=False,
            tenant_id=tenant_id,
        )

    return {
        "status": "review_required" if comparison["passes_quality_gate"] else "rejected",
        "active_model_version": active_version,
        "candidate_model_version": candidate_version,
        "active_metrics": jsonable(active_metrics),
        "candidate_metrics": jsonable(candidate_metrics),
        "comparison": comparison,
        "activated": False,
    }


def compare_metrics(active: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    active_silhouette = float(active.get("silhouette") or 0)
    candidate_silhouette = float(candidate.get("silhouette") or 0)
    active_db = float(active.get("davies_bouldin") or float("inf"))
    candidate_db = float(candidate.get("davies_bouldin") or float("inf"))
    active_ch = float(active.get("calinski_harabasz") or 0)
    candidate_ch = float(candidate.get("calinski_harabasz") or 0)
    checks = {
        "silhouette": candidate_silhouette >= active_silhouette - 0.03,
        "davies_bouldin": candidate_db <= active_db * 1.15,
        "calinski_harabasz": candidate_ch >= active_ch * 0.85,
        "cluster_coverage": int(candidate.get("min_cluster_size") or 0) > 0,
    }
    return {
        "checks": checks,
        "passes_quality_gate": all(checks.values()),
        "silhouette_delta": candidate_silhouette - active_silhouette,
        "davies_bouldin_delta": candidate_db - active_db,
        "calinski_harabasz_delta": candidate_ch - active_ch,
        "decision": "candidate_for_manual_review" if all(checks.values()) else "reject_candidate",
    }


def activate_candidate_model(model_version: str) -> dict[str, Any]:
    previous_version = str(load_persisted_model_bundle()["manifest"]["model_version"])
    activation = activate_persisted_model_bundle(model_version)
    repository = SupabaseRepository()
    if repository.configured:
        repository.rpc("activate_model_version", {"target_model_version": model_version})
    return {**activation, "previous_model_version": previous_version}
