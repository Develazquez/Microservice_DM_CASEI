from __future__ import annotations

from app.services.candidate_model_service import compare_metrics


def test_candidate_with_small_variation_passes_quality_gate():
    result = compare_metrics(
        {"silhouette": 0.35, "davies_bouldin": 1.40, "calinski_harabasz": 440, "min_cluster_size": 200},
        {"silhouette": 0.34, "davies_bouldin": 1.42, "calinski_harabasz": 430, "min_cluster_size": 180},
    )

    assert result["passes_quality_gate"] is True
    assert result["decision"] == "candidate_for_manual_review"


def test_degraded_candidate_is_rejected():
    result = compare_metrics(
        {"silhouette": 0.35, "davies_bouldin": 1.40, "calinski_harabasz": 440, "min_cluster_size": 200},
        {"silhouette": 0.20, "davies_bouldin": 2.20, "calinski_harabasz": 200, "min_cluster_size": 1},
    )

    assert result["passes_quality_gate"] is False
    assert result["decision"] == "reject_candidate"
