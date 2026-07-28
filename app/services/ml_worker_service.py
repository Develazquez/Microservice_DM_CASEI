from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models.config import (
    CASEI_AUTO_INFERENCE_ENABLED,
    CASEI_ML_EVENT_DEBOUNCE_SECONDS,
    CASEI_ML_JOB_TIMEOUT_SECONDS,
    CASEI_ML_WORKER_ID,
)
from app.repositories.supabase_repository import SupabaseRepository
from app.services.candidate_model_service import train_candidate_model
from app.services.ml_job_service import enqueue_job
from app.services.model_bundle_inference_service import infer_with_active_bundle, persist_active_inference_snapshot
from app.services.search_index_refresh_service import refresh_search_index
from app.services.security_audit_service import SecurityContext
from app.services.supabase_results_sync_service import publish_inference_result
from app.services.supabase_sync_service import promote_supabase_preview, sync_from_supabase


def worker_once() -> dict[str, Any]:
    repository = SupabaseRepository()
    repository.require_configured()
    recovered = repository.rpc(
        "recover_stale_ml_runs",
        {"timeout_seconds": CASEI_ML_JOB_TIMEOUT_SECONDS},
    )
    event_result = consume_data_events(repository) if CASEI_AUTO_INFERENCE_ENABLED else {"claimed": 0, "jobs": 0}
    claimed = repository.rpc("claim_next_ml_run", {"worker_id": CASEI_ML_WORKER_ID}) or []
    if not claimed:
        return {"status": "idle", "recovered": int(recovered or 0), "events": event_result}
    job = claimed[0] if isinstance(claimed, list) else claimed
    result = process_claimed_job(repository, job)
    return {"status": "processed", "recovered": int(recovered or 0), "events": event_result, "job": result}


def consume_data_events(repository: SupabaseRepository) -> dict[str, int]:
    events = repository.rpc(
        "claim_ml_data_events",
        {
            "worker_id": CASEI_ML_WORKER_ID,
            "max_events": 500,
            "debounce_seconds": CASEI_ML_EVENT_DEBOUNCE_SECONDS,
            "stale_seconds": CASEI_ML_JOB_TIMEOUT_SECONDS,
        },
    ) or []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        key = str(event.get("source_batch_id") or event.get("id"))
        grouped[key].append(event)

    jobs = 0
    for group in grouped.values():
        event_ids = [str(event["id"]) for event in group]
        try:
            first = group[0]
            requester = str(first.get("requested_by") or "") or None
            context = SecurityContext(role="tutor" if first.get("source_batch_id") else "director", user_id=requester)
            enqueue_job(
                context=context,
                operation="inference",
                trigger_source="tutor_import_confirmed",
                source_batch_id=first.get("source_batch_id"),
                student_profile_ids=sorted(
                    {str(event["student_profile_id"]) for event in group if event.get("student_profile_id")}
                ),
                notes="Inferencia automatica consolidada desde ml_data_events.",
            )
            repository.rpc(
                "finish_ml_data_events",
                {"event_ids": event_ids, "worker_id": CASEI_ML_WORKER_ID, "failure_message": None},
            )
            jobs += 1
        except Exception as exc:
            repository.rpc(
                "finish_ml_data_events",
                {"event_ids": event_ids, "worker_id": CASEI_ML_WORKER_ID, "failure_message": str(exc)},
            )
    return {"claimed": len(events), "jobs": jobs}


