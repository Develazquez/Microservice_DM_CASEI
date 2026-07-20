from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable

import pandas as pd

from app.models.config import SEARCH_INDEX_STATE, STUDENT_PERIOD_DATASET
from app.services.academic_bm25_search_service import clear_index_cache, get_cached_index, load_search_documents
from app.services.model_persistence_service import load_persisted_model_bundle


def refresh_search_index(student_ids: Iterable[str] | None = None) -> dict[str, Any]:
    selected_ids = sorted({str(value) for value in (student_ids or []) if str(value)})
    documents = load_search_documents()
    clear_index_cache()
    get_cached_index(documents)
    model_version = str(load_persisted_model_bundle()["manifest"]["model_version"])
    dataset_hash = sha256(STUDENT_PERIOD_DATASET.read_bytes()).hexdigest() if STUDENT_PERIOD_DATASET.exists() else None
    state = {
        "model_version": model_version,
        "dataset_hash": dataset_hash,
        "documents": int(len(documents)),
        "students": int(documents["id_estudiante"].nunique()) if not documents.empty else 0,
        "refresh_mode": "incremental_compact_rebuild" if selected_ids else "full_rebuild",
        "affected_student_ids": selected_ids,
        "refreshed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    SEARCH_INDEX_STATE.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_INDEX_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state
