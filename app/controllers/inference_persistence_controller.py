from __future__ import annotations

from app.services.inference_persistence_service import run_phase_10


class InferencePersistenceController:
    """Controller for inference persistence and history phase."""

    def run(self) -> None:
        run_phase_10()
