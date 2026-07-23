from __future__ import annotations

import unittest

import pandas as pd

from app.models.config import CARDEX_COLUMNS, FINAL_FEATURES, SUPABASE_SNAPSHOT_REGISTRY_DIR
from app.repositories.factory import repository_status
from app.services import supabase_sync_service
from app.services.supabase_sync_service import (
    build_cardex_from_supabase,
    build_student_period_preview,
    infer_cohort,
    validate_against_local_sources,
)


class SupabaseSyncServiceTests(unittest.TestCase):
    def test_snapshot_registry_directory_is_available_to_sync_service(self) -> None:
        self.assertEqual(
            supabase_sync_service.SUPABASE_SNAPSHOT_REGISTRY_DIR,
            SUPABASE_SNAPSHOT_REGISTRY_DIR,
        )

    def test_repository_status_has_fallback_contract(self) -> None:
        status = repository_status(mode="local")
        self.assertEqual(status["mode"], "local")
        self.assertEqual(status["selected_repository"], "local")
        self.assertIn("supabase", status)

    def test_build_student_period_preview_from_historial(self) -> None:
        source = {
            "profiles": [
                {
                    "id": "student-1",
                    "matricula": "IAG20260001",
                    "carrera": "Ingenieria Agroindustrial",
                    "program_id": "program-1",
                    "sexo": "F",
                    "estatus_academico": "activo",
                }
            ],
            "historial_academico": [
                {
                    "student_id": "student-1",
                    "subject_id": "subject-1",
                    "period_id": "period-1",
                    "grade": 80,
                    "calificacion_extra": None,
                    "status": "aprobada",
                    "attempt_type": "ordinario",
                },
                {
                    "student_id": "student-1",
                    "subject_id": "subject-2",
                    "period_id": "period-1",
                    "grade": 60,
                    "calificacion_extra": 75,
                    "status": "aprobada_extra",
                    "attempt_type": "extraordinario",
                },
            ],
            "materias": [
                {"id": "subject-1", "nombre": "Materia A", "creditos": 5},
                {"id": "subject-2", "nombre": "Materia B", "creditos": 4},
            ],
            "periodos": [{"id": "period-1", "clave": "2026-1", "nombre": "2026-1"}],
            "carga_academica": [],
        }

        preview = build_student_period_preview(source)

        self.assertEqual(len(preview), 1)
        row = preview.iloc[0]
        self.assertEqual(row["id_estudiante"], "IAG20260001")
        self.assertEqual(row["id_periodo"], "2026-1")
        self.assertEqual(row["sexo"], "F")
        self.assertEqual(row["materias_aprobadas"], 2)
        self.assertEqual(row["materias_reprobadas_periodo"], 0)
        self.assertEqual(row["creditos_inscritos_periodo"], 9)
        self.assertTrue(set(FINAL_FEATURES).issubset(preview.columns))

    def test_real_pdf_identifiers_preserve_cardex_contract(self) -> None:
        source = {
            "profiles": [
                {
                    "id": "student-legacy",
                    "matricula": "193243",
                    "nombre": "Moisés De Jesús",
                    "apellidos": "Anzueto González",
                    "carrera": "Ingeniería en Desarrollo de Software",
                    "program_id": "program-ids",
                    "estatus_academico": "Activo",
                    "cuatrimestre_actual": 2,
                }
            ],
            "historial_academico": [
                {
                    "student_id": "student-legacy",
                    "subject_id": "subject-1",
                    "period_id": "period-2020-1",
                    "grade": 77,
                    "calificacion_extra": None,
                    "status": "Aprobado",
                    "attempt_type": "Ordinario",
                }
            ],
            "materias": [
                {
                    "id": "subject-1",
                    "nombre": "Ingeniería de Software Asistida por Computadora",
                    "creditos": 6,
                }
            ],
            "periodos": [
                {
                    "id": "period-2020-1",
                    "clave": "2020-1",
                    "nombre": "ENERO-ABRIL 2020",
                }
            ],
            "academic_programs": [
                {
                    "id": "program-ids",
                    "clave": "NME",
                    "nombre": "Ingeniería en Desarrollo de Software",
                }
            ],
            "carga_academica": [],
        }

        cardex = build_cardex_from_supabase(source)

        self.assertEqual(list(cardex.columns), CARDEX_COLUMNS)
        self.assertEqual(cardex.iloc[0]["Nombre"], "Moisés De Jesús Anzueto González")
        self.assertEqual(cardex.iloc[0]["Periodo"], 1)
        self.assertEqual(cardex.iloc[0]["PeriodoCursado"], "2020-1")
        self.assertEqual(cardex.iloc[0]["EstatusCardex"], "ordinario")
        self.assertEqual(infer_cohort("193243"), "2019")
        self.assertEqual(infer_cohort("243678"), "2024")

    def test_validation_marks_preview_as_non_replacement(self) -> None:
        preview = pd.DataFrame(
            [
                {
                    "id_estudiante": "IAG20260001",
                    "id_periodo": "2026-1",
                    "programa": "Ingenieria Agroindustrial",
                    "student_profile_id": "student-1",
                    "program_id": "program-1",
                    "sexo": "F",
                    "promedio_general": 80,
                    "promedio_periodo": 80,
                    "materias_reprobadas_periodo": 0,
                    "materias_reprobadas_acumuladas": 0,
                    "creditos_inscritos_periodo": 9,
                    "creditos_aprobados_periodo": 9,
                    "bandera_dato_incompleto": 0,
                }
            ]
        )

        validation = validate_against_local_sources(
            source={"profiles": [{"id": "student-1"}]},
            preview=preview,
            source_hash="abc123",
        )

        self.assertFalse(validation["decision"]["active_dataset_replaced"])
        self.assertTrue(validation["decision"]["requires_academic_review"])
        self.assertIn("comparison", validation)


if __name__ == "__main__":
    unittest.main()
