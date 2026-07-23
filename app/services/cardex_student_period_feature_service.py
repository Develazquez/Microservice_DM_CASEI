from __future__ import annotations

import hashlib
import re
import unicodedata

import numpy as np
import pandas as pd

from app.models.config import CARDEX_COLUMNS


PLAN_CREDITS = {
    "IDS": 270,
    "IBM": 282,
    "IEN": 264,
    "IAG": 276,
}

PERIOD_NAME_NUMBER = {
    "enero-abril": 1,
    "mayo-agosto": 2,
    "septiembre-diciembre": 3,
}


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def stable_unit(*parts: object) -> float:
    key = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def stable_noise(scale: float, *parts: object) -> float:
    return (stable_unit(*parts) - 0.5) * 2 * scale


def stable_int(low: int, high: int, *parts: object) -> int:
    if high <= low:
        return low
    return low + int(stable_unit(*parts) * (high - low + 1))


def parse_cohort(matricula: object) -> int:
    text = str(matricula).strip()
    match = re.search(r"(20\d{2})", text)
    if match:
        return int(match.group(1))
    legacy = re.fullmatch(r"(\d{2})\d{4}", text)
    if legacy:
        return 2000 + int(legacy.group(1))
    return 2022


def period_order(period: object) -> int:
    text = str(period)
    normalized = normalize_text(text).strip()
    named = re.search(
        r"(enero-abril|mayo-agosto|septiembre-diciembre)\s+(20\d{2})",
        normalized,
    )
    if named:
        return int(named.group(2)) * 3 + PERIOD_NAME_NUMBER[named.group(1)]
    match = re.search(r"(20\d{2})\s*-\s*([123])", text)
    if not match:
        return 0
    return int(match.group(1)) * 3 + int(match.group(2))


def plan_total_credits(plan_key: object, carrera: object) -> int:
    prefix = str(plan_key).split("-")[0].upper()
    if prefix in PLAN_CREDITS:
        return PLAN_CREDITS[prefix]
    normalized = normalize_text(carrera)
    if "software" in normalized:
        return PLAN_CREDITS["IDS"]
    if "biomed" in normalized:
        return PLAN_CREDITS["IBM"]
    if "energia" in normalized:
        return PLAN_CREDITS["IEN"]
    if "agro" in normalized:
        return PLAN_CREDITS["IAG"]
    return 270


def academic_status(raw_status: object, promedio_general: float, failed_accumulated: int, lag: int) -> str:
    normalized = normalize_text(raw_status)
    if "baja" in normalized:
        return "Baja Temporal"
    if "egres" in normalized:
        return "Egresado"
    if "irregular" in normalized or promedio_general < 70 or failed_accumulated >= 3 or lag >= 3:
        return "Irregular"
    return "Regular"


def prepare_cardex(raw: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(CARDEX_COLUMNS) - set(raw.columns))
    if missing:
        raise ValueError(f"Dataset cardex is missing required columns: {missing}")

    df = raw[CARDEX_COLUMNS].copy()
    df["Final"] = pd.to_numeric(df["Final"], errors="coerce")
    df["Extr"] = pd.to_numeric(df["Extr"], errors="coerce")
    df["Credito"] = pd.to_numeric(df["Credito"], errors="coerce").fillna(0).clip(lower=0)
    df["CuatrimestreActual"] = pd.to_numeric(df["CuatrimestreActual"], errors="coerce").fillna(1).clip(lower=1)
    df["PeriodoAnalitico"] = df["PeriodoCursado"].fillna(df["Periodo"])
    df["status_materia_norm"] = df["EstatusMateria"].map(normalize_text)
    df["cardex_norm"] = df["EstatusCardex"].map(normalize_text)
    df["score"] = df["Final"]
    use_extra = df["Extr"].notna() & (df["score"].isna() | (df["score"] < 70))
    df.loc[use_extra, "score"] = df.loc[use_extra, "Extr"]
    return df


