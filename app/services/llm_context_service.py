from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import numpy as np
import pandas as pd

from app.services.security_audit_service import SecurityContext, apply_student_scope
from app.services.segmentation_api_service import (
    current_manifest,
    dataframe_records,
    jsonable,
    student_detail,
    student_history,
    student_view,
)


CONTEXT_VERSION = "casei-llm-rag-context-v1"

DATA_WARNINGS = [
    "Los clusters son apoyo tutorial y analitico; no son diagnostico automatico definitivo.",
    "El dataset crudo actual no contiene asistencia, tutorias, asesorias, incidencias ni permisos reales.",
    "Las senales operativas de asistencia y acompanamiento se estiman para prototipo local y deben sustituirse por datos institucionales reales cuando existan.",
]

SAFETY_RULES = [
    "Usar el contexto para orientar acompanamiento tutorial y analisis academico.",
    "No usar el perfil para sanciones, exclusion, etiquetado permanente o decisiones automaticas.",
    "Contrastar cualquier recomendacion con tutor, coordinacion y evidencia institucional adicional.",
    "Evitar exponer identificadores de alumno fuera de roles autorizados.",
]

ROLE_POLICIES: dict[str, dict[str, Any]] = {
    "director": {
        "role": "director",
        "scope": "institucional",
        "identifier_visibility": "full",
        "max_history": 12,
        "can_view_student_detail": True,
        "can_view_rag_documents": True,
        "required_upstream_control": "Autenticacion CASEI y autorizacion institucional.",
    },
    "coordinador": {
        "role": "coordinador",
        "scope": "programa_academico",
        "identifier_visibility": "full",
        "max_history": 10,
        "can_view_student_detail": True,
        "can_view_rag_documents": True,
        "required_upstream_control": "Autenticacion CASEI y filtro por programa/area autorizada.",
    },
    "tutor": {
        "role": "tutor",
        "scope": "tutorados_asignados",
        "identifier_visibility": "full",
        "max_history": 8,
        "can_view_student_detail": True,
        "can_view_rag_documents": True,
        "required_upstream_control": "Autenticacion CASEI y validacion de tutorado asignado antes de llamar al microservicio.",
    },
    "analista": {
        "role": "analista",
        "scope": "analitica_pseudonimizada",
        "identifier_visibility": "pseudonymized",
        "max_history": 4,
        "can_view_student_detail": True,
        "can_view_rag_documents": True,
        "required_upstream_control": "Autenticacion CASEI y uso de datos pseudonimizados para analisis.",
    },
}

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_role(role: str) -> str:
    role = role.strip().lower()
    if role not in ROLE_POLICIES:
        valid = ", ".join(sorted(ROLE_POLICIES))
        raise ValueError(f"Rol no soportado para contexto LLM/RAG: {role}. Roles validos: {valid}.")
    return role


def role_policy(role: str) -> dict[str, Any]:
    return dict(ROLE_POLICIES[normalized_role(role)])


def student_reference(student_id: str, policy: dict[str, Any]) -> str:
    if policy["identifier_visibility"] == "pseudonymized":
        digest = sha256(student_id.upper().encode("utf-8")).hexdigest()[:12]
        return f"student-{digest}"
    return student_id


def safe_number(value: Any, digits: int = 4) -> float | int | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(number) or np.isinf(number):
        return None
    if number.is_integer():
        return int(number)
    return round(number, digits)


def safe_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    text = str(value).strip()
    return text or None


def compact_record(record: dict[str, Any], model_version: str, student_ref: str) -> dict[str, Any]:
    return {
        "student_reference": student_ref,
        "id_periodo": safe_text(record.get("id_periodo")),
        "programa": safe_text(record.get("programa")),
        "estatus_academico": safe_text(record.get("estatus_academico")),
        "cluster": safe_number(record.get("cluster")),
        "perfil_academico": safe_text(record.get("perfil_academico")),
        "prioridad_tutorial": safe_text(record.get("prioridad_tutorial")),
        "membership_score": safe_number(record.get("membership_score")),
        "promedio_general": safe_number(record.get("promedio_general")),
        "promedio_periodo": safe_number(record.get("promedio_periodo")),
        "porcentaje_asistencia": safe_number(record.get("porcentaje_asistencia")),
        "materias_reprobadas_periodo": safe_number(record.get("materias_reprobadas_periodo")),
        "materias_reprobadas_acumuladas": safe_number(record.get("materias_reprobadas_acumuladas")),
        "rezago_materias": safe_number(record.get("rezago_materias")),
        "tendencia_promedio": safe_number(record.get("tendencia_promedio")),
        "model_version": model_version,
    }


