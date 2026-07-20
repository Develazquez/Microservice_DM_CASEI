from __future__ import annotations

from app.services import security_audit_service
from app.services.security_audit_service import SecurityContext, audit_items_access


def test_audit_items_access_inserts_unique_students_in_one_batch(monkeypatch) -> None:
    inserted_batches: list[list[dict[str, object]]] = []

    class FakeRepository:
        configured = True

        def insert_rows(self, table: str, rows: list[dict[str, object]]) -> int:
            assert table == "llm_context_audit"
            inserted_batches.append(rows)
            return len(rows)

    monkeypatch.setattr(security_audit_service, "SupabaseRepository", FakeRepository)
    context = SecurityContext(
        role="director",
        user_id="00000000-0000-0000-0000-000000000001",
        purpose="dashboard_test",
    )

    audit_items_access(
        context,
        endpoint="GET /cacei/segmentation/students",
        items=[
            {"id_estudiante": "A001", "id_periodo": "2026-1"},
            {"id_estudiante": "A001", "id_periodo": "2026-2"},
            {"id_estudiante": "A002", "id_periodo": "2026-1"},
        ],
        model_version="model-v1",
    )

    assert len(inserted_batches) == 1
    assert [row["student_id"] for row in inserted_batches[0]] == ["A001", "A002"]
    assert all(row["purpose"] == "dashboard_test" for row in inserted_batches[0])
