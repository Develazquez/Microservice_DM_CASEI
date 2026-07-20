from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "dataset_crudo_2000_estudiantes.csv"

PERIOD_LABELS = {
    "2022-1": "Septiembre-Diciembre 2022",
    "2022-2": "Enero-Abril 2023",
    "2023-1": "Mayo-Agosto 2023",
    "2023-2": "Septiembre-Diciembre 2023",
    "2024-1": "Septiembre-Diciembre 2023",
    "2024-2": "Septiembre-Diciembre 2023",
    "2025-1": "Septiembre-Diciembre 2023",
}

PERIOD_NUMBERS = {
    "Septiembre-Diciembre 2022": "3",
    "Enero-Abril 2023": "1",
    "Mayo-Agosto 2023": "2",
    "Septiembre-Diciembre 2023": "3",
}

CARDEX_STATUS = {
    "Ordinario": "ordinario",
    "En curso": "ordinario",
    "Extraordinario": "repeticion",
    "Ordinario no acreditado": "repeticion",
    "Sin derecho": "repeticion",
    "Recursamiento": "repeticion",
    "Extraordinario no acreditado": "repeticion",
    "Baja administrativa": "repeticion",
}

STUDENT_STATUS = {
    "Activo": "Activo",
    "Irregular": "Inscrito",
    "Baja Temporal": "Baja Temporal",
    "Egresado": "Egresado",
}

ALLOWED_STUDENT_STATUS = {
    "Baja Academica",
    "Inscrito",
    "Abandono Escolar",
    "Baja Definitiva",
    "Egresado",
    "Baja Temporal",
    "Desconocido",
    "Sin Carga",
    "Titulo Profesional Ausente",
    "Movilidad Academica",
    "Proceso de Titulacion",
    "Activo",
    "Inactivo",
}


def normalize_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    source_period = data["PeriodoCursado"].where(data["PeriodoCursado"].ne(""), data["Periodo"])
    data["PeriodoCursado"] = source_period.map(PERIOD_LABELS).fillna(source_period)
    data["Periodo"] = data["PeriodoCursado"].map(PERIOD_NUMBERS)
    data["EstatusCardex"] = data["EstatusCardex"].map(CARDEX_STATUS).fillna("ordinario")

    cohort = data["Matricula"].str.extract(r"(20\d{2})", expand=False)
    data["PlanEstudiosClave"] = cohort.fillna("2022").astype(int).le(2021).map({True: "004", False: "NME"})
    data["EstatusAlumno"] = data["EstatusAlumno"].map(STUDENT_STATUS).fillna("Desconocido")

    expected = {
        "Periodo": {"1", "2", "3"},
        "EstatusCardex": {"ordinario", "repeticion"},
        "PeriodoCursado": set(PERIOD_NUMBERS),
        "PlanEstudiosClave": {"004", "NME"},
        "EstatusAlumno": ALLOWED_STUDENT_STATUS,
    }
    for column, allowed in expected.items():
        unexpected = set(data[column].dropna().astype(str)) - allowed
        if unexpected:
            raise ValueError(f"{column} contiene valores fuera del contrato: {sorted(unexpected)}")

    data.to_csv(path, index=False, encoding="utf-8")
    return data


if __name__ == "__main__":
    normalized = normalize_dataset()
    print(f"Dataset normalizado: {len(normalized)} filas en {DATASET_PATH}")
