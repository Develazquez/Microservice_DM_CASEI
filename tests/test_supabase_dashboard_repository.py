from __future__ import annotations

import pandas as pd

from app.repositories.supabase_repository import SupabaseRepository
from app.services import segmentation_api_service
from app.services.academic_bm25_search_service import build_search_documents, get_cached_index


class DashboardRepository(SupabaseRepository):
    def __init__(self) -> None:
        super().__init__("https://example.supabase.co", "service-role")

    def fetch_table(self, table, select="*", filters=None, limit=None, order=None):
        if table == "ml_model_versions":
            return [
                {
                    "model_version": "model-active",
                    "algorithm": "kmeans",
                    "selected_representation": "pca_90",
                    "selected_k": 2,
                    "metrics": {"silhouette": 0.3},
                    "artifact_manifest": {},
                    "is_active": True,
                    "created_at": "2026-07-23T10:00:00Z",
                }
            ]
        if table == "cluster_assignments":
            return [
                {
                    "execution_id": "run-new",
                    "model_version": "model-active",
                    "student_profile_id": "profile-1",
                    "id_estudiante": "IDS1",
                    "id_periodo": "2023-3",
                    "programa": "IDS",
                    "cluster": 1,
                    "perfil_academico": "Crítico / rezago alto",
                    "prioridad_tutorial": "alta",
                    "membership_score": 0.8,
                    "distance_to_centroid": 0.2,
                    "created_at": "2026-07-23T10:20:00Z",
                },
                {
                    "execution_id": "run-old",
                    "model_version": "model-active",
                    "student_profile_id": "profile-1",
                    "id_estudiante": "IDS1",
                    "id_periodo": "2023-3",
                    "programa": "IDS",
                    "cluster": 0,
                    "perfil_academico": "Regular / seguimiento preventivo",
                    "prioridad_tutorial": "baja-media",
                    "created_at": "2026-07-23T10:10:00Z",
                },
            ]
        if table == "student_period_features":
            return [
                {
                    "execution_id": "run-new",
                    "student_profile_id": "profile-1",
                    "id_estudiante": "IDS1",
                    "id_periodo": "2023-3",
                    "programa": "IDS",
                    "cohorte": "2020",
                    "estatus_academico": "Activo",
                    "promedio_general": 63.5,
                    "porcentaje_asistencia": 58.0,
                    "rezago_materias": 3,
                    "features": {
                        "materias_reprobadas_acumuladas": 4,
                        "materias_reprobadas_periodo": 2,
                    },
                    "created_at": "2026-07-23T10:20:00Z",
                }
            ]
        if table == "profiles":
            return [
                {
                    "id": "profile-1",
                    "matricula": "IDS1",
                    "nombre": "Ana",
                    "apellidos": "López",
                }
            ]
        raise AssertionError(f"Unexpected table: {table}")


def test_current_student_segmentation_uses_latest_partial_result() -> None:
    result = DashboardRepository().current_student_segmentation()

    assert len(result) == 1
    row = result.iloc[0]
    assert row["cluster"] == 1
    assert row["promedio_general"] == 63.5
    assert row["materias_reprobadas_acumuladas"] == 4
    assert row["nombre"] == "Ana López"


def test_active_model_metadata_is_exposed() -> None:
    result = DashboardRepository().active_model_metadata()

    assert result["model_version"] == "model-active"
    assert result["selected_k"] == 2


def test_summary_uses_supabase_active_model_and_current_rows(monkeypatch) -> None:
    students = pd.DataFrame(
        [
            {
                "id_estudiante": "IDS1",
                "id_periodo": "2023-3",
                "programa": "IDS",
                "cluster": 1,
                "perfil_academico": "Crítico / rezago alto",
                "prioridad_tutorial": "alta",
                "promedio_general": 63.5,
                "porcentaje_asistencia": 58.0,
            }
        ]
    )

    class SummaryRepository:
        def require_configured(self) -> None:
            return None

        def current_student_segmentation(self) -> pd.DataFrame:
            return students

        def active_model_metadata(self):
            return {
                "model_version": "model-active",
                "selected_representation": "pca_90",
                "selected_k": 2,
                "metrics": {"silhouette": 0.3},
            }

    monkeypatch.setattr(segmentation_api_service, "CASEI_DB_MODE", "supabase")
    monkeypatch.setattr(segmentation_api_service, "SupabaseRepository", SummaryRepository)

    result = segmentation_api_service.segmentation_summary()

    assert result["model_version"] == "model-active"
    assert result["total_records"] == 1
    assert result["average_score"] == 63.5


def test_live_supabase_rows_are_searchable_by_profile() -> None:
    source = pd.DataFrame(
        [
            {
                "id_estudiante": "IDS1",
                "id_periodo": "2023-3",
                "programa": "Ingeniería en Desarrollo de Software",
                "cohorte": "2020",
                "estatus_academico": "Activo",
                "cluster": 0,
                "perfil_academico": "Regular / seguimiento preventivo",
                "promedio_general": 84.0,
                "porcentaje_asistencia": 91.0,
                "rezago_materias": 0,
                "materias_reprobadas_acumuladas": 0,
            }
        ]
    )

    documents = build_search_documents(source)
    results = get_cached_index(documents).search("alumnos regulares", top_k=10)

    assert len(results) == 1
    assert results.iloc[0]["id_estudiante"] == "IDS1"
    assert results.iloc[0]["perfil_sugerido"] == "Regular / seguimiento preventivo"


def test_colloquial_query_has_bm25_fallback_without_embeddings() -> None:
    source = pd.DataFrame(
        [
            {
                "id_estudiante": "IDS-RISK",
                "id_periodo": "2023-3",
                "programa": "Ingeniería en Desarrollo de Software",
                "cohorte": "2020",
                "estatus_academico": "Activo",
                "cluster": 1,
                "perfil_academico": "Crítico / rezago alto",
                "promedio_general": 52.0,
                "porcentaje_asistencia": 55.0,
                "rezago_materias": 4,
                "materias_reprobadas_acumuladas": 5,
            }
        ]
    )

    documents = build_search_documents(source)
    results = get_cached_index(documents).search("los que van flojos", top_k=10)

    assert len(results) == 1
    assert results.iloc[0]["id_estudiante"] == "IDS-RISK"
