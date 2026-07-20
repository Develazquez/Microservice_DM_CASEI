from __future__ import annotations

from hashlib import sha256
from datetime import datetime, timezone
import json
from typing import Any

from app.repositories.supabase_repository import SupabaseRepository
from app.services.security_audit_service import AuthorizationError, SecurityContext


FINAL_STATUSES = {"completed", "review_required", "rejected", "failed", "cancelled"}


def enqueue_job(
    context: SecurityContext,
    operation: str = "auto",
    trigger_source: str = "director_manual",
    source_hash: str | None = None,
    scope: dict[str, Any] | None = None,
    source_batch_id: str | None = None,
    student_profile_ids: list[str] | None = None,
    notes: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    normalized_operation = operation.strip().lower()
    if normalized_operation not in {"auto", "inference", "retrain"}:
        raise ValueError(f"Operacion ML no soportada: {operation}")
    if normalized_operation == "retrain" and context.role != "director":
        raise AuthorizationError("Solo el director puede solicitar reentrenamiento.")
    if context.role not in {"director", "tutor"}:
        raise AuthorizationError("El rol autenticado no puede crear trabajos ML.")

    resolved_scope = scope or {}
    resolved_idempotency = idempotency_key or build_idempotency_key(
        normalized_operation,
        trigger_source,
        source_hash,
        resolved_scope,
        source_batch_id,
    )
    if not source_hash and not source_batch_id and idempotency_key is None:
        minute_bucket = int(datetime.now(timezone.utc).timestamp() // 60)
        resolved_idempotency = f"{resolved_idempotency}:{minute_bucket}"
    repository = SupabaseRepository()
    execution_id = repository.rpc(
        "enqueue_ml_run",
        {
            "p_operation": normalized_operation,
            "p_trigger_source": trigger_source,
            "p_source_hash": source_hash,
            "p_scope": resolved_scope,
            "p_idempotency_key": resolved_idempotency,
            "p_source_batch_id": source_batch_id,
            "p_student_ids": student_profile_ids or [],
            "p_notes": notes,
            "p_requested_by": context.user_id,
        },
    )
    return get_job(str(execution_id), context)


def get_job(execution_id: str, context: SecurityContext) -> dict[str, Any]:
    repository = SupabaseRepository()
    rows = repository.fetch_table(
        "ml_model_runs",
        select="*",
        filters={"execution_id": f"eq.{execution_id}"},
        limit=1,
    )
    if not rows:
        raise FileNotFoundError(f"Trabajo ML no encontrado: {execution_id}")
    job = rows[0]
    require_job_access(job, context)
    return job


def cancel_job(execution_id: str, context: SecurityContext) -> dict[str, Any]:
    job = get_job(execution_id, context)
    if job.get("status") in FINAL_STATUSES:
        raise ValueError(f"El trabajo ya termino con estado {job.get('status')}.")
    SupabaseRepository().patch_rows(
        "ml_model_runs",
        {"status": "cancelled", "progress": int(job.get("progress") or 0)},
        {"execution_id": f"eq.{execution_id}", "status": "in.(queued,claimed)"},
    )
    return get_job(execution_id, context)


def active_model() -> dict[str, Any]:
    rows = SupabaseRepository().fetch_table(
        "ml_model_versions",
        select="*",
        filters={"is_active": "eq.true"},
        limit=1,
    )
    if not rows:
        raise FileNotFoundError("No existe una version activa en Supabase.")
    return rows[0]


def require_job_access(job: dict[str, Any], context: SecurityContext) -> None:
    if context.role == "director":
        return
    if context.user_id and str(job.get("requested_by") or "") == context.user_id:
        return
    raise AuthorizationError("El usuario no tiene acceso a este trabajo ML.")


def build_idempotency_key(
    operation: str,
    trigger_source: str,
    source_hash: str | None,
    scope: dict[str, Any],
    source_batch_id: str | None,
) -> str:
    payload = json.dumps(
        {
            "operation": operation,
            "trigger_source": trigger_source,
            "source_hash": source_hash,
            "scope": scope,
            "source_batch_id": source_batch_id,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return "casei:" + sha256(payload.encode("utf-8")).hexdigest()
