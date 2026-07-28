from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from app.repositories.supabase_repository import SupabaseRepository


SCOPED_ROLES = {"tutor", "coordinador"}
VALID_ROLES = {"director", "coordinador", "tutor", "analista"}


class AuthorizationError(PermissionError):
    """Raised when the caller role cannot access the requested student data."""


@dataclass(frozen=True)
class SecurityContext:
    role: str = "director"
    user_id: str | None = None
    tenant_id: str | None = None
    program_id: str | None = None
    program_name: str | None = None
    purpose: str | None = None
    source: str = "headers"

    @property
    def is_scoped(self) -> bool:
        return self.role in SCOPED_ROLES


def normalize_role(role: str | None) -> str:
    normalized = (role or "director").strip().lower()
    if normalized not in VALID_ROLES:
        valid = ", ".join(sorted(VALID_ROLES))
        raise AuthorizationError(f"Rol no autorizado para segmentacion: {normalized}. Roles validos: {valid}.")
    return normalized


def security_context_from_headers(headers: Mapping[str, str], role: str | None = None) -> SecurityContext:
    header_role = headers.get("x-casei-role") or headers.get("X-CASEI-ROLE")
    query_role = normalize_role(role) if role else None
    normalized_header_role = normalize_role(header_role) if header_role else None
    if query_role and normalized_header_role and query_role != normalized_header_role:
        raise AuthorizationError("El rol solicitado no coincide con el rol autenticado recibido por headers.")
    selected_role = query_role or normalized_header_role or "director"
    return SecurityContext(
        role=selected_role,
        user_id=headers.get("x-casei-user-id") or headers.get("X-CASEI-USER-ID"),
        tenant_id=headers.get("x-casei-tenant-id") or headers.get("X-CASEI-TENANT-ID"),
        program_id=headers.get("x-casei-program-id") or headers.get("X-CASEI-PROGRAM-ID"),
        program_name=headers.get("x-casei-program") or headers.get("X-CASEI-PROGRAM"),
        purpose=headers.get("x-casei-purpose") or headers.get("X-CASEI-PURPOSE"),
    )


def apply_student_scope(df: pd.DataFrame, context: SecurityContext | None) -> pd.DataFrame:
    if context is None or context.role in {"director", "analista"}:
        return df
    if df.empty:
        return df
    if context.role == "coordinador":
        return apply_program_scope(df, context)
    if context.role == "tutor":
        return apply_tutor_scope(df, context)
    return df.iloc[0:0]


def require_student_access(student_id: str, context: SecurityContext | None) -> None:
    if context is None or context.role in {"director", "analista"}:
        return
    probe = pd.DataFrame([{"id_estudiante": student_id}])
    scoped = apply_student_scope(probe, context)
    if scoped.empty:
        raise AuthorizationError("El usuario no tiene alcance autorizado para consultar este alumno.")


def apply_program_scope(df: pd.DataFrame, context: SecurityContext) -> pd.DataFrame:
    if not context.program_id and not context.program_name:
        raise AuthorizationError("El rol coordinador requiere X-CASEI-PROGRAM-ID o X-CASEI-PROGRAM.")
    scoped = df
    if context.program_id and "program_id" in scoped.columns:
        scoped = scoped[scoped["program_id"].fillna("").astype(str) == context.program_id]
    elif context.program_name and "programa" in scoped.columns:
        scoped = scoped[scoped["programa"].fillna("").str.lower() == context.program_name.lower()]
    return scoped


def apply_tutor_scope(df: pd.DataFrame, context: SecurityContext) -> pd.DataFrame:
    if not context.user_id:
        raise AuthorizationError("El rol tutor requiere X-CASEI-USER-ID para validar alcance.")
    allowed = tutor_allowed_student_ids(context.user_id, tenant_id=context.tenant_id)
    if not allowed:
        return df.iloc[0:0]
    if "student_profile_id" in df.columns:
        by_profile = df["student_profile_id"].fillna("").astype(str).isin(allowed["profile_ids"])
    else:
        by_profile = pd.Series(False, index=df.index)
    if "id_estudiante" in df.columns:
        by_matricula = df["id_estudiante"].fillna("").astype(str).isin(allowed["matriculas"])
    else:
        by_matricula = pd.Series(False, index=df.index)
    return df[by_profile | by_matricula]


def tutor_allowed_student_ids(tutor_id: str, tenant_id: str | None = None) -> dict[str, set[str]]:
    repository = SupabaseRepository()
    repository.require_configured()
    scope_rows = repository.fetch_tutor_scope(tutor_id=tutor_id, tenant_id=tenant_id, limit=10000)
    profile_ids = {str(row.get("student_id")) for row in scope_rows if row.get("student_id")}
    if not profile_ids:
        return {"profile_ids": set(), "matriculas": set()}
    filters: dict[str, str] = {"rol": "eq.alumno"}
    if tenant_id:
        filters["tenant_id"] = f"eq.{tenant_id}"
    profile_rows = repository.fetch_table(
        "profiles",
        select="id,matricula",
        filters=filters,
        limit=10000,
    )
    matriculas = {
        str(row.get("matricula"))
        for row in profile_rows
        if row.get("id") and str(row.get("id")) in profile_ids and row.get("matricula")
    }
    return {"profile_ids": profile_ids, "matriculas": matriculas}


def audit_context_access(
    context: SecurityContext | None,
    endpoint: str,
    student_id: str | None = None,
    model_version: str | None = None,
    purpose: str | None = None,
) -> None:
    if context is None or not context.user_id:
        return
    repository = SupabaseRepository()
    if not repository.configured:
        return
    payload: dict[str, Any] = {
        "requested_by": context.user_id,
        "role": context.role,
        "student_id": student_id,
        "endpoint": endpoint,
        "purpose": purpose or context.purpose or "academic_segmentation_access",
        "model_version": model_version,
    }
    if context.tenant_id:
        payload["tenant_id"] = context.tenant_id
    try:
        repository.insert_rows("llm_context_audit", [payload])
    except Exception:
        # La auditoria no debe romper la consulta local; se monitorea por health/logs en despliegue.
        return


def audit_items_access(
    context: SecurityContext | None,
    endpoint: str,
    items: list[dict[str, Any]],
    model_version: str | None = None,
) -> None:
    if context is None or not context.user_id:
        return
    repository = SupabaseRepository()
    if not repository.configured:
        return

    seen: set[str] = set()
    payloads: list[dict[str, Any]] = []
    for item in items:
        student_id = item.get("id_estudiante") or item.get("student_id")
        if not student_id:
            continue
        key = str(student_id)
        if key in seen:
            continue
        seen.add(key)
        item_payload: dict[str, Any] = {
            "requested_by": context.user_id,
            "role": context.role,
            "student_id": key,
            "endpoint": endpoint,
            "purpose": context.purpose or "academic_segmentation_access",
            "model_version": model_version,
        }
        if context.tenant_id:
            item_payload["tenant_id"] = context.tenant_id
        payloads.append(item_payload)

    try:
        repository.insert_rows("llm_context_audit", payloads)
    except Exception:
        # La auditoria no debe bloquear la respuesta de datos academicos.
        return
