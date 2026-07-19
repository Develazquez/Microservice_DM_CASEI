from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from app.models.config import CASEI_DB_MODE
from app.repositories.local_repository import LocalSegmentationRepository
from app.repositories.supabase_repository import SupabaseRepository


@runtime_checkable
class SegmentationRepository(Protocol):
    def student_period_features(self) -> pd.DataFrame:
        ...

    def current_model_bundle(self) -> dict:
        ...


def get_segmentation_repository(mode: str | None = None) -> SegmentationRepository:
    selected_mode = (mode or CASEI_DB_MODE or "local").strip().lower()
    if selected_mode in {"supabase", "postgres", "postgresql"}:
        repository = SupabaseRepository()
        if repository.configured:
            return repository
        return LocalSegmentationRepository(reason="supabase_missing_configuration")
    if selected_mode in {"local", "sqlite", "csv"}:
        return LocalSegmentationRepository(reason="configured_local_mode")
    return LocalSegmentationRepository(reason=f"unsupported_mode:{selected_mode}")


def repository_status(mode: str | None = None) -> dict:
    selected_mode = (mode or CASEI_DB_MODE or "local").strip().lower()
    supabase = SupabaseRepository()
    selected = "supabase" if selected_mode in {"supabase", "postgres", "postgresql"} and supabase.configured else "local"
    fallback_reason = None
    if selected_mode in {"supabase", "postgres", "postgresql"} and not supabase.configured:
        fallback_reason = "supabase_missing_configuration"
    elif selected_mode not in {"supabase", "postgres", "postgresql", "local", "sqlite", "csv"}:
        fallback_reason = f"unsupported_mode:{selected_mode}"
    return {
        "mode": selected_mode,
        "selected_repository": selected,
        "fallback_reason": fallback_reason,
        "supabase": supabase.configuration_status(),
    }
