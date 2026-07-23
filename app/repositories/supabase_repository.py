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

    def active_model_metadata(self) -> dict[str, Any]:
        rows = self.fetch_table(
            "ml_model_versions",
            select="model_version,algorithm,selected_representation,selected_k,metrics,artifact_manifest,is_active,created_at",
            filters={"is_active": "eq.true"},
            limit=1,
        )
        if not rows:
            raise FileNotFoundError("Supabase no contiene una version activa del modelo.")
        return rows[0]

    def current_student_segmentation(self, limit: int = 10000) -> pd.DataFrame:
        """Build the current student-period view from persisted inference results.

        Partial inference runs append rows instead of replacing the historical
        tables. The newest assignment for every student-period is therefore the
        active snapshot exposed to the API.
        """
        active_model = self.active_model_metadata()
        model_version = str(active_model["model_version"])
        assignments = self.fetch_table(
            "cluster_assignments",
            select="*",
            filters={"model_version": f"eq.{model_version}"},
            limit=limit,
            order="created_at.desc",
        )
        if not assignments:
            raise FileNotFoundError(
                f"Supabase no contiene asignaciones para el modelo activo {model_version}."
            )

        assignment_df = pd.DataFrame(assignments)
        keys = ["id_estudiante", "id_periodo"]
        assignment_df = assignment_df.drop_duplicates(subset=keys, keep="first")
        execution_ids = set(assignment_df["execution_id"].dropna().astype(str))

        feature_rows = self.fetch_table(
            "student_period_features",
            select="*",
            limit=limit,
            order="created_at.desc",
        )
        feature_df = pd.DataFrame(feature_rows)
        if not feature_df.empty:
            feature_df = feature_df[
                feature_df["execution_id"].fillna("").astype(str).isin(execution_ids)
            ].copy()
            feature_df = feature_df.drop_duplicates(
                subset=["execution_id", *keys],
                keep="first",
            )
            feature_df = self._expand_feature_payload(feature_df)

        view = assignment_df
        if not feature_df.empty:
            feature_columns = [
                column
                for column in feature_df.columns
                if column not in {"id", "created_at", "features"}
            ]
            view = assignment_df.merge(
                feature_df[feature_columns],
                on=["execution_id", *keys],
                how="left",
                suffixes=("", "_feature"),
            )
            view = self._coalesce_feature_columns(view)

        profile_rows = self.fetch_table(
            "profiles",
            select="id,matricula,nombre,apellidos",
            filters={"rol": "eq.alumno"},
            limit=limit,
        )
        if profile_rows:
            profiles = pd.DataFrame(profile_rows).rename(
                columns={"id": "student_profile_id_lookup"}
            )
            profiles["nombre_completo"] = (
                profiles[["nombre", "apellidos"]]
                .fillna("")
                .astype(str)
                .agg(" ".join, axis=1)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )

            # Primary merge: student_profile_id → profiles.id
            view = view.merge(
                profiles[
                    [
                        "student_profile_id_lookup",
                        "nombre_completo",
                    ]
                ],
                left_on="student_profile_id",
                right_on="student_profile_id_lookup",
                how="left",
            )
            view["nombre"] = view["nombre_completo"]
            view = view.drop(
                columns=["student_profile_id_lookup", "nombre_completo"],
                errors="ignore",
            )

            # Fallback merge: id_estudiante → profiles.matricula (case-insensitive)
            # Resolves names when student_profile_id was not set during sync.
            missing_mask = view["nombre"].fillna("").str.strip() == ""
            if missing_mask.any():
                profiles_by_mat = profiles.copy()
                profiles_by_mat["matricula_upper"] = (
                    profiles_by_mat["matricula"].fillna("").astype(str).str.upper()
                )
                profiles_by_mat = profiles_by_mat.drop_duplicates(
                    subset=["matricula_upper"], keep="first"
                )
                view["_id_est_upper"] = (
                    view["id_estudiante"].fillna("").astype(str).str.upper()
                )
                fallback = view.loc[missing_mask, ["_id_est_upper"]].merge(
                    profiles_by_mat[["matricula_upper", "nombre_completo"]],
                    left_on="_id_est_upper",
                    right_on="matricula_upper",
                    how="left",
                )
                view.loc[missing_mask, "nombre"] = fallback["nombre_completo"].values
                view = view.drop(columns=["_id_est_upper"], errors="ignore")

        return view.reset_index(drop=True)

    @staticmethod
    def _expand_feature_payload(features: pd.DataFrame) -> pd.DataFrame:
        if "features" not in features.columns:
            return features
        payload = pd.json_normalize(
            features["features"].apply(lambda value: value if isinstance(value, dict) else {})
        )
        payload.index = features.index
        expanded = features.copy()
        for column in payload.columns:
            if column not in expanded.columns:
                expanded[column] = payload[column]
            else:
                expanded[column] = expanded[column].combine_first(payload[column])
        return expanded

    @staticmethod
    def _coalesce_feature_columns(view: pd.DataFrame) -> pd.DataFrame:
        feature_suffix = "_feature"
        for column in list(view.columns):
            if not column.endswith(feature_suffix):
                continue
            target = column[: -len(feature_suffix)]
            if target in view.columns:
                view[target] = view[target].combine_first(view[column])
            else:
                view[target] = view[column]
            view = view.drop(columns=[column])
        return view

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

    def rpc(self, function_name: str, parameters: dict[str, Any] | None = None) -> Any:
        return self._request("POST", f"rpc/{function_name}", payload=parameters or {})

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

    def delete_rows(self, table: str, filters: dict[str, str]) -> None:
        """Delete rows matching the given PostgREST filters."""
        if not filters:
            raise ValueError("delete_rows requires at least one filter to prevent accidental full-table deletes.")
        self._request("DELETE", table, params=filters, prefer="return=minimal")

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