def process_claimed_job(repository: SupabaseRepository, job: dict[str, Any]) -> dict[str, Any]:
    execution_id = str(job["execution_id"])
    operation = str(job.get("run_type") or "auto")
    _tid = str(job["tenant_id"]) if job.get("tenant_id") else None
    try:
        heartbeat(repository, execution_id, "validating", 10)
        sync = sync_from_supabase(limit=10000, write_preview=True, tenant_id=_tid)
        source_hash = str(sync["source_hash"])
        promote_supabase_preview(source_hash, reviewed_by=str(job.get("requested_by") or "") or None)
        repository.patch_rows(
            "ml_model_runs",
            {"source_hash": source_hash},
            {"execution_id": f"eq.{execution_id}"},
        )

        if operation == "retrain":
            heartbeat(repository, execution_id, "processing", 35)
            candidate = train_candidate_model(tenant_id=_tid)
            final_status = str(candidate["status"])
            repository.patch_rows(
                "ml_model_runs",
                {
                    "candidate_model_version": candidate["candidate_model_version"],
                    "metrics": candidate,
                    "review_notes": candidate["comparison"]["decision"],
                },
                {"execution_id": f"eq.{execution_id}"},
            )
            repository.rpc(
                "fail_ml_run",
                {
                    "target_execution_id": execution_id,
                    "worker_id": CASEI_ML_WORKER_ID,
                    "failure_message": candidate["comparison"]["decision"],
                    "final_status": final_status,
                },
            )
            return {"execution_id": execution_id, **candidate}

        heartbeat(repository, execution_id, "processing", 45)
        student_ids = matriculas_for_job(repository, execution_id, tenant_id=_tid)
        inference = infer_with_active_bundle(
            student_ids=student_ids or None,
            model_version=active_model_version(repository, tenant_id=_tid),
        )
        heartbeat(repository, execution_id, "publishing", 80)
        counts = publish_inference_result(inference, execution_id, source_hash, tenant_id=_tid)
        snapshot = persist_active_inference_snapshot(inference)
        search_index = refresh_search_index(student_ids=student_ids or None)
        repository.patch_rows(
            "ml_run_students",
            {"status": "completed"},
            {"execution_id": f"eq.{execution_id}"},
        )
        metrics = {
            **inference.metadata(),
            "published_counts": counts,
            "active_snapshot": snapshot,
            "search_index": search_index,
        }
        repository.rpc(
            "complete_ml_run",
            {
                "target_execution_id": execution_id,
                "worker_id": CASEI_ML_WORKER_ID,
                "final_metrics": metrics,
                "resolved_model_version": inference.model_version,
            },
        )
        return {"execution_id": execution_id, "status": "completed", **metrics}
    except Exception as exc:
        try:
            repository.rpc(
                "fail_ml_run",
                {
                    "target_execution_id": execution_id,
                    "worker_id": CASEI_ML_WORKER_ID,
                    "failure_message": str(exc),
                    "final_status": "failed",
                },
            )
        finally:
            raise


def matriculas_for_job(repository: SupabaseRepository, execution_id: str, tenant_id: str | None = None) -> list[str]:
    run_students = repository.fetch_table(
        "ml_run_students",
        select="student_profile_id",
        filters={"execution_id": f"eq.{execution_id}"},
        limit=10000,
    )
    profile_ids = {str(row.get("student_profile_id")) for row in run_students if row.get("student_profile_id")}
    if not profile_ids:
        return []
    filters: dict[str, str] = {"rol": "eq.alumno"}
    if tenant_id:
        filters["tenant_id"] = f"eq.{tenant_id}"
    profiles = repository.fetch_table(
        "profiles",
        select="id,matricula",
        filters=filters,
        limit=10000,
    )
    return [str(row["matricula"]) for row in profiles if str(row.get("id")) in profile_ids and row.get("matricula")]


def heartbeat(repository: SupabaseRepository, execution_id: str, status: str, progress: int) -> None:
    repository.rpc(
        "heartbeat_ml_run",
        {
            "target_execution_id": execution_id,
            "worker_id": CASEI_ML_WORKER_ID,
            "next_status": status,
            "next_progress": progress,
        },
    )


def active_model_version(repository: SupabaseRepository, tenant_id: str | None = None) -> str | None:
    filters: dict[str, str] = {"is_active": "eq.true"}
    if tenant_id:
        filters["tenant_id"] = f"eq.{tenant_id}"
    rows = repository.fetch_table(
        "ml_model_versions",
        select="model_version",
        filters=filters,
        limit=1,
    )
    return str(rows[0]["model_version"]) if rows else None
