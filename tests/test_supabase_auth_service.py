from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import supabase_auth_service as auth
from app.services.security_audit_service import AuthorizationError


class FakeResponse:
    status_code = 200

    def json(self):
        return {"id": "user-1"}


def test_token_identity_comes_from_supabase(monkeypatch):
    monkeypatch.setattr(auth, "CASEI_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(auth, "CASEI_SUPABASE_ANON_KEY", "anon")
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(
        auth,
        "_profile_for_user",
        lambda user_id: {"id": user_id, "rol": "tutor", "program_id": "program-1", "carrera": "IDS"},
    )
    monkeypatch.setattr(auth, "_program_name", lambda program_id: "Ingenieria en Desarrollo de Software")

    context = auth.validate_supabase_access_token("valid-token")

    assert context.user_id == "user-1"
    assert context.role == "tutor"
    assert context.program_id == "program-1"
    assert context.source == "supabase_jwt"


def test_requested_role_cannot_override_jwt(monkeypatch):
    monkeypatch.setattr(
        auth,
        "validate_supabase_access_token",
        lambda token, purpose=None: auth.SecurityContext(role="tutor", user_id="user-1"),
    )
    request = SimpleNamespace(
        headers={"authorization": "Bearer token"},
    )

    with pytest.raises(AuthorizationError):
        auth.security_context_from_request(request, requested_role="director")


def test_production_rejects_unsigned_development_headers(monkeypatch):
    monkeypatch.setattr(auth, "CASEI_ALLOW_DEV_IDENTITY_HEADERS", False)
    request = SimpleNamespace(headers={"x-casei-role": "director"})

    with pytest.raises(auth.AuthenticationError):
        auth.security_context_from_request(request)
