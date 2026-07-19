from __future__ import annotations

from typing import Any

import pandas as pd

from app.models.config import STUDENT_PERIOD_DATASET
from app.services.model_persistence_service import load_persisted_model_bundle


class LocalSegmentationRepository:
    """Read current local artifacts without requiring Supabase."""

    def __init__(self, reason: str | None = None) -> None:
        self.reason = reason

    def configuration_status(self) -> dict[str, Any]:
        return {
            "configured": True,
            "source": "local_csv_sqlite",
            "reason": self.reason,
            "student_period_dataset": str(STUDENT_PERIOD_DATASET),
        }

    def student_period_features(self) -> pd.DataFrame:
        if not STUDENT_PERIOD_DATASET.exists():
            raise FileNotFoundError(f"Student-period dataset not found: {STUDENT_PERIOD_DATASET}")
        return pd.read_csv(STUDENT_PERIOD_DATASET)

    def current_model_bundle(self) -> dict[str, Any]:
        return load_persisted_model_bundle()
