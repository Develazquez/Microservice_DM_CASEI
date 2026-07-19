from __future__ import annotations

from app.services.profile_interpretation_service import run_phase_7


class ProfileInterpretationController:
    """Controller for academic profile interpretation phase."""

    def run(self) -> None:
        run_phase_7()
