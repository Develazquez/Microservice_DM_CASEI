from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.models.search_query_schemas import SemanticHint
from app.services.academic_bm25_search_service import load_search_documents
from app.services.academic_search_orchestrator_service import (
    requires_semantic,
    requires_slm,
    search_academic_documents,
)
from app.services.academic_semantic_embedding_service import (
    EmbeddingUnavailableError,
    build_and_persist_semantic_index,
    embed_texts,
    file_checksum_matches,
    reset_semantic_runtime_state,
    select_semantic_hints,
    semantic_descriptor,
    semantic_query_text,
)
from app.services.hybrid_search_ranking_service import reciprocal_rank_fusion
from runpod_gateway.main import app as gateway_app


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "semantic_search_queries.json"


def sample_documents() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "document_id": "A::2024-1",
                "id_estudiante": "A",
                "id_periodo": "2024-1",
                "programa": "Ingenieria de Software",
                "cohorte": "2022",
                "estatus_academico": "Regular",
                "cluster": 0,
                "perfil_sugerido": "Regular / seguimiento preventivo",
                "promedio_general": 88.0,
                "porcentaje_asistencia": 91.0,
                "rezago_materias": 0,
                "materias_reprobadas": 0,
                "promedio_bucket": "promedio alto",
                "asistencia_bucket": "asistencia alta",
                "rezago_bucket": "sin rezago",
                "reprobadas_bucket": "sin reprobadas",
                "acompanamiento_bucket": "sin tutorias",
                "incidencias_bucket": "sin incidencias",
                "search_text": "software regular seguimiento preventivo promedio alto asistencia alta sin rezago",
            },
            {
                "document_id": "B::2024-1",
                "id_estudiante": "B",
                "id_periodo": "2024-1",
                "programa": "Ingenieria Biomedica",
                "cohorte": "2021",
                "estatus_academico": "Regular",
                "cluster": 1,
                "perfil_sugerido": "Riesgo academico moderado",
                "promedio_general": 58.0,
                "porcentaje_asistencia": 55.0,
                "rezago_materias": 4,
                "materias_reprobadas": 3,
                "promedio_bucket": "promedio bajo",
                "asistencia_bucket": "asistencia baja",
                "rezago_bucket": "rezago alto",
                "reprobadas_bucket": "reprobadas altas",
                "acompanamiento_bucket": "con tutorias",
                "incidencias_bucket": "con incidencias",
                "search_text": "biomedica riesgo academico moderado promedio bajo asistencia baja rezago alto reprobadas",
            },
        ]
    )


class SemanticServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_semantic_runtime_state()

    def test_descriptor_excludes_student_identifiers(self) -> None:
        row = sample_documents().iloc[0].copy()
        row["id_estudiante"] = "IDS20200001"
        row["nombre"] = "Nombre Privado"
        descriptor = semantic_descriptor(row)
        self.assertNotIn("IDS20200001", descriptor)
        self.assertNotIn("Nombre Privado", descriptor)
        self.assertIn("Ingenieria de Software", descriptor)

    def test_embedding_cache_reuses_float32_vector(self) -> None:
        expected = np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32)
        with (
            patch("app.services.academic_semantic_embedding_service.OLLAMA_GATEWAY_URL", ""),
            patch(
                "app.services.academic_semantic_embedding_service.request_direct_embeddings",
                return_value=expected,
            ) as request,
        ):
            first, first_hit = embed_texts(["Los que van flojos"])
            second, second_hit = embed_texts(["  los que van flojos  "])
        self.assertFalse(first_hit)
        self.assertTrue(second_hit)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(first.dtype, np.float32)
        np.testing.assert_allclose(first, second)

    def test_text_checksum_accepts_only_line_ending_normalization(self) -> None:
        expected = b"document_id,descriptor_hash\r\nA::2024-1,abc\r\n"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "semantic_document_ids.csv"
            path.write_bytes(expected.replace(b"\r\n", b"\n"))
            self.assertTrue(file_checksum_matches(path, hashlib.sha256(expected).hexdigest()))

            path.write_bytes(b"document_id,descriptor_hash\nA::2024-1,changed\n")
            self.assertFalse(file_checksum_matches(path, hashlib.sha256(expected).hexdigest()))

    def test_binary_checksum_remains_strict(self) -> None:
        expected = b"\x93NUMPY\r\nbinary"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "semantic_embeddings.npy"
            path.write_bytes(expected.replace(b"\r\n", b"\n"))
            self.assertFalse(file_checksum_matches(path, hashlib.sha256(expected).hexdigest()))

    def test_query_expansion_uses_controlled_catalog_paraphrases(self) -> None:
        catalog = {
            "concepts": [
                {
                    "id": "low_performance",
                    "label": "bajo rendimiento",
                    "description": "dificultad academica",
                    "phrases": ["va flojo"],
                },
                {
                    "id": "academic_lag",
                    "label": "rezago academico",
                    "description": "atraso curricular",
                    "phrases": ["se esta quedando"],
                },
            ]
        }
        expanded, concepts = semantic_query_text("los que van flojos y se estan quedando", catalog)
        self.assertEqual(concepts, ["low_performance", "academic_lag"])
        self.assertIn("bajo rendimiento", expanded)
        self.assertIn("rezago academico", expanded)

    def test_colloquial_catalog_phrases_expand_to_expected_concepts(self) -> None:
        catalog_path = Path(__file__).parents[1] / "app" / "models" / "semantic_catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        cases = {
            "quienes necesitan que los revisemos": "tutorial_follow_up",
            "los que van de maravilla": "high_performance",
            "los que sacan buenas notas": "high_performance",
            "quienes faltan un monton": "low_attendance",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                _, concepts = semantic_query_text(query, catalog)
                self.assertIn(expected, concepts)
        _, good_grades_concepts = semantic_query_text("los que sacan buenas notas", catalog)
        self.assertEqual(good_grades_concepts, ["high_performance"])

    def test_explicit_high_performance_blocks_conflicting_prototypes(self) -> None:
        catalog = {
            "concepts": [
                {
                    "id": "high_performance",
                    "label": "buen desempeno",
                    "allowed_effect": "ranking",
                    "conflicts_with": ["low_performance", "multiple_risk_signals"],
                },
                {
                    "id": "low_performance",
                    "label": "bajo rendimiento",
                    "allowed_effect": "ranking",
                },
                {
                    "id": "atypical_attendance",
                    "label": "buen promedio con baja asistencia",
                    "allowed_effect": "qwen_context",
                    "requires_catalog_match": True,
                },
                {
                    "id": "multiple_risk_signals",
                    "label": "multiples senales",
                    "allowed_effect": "qwen_context",
                    "requires_catalog_match": True,
                },
            ]
        }
        hints = select_semantic_hints(
            catalog,
            ["high_performance", "low_performance", "atypical_attendance", "multiple_risk_signals"],
            np.asarray([0.87, 0.82, 0.88, 0.84], dtype=np.float32),
            ["high_performance"],
        )
        self.assertEqual([hint.concept_id for hint in hints], ["high_performance"])

    def test_full_index_persists_aligned_ids_and_checksums(self) -> None:
        documents = sample_documents()
        catalog = {
            "version": "test-v1",
            "concepts": [
                {
                    "id": "low_performance",
                    "label": "bajo rendimiento",
                    "description": "dificultad academica",
                    "phrases": ["va flojo"],
                    "allowed_effect": "ranking",
                }
            ],
        }
        vectors = [
            np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            np.asarray([[0.5, 0.5]], dtype=np.float32),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog_path = root / "semantic_catalog.json"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with (
                patch("app.services.academic_semantic_embedding_service.PROJECT_ROOT", root),
                patch("app.services.academic_semantic_embedding_service.SEARCH_REGISTRY_DIR", root / "registry"),
                patch("app.services.academic_semantic_embedding_service.CURRENT_SEARCH_INDEX_POINTER", root / "current.json"),
                patch("app.services.academic_semantic_embedding_service.SEMANTIC_CATALOG_PATH", catalog_path),
                patch("app.services.academic_semantic_embedding_service.embed_texts", side_effect=[(vectors[0], False), (vectors[1], False)]),
            ):
                manifest = build_and_persist_semantic_index(documents)
            target = root / "registry" / manifest["search_version"]
            ids = pd.read_csv(target / "semantic_document_ids.csv")
            matrix = np.load(target / "semantic_embeddings.npy", allow_pickle=False)
            self.assertEqual(ids["document_id"].tolist(), ["A::2024-1", "B::2024-1"])
            self.assertEqual(matrix.shape, (2, 2))
            self.assertTrue((target / "manifest.json").exists())

    def test_unchanged_index_reuses_document_vectors(self) -> None:
        documents = sample_documents()
        catalog = {
            "version": "test-v1",
            "concepts": [
                {
                    "id": "low_performance",
                    "label": "bajo rendimiento",
                    "description": "dificultad academica",
                    "phrases": ["va flojo"],
                    "allowed_effect": "ranking",
                }
            ],
        }
        document_vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        prototype_vectors = np.asarray([[0.5, 0.5]], dtype=np.float32)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog_path = root / "semantic_catalog.json"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with (
                patch("app.services.academic_semantic_embedding_service.PROJECT_ROOT", root),
                patch("app.services.academic_semantic_embedding_service.SEARCH_REGISTRY_DIR", root / "registry"),
                patch("app.services.academic_semantic_embedding_service.CURRENT_SEARCH_INDEX_POINTER", root / "current.json"),
                patch("app.services.academic_semantic_embedding_service.SEMANTIC_CATALOG_PATH", catalog_path),
                patch(
                    "app.services.academic_semantic_embedding_service.embed_texts",
                    side_effect=[
                        (document_vectors, False),
                        (prototype_vectors, False),
                        (prototype_vectors, False),
                    ],
                ) as embed,
            ):
                first = build_and_persist_semantic_index(documents)
                second = build_and_persist_semantic_index(documents)
        self.assertEqual(first["build_mode"], "full")
        self.assertEqual(second["build_mode"], "incremental")
        self.assertEqual(second["reused_documents"], 2)
        self.assertEqual(second["embedded_documents"], 0)
        self.assertEqual(embed.call_count, 3)

    def test_prototypes_only_aborts_before_embedding_changed_documents(self) -> None:
        documents = sample_documents()
        catalog = {
            "version": "test-v2",
            "concepts": [
                {
                    "id": "low_performance",
                    "label": "bajo rendimiento",
                    "description": "dificultad academica",
                    "phrases": ["va flojo"],
                    "allowed_effect": "ranking",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog_path = root / "semantic_catalog.json"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with (
                patch("app.services.academic_semantic_embedding_service.PROJECT_ROOT", root),
                patch("app.services.academic_semantic_embedding_service.SEARCH_REGISTRY_DIR", root / "registry"),
                patch("app.services.academic_semantic_embedding_service.CURRENT_SEARCH_INDEX_POINTER", root / "current.json"),
                patch("app.services.academic_semantic_embedding_service.SEMANTIC_CATALOG_PATH", catalog_path),
                patch("app.services.academic_semantic_embedding_service.embed_texts") as embed,
            ):
                with self.assertRaisesRegex(EmbeddingUnavailableError, "prototypes-only"):
                    build_and_persist_semantic_index(
                        documents,
                        require_full_document_reuse=True,
                    )
        embed.assert_not_called()


class HybridRoutingTests(unittest.TestCase):
    def test_semantic_router_detects_colloquial_query(self) -> None:
        self.assertTrue(requires_semantic("los que van flojos", sample_documents()))
        self.assertFalse(requires_semantic("promedio menor a 70", sample_documents()))

    def test_rrf_never_reintroduces_document_outside_authorized_scope(self) -> None:
        authorized = sample_documents().iloc[[0]].copy()
        bm25 = authorized.copy()
        bm25.insert(0, "rank", [1])
        bm25.insert(1, "score_bm25", [2.0])
        semantic = sample_documents().copy()
        semantic.insert(0, "rank_semantic", [2, 1])
        semantic.insert(1, "score_semantic", [0.7, 0.95])
        result = reciprocal_rank_fusion(authorized, bm25, semantic, top_k=10)
        self.assertEqual(result["document_id"].tolist(), ["A::2024-1"])

    def test_colloquial_query_uses_semantic_rank_without_unsafe_filter(self) -> None:
        documents = sample_documents()
        semantic_results = documents.iloc[[1]].copy()
        semantic_results.insert(0, "rank_semantic", [1])
        semantic_results.insert(1, "score_semantic", [0.95])
        semantic_payload = {
            "results": semantic_results,
            "hints": [SemanticHint(concept_id="low_performance", label="bajo rendimiento", similarity=0.94)],
            "metadata": {"model": "test", "index_version": "v1", "cache_hit": False},
        }
        with (
            patch("app.services.academic_search_orchestrator_service.CASEI_SEMANTIC_SEARCH_ENABLED", True),
            patch("app.services.academic_search_orchestrator_service.semantic_search_documents", return_value=semantic_payload),
            patch("app.services.academic_search_orchestrator_service.interpret_query") as interpret,
        ):
            result = search_academic_documents(
                documents,
                "los que van flojos",
                top_k=10,
                mode="auto",
                retrieval="hybrid",
                explain=True,
            )
        interpret.assert_not_called()
        self.assertEqual(result["results"].iloc[0]["document_id"], "B::2024-1")
        self.assertEqual(result["metadata"]["applied_filters"], {})
        semantic_rows = [
            row for row in result["metadata"]["conclusion_matrix"]
            if row["evidence_type"] == "semantic_similarity"
        ]
        self.assertEqual(semantic_rows[0]["action"], "rank")

    def test_semantic_failure_falls_back_to_bm25(self) -> None:
        with (
            patch("app.services.academic_search_orchestrator_service.CASEI_SEMANTIC_SEARCH_ENABLED", True),
            patch("app.services.academic_search_orchestrator_service.CASEI_SLM_ENABLED", False),
            patch(
                "app.services.academic_search_orchestrator_service.semantic_search_documents",
                side_effect=EmbeddingUnavailableError("indice no disponible"),
            ),
        ):
            result = search_academic_documents(
                sample_documents(), "los que van flojos", 10, mode="auto", retrieval="hybrid"
            )
        self.assertEqual(result["metadata"]["processing_mode"], "fallback_bm25")
        self.assertTrue(any("indice no disponible" in warning for warning in result["metadata"]["warnings"]))


class SemanticGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(gateway_app)

    def test_embed_requires_api_key(self) -> None:
        with patch.dict(os.environ, {"CASEI_SLM_GATEWAY_API_KEY": "secret"}):
            response = self.client.post("/embed", json={"texts": ["consulta"]})
        self.assertEqual(response.status_code, 401)

    def test_embed_returns_vectors(self) -> None:
        with (
            patch.dict(os.environ, {"CASEI_SLM_GATEWAY_API_KEY": "secret"}),
            patch("runpod_gateway.main.request_direct_embeddings", return_value=np.asarray([[1.0, 0.0]], dtype=np.float32)),
        ):
            response = self.client.post(
                "/embed",
                headers={"X-CASEI-SLM-KEY": "secret"},
                json={"texts": ["consulta"]},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["embeddings"], [[1.0, 0.0]])

    def test_ready_requires_exact_tag_when_model_has_tag(self) -> None:
        with (
            patch.dict(os.environ, {"CASEI_SLM_GATEWAY_API_KEY": "secret"}),
            patch(
                "runpod_gateway.main.ollama_models",
                return_value=["qwen3:otra-version", "qwen3-embedding:0.6b"],
            ),
        ):
            response = self.client.get(
                "/ready",
                headers={"X-CASEI-SLM-KEY": "secret"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("qwen3:4b-instruct-2507-q4_K_M", response.json()["detail"])


class EvaluationFixtureTests(unittest.TestCase):
    def test_fixture_contains_at_least_100_labeled_queries(self) -> None:
        queries = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(queries), 100)
        self.assertEqual(len({item["id"] for item in queries}), len(queries))
        for item in queries:
            self.assertTrue(item["query"].strip())
            self.assertTrue(item["expected_intent"].strip())
            self.assertIn("prohibited_filters", item)

    def test_labeled_queries_match_lazy_router(self) -> None:
        queries = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        documents = load_search_documents()
        for item in queries:
            with self.subTest(query_id=item["id"], route="slm"):
                self.assertEqual(requires_slm(item["query"], documents), item["requires_slm"])
            with self.subTest(query_id=item["id"], route="semantic"):
                self.assertEqual(
                    requires_semantic(item["query"], documents),
                    item["requires_semantic"],
                )


if __name__ == "__main__":
    unittest.main()
