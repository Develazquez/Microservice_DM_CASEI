from __future__ import annotations

from typing import Any

import httpx
from fastapi import Request

from app.models.config import (
    CASEI_ALLOW_DEV_IDENTITY_HEADERS,
    CASEI_AUTH_TIMEOUT_SECONDS,
    CASEI_SUPABASE_ANON_KEY,
    CASEI_SUPABASE_SERVICE_ROLE_KEY,
    CASEI_SUPABASE_URL,
)
from app.repositories.supabase_repository import SupabaseRepository
from app.services.security_audit_service import (
    AuthorizationError,
    SecurityContext,
    normalize_role,
    security_context_from_headers,
)


PROFILE_ROLE_MAP = {
    "director": "director",
    "tutor": "tutor",
    "encargado": "coordinador",
}


class AuthenticationError(AuthorizationError):
    """Raised when a production request lacks a valid Supabase access token."""


def security_context_from_request(
    request: Request,
    requested_role: str | None = None,
) -> SecurityContext:
    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        context = validate_supabase_access_token(token, purpose=request.headers.get("x-casei-purpose"))
        if requested_role and normalize_role(requested_role) != context.role:
            raise AuthorizationError("El rol solicitado no coincide con el perfil autenticado.")
        return context

    if CASEI_ALLOW_DEV_IDENTITY_HEADERS:
        context = security_context_from_headers(request.headers, role=requested_role)
        return SecurityContext(
            role=context.role,
            user_id=context.user_id,
            tenant_id=context.tenant_id,
            program_id=context.program_id,
            program_name=context.program_name,
            purpose=context.purpose,
            source="development_headers",
        )

    raise AuthenticationError("Se requiere un access token valido de Supabase.")


def validate_supabase_access_token(token: str, purpose: str | None = None) -> SecurityContext:
    if not CASEI_SUPABASE_URL:
        raise AuthenticationError("Supabase Auth no esta configurado en el microservicio.")
    api_key = CASEI_SUPABASE_ANON_KEY or CASEI_SUPABASE_SERVICE_ROLE_KEY
    if not api_key:
        raise AuthenticationError("Falta la API key necesaria para validar tokens de Supabase.")

    try:
        response = httpx.get(
            f"{CASEI_SUPABASE_URL.rstrip('/')}/auth/v1/user",
            headers={"apikey": api_key, "Authorization": f"Bearer {token}"},
            timeout=CASEI_AUTH_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise AuthenticationError(f"No fue posible validar la sesion de Supabase: {exc}") from exc

    if response.status_code != 200:
        raise AuthenticationError("El access token de Supabase es invalido o expiro.")

    user = response.json()
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        raise AuthenticationError("Supabase no devolvio un identificador de usuario valido.")

    # Extraer tenant_id del JWT app_metadata
    app_metadata = user.get("app_metadata", {})
    tenant_id = _optional_text(app_metadata.get("tenant_id"))

    profile = _profile_for_user(user_id)
    raw_role = str(profile.get("rol") or "").strip().lower()
    role = PROFILE_ROLE_MAP.get(raw_role)
    if not role:
        raise AuthorizationError(f"El rol {raw_role or 'sin rol'} no tiene acceso a segmentacion.")

    program_id = _optional_text(profile.get("program_id"))
    program_name = _optional_text(profile.get("carrera"))
    if program_id:
        program_name = _program_name(program_id) or program_name

    return SecurityContext(
        role=role,
        user_id=user_id,
        tenant_id=tenant_id,
        program_id=program_id,
        program_name=program_name,
        purpose=purpose,
        source="supabase_jwt",
    )


def require_roles(context: SecurityContext, *allowed_roles: str) -> None:
    if context.role not in set(allowed_roles):
        allowed = ", ".join(sorted(allowed_roles))
        raise AuthorizationError(f"La operacion requiere uno de estos roles: {allowed}.")


def _profile_for_user(user_id: str) -> dict[str, Any]:
    repository = SupabaseRepository()
    repository.require_configured()
    rows = repository.fetch_table(
        "profiles",
        select="id,rol,carrera,program_id",
        filters={"id": f"eq.{user_id}"},
        limit=1,
    )
    if not rows:
        raise AuthorizationError("No existe un perfil CASEI para el usuario autenticado.")
    return rows[0]


def _program_name(program_id: str) -> str | None:
    repository = SupabaseRepository()
    rows = repository.fetch_table(
        "academic_programs",
        select="id,nombre",
        filters={"id": f"eq.{program_id}"},
        limit=1,
    )
    return _optional_text(rows[0].get("nombre")) if rows else None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
