from __future__ import annotations

from app.services.clustering_training_evaluation_service import run_phase_5_6


class ClusteringController:
    """Controller for K selection and K-Means training phases."""

    def run(self) -> None:
        run_phase_5_6()
