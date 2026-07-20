from __future__ import annotations

import pandas as pd

from app.models.config import STUDENT_PERIOD_DATASET
from app.services.model_bundle_inference_service import infer_with_active_bundle
from app.services.model_persistence_service import load_persisted_model_bundle


def test_active_bundle_reproduces_training_assignments():
    expected = load_persisted_model_bundle()["cluster_assignments"]
    actual = infer_with_active_bundle(dataset=pd.read_csv(STUDENT_PERIOD_DATASET)).assignments
    merged = expected[["id_estudiante", "id_periodo", "cluster"]].merge(
        actual[["id_estudiante", "id_periodo", "cluster"]],
        on=["id_estudiante", "id_periodo"],
        suffixes=("_expected", "_actual"),
    )

    assert len(merged) == len(expected)
    assert (merged["cluster_expected"] == merged["cluster_actual"]).mean() == 1.0


def test_inference_can_limit_students():
    source = pd.read_csv(STUDENT_PERIOD_DATASET)
    student_id = str(source.iloc[0]["id_estudiante"])

    result = infer_with_active_bundle(student_ids=[student_id], dataset=source)

    assert set(result.assignments["id_estudiante"].astype(str)) == {student_id}
    assert result.inferred_records > 0
