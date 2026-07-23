from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.services.model_persistence_service import (
    load_persisted_model_bundle,
    validate_loaded_contract,
    validate_manifest_files,
)


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

    def test_strict_checksums_accept_only_line_ending_changes(self) -> None:
        crlf_content = b"column,value\r\nfirst,1\r\n"
        lf_content = crlf_content.replace(b"\r\n", b"\n")

        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_dir = Path(temp_dir)
            artifact_path = bundle_dir / "artifact.csv"
            artifact_path.write_bytes(lf_content)
            manifest = {
                "artifacts": [
                    {
                        "bundle_path": "artifact.csv",
                        "role": "test",
                        "required_for_load": True,
                        "sha256": hashlib.sha256(crlf_content).hexdigest(),
                    }
                ]
            }

            with patch.dict(os.environ, {"CASEI_STRICT_BUNDLE_CHECKSUMS": "true"}):
                validation = validate_manifest_files(manifest, bundle_dir).iloc[0]

            self.assertFalse(bool(validation["raw_checksum_ok"]))
            self.assertTrue(bool(validation["eol_tolerated"]))
            self.assertFalse(bool(validation["checksum_bypassed"]))
            self.assertTrue(bool(validation["checksum_ok"]))

    def test_strict_checksums_reject_content_changes(self) -> None:
        expected_content = b"column,value\r\nfirst,1\r\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_dir = Path(temp_dir)
            artifact_path = bundle_dir / "artifact.csv"
            artifact_path.write_bytes(b"column,value\nfirst,9\n")
            manifest = {
                "artifacts": [
                    {
                        "bundle_path": "artifact.csv",
                        "role": "test",
                        "required_for_load": True,
                        "sha256": hashlib.sha256(expected_content).hexdigest(),
                    }
                ]
            }

            with patch.dict(os.environ, {"CASEI_STRICT_BUNDLE_CHECKSUMS": "true"}):
                validation = validate_manifest_files(manifest, bundle_dir).iloc[0]

            self.assertFalse(bool(validation["checksum_ok"]))


if __name__ == "__main__":
    unittest.main()