def persisted_history_item(item: dict[str, Any], student_ref: str) -> dict[str, Any]:
    return {
        "student_reference": student_ref,
        "execution_id": safe_text(item.get("execution_id")),
        "id_periodo": safe_text(item.get("id_periodo")),
        "run_type": safe_text(item.get("run_type")),
        "status": safe_text(item.get("status")),
        "model_version": safe_text(item.get("model_version")),
        "selected_representation": safe_text(item.get("selected_representation")),
        "selected_k": safe_number(item.get("selected_k")),
        "started_at_utc": safe_text(item.get("started_at_utc")),
        "cluster": safe_number(item.get("cluster")),
        "perfil_academico": safe_text(item.get("perfil_academico")),
        "prioridad_tutorial": safe_text(item.get("prioridad_tutorial")),
        "membership_score": safe_number(item.get("membership_score")),
    }


def academic_summary(latest: dict[str, Any], manifest: dict[str, Any], student_ref: str) -> dict[str, Any]:
    model = manifest["model"]
    return {
        "student_reference": student_ref,
        "latest_period": safe_text(latest.get("id_periodo")),
        "program": safe_text(latest.get("programa")),
        "cohort": safe_text(latest.get("cohorte")),
        "academic_status": safe_text(latest.get("estatus_academico")),
        "profile": {
            "cluster": safe_number(latest.get("cluster")),
            "perfil_academico": safe_text(latest.get("perfil_academico")),
            "prioridad_tutorial": safe_text(latest.get("prioridad_tutorial")),
            "membership_score": safe_number(latest.get("membership_score")),
            "distance_to_centroid": safe_number(latest.get("distance_to_centroid")),
            "selected_k": safe_number(model.get("selected_k")),
            "selected_representation": safe_text(model.get("selected_representation")),
            "model_version": safe_text(manifest.get("model_version")),
        },
        "performance": {
            "promedio_general": safe_number(latest.get("promedio_general")),
            "promedio_periodo": safe_number(latest.get("promedio_periodo")),
            "porcentaje_avance": safe_number(latest.get("porcentaje_avance")),
            "porcentaje_asistencia": safe_number(latest.get("porcentaje_asistencia")),
            "tendencia_promedio": safe_number(latest.get("tendencia_promedio")),
            "varianza_calificaciones": safe_number(latest.get("varianza_calificaciones")),
        },
        "academic_progress": {
            "creditos_aprobados_periodo": safe_number(latest.get("creditos_aprobados_periodo")),
            "creditos_inscritos_periodo": safe_number(latest.get("creditos_inscritos_periodo")),
            "creditos_totales_plan": safe_number(latest.get("creditos_totales_plan")),
            "periodos_cursados": safe_number(latest.get("periodos_cursados")),
            "periodos_sin_inscripcion": safe_number(latest.get("periodos_sin_inscripcion")),
        },
        "risk_and_support_signals": {
            "materias_reprobadas_periodo": safe_number(latest.get("materias_reprobadas_periodo")),
            "materias_reprobadas_acumuladas": safe_number(latest.get("materias_reprobadas_acumuladas")),
            "rezago_materias": safe_number(latest.get("rezago_materias")),
            "recursamientos": safe_number(latest.get("recursamientos")),
            "tutorias_abiertas": safe_number(latest.get("tutorias_abiertas")),
            "tutorias_cerradas": safe_number(latest.get("tutorias_cerradas")),
            "compromisos_pendientes": safe_number(latest.get("compromisos_pendientes")),
            "compromisos_cumplidos": safe_number(latest.get("compromisos_cumplidos")),
            "num_incidencias": safe_number(latest.get("num_incidencias")),
            "permisos_aprobados": safe_number(latest.get("permisos_aprobados")),
            "permisos_rechazados": safe_number(latest.get("permisos_rechazados")),
        },
        "interpretation": {
            "lectura_funcional": safe_text(latest.get("lectura_funcional")),
            "acciones_sugeridas": safe_text(latest.get("acciones_sugeridas")),
            "cautela_interpretacion": safe_text(latest.get("cautela_interpretacion")),
        },
    }


