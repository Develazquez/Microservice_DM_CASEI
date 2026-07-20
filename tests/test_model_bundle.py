from __future__ import annotations

import unittest

from app.services.model_persistence_service import load_persisted_model_bundle, validate_loaded_contract


class ModelBundleTests(unittest.TestCase):
    def test_current_model_bundle_loads_and_passes_contract(self) -> None:
        loaded = load_persisted_model_bundle()
        checks = validate_loaded_contract(loaded)

        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
        self.assertEqual(loaded["manifest"]["model"]["selected_representation"], "pca_90")
        self.assertEqual(loaded["manifest"]["model"]["selected_k"], 2)
        self.assertEqual(len(loaded["cluster_assignments"]), 999)
        self.assertEqual(len(loaded["profile_catalog"]), 2)

    def test_current_model_metrics_are_regression_guarded(self) -> None:
        loaded = load_persisted_model_bundle()
        metrics = loaded["manifest"]["model"]["metrics"]

        self.assertAlmostEqual(metrics["silhouette"], 0.3255789062232767, places=6)
        self.assertAlmostEqual(metrics["davies_bouldin"], 1.4632741329176733, places=6)
        self.assertAlmostEqual(metrics["calinski_harabasz"], 310.1769170943589, places=4)


if __name__ == "__main__":
    unittest.main()
