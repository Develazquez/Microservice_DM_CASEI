from __future__ import annotations

from app.services.exploratory_analysis_feature_engineering_pca_service import main as run_phase_2_4_pipeline


class AnalysisController:
    """Controller for EDA, feature selection, and PCA phases."""

    def run(self) -> None:
        run_phase_2_4_pipeline()
