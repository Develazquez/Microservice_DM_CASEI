from __future__ import annotations

from types import SimpleNamespace

from app.services import ml_worker_service as worker


class FakeRepository:
    def __init__(self):
        self.rpc_calls = []
        self.patch_calls = []

    def rpc(self, name, parameters=None):
        self.rpc_calls.append((name, parameters or {}))
        return None

    def patch_rows(self, table, payload, filters):
        self.patch_calls.append((table, payload, filters))

    def fetch_table(self, table, **kwargs):
        return []


class FakeInference:
    model_version = "model-v1"

    def metadata(self):
        return {
            "model_version": self.model_version,
            "source_records": 2,
            "inferred_records": 2,
            "out_of_distribution_records": 0,
        }


def test_worker_processes_and_completes_inference(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(worker, "sync_from_supabase", lambda **kwargs: {"source_hash": "a" * 64})
    monkeypatch.setattr(worker, "promote_supabase_preview", lambda *args, **kwargs: {"status": "promoted"})
    monkeypatch.setattr(worker, "infer_with_active_bundle", lambda **kwargs: FakeInference())
    monkeypatch.setattr(worker, "publish_inference_result", lambda *args, **kwargs: {"cluster_assignments": 2})
    monkeypatch.setattr(worker, "persist_active_inference_snapshot", lambda result: {"records": 2})
    monkeypatch.setattr(worker, "refresh_search_index", lambda **kwargs: {"documents": 2})

    result = worker.process_claimed_job(
        repository,
        {"execution_id": "run-1", "run_type": "inference", "requested_by": "director-1"},
    )

    assert result["status"] == "completed"
    rpc_names = [name for name, _ in repository.rpc_calls]
    assert rpc_names.count("heartbeat_ml_run") == 3
    assert rpc_names[-1] == "complete_ml_run"


def test_worker_marks_failure_without_hiding_exception(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(worker, "sync_from_supabase", lambda **kwargs: (_ for _ in ()).throw(ValueError("invalid source")))

    try:
        worker.process_claimed_job(repository, {"execution_id": "run-2", "run_type": "inference"})
    except ValueError as exc:
        assert str(exc) == "invalid source"
    else:
        raise AssertionError("El worker debio propagar el fallo para observabilidad.")

    assert repository.rpc_calls[-1][0] == "fail_ml_run"
    assert repository.rpc_calls[-1][1]["final_status"] == "failed"


def test_worker_propagates_tenant_to_candidate_training(monkeypatch):
    repository = FakeRepository()
    captured = {}
    monkeypatch.setattr(worker, "sync_from_supabase", lambda **kwargs: {"source_hash": "a" * 64})
    monkeypatch.setattr(worker, "promote_supabase_preview", lambda *args, **kwargs: {"status": "promoted"})

    def fake_train_candidate_model(**kwargs):
        captured.update(kwargs)
        return {
            "status": "review_required",
            "candidate_model_version": "model-v2",
            "comparison": {"decision": "candidate_for_manual_review"},
        }

    monkeypatch.setattr(worker, "train_candidate_model", fake_train_candidate_model)

    result = worker.process_claimed_job(
        repository,
        {
            "execution_id": "run-tenant",
            "run_type": "retrain",
            "requested_by": "director-1",
            "tenant_id": "tenant-1",
        },
    )

    assert result["status"] == "review_required"
    assert captured["tenant_id"] == "tenant-1"
