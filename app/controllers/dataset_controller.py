from __future__ import annotations

from app.services.synthetic_dataset_generation_validation_service import run_dataset_v2_pipeline


class DatasetController:
    """Controller for dataset realism validation and synthetic v2 generation."""

    def run(self) -> None:
        run_dataset_v2_pipeline()

