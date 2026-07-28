from __future__ import annotations

from app.services.supabase_results_sync_service import (
    build_assignment_rows,
    build_feature_rows,
    build_profile_history_rows,
    ensure_model_version_registered,
    require_tenant_id,
)

import pandas as pd
import pytest


TENANT_ID = "00000000-0000-4000-8000-000000000001"


def test_result_builders_include_tenant_id():
    frame = pd.DataFrame(
        [
            {
                "id_estudiante": "IDS20200001",
                "id_periodo": "2026-1",
                "programa": "Ingenieria en Desarrollo de Software",
                "cluster": 1,
                "perfil_academico": "Riesgo academico moderado",
            }
        ]
    )
    kwargs = {
        "execution_id": "00000000-0000-4000-8000-000000000002",
        "identities": {},
        "programs": {},
        "tenant_id": TENANT_ID,
    }

    features = build_feature_rows(frame, source_hash="a" * 64, **kwargs)
    assignments = build_assignment_rows(frame, model_version="model-v1", **kwargs)
    history = build_profile_history_rows(frame, model_version="model-v1", **kwargs)

    assert features[0]["tenant_id"] == TENANT_ID
    assert assignments[0]["tenant_id"] == TENANT_ID
    assert history[0]["tenant_id"] == TENANT_ID


def test_result_publication_requires_tenant_id():
    with pytest.raises(ValueError, match="tenant_id"):
        require_tenant_id(None)


def test_model_version_registration_includes_tenant_id(monkeypatch):
    class FakeRepository:
        def __init__(self):
            self.fetch_calls = []
            self.inserted_rows = []

        def fetch_table(self, table, **kwargs):
            self.fetch_calls.append((table, kwargs))
            return []

        def insert_rows(self, table, rows, **kwargs):
            self.inserted_rows.extend(rows)
            return len(rows)

    monkeypatch.setattr(
        "app.services.supabase_results_sync_service.load_persisted_model_bundle",
        lambda _version: {
            "manifest": {
                "model_version": "model-v1",
                "model": {
                    "algorithm": "kmeans",
                    "selected_representation": "pca_90",
                    "selected_k": 2,
                    "metrics": {},
                },
            }
        },
    )
    repository = FakeRepository()

    ensure_model_version_registered(
        repository,
        "model-v1",
        activate_if_missing=False,
        tenant_id=TENANT_ID,
    )

    assert repository.inserted_rows[0]["tenant_id"] == TENANT_ID
    active_filters = repository.fetch_calls[0][1]["filters"]
    assert active_filters["tenant_id"] == f"eq.{TENANT_ID}"