def retrieval_text(summary: dict[str, Any], history: list[dict[str, Any]]) -> str:
    profile = summary["profile"]
    performance = summary["performance"]
    progress = summary["academic_progress"]
    signals = summary["risk_and_support_signals"]
    interpretation = summary["interpretation"]
    history_periods = ", ".join(
        item["id_periodo"] for item in history if item.get("id_periodo")
    )

    parts = [
        f"Alumno {summary['student_reference']} del programa {summary.get('program') or 'no especificado'}; periodo actual {summary.get('latest_period') or 'no especificado'}.",
        f"Perfil actual: {profile.get('perfil_academico') or 'sin perfil'}; prioridad tutorial {profile.get('prioridad_tutorial') or 'sin prioridad'}; cluster {profile.get('cluster')}.",
        f"Desempeno: promedio general {performance.get('promedio_general')}, promedio de periodo {performance.get('promedio_periodo')}, asistencia estimada {performance.get('porcentaje_asistencia')} y avance {performance.get('porcentaje_avance')}.",
        f"Rezago y apoyo: reprobadas periodo {signals.get('materias_reprobadas_periodo')}, reprobadas acumuladas {signals.get('materias_reprobadas_acumuladas')}, rezago {signals.get('rezago_materias')}, tutorias abiertas {signals.get('tutorias_abiertas')} y compromisos pendientes {signals.get('compromisos_pendientes')}.",
        f"Progreso curricular: creditos aprobados periodo {progress.get('creditos_aprobados_periodo')}, creditos inscritos {progress.get('creditos_inscritos_periodo')} y periodos sin inscripcion {progress.get('periodos_sin_inscripcion')}.",
    ]
    if history_periods:
        parts.append(f"Historial compacto incluido para los periodos: {history_periods}.")
    if interpretation.get("lectura_funcional"):
        parts.append(f"Lectura funcional del perfil: {interpretation['lectura_funcional']}")
    if interpretation.get("acciones_sugeridas"):
        parts.append(f"Acciones sugeridas: {interpretation['acciones_sugeridas']}")
    parts.append("Restriccion: esta informacion orienta acompanamiento academico y no debe tratarse como diagnostico automatico definitivo.")
    return " ".join(parts)


def rag_document(
    summary: dict[str, Any],
    history: list[dict[str, Any]],
    policy: dict[str, Any],
    generated_at_utc: str,
) -> dict[str, Any]:
    profile = summary["profile"]
    metadata = {
        "student_reference": summary["student_reference"],
        "program": summary.get("program"),
        "latest_period": summary.get("latest_period"),
        "academic_status": summary.get("academic_status"),
        "cluster": profile.get("cluster"),
        "perfil_academico": profile.get("perfil_academico"),
        "prioridad_tutorial": profile.get("prioridad_tutorial"),
        "model_version": profile.get("model_version"),
        "selected_representation": profile.get("selected_representation"),
        "selected_k": profile.get("selected_k"),
        "role_scope": policy["scope"],
        "identifier_visibility": policy["identifier_visibility"],
    }
    document_id = (
        f"casei:{CONTEXT_VERSION}:{metadata['model_version']}:"
        f"{summary['student_reference']}:{summary.get('latest_period')}"
    )
    return {
        "document_id": document_id,
        "document_type": "student_academic_context",
        "generated_at_utc": generated_at_utc,
        "retrieval_title": f"Contexto academico {summary['student_reference']} - {metadata.get('perfil_academico')}",
        "retrieval_text": retrieval_text(summary, history),
        "metadata": metadata,
        "embedding_fields": [
            "retrieval_title",
            "retrieval_text",
            "metadata.program",
            "metadata.perfil_academico",
            "metadata.prioridad_tutorial",
        ],
        "source_fields": {
            "academic_summary": summary,
            "compact_profile_history": history,
        },
        "allowed_use": [
            "acompanamiento tutorial",
            "priorizacion academica",
            "consulta RAG para tutor inteligente",
        ],
        "forbidden_use": [
            "diagnostico automatico definitivo",
            "sancion o exclusion automatizada",
            "exposicion de identificadores a roles no autorizados",
        ],
    }


def context_contract() -> dict[str, Any]:
    return {
        "context_version": CONTEXT_VERSION,
        "generated_at_utc": utc_now(),
        "purpose": "Preparar salida controlada para futuro tutor inteligente con LLM y RAG.",
        "source": {
            "service": "academic-segmentation",
            "active_dataset": "data/raw/dataset_crudo_2000_estudiantes.csv",
            "student_period_view": "data/processed/student_period_features.csv",
            "model_pointer": "artifacts/current_model.json",
        },
        "roles": list(ROLE_POLICIES.values()),
        "field_groups": {
            "academic_summary": [
                "perfil academico",
                "prioridad tutorial",
                "desempeno",
                "avance curricular",
                "senales de rezago y acompanamiento",
                "interpretacion cautelosa",
            ],
            "compact_profile_history": [
                "periodo",
                "cluster",
                "perfil",
                "prioridad",
                "metricas academicas clave",
                "version de modelo",
            ],
            "rag_context": [
                "document_id",
                "retrieval_title",
                "retrieval_text",
                "metadata",
                "allowed_use",
                "forbidden_use",
            ],
        },
        "required_upstream_controls": [
            "Autenticar usuario en CASEI antes de llamar al microservicio.",
            "Validar rol y alcance institucional en la web/API gateway.",
            "Para tutores, confirmar que el alumno pertenece a sus tutorados asignados.",
            "Evitar almacenar respuestas generadas por LLM sin trazabilidad de modelo, fecha y fuente.",
        ],
        "safety_rules": SAFETY_RULES,
        "data_warnings": DATA_WARNINGS,
        "endpoints": [
            "GET /api/v1/segmentation/context/contract",
            "GET /api/v1/segmentation/students/{student_id}/llm-context",
            "GET /api/v1/segmentation/rag/documents",
        ],
    }


