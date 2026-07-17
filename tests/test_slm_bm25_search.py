from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.models.search_query_schemas import NumericCondition, StructuredAcademicQuery
from app.services.academic_bm25_search_service import BM25Index
from app.services.academic_search_orchestrator_service import (
    UnsupportedSourceFilterError,
    build_query_catalogs,
    requires_slm,
    search_academic_documents,
    validate_interpretation,
)
from app.services.ollama_query_interpretation_service import SlmUnavailableError, build_prompt, request_direct_ollama
from app.models.search_query_schemas import InterpretationRequest
from runpod_gateway.main import app as gateway_app


DIRECT_QUERIES = [
    "riesgo academico", "promedio bajo", "asistencia alta", "rezago alto",
    "reprobadas moderadas", "regular", "critico", "atipico", "seguimiento preventivo",
    "ausentismo", "ingenieria software", "biomedica", "energia", "agroindustrial",
    "tutorias", "incidencias", "promedio alto", "asistencia baja", "sin rezago",
    "riesgo moderado",
]

COMPLEX_QUERIES = [
    "promedio mayor a 80", "asistencia menor a 60", "rezago entre 2 y 4",
    "promedio bajo y asistencia baja", "software excepto regulares", "alumnos no criticos",
    "sin reprobadas y promedio alto", "desde 2020 hasta 2022", "por encima de 85",
    "por debajo de 50", "perfil regular pero con rezago", "programa y cohorte",
    "asistencia superior a 90", "promedio inferior a 70", "riesgo y ademas incidencias",
    "entre 60 y 80 de promedio", "no mostrar atipicos", "todos excepto software",
    "rezago mayor a 3 y reprobadas", "promedio menor a 70 pero asistencia alta",
]


def sample_documents() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "document_id": "A::2024-1", "id_estudiante": "A", "id_periodo": "2024-1",
                "programa": "Ingenieria de Software", "cohorte": "2022", "estatus_academico": "Regular",
                "cluster": 0, "perfil_sugerido": "Regular / seguimiento preventivo",
                "promedio_general": 88.0, "porcentaje_asistencia": 91.0, "rezago_materias": 0,
                "materias_reprobadas": 0, "search_text": "software regular seguimiento preventivo promedio alto asistencia alta sin rezago",
            },
            {
                "document_id": "B::2024-1", "id_estudiante": "B", "id_periodo": "2024-1",
                "programa": "Ingenieria Biomedica", "cohorte": "2021", "estatus_academico": "Regular",
                "cluster": 1, "perfil_sugerido": "Riesgo academico moderado",
                "promedio_general": 58.0, "porcentaje_asistencia": 55.0, "rezago_materias": 4,
                "materias_reprobadas": 3, "search_text": "biomedica riesgo academico moderado promedio bajo asistencia baja rezago alto reprobadas incidencias",
            },
        ]
    )


