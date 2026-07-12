from __future__ import annotations

import unittest

import pandas as pd

from app.models.config import CARDEX_COLUMNS, RAW_DATASET, STUDENT_PERIOD_DATASET, PROCESSED_DIR


class DataQualityTests(unittest.TestCase):
    def test_active_raw_cardex_dataset_has_expected_schema(self) -> None:
        raw = pd.read_csv(RAW_DATASET, encoding="utf-8-sig")

        self.assertEqual(len(raw), 2000)
        self.assertEqual(list(raw.columns), CARDEX_COLUMNS)
        self.assertGreater(raw["Matricula"].nunique(), 300)
        self.assertGreater(raw["Carrera"].nunique(), 1)

    def test_student_period_features_are_unique_and_complete(self) -> None:
        features = pd.read_csv(STUDENT_PERIOD_DATASET)

        self.assertEqual(len(features), 1277)
        self.assertEqual(features.duplicated(["id_estudiante", "id_periodo"]).sum(), 0)
        self.assertTrue(features["promedio_general"].between(0, 100).all())
        self.assertTrue(features["porcentaje_asistencia"].between(0, 100).all())
        self.assertTrue((features["rezago_materias"] >= 0).all())

    def test_cluster_assignments_match_student_period_view(self) -> None:
        features = pd.read_csv(STUDENT_PERIOD_DATASET)
        assignments = pd.read_csv(PROCESSED_DIR / "cluster_assignments.csv")

        self.assertEqual(len(assignments), len(features))
        self.assertEqual(assignments.duplicated(["id_estudiante", "id_periodo"]).sum(), 0)
        merged = assignments.merge(
            features[["id_estudiante", "id_periodo"]],
            on=["id_estudiante", "id_periodo"],
            how="left",
            indicator=True,
        )
        self.assertEqual((merged["_merge"] != "both").sum(), 0)


if __name__ == "__main__":
    unittest.main()
