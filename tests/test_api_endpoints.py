from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class ApiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_openapi_exposes_expected_routes_and_schemas(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        spec = response.json()

        expected_paths = {
            "/health",
            "/api/v1/segmentation/health",
            "/api/v1/segmentation/run",
            "/api/v1/segmentation/summary",
            "/api/v1/segmentation/context/contract",
            "/api/v1/segmentation/sync/status",
            "/api/v1/segmentation/sync/from-supabase",
            "/api/v1/segmentation/students",
            "/api/v1/segmentation/students/{student_id}",
            "/api/v1/segmentation/students/{student_id}/llm-context",
            "/api/v1/segmentation/students/{student_id}/history",
            "/api/v1/segmentation/search",
            "/api/v1/segmentation/rag/documents",
            "/api/v1/segmentation/clusters",
            "/api/v1/segmentation/history",
            "/api/v1/segmentation/history/{execution_id}",
        }
        self.assertTrue(expected_paths.issubset(set(spec["paths"])))
        self.assertIn("RunSegmentationRequest", spec["components"]["schemas"])
        self.assertIn("SegmentationSummaryResponse", spec["components"]["schemas"])
        self.assertIn("HistoryRunResponse", spec["components"]["schemas"])
        self.assertIn("LlmContextContractResponse", spec["components"]["schemas"])
        self.assertIn("StudentLlmContextResponse", spec["components"]["schemas"])
        self.assertIn("RagDocumentsResponse", spec["components"]["schemas"])
        self.assertIn("SupabaseSyncRequest", spec["components"]["schemas"])
        self.assertIn("SupabaseSyncResponse", spec["components"]["schemas"])
        self.assertIn("SupabaseResultsSyncRequest", spec["components"]["schemas"])
        self.assertIn("SupabaseResultsSyncResponse", spec["components"]["schemas"])

    def test_health_summary_students_and_clusters_endpoints(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        summary = self.client.get("/api/v1/segmentation/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["total_records"], 1277)
        self.assertEqual(summary.json()["selected_k"], 2)

        students = self.client.get("/api/v1/segmentation/students?limit=2")
        self.assertEqual(students.status_code, 200)
        self.assertEqual(len(students.json()["items"]), 2)

        clusters = self.client.get("/api/v1/segmentation/clusters")
        self.assertEqual(clusters.status_code, 200)
        self.assertEqual(len(clusters.json()["profiles"]), 2)

    def test_student_search_and_history_endpoints(self) -> None:
        student = self.client.get("/api/v1/segmentation/students/IAG20200007")
        self.assertEqual(student.status_code, 200)
        self.assertEqual(student.json()["total_records"], 3)

        student_history = self.client.get("/api/v1/segmentation/students/IAG20200007/history")
        self.assertEqual(student_history.status_code, 200)
        self.assertGreaterEqual(student_history.json()["total"], 3)

        search = self.client.get("/api/v1/segmentation/search?q=riesgo%20academico&top_k=3")
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.json()["items"]), 3)

    def test_llm_context_contract_and_rag_documents(self) -> None:
        contract = self.client.get("/api/v1/segmentation/context/contract")
        self.assertEqual(contract.status_code, 200)
        self.assertEqual(contract.json()["context_version"], "casei-llm-rag-context-v1")
        self.assertIn("tutor", {role["role"] for role in contract.json()["roles"]})

        tutor_context = self.client.get(
            "/api/v1/segmentation/students/IAG20200007/llm-context?role=tutor&max_history=2"
        )
        self.assertEqual(tutor_context.status_code, 403)

        context = self.client.get(
            "/api/v1/segmentation/students/IAG20200007/llm-context?role=director&max_history=2"
        )
        self.assertEqual(context.status_code, 200)
        body = context.json()
        self.assertEqual(body["student_reference"], "IAG20200007")
        self.assertLessEqual(len(body["compact_profile_history"]), 2)
        self.assertIn("academic_summary", body)
        self.assertIn("diagnostico automatico definitivo", body["safety"]["interpretation_limit"])

        analyst_context = self.client.get(
            "/api/v1/segmentation/students/IAG20200007/llm-context?role=analista&max_history=2"
        )
        self.assertEqual(analyst_context.status_code, 200)
        self.assertTrue(analyst_context.json()["student_reference"].startswith("student-"))
        self.assertNotEqual(analyst_context.json()["student_reference"], "IAG20200007")

        rag = self.client.get(
            "/api/v1/segmentation/rag/documents?role=analista&student_id=IAG20200007&limit=1"
        )
        self.assertEqual(rag.status_code, 200)
        rag_body = rag.json()
        self.assertEqual(rag_body["total"], 1)
        self.assertEqual(rag_body["items"][0]["metadata"]["identifier_visibility"], "pseudonymized")
        self.assertNotIn("IAG20200007", rag_body["items"][0]["retrieval_text"])

    def test_supabase_sync_status_and_contract(self) -> None:
        status = self.client.get("/api/v1/segmentation/sync/status")
        self.assertEqual(status.status_code, 200)
        self.assertIn(status.json()["status"], {"configured", "missing_configuration"})

        fake_response = {
            "status": "completed",
            "started_at_utc": "2026-07-07T00:00:00Z",
            "finished_at_utc": "2026-07-07T00:00:01Z",
            "source_hash": "abc123",
            "counts": {"profiles": 1},
            "preview_records": 1,
            "snapshot_path": "data/storage/supabase_academic_source_snapshot.json",
            "preview_path": "data/processed/supabase_student_period_features_preview.csv",
            "active_dataset_replaced": False,
            "note": "mock",
        }

        with patch("app.controllers.segmentation_api_controller.sync_from_supabase", return_value=fake_response):
            response = self.client.post(
                "/api/v1/segmentation/sync/from-supabase",
                json={"limit": 10, "write_preview": True},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertFalse(response.json()["active_dataset_replaced"])


    def test_supabase_results_sync_contract(self) -> None:
        fake_response = {
            "status": "completed",
            "execution_id": "00000000-0000-4000-8000-000000000001",
            "model_version": "casei-kmeans-pca90-k2-68c23826aa1e",
            "started_at_utc": "2026-07-07T00:00:00Z",
            "finished_at_utc": "2026-07-07T00:00:02Z",
            "duration_seconds": 2.0,
            "source_hash": "abc123",
            "counts": {
                "ml_model_versions": 1,
                "ml_model_runs": 1,
                "student_period_features": 1277,
                "cluster_assignments": 1277,
                "student_profile_history": 1277,
                "rag_context_documents": 100,
            },
            "active_model_version": "casei-kmeans-pca90-k2-68c23826aa1e",
            "note": "mock",
        }

        with patch("app.controllers.segmentation_api_controller.sync_results_to_supabase", return_value=fake_response):
            response = self.client.post(
                "/api/v1/segmentation/sync/to-supabase",
                json={"include_rag_documents": True, "max_rag_documents": 100, "batch_size": 250},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["counts"]["cluster_assignments"], 1277)

    def test_run_endpoint_contract_without_mutating_pipeline(self) -> None:
        fake_response = {
            "execution_id": "mock-run",
            "status": "completed",
            "mode": "load_existing",
            "steps": ["load_current_model", "phase_10_inference_persist"],
            "started_at_utc": "2026-07-06T00:00:00Z",
            "finished_at_utc": "2026-07-06T00:00:01Z",
            "duration_seconds": 1.0,
            "model_version": "casei-kmeans-pca90-k2-68c23826aa1e",
            "inference_persistence": {
                "execution_id": "mock-run",
                "assignments_count": 1277,
                "students_count": 387,
            },
            "summary": {
                "total_students": 387,
                "total_records": 1277,
                "selected_k": 2,
                "selected_representation": "pca_90",
            },
        }

        with patch("app.controllers.segmentation_api_controller.run_segmentation", return_value=fake_response):
            response = self.client.post("/api/v1/segmentation/run", json={"mode": "load_existing"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["inference_persistence"]["assignments_count"], 1277)


if __name__ == "__main__":
    unittest.main()
