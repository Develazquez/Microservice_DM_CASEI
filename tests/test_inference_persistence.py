from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.services import inference_persistence_service as persistence


class InferencePersistenceTests(unittest.TestCase):
    def test_persist_snapshot_and_query_history_in_temporary_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir)
            db_path = storage_dir / "history.sqlite"
            schema_path = storage_dir / "schema.sql"
            report_path = storage_dir / "report.md"

            with patch.multiple(
                persistence,
                STORAGE_DIR=storage_dir,
                INFERENCE_HISTORY_DB=db_path,
                INFERENCE_SCHEMA_PATH=schema_path,
                INFERENCE_PERSISTENCE_REPORT=report_path,
            ):
                result = persistence.persist_inference_snapshot(
                    execution_id="test-execution",
                    run_type="test_snapshot",
                    parameters={"test": True},
                    notes="temporary test snapshot",
                )
                summary = persistence.persistence_summary()
                runs = persistence.list_inference_runs()
                run_detail = persistence.get_inference_run("test-execution", limit=3)
                student_history = persistence.get_student_inference_history("IAG20200007")

        self.assertEqual(result["assignments_count"], 999)
        self.assertEqual(summary["runs"], 1)
        self.assertEqual(summary["student_inferences"], 999)
        self.assertEqual(len(runs), 1)
        self.assertEqual(run_detail["total_inferences"], 999)
        self.assertEqual(len(run_detail["items"]), 3)
        self.assertEqual(student_history["total"], 3)


if __name__ == "__main__":
    unittest.main()
