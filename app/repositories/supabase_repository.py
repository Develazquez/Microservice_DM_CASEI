from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

import pandas as pd

from app.models.config import CASEI_SUPABASE_SERVICE_ROLE_KEY, CASEI_SUPABASE_URL, STUDENT_PERIOD_DATASET
from app.services.model_persistence_service import load_persisted_model_bundle


class SupabaseRepository:
    """Small PostgREST client for CASEI Supabase tables.

    The repository intentionally uses the Python standard library so the
    microservice can keep running without adding a Supabase SDK dependency.
    """

    def __init__(self, url: str | None = None, service_role_key: str | None = None) -> None:
        self.url = (url or CASEI_SUPABASE_URL or "").rstrip("/")
        self.service_role_key = service_role_key or CASEI_SUPABASE_SERVICE_ROLE_KEY or ""

    @property
    def configured(self) -> bool:
        return bool(self.url and self.service_role_key)

    def configuration_status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "url_present": bool(self.url),
            "service_role_key_present": bool(self.service_role_key),
            "rest_url": f"{self.url}/rest/v1" if self.url else None,
        }

    def require_configured(self) -> None:
        if not self.configured:
            raise ValueError(
                "Supabase no esta configurado. Define CASEI_SUPABASE_URL y "
                "CASEI_SUPABASE_SERVICE_ROLE_KEY, o las variables equivalentes de CASEI web."
            )

    def student_period_features(self) -> pd.DataFrame:
        rows = self.fetch_table("student_period_features", limit=10000)
        if rows:
            return pd.DataFrame(rows)
        if not STUDENT_PERIOD_DATASET.exists():
            raise FileNotFoundError(f"Student-period dataset not found: {STUDENT_PERIOD_DATASET}")
        return pd.read_csv(STUDENT_PERIOD_DATASET)

    def current_model_bundle(self) -> dict[str, Any]:
        return load_persisted_model_bundle()

    def fetch_table(
        self,
        table: str,
        select: str = "*",
        filters: dict[str, str] | None = None,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        self.require_configured()
        params: dict[str, Any] = {"select": select}
        if limit is not None:
            params["limit"] = str(limit)
        if order:
            params["order"] = order
        if filters:
            params.update(filters)
        return self._request("GET", table, params=params)


    def insert_rows(
        self,
        table: str,
        rows: list[dict[str, Any]],
        upsert: bool = False,
        on_conflict: str | None = None,
    ) -> int:
        if not rows:
            return 0
        params = {"on_conflict": on_conflict} if upsert and on_conflict else None
        prefer = "resolution=merge-duplicates,return=minimal" if upsert else "return=minimal"
        self._request("POST", table, params=params, payload=rows, prefer=prefer)
        return len(rows)

    def patch_rows(
        self,
        table: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> None:
        self._request("PATCH", table, params=filters, payload=payload, prefer="return=minimal")

    def fetch_student_identity_lookup(self, limit: int = 10000) -> dict[str, dict[str, Any]]:
        rows = self.fetch_table(
            "profiles",
            select="id,matricula,carrera,program_id,sexo,rol",
            filters={"rol": "eq.alumno"},
            limit=limit,
        )
        return {str(row.get("matricula")): row for row in rows if row.get("matricula")}

    def fetch_program_lookup(self, limit: int = 1000) -> dict[str, dict[str, Any]]:
        rows = self.fetch_academic_programs(limit=limit)
        return {str(row.get("nombre")): row for row in rows if row.get("nombre")}

    def fetch_academic_programs(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self.fetch_table("academic_programs", select="id,clave,nombre,activo", limit=limit, order="nombre.asc")

    def fetch_profile_role_counts(self, limit: int = 10000) -> list[dict[str, Any]]:
        rows = self.fetch_table("profiles", select="rol,matricula", limit=limit)
        counts: dict[str, dict[str, int | str]] = {}
        for row in rows:
            role = str(row.get("rol") or "sin_rol")
            current = counts.setdefault(role, {"rol": role, "profiles": 0, "with_matricula": 0})
            current["profiles"] = int(current["profiles"]) + 1
            if row.get("matricula"):
                current["with_matricula"] = int(current["with_matricula"]) + 1
        return list(counts.values())

    def fetch_tutor_scope(self, tutor_id: str | None = None, limit: int = 10000) -> list[dict[str, Any]]:
        filters = {"tutor_id": f"eq.{tutor_id}"} if tutor_id else None
        return self.fetch_table(
            "tutor_student_scope",
            select="tutor_id,student_id,program_id,program_name,group_id,period_id,scope_source,active",
            filters=filters,
            limit=limit,
        )

    def fetch_academic_source_data(self, limit: int = 1000) -> dict[str, list[dict[str, Any]]]:
        limit = max(1, min(int(limit), 10000))
        return {
            "profile_role_counts": self.fetch_profile_role_counts(limit=10000),
            "academic_programs": self.fetch_academic_programs(limit=1000),
            "profiles": self.fetch_table(
                "profiles",
                select="id,matricula,nombre,apellidos,carrera,program_id,sexo,rol,estatus_academico,cuatrimestre_actual",
                filters={"rol": "eq.alumno"},
                limit=limit,
            ),
            "historial_academico": self.fetch_table(
                "historial_academico",
                select="id,student_id,subject_id,period_id,grade,calificacion_extra,status,attempt_type",
                limit=limit * 5,
            ),
            "carga_academica": self.fetch_table(
                "carga_academica",
                select="id,alumno_id,materia_id,grupo_id,periodo_id,docente_id,calificacion_final,calificacion_extraordinario,estatus",
                limit=limit * 5,
            ),
            "materias": self.fetch_table(
                "materias",
                select="id,nombre,clave,creditos,cuatrimestre_plan",
                limit=limit * 2,
            ),
            "periodos": self.fetch_table(
                "periodos",
                select="id,nombre,clave,fecha_inicio,fecha_fin,activo",
                limit=500,
            ),
            "grupos": self.fetch_table(
                "grupos",
                select="id,nombre,clave,periodo_id,tutor_id,program_id,activo",
                limit=limit,
            ),
            "tutor_program_assignments": self.fetch_table(
                "tutor_program_assignments",
                select="id,tutor_id,program_id,is_primary,active",
                limit=limit,
            ),
            "tutor_student_scope": self.fetch_tutor_scope(limit=limit * 5),
        }

    def _request(
        self,
        method: str,
        table: str,
        params: dict[str, Any] | None = None,
        payload: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{self.url}/rest/v1/{table}{query}",
            method=method,
            headers={
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                **({"Prefer": prefer} if prefer else {}),
            },
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"Supabase REST error on {table}: HTTP {exc.code} {detail}") from exc
        except URLError as exc:
            raise ValueError(f"Supabase REST connection error on {table}: {exc.reason}") from exc


