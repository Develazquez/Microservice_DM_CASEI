from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunSegmentationRequest(BaseModel):
    mode: Literal["load_existing", "retrain_local"] = Field(
        default="load_existing",
        description="load_existing valida y carga el bundle actual; retrain_local regenera fases 2-8.",
    )
    persist_model: bool = Field(
        default=True,
        description="Cuando mode=retrain_local, registra un nuevo bundle versionado en Fase 8.",
    )
    refresh_search_index: bool = Field(
        default=False,
        description="Regenera artefactos BM25 despues de cargar o entrenar.",
    )
    notes: str | None = Field(default=None, max_length=500)