class SearchOrchestratorTests(unittest.TestCase):
    def test_evaluation_set_contains_40_queries(self) -> None:
        self.assertEqual(len(DIRECT_QUERIES) + len(COMPLEX_QUERIES), 40)

    def test_contract_rejects_sql_like_normalization(self) -> None:
        with self.assertRaises(ValidationError):
            StructuredAcademicQuery(normalized_query="promedio_general < 70")

    def test_prompt_does_not_send_source_column_names(self) -> None:
        request = InterpretationRequest(
            query="promedio bajo",
            catalogs={"source_columns": ["promedio_general"], "version": "v1"},
        )
        self.assertNotIn("promedio_general", build_prompt(request))

    def test_complexity_gate_covers_evaluation_set(self) -> None:
        documents = sample_documents()
        for query in COMPLEX_QUERIES:
            with self.subTest(query=query):
                self.assertTrue(requires_slm(query, documents))

    def test_direct_bm25_excludes_zero_scores(self) -> None:
        results = BM25Index(sample_documents()).search("termino-inexistente", top_k=10)
        self.assertTrue(results.empty)

    def test_simple_query_does_not_call_slm(self) -> None:
        with patch("app.services.academic_search_orchestrator_service.interpret_query") as mocked:
            result = search_academic_documents(sample_documents(), "riesgo academico", 10, mode="auto")
        mocked.assert_not_called()
        self.assertEqual(result["metadata"]["processing_mode"], "direct_bm25")

    def test_forced_slm_applies_numeric_filter_and_expansion(self) -> None:
        interpretation = StructuredAcademicQuery(
            normalized_query="riesgo academico",
            keywords=["riesgo"],
            synonyms=["rezago"],
            promedio=NumericCondition(operator="lt", value=70),
            confidence=0.95,
        )
        with (
            patch("app.services.academic_search_orchestrator_service.CASEI_SLM_ENABLED", True),
            patch("app.services.academic_search_orchestrator_service.interpret_query", return_value=(interpretation, False)),
        ):
            result = search_academic_documents(sample_documents(), "promedio menor a 70", 10, mode="slm")
        self.assertEqual(result["metadata"]["processing_mode"], "slm_bm25")
        self.assertEqual(result["metadata"]["candidate_count"], 1)
        self.assertEqual(result["results"].iloc[0]["id_estudiante"], "B")

    def test_numeric_filter_without_number_is_discarded(self) -> None:
        interpretation = StructuredAcademicQuery(
            normalized_query="rezago alto",
            keywords=["rezago alto"],
            rezago=NumericCondition(operator="gt", value=0),
            confidence=0.8,
        )
        with (
            patch("app.services.academic_search_orchestrator_service.CASEI_SLM_ENABLED", True),
            patch("app.services.academic_search_orchestrator_service.interpret_query", return_value=(interpretation, False)),
        ):
            result = search_academic_documents(sample_documents(), "rezago alto", 10, mode="slm")
        self.assertNotIn("rezago", result["metadata"]["applied_filters"])
        self.assertTrue(any("no proporciona una cifra" in warning for warning in result["metadata"]["warnings"]))

    def test_explicit_filter_overrides_inferred_filter(self) -> None:
        interpretation = StructuredAcademicQuery(
            normalized_query="riesgo",
            keywords=["riesgo"],
            programa="Ingenieria Biomedica",
            confidence=0.9,
        )
        with (
            patch("app.services.academic_search_orchestrator_service.CASEI_SLM_ENABLED", True),
            patch("app.services.academic_search_orchestrator_service.interpret_query", return_value=(interpretation, False)),
        ):
            result = search_academic_documents(
                sample_documents(), "programa con riesgo", 10, mode="slm", programa="Ingenieria de Software"
            )
        self.assertEqual(result["metadata"]["applied_filters"]["programa"], "Ingenieria de Software")
        self.assertTrue(any("prevalecio" in warning for warning in result["metadata"]["warnings"]))

    def test_slm_failure_falls_back_to_bm25(self) -> None:
        with (
            patch("app.services.academic_search_orchestrator_service.CASEI_SLM_ENABLED", True),
            patch("app.services.academic_search_orchestrator_service.interpret_query", side_effect=SlmUnavailableError("Pod apagado")),
        ):
            result = search_academic_documents(sample_documents(), "promedio mayor a 80", 10, mode="slm")
        self.assertEqual(result["metadata"]["processing_mode"], "fallback_bm25")

    def test_sex_filter_is_rejected_when_source_does_not_support_it(self) -> None:
        with self.assertRaises(UnsupportedSourceFilterError):
            search_academic_documents(sample_documents(), "estudiantes", 10, sexo="F")

    def test_student_identifier_stays_on_direct_route(self) -> None:
        with patch("app.services.academic_search_orchestrator_service.interpret_query") as mocked:
            result = search_academic_documents(sample_documents(), "IAG20200007 con riesgo", 10, mode="slm")
        mocked.assert_not_called()
        self.assertEqual(result["metadata"]["processing_mode"], "direct_bm25")
        self.assertTrue(any("identificador" in warning for warning in result["metadata"]["warnings"]))


class RunPodGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(gateway_app)

    def test_interpret_requires_api_key(self) -> None:
        with patch.dict(os.environ, {"CASEI_SLM_GATEWAY_API_KEY": "secret"}):
            response = self.client.post("/interpret", json={"query": "riesgo", "catalogs": {"version": "v1"}})
        self.assertEqual(response.status_code, 401)

    def test_interpret_returns_structured_response(self) -> None:
        interpretation = StructuredAcademicQuery(normalized_query="riesgo", keywords=["riesgo"], confidence=1)
        with (
            patch.dict(os.environ, {"CASEI_SLM_GATEWAY_API_KEY": "secret"}),
            patch("runpod_gateway.main.request_direct_ollama", return_value=interpretation),
        ):
            response = self.client.post(
                "/interpret",
                headers={"X-CASEI-SLM-KEY": "secret"},
                json={"query": "riesgo", "catalogs": {"version": "v1"}},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["interpretation"]["normalized_query"], "riesgo")


@unittest.skipUnless(os.getenv("CASEI_RUN_OLLAMA_TESTS") == "true", "Requiere Ollama y el modelo configurado.")
class OllamaIntegrationTests(unittest.TestCase):
    def test_real_model_returns_validated_numeric_filter(self) -> None:
        catalogs = build_query_catalogs(sample_documents())
        request = InterpretationRequest(
            query="estudiantes con promedio menor a 70 y rezago alto",
            catalogs=catalogs,
        )
        interpretation = request_direct_ollama(request, timeout=120)
        validated, warnings = validate_interpretation(interpretation, catalogs, request.query)
        self.assertIsNotNone(validated.promedio)
        self.assertEqual(validated.promedio.operator, "lt")
        self.assertEqual(validated.promedio.value, 70)
        self.assertIsNone(validated.rezago)
        self.assertTrue(any("no proporciona una cifra" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