def student_llm_context(
    student_id: str,
    role: str = "tutor",
    max_history: int = 6,
    security_context: SecurityContext | None = None,
) -> dict[str, Any] | None:
    policy = role_policy(role)
    max_history = max(1, min(int(max_history), int(policy["max_history"])))
    detail = student_detail(student_id, security_context=security_context)
    if detail is None:
        return None

    manifest = current_manifest()
    model_version = manifest["model_version"]
    generated_at = utc_now()
    student_ref = student_reference(student_id, policy)
    records = sorted(detail["records"], key=lambda item: str(item.get("id_periodo") or ""))
    latest = records[-1]
    compact = [compact_record(record, model_version, student_ref) for record in records[-max_history:]]
    persisted = student_history(student_id, limit=max_history)
    persisted_compact = [
        persisted_history_item(item, student_ref)
        for item in persisted.get("items", [])[:max_history]
    ]
    summary = academic_summary(latest, manifest, student_ref)

    return jsonable(
        {
            "context_version": CONTEXT_VERSION,
            "generated_at_utc": generated_at,
            "model_version": model_version,
            "role": policy["role"],
            "student_reference": student_ref,
            "access_control": {
                "role_scope": policy["scope"],
                "identifier_visibility": policy["identifier_visibility"],
                "max_history": max_history,
                "enforced_in_microservice": [
                    "validacion de rol soportado",
                    "limite de historial",
                    "pseudonimizacion para rol analista",
                ],
                "required_upstream_control": policy["required_upstream_control"],
            },
            "academic_summary": summary,
            "compact_profile_history": compact,
            "persisted_profile_history": persisted_compact,
            "rag_context": rag_document(summary, compact, policy, generated_at),
            "safety": {
                "rules": SAFETY_RULES,
                "interpretation_limit": "Perfil academico de apoyo tutorial/analitico, no diagnostico automatico definitivo.",
            },
            "data_warnings": DATA_WARNINGS,
        }
    )


def latest_student_rows() -> pd.DataFrame:
    students = student_view()
    if students.empty:
        return students
    return (
        students.sort_values(["id_estudiante", "id_periodo"])
        .groupby("id_estudiante", as_index=False, dropna=False)
        .tail(1)
        .sort_values(["id_estudiante", "id_periodo"])
    )


def rag_documents(
    role: str = "analista",
    perfil: str | None = None,
    programa: str | None = None,
    cluster: int | None = None,
    student_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    security_context: SecurityContext | None = None,
) -> dict[str, Any]:
    policy = role_policy(role)
    if policy["role"] == "tutor" and not student_id:
        raise ValueError("El rol tutor debe solicitar documentos RAG filtrados por student_id.")
    if policy["role"] == "coordinador" and not (programa or student_id):
        raise ValueError("El rol coordinador debe filtrar documentos RAG por programa o student_id.")

    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    rows = apply_student_scope(latest_student_rows(), security_context)

    if perfil:
        rows = rows[rows["perfil_academico"].fillna("").str.contains(perfil, case=False, na=False)]
    if programa:
        rows = rows[rows["programa"].fillna("").str.contains(programa, case=False, na=False)]
    if cluster is not None:
        rows = rows[rows["cluster"] == cluster]
    if student_id:
        rows = rows[rows["id_estudiante"].fillna("").str.upper() == student_id.upper()]

    total = int(len(rows))
    page = rows.iloc[offset : offset + limit]
    items: list[dict[str, Any]] = []
    for row in dataframe_records(page):
        context = student_llm_context(row["id_estudiante"], role=role, max_history=3, security_context=security_context)
        if context:
            items.append(context["rag_context"])

    return {
        "context_version": CONTEXT_VERSION,
        "generated_at_utc": utc_now(),
        "role": policy["role"],
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
        "data_warnings": DATA_WARNINGS,
    }
