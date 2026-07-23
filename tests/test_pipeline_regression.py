from __future__ import annotations

import unittest

import pandas as pd

from app.models.config import REPORTS_DIR
from app.services.cardex_student_period_feature_service import parse_cohort, period_order
from app.services.segmentation_api_service import segmentation_summary


class PipelineRegressionTests(unittest.TestCase):
    def test_real_institutional_periods_and_legacy_matriculas(self) -> None:
        self.assertEqual(parse_cohort("193243"), 2019)
        self.assertEqual(parse_cohort("243678"), 2024)
        self.assertEqual(parse_cohort("IDS20200001"), 2020)
        self.assertEqual(period_order("ENERO-ABRIL 2020"), 2020 * 3 + 1)
        self.assertEqual(period_order("Mayo-Agosto 2026"), 2026 * 3 + 2)
        self.assertEqual(period_order("2026-3"), 2026 * 3 + 3)

    def test_k_selection_metrics_keep_current_operational_choice(self) -> None:
        metrics = pd.read_csv(REPORTS_DIR / "k_selection_metrics.csv")
        selected = metrics[(metrics["representation"] == "pca_90") & (metrics["k"] == 2)].iloc[0]

        self.assertAlmostEqual(float(selected["silhouette"]), 0.3255789062232767, places=6)
        self.assertAlmostEqual(float(selected["davies_bouldin"]), 1.4632741329176733, places=6)
        self.assertEqual(int(selected["n_samples"]), 999)

    def test_summary_contract_matches_dashboard_expectations(self) -> None:
        summary = segmentation_summary()

        self.assertEqual(summary["total_records"], 999)
        self.assertEqual(summary["total_students"], 387)
        self.assertEqual(summary["selected_k"], 2)
        self.assertEqual(len(summary["profile_distribution"]), 2)
        self.assertGreater(summary["students_in_follow_up"], 0)


if __name__ == "__main__":
    unittest.main()