def build_student_period_features(raw: pd.DataFrame) -> pd.DataFrame:
    df = prepare_cardex(raw)
    records: list[dict[str, object]] = []

    for matricula, student_rows in df.groupby("Matricula", sort=True):
        student_rows = student_rows.copy()
        student_rows["period_order"] = student_rows["PeriodoAnalitico"].map(period_order)
        student_rows = student_rows.sort_values(["period_order", "Materia"])

        cumulative_scores: list[float] = []
        cumulative_approved = 0
        cumulative_failed = 0
        cumulative_approved_credits = 0.0
        cumulative_retake = 0
        observed_periods = 0
        first_period_order = int(student_rows["period_order"].replace(0, np.nan).min()) if student_rows["period_order"].replace(0, np.nan).notna().any() else 0

        for period, period_rows in student_rows.groupby("PeriodoAnalitico", sort=False):
            period_rows = period_rows.copy()
            observed_periods += 1

            status_norm = period_rows["status_materia_norm"]
            approved_mask = status_norm.eq("aprobada")
            failed_mask = status_norm.eq("reprobada")
            in_course_mask = status_norm.eq("cursando")
            baja_mask = status_norm.eq("baja")
            period_scores = period_rows["score"].dropna().astype(float).tolist()

            approved_period = int(approved_mask.sum())
            failed_period = int(failed_mask.sum())
            in_course_period = int(in_course_mask.sum())
            approved_credits_period = float(period_rows.loc[approved_mask, "Credito"].sum())
            enrolled_credits_period = float(period_rows["Credito"].sum())
            retake_period = int(
                period_rows["cardex_norm"].str.contains("recursamiento|repeticion", na=False).sum()
            )

            cumulative_scores.extend(period_scores)
            cumulative_approved += approved_period
            cumulative_failed += failed_period
            cumulative_approved_credits += approved_credits_period
            cumulative_retake += retake_period

            carrera = period_rows["Carrera"].mode().iloc[0]
            plan_key = period_rows["PlanEstudiosClave"].mode().iloc[0]
            total_plan_credits = plan_total_credits(plan_key, carrera)
            current_order = period_order(period)
            cohort = parse_cohort(matricula)
            expected_periods = (
                max(observed_periods, current_order - period_order(f"{cohort}-1") + 1)
                if current_order
                else observed_periods
            )
            periods_without_enrollment = int(max(0, min(8, expected_periods - observed_periods)))

            promedio_periodo = float(np.mean(period_scores)) if period_scores else np.nan
            promedio_general = float(np.mean(cumulative_scores)) if cumulative_scores else 70.0
            lag = int(max(0, cumulative_failed - cumulative_retake + periods_without_enrollment // 2))
            status = academic_status(
                period_rows["EstatusAlumno"].mode().iloc[0],
                promedio_general,
                cumulative_failed,
                lag,
            )

            attendance_signal = promedio_periodo if not np.isnan(promedio_periodo) else promedio_general
            attendance = (
                82
                + (attendance_signal - 75) * 0.35
                - failed_period * 6.5
                - lag * 2.0
                - periods_without_enrollment * 1.2
                + stable_noise(5.0, matricula, period, "attendance")
            )
            if status == "Baja Temporal":
                attendance -= 30
            elif status == "Egresado":
                attendance += 5
            attendance = float(np.clip(attendance, 12, 99))

            faltas = int(np.clip(round((100 - attendance) / 100 * 32 + stable_noise(2.0, matricula, period, "faltas")), 0, 32))
            retardos = int(np.clip(round((100 - attendance) / 18 + stable_noise(1.5, matricula, period, "retardos")), 0, 12))
            low_grade_pressure = max(0.0, 70.0 - attendance_signal) / 10.0
            tutorias_abiertas = int(np.clip(round(failed_period * 0.9 + lag * 0.25 + low_grade_pressure * 0.4), 0, 8))
            tutorias_cerradas = int(np.clip(stable_int(0, 2, matricula, period, "cerradas") + max(0, approved_period - failed_period) // 3, 0, 8))
            num_asesorias = int(np.clip(round(failed_period * 1.1 + low_grade_pressure + stable_int(0, 2, matricula, period, "asesorias")), 0, 10))
            num_incidencias = int(np.clip(round((attendance < 60) + failed_period * 0.5 + (status == "Baja Temporal") * 2), 0, 8))
            permisos_aprobados = int(np.clip(round(max(0, faltas - 5) / 7 + stable_int(0, 2, matricula, period, "permisos-ok")), 0, 10))
            permisos_rechazados = int(np.clip(round(max(0, faltas - 10) / 8 + stable_int(0, 1, matricula, period, "permisos-no")), 0, 8))
            compromisos_pendientes = int(np.clip(round(tutorias_abiertas * 0.8 + num_incidencias * 0.5), 0, 10))
            compromisos_cumplidos = int(np.clip(round(tutorias_cerradas * 0.9 + max(0, approved_period - failed_period) / 3), 0, 10))
            period_variance = float(np.var(period_scores)) if len(period_scores) > 1 else abs(stable_noise(8.0, matricula, period, "variance")) + 2
            previous_average = float(np.mean(cumulative_scores[:-len(period_scores)])) if period_scores and len(cumulative_scores) > len(period_scores) else promedio_general
            tendencia = promedio_periodo - previous_average if not np.isnan(promedio_periodo) else np.nan
            incomplete_flag = int(period_rows["score"].isna().any() or bool(baja_mask.any()))

            records.append(
                {
                    "id_estudiante": str(matricula),
                    "id_periodo": str(period),
                    "programa": str(carrera),
                    "cohorte": cohort,
                    "promedio_general": round(promedio_general, 2),
                    "promedio_periodo": round(promedio_periodo, 2) if not np.isnan(promedio_periodo) else np.nan,
                    "materias_aprobadas": cumulative_approved,
                    "materias_reprobadas": cumulative_failed,
                    "materias_en_curso": in_course_period,
                    "creditos_acumulados": round(cumulative_approved_credits, 2),
                    "porcentaje_avance": round(cumulative_approved_credits / total_plan_credits * 100, 2),
                    "porcentaje_asistencia": round(attendance, 2),
                    "faltas": faltas,
                    "retardos": retardos,
                    "num_tutorias": tutorias_abiertas + tutorias_cerradas,
                    "num_asesorias": num_asesorias,
                    "num_incidencias": num_incidencias,
                    "num_permisos": permisos_aprobados + permisos_rechazados,
                    "recursamientos": cumulative_retake,
                    "rezago_materias": lag,
                    "estatus_academico": status,
                    "creditos_inscritos_periodo": round(enrolled_credits_period, 2),
                    "creditos_aprobados_periodo": round(approved_credits_period, 2),
                    "creditos_totales_plan": total_plan_credits,
                    "periodos_cursados": observed_periods,
                    "periodos_sin_inscripcion": periods_without_enrollment,
                    "materias_reprobadas_periodo": failed_period,
                    "materias_reprobadas_acumuladas": cumulative_failed,
                    "materias_en_curso_periodo": in_course_period,
                    "tendencia_promedio": round(float(tendencia), 2) if not np.isnan(tendencia) else np.nan,
                    "varianza_calificaciones": round(period_variance, 2),
                    "tutorias_abiertas": tutorias_abiertas,
                    "tutorias_cerradas": tutorias_cerradas,
                    "compromisos_pendientes": compromisos_pendientes,
                    "compromisos_cumplidos": compromisos_cumplidos,
                    "permisos_aprobados": permisos_aprobados,
                    "permisos_rechazados": permisos_rechazados,
                    "bandera_dato_incompleto": incomplete_flag,
                }
            )

    result = pd.DataFrame(records)
    return result.sort_values(["id_estudiante", "id_periodo"]).reset_index(drop=True)
