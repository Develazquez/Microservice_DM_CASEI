from __future__ import annotations

from app.services.model_persistence_service import run_phase_8


class ModelPersistenceController:
    """Controller for model persistence and registry phase."""

    def run(self) -> None:
        run_phase_8()
