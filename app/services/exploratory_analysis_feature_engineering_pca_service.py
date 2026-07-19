from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from app.models.config import (
    ARTIFACTS_DIR,
    CARDEX_COLUMNS,
    FEATURE_DECISIONS,
    FIGURES_DIR,
    FINAL_FEATURES,
    METADATA_COLUMNS,
    NUMERIC_COLUMNS,
    PROCESSED_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    RAW_DATASET,
    REPORTS_DIR,
    STUDENT_PERIOD_DATASET,
)
from app.services.cardex_student_period_feature_service import build_student_period_features


REPO_ROOT = PROJECT_ROOT
SOURCE_DATASET = RAW_DATASET


def ensure_dirs() -> None:
    for path in [RAW_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, ARTIFACTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def copy_dataset() -> None:
    if not SOURCE_DATASET.exists():
        raise FileNotFoundError(f"Dataset not found: {SOURCE_DATASET}")
    if SOURCE_DATASET.resolve() == RAW_DATASET.resolve():
        return
    shutil.copy2(SOURCE_DATASET, RAW_DATASET)


def read_dataset() -> pd.DataFrame:
    df = pd.read_csv(RAW_DATASET, encoding="utf-8-sig")
    if set(CARDEX_COLUMNS).issubset(df.columns):
        cardex_quality = pd.DataFrame(
            {
                "variable": df.columns,
                "dtype": [str(df[col].dtype) for col in df.columns],
                "null_count": [int(df[col].isna().sum()) for col in df.columns],
                "null_rate": [float(df[col].isna().mean()) for col in df.columns],
                "unique_count": [int(df[col].nunique()) for col in df.columns],
            }
        )
        analytic = build_student_period_features(df)
        STUDENT_PERIOD_DATASET.parent.mkdir(parents=True, exist_ok=True)
        analytic.to_csv(STUDENT_PERIOD_DATASET, index=False)
        cardex_quality.to_csv(REPORTS_DIR / "raw_cardex_quality_summary.csv", index=False)
        df = analytic

    missing = sorted(set(METADATA_COLUMNS + NUMERIC_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    return df


def write_markdown(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_Sin datos._"
    view = df.head(max_rows).copy()
    headers = list(view.columns)
    rows = []
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in view.iterrows():
        values = [format_markdown_value(row[col]) for col in headers]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def format_markdown_value(value: object) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.4g}"
    return str(value).replace("|", "/")


def detect_iqr_outliers(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    records = []
    for column in columns:
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((df[column] < lower) | (df[column] > upper)).sum())
        records.append(
            {
                "variable": column,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": lower,
                "upper_bound": upper,
                "outlier_count": count,
                "outlier_rate": count / len(df),
            }
        )
    return pd.DataFrame(records)


def strong_correlations(correlation: pd.DataFrame, threshold: float = 0.85) -> pd.DataFrame:
    records = []
    columns = list(correlation.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            value = correlation.loc[left, right]
            if abs(value) >= threshold:
                records.append(
                    {
                        "variable_a": left,
                        "variable_b": right,
                        "correlation": value,
                    }
                )
    return pd.DataFrame(records).sort_values(
        by="correlation", key=lambda s: s.abs(), ascending=False
    )


def save_histogram_svg(series: pd.Series, path: Path, title: str) -> None:
    counts, bins = np.histogram(series.dropna().to_numpy(), bins=10)
    width = 720
    height = 360
    margin_left = 56
    margin_bottom = 48
    margin_top = 42
    plot_w = width - margin_left - 24
    plot_h = height - margin_top - margin_bottom
    max_count = max(int(counts.max()), 1)
    bar_gap = 4
    bar_w = plot_w / len(counts) - bar_gap
    rects = []
    labels = []
    for i, count in enumerate(counts):
        bar_h = (count / max_count) * plot_h
        x = margin_left + i * (plot_w / len(counts))
        y = margin_top + plot_h - bar_h
        rects.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" fill="#2563eb" />'
        )
        labels.append(
            f'<text x="{x + bar_w / 2:.2f}" y="{height - 18}" font-size="10" text-anchor="middle">{bins[i]:.0f}</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{margin_left}" y="24" font-size="16" font-family="Arial" font-weight="700">{title}</text>
  <line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{width - 24}" y2="{margin_top + plot_h}" stroke="#111827"/>
  <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#111827"/>
  {''.join(rects)}
  {''.join(labels)}
  <text x="{margin_left}" y="{height - 6}" font-size="11" font-family="Arial">Rangos aproximados</text>
  <text x="10" y="{margin_top + 16}" font-size="11" font-family="Arial">Frecuencia</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def save_correlation_heatmap_svg(correlation: pd.DataFrame, path: Path) -> None:
    labels = list(correlation.columns)
    cell = 28
    left = 220
    top = 170
    width = left + cell * len(labels) + 40
    height = top + cell * len(labels) + 40
    cells = []
    xlabels = []
    ylabels = []
    for i, label in enumerate(labels):
        x = left + i * cell
        y = top + i * cell
        xlabels.append(
            f'<text x="{x + cell / 2:.1f}" y="{top - 8}" font-size="10" font-family="Arial" text-anchor="end" transform="rotate(-55 {x + cell / 2:.1f},{top - 8})">{label}</text>'
        )
        ylabels.append(
            f'<text x="{left - 8}" y="{y + 18}" font-size="10" font-family="Arial" text-anchor="end">{label}</text>'
        )
    for row, y_label in enumerate(labels):
        for col, x_label in enumerate(labels):
            value = float(correlation.loc[y_label, x_label])
            color = correlation_color(value)
            x = left + col * cell
            y = top + row * cell
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color}" stroke="#ffffff" stroke-width="1"><title>{y_label} / {x_label}: {value:.2f}</title></rect>'
            )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="24" y="28" font-size="16" font-family="Arial" font-weight="700">Matriz de correlacion</text>
  {''.join(xlabels)}
  {''.join(ylabels)}
  {''.join(cells)}
  <text x="24" y="58" font-size="12" font-family="Arial">Azul: correlacion positiva. Rojo: negativa. Blanco: baja.</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def correlation_color(value: float) -> str:
    value = max(-1.0, min(1.0, value))
    if value >= 0:
        intensity = int(255 - 155 * value)
        return f"rgb({intensity},{intensity},255)"
    intensity = int(255 - 155 * abs(value))
    return f"rgb(255,{intensity},{intensity})"


def run_eda(df: pd.DataFrame) -> None:
    numeric = df[NUMERIC_COLUMNS]
    quality = pd.DataFrame(
        {
            "variable": df.columns,
            "dtype": [str(df[col].dtype) for col in df.columns],
            "null_count": [int(df[col].isna().sum()) for col in df.columns],
            "null_rate": [float(df[col].isna().mean()) for col in df.columns],
            "unique_count": [int(df[col].nunique()) for col in df.columns],
        }
    )
    descriptive = numeric.describe().T.reset_index().rename(columns={"index": "variable"})
    correlation = numeric.corr()
    strong_corr = strong_correlations(correlation)
    outliers = detect_iqr_outliers(df, NUMERIC_COLUMNS)

    by_program = (
        df.groupby("programa")[["promedio_general", "porcentaje_asistencia", "rezago_materias", "materias_reprobadas"]]
        .mean()
        .round(2)
        .reset_index()
    )
    by_cohort = (
        df.groupby("cohorte")[["promedio_general", "porcentaje_asistencia", "rezago_materias", "materias_reprobadas"]]
        .mean()
        .round(2)
        .reset_index()
    )
    by_period = (
        df.groupby("id_periodo")[["promedio_general", "porcentaje_asistencia", "rezago_materias", "materias_reprobadas"]]
        .mean()
        .round(2)
        .reset_index()
    )
    status_counts = (
        df["estatus_academico"].value_counts().rename_axis("estatus_academico").reset_index(name="registros")
    )

    quality.to_csv(REPORTS_DIR / "quality_summary.csv", index=False)
    descriptive.to_csv(REPORTS_DIR / "descriptive_statistics.csv", index=False)
    correlation.to_csv(REPORTS_DIR / "correlation_matrix.csv")
    strong_corr.to_csv(REPORTS_DIR / "strong_correlations.csv", index=False)
    outliers.to_csv(REPORTS_DIR / "outlier_summary.csv", index=False)
    by_program.to_csv(REPORTS_DIR / "group_by_program.csv", index=False)
    by_cohort.to_csv(REPORTS_DIR / "group_by_cohort.csv", index=False)
    by_period.to_csv(REPORTS_DIR / "group_by_period.csv", index=False)
    status_counts.to_csv(REPORTS_DIR / "status_counts.csv", index=False)

    save_histogram_svg(df["promedio_general"], FIGURES_DIR / "hist_promedio_general.svg", "Distribucion de promedio_general")
    save_histogram_svg(df["porcentaje_asistencia"], FIGURES_DIR / "hist_porcentaje_asistencia.svg", "Distribucion de porcentaje_asistencia")
    save_histogram_svg(df["rezago_materias"], FIGURES_DIR / "hist_rezago_materias.svg", "Distribucion de rezago_materias")
    save_correlation_heatmap_svg(correlation, FIGURES_DIR / "correlation_heatmap.svg")

    report = f"""
# Fase 2 - Reporte EDA

## Resumen del dataset

- Archivo fuente: `{RAW_DATASET.relative_to(REPO_ROOT)}`
- Dataset analitico generado: `{STUDENT_PERIOD_DATASET.relative_to(REPO_ROOT)}`
- Registros: {len(df)}
- Columnas: {len(df.columns)}
- Unidad analitica asumida: un estudiante en un periodo academico.
- Columnas sin nulos: {int((quality["null_count"] == 0).sum())} de {len(quality)}

## Calidad de datos

{markdown_table(quality)}

## Distribucion de estatus academico

{markdown_table(status_counts)}

## Estadistica descriptiva de variables numericas

{markdown_table(descriptive[["variable", "mean", "std", "min", "25%", "50%", "75%", "max"]], max_rows=30)}

## Correlaciones fuertes

Umbral usado: `abs(correlacion) >= 0.85`.

{markdown_table(strong_corr, max_rows=30)}

## Outliers por regla IQR

{markdown_table(outliers[["variable", "outlier_count", "outlier_rate", "lower_bound", "upper_bound"]], max_rows=30)}

## Comparacion por programa

{markdown_table(by_program)}

## Comparacion por cohorte

{markdown_table(by_cohort)}

## Comparacion por periodo

{markdown_table(by_period)}

## Graficas generadas

- `data/reports/figures/hist_promedio_general.svg`
- `data/reports/figures/hist_porcentaje_asistencia.svg`
- `data/reports/figures/hist_rezago_materias.svg`
- `data/reports/figures/correlation_heatmap.svg`

## Hallazgos accionables

- El dataset fuente es cardex crudo por materia. El pipeline lo agrega a estudiante-periodo antes del EDA, seleccion de variables, PCA y clustering.
- Como el cardex no contiene asistencia ni seguimiento tutorial directo, esas senales se estiman de forma deterministica a partir de calificaciones, estatus, creditos, reprobadas y rezago. En una integracion institucional real se recomienda sustituirlas por datos operativos reales.
- `materias_aprobadas`, `creditos_acumulados` y `porcentaje_avance` son variables derivadas entre si. Conviene conservar solo una para clustering.
- `porcentaje_asistencia` y `faltas` describen dimensiones muy cercanas en sentido inverso. Para la primera version se conserva el porcentaje por ser normalizado e interpretable.
- Las variables de acompanamiento (`num_tutorias`, `num_asesorias`) e incidencias deben mantenerse porque ayudan a diferenciar perfiles academicos mas alla del promedio.
"""
    write_markdown(REPORTS_DIR / "eda_report.md", report)


def run_feature_selection(df: pd.DataFrame) -> None:
    numeric = df[NUMERIC_COLUMNS]
    variance = numeric.var(numeric_only=True)
    missing_rate = df[NUMERIC_COLUMNS].isna().mean()
    correlation = numeric.corr().abs()

    records = []
    for column in NUMERIC_COLUMNS:
        decision, reason = FEATURE_DECISIONS[column]
        max_corr = float(correlation[column].drop(labels=[column]).max())
        records.append(
            {
                "variable": column,
                "decision": decision,
                "reason": reason,
                "variance": float(variance[column]),
                "missing_rate": float(missing_rate[column]),
                "max_abs_correlation": max_corr,
            }
        )
    matrix = pd.DataFrame(records)
    matrix.to_csv(REPORTS_DIR / "feature_selection_matrix.csv", index=False)

    selected_dataset = df[METADATA_COLUMNS + FINAL_FEATURES].copy()
    selected_dataset.to_csv(PROCESSED_DIR / "selected_features.csv", index=False)
    pd.DataFrame({"feature": FINAL_FEATURES}).to_csv(PROCESSED_DIR / "final_feature_list.csv", index=False)

    included = matrix[matrix["decision"] == "include"]
    excluded = matrix[matrix["decision"] == "exclude"]
    report = f"""
# Fase 3 - Seleccion de Variables

## Criterios aplicados

- Excluir identificadores y metadatos operativos del entrenamiento: `id_estudiante`, `id_periodo`, `programa`, `cohorte`, `estatus_academico`.
- Mantener variables explicables para tutores y coordinadores.
- Reducir colinealidad evidente en variables derivadas.
- Mantener indicadores de desempeno, avance, asistencia, acompanamiento e incidencias.

## Variables finales para clustering

{markdown_table(pd.DataFrame({"feature": FINAL_FEATURES}), max_rows=40)}

## Variables incluidas

{markdown_table(included[["variable", "reason", "variance", "max_abs_correlation"]], max_rows=40)}

## Variables descartadas

{markdown_table(excluded[["variable", "reason", "variance", "max_abs_correlation"]], max_rows=40)}

## Matriz de seleccion

La matriz completa queda en:

```text
data/reports/feature_selection_matrix.csv
```

## Dataset resultante

El dataset con metadatos y variables finales queda en:

```text
data/processed/selected_features.csv
```

## Decision tecnica

El primer feature set queda compuesto por {len(FINAL_FEATURES)} variables numericas. Es suficientemente compacto para una primera segmentacion y conserva las dimensiones academicas mas importantes: desempeno, avance, carga, asistencia, acompanamiento, incidencias y rezago.
"""
    write_markdown(REPORTS_DIR / "feature_selection.md", report)


def standardize(df: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    values = df[columns].copy()
    means = values.mean()
    values = values.fillna(means)
    stds = values.std(ddof=0).replace(0, 1)
    scaled = (values - means) / stds
    params = pd.DataFrame(
        {
            "feature": columns,
            "mean": [float(means[col]) for col in columns],
            "std": [float(stds[col]) for col in columns],
        }
    )
    return scaled, params


def run_pca(df: pd.DataFrame) -> None:
    selected = df[METADATA_COLUMNS + FINAL_FEATURES].copy()
    scaled, scaler_params = standardize(selected, FINAL_FEATURES)

    x = scaled.to_numpy(dtype=float)
    u, singular_values, vt = np.linalg.svd(x, full_matrices=False)
    explained_variance = (singular_values**2) / (len(x) - 1)
    explained_ratio = explained_variance / explained_variance.sum()
    cumulative_ratio = np.cumsum(explained_ratio)
    n_components_90 = int(np.argmax(cumulative_ratio >= 0.90) + 1)
    n_components_95 = int(np.argmax(cumulative_ratio >= 0.95) + 1)

    component_names = [f"PC{i + 1}" for i in range(len(FINAL_FEATURES))]
    explained = pd.DataFrame(
        {
            "component": component_names,
            "explained_variance": explained_variance,
            "explained_variance_ratio": explained_ratio,
            "cumulative_explained_variance_ratio": cumulative_ratio,
        }
    )
    components = pd.DataFrame(vt, columns=FINAL_FEATURES)
    components.insert(0, "component", component_names)

    scores = pd.DataFrame(u * singular_values, columns=component_names)
    pca_scores = pd.concat([selected[METADATA_COLUMNS].reset_index(drop=True), scores], axis=1)
    pca_scores_90 = pd.concat(
        [
            selected[METADATA_COLUMNS].reset_index(drop=True),
            scores[component_names[:n_components_90]].reset_index(drop=True),
        ],
        axis=1,
    )
    pca_scores_95 = pd.concat(
        [
            selected[METADATA_COLUMNS].reset_index(drop=True),
            scores[component_names[:n_components_95]].reset_index(drop=True),
        ],
        axis=1,
    )
    scaled_dataset = pd.concat([selected[METADATA_COLUMNS].reset_index(drop=True), scaled.reset_index(drop=True)], axis=1)

    scaler_params.to_csv(ARTIFACTS_DIR / "scaler_params.csv", index=False)
    explained.to_csv(REPORTS_DIR / "pca_explained_variance.csv", index=False)
    components.to_csv(ARTIFACTS_DIR / "pca_components.csv", index=False)
    scaled_dataset.to_csv(PROCESSED_DIR / "scaled_features.csv", index=False)
    pca_scores.to_csv(PROCESSED_DIR / "pca_scores.csv", index=False)
    pca_scores_90.to_csv(PROCESSED_DIR / "pca_scores_90.csv", index=False)
    pca_scores_95.to_csv(PROCESSED_DIR / "pca_scores_95.csv", index=False)

    use_decision = (
        "PCA se recomienda como representacion alternativa para visualizacion y comparacion, "
        "pero el baseline de clustering debe conservar las variables escaladas originales para mantener interpretabilidad."
    )
    if n_components_90 <= max(3, math.ceil(len(FINAL_FEATURES) * 0.6)):
        use_decision = (
            "PCA puede usarse como entrada compacta para clustering porque alcanza 90% de varianza con una reduccion relevante de dimensiones. "
            "Aun asi, se debe comparar contra las variables escaladas originales en la fase de seleccion de K."
        )

    metadata = {
        "method": "numpy.linalg.svd",
        "input_features": FINAL_FEATURES,
        "n_input_features": len(FINAL_FEATURES),
        "n_components_total": len(FINAL_FEATURES),
        "n_components_90_variance": n_components_90,
        "n_components_95_variance": n_components_95,
        "recommended_use": use_decision,
        "outputs": {
            "scaler_params": str((ARTIFACTS_DIR / "scaler_params.csv").relative_to(REPO_ROOT)),
            "pca_components": str((ARTIFACTS_DIR / "pca_components.csv").relative_to(REPO_ROOT)),
            "pca_scores": str((PROCESSED_DIR / "pca_scores.csv").relative_to(REPO_ROOT)),
            "pca_scores_90": str((PROCESSED_DIR / "pca_scores_90.csv").relative_to(REPO_ROOT)),
            "pca_scores_95": str((PROCESSED_DIR / "pca_scores_95.csv").relative_to(REPO_ROOT)),
        },
    }
    (ARTIFACTS_DIR / "pca_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    top_loadings = []
    for pc in component_names[: min(5, len(component_names))]:
        row = components[components["component"] == pc].iloc[0]
        loadings = row[FINAL_FEATURES].astype(float).abs().sort_values(ascending=False).head(5)
        top_loadings.append(
            {
                "component": pc,
                "top_features": ", ".join(loadings.index.tolist()),
            }
        )
    top_loadings_df = pd.DataFrame(top_loadings)

    report = f"""
# Fase 4 - PCA

## Preparacion

- Variables de entrada: {len(FINAL_FEATURES)}
- Registros usados: {len(selected)}
- Escalado aplicado: media 0 y desviacion estandar 1 con calculo propio en numpy/pandas.
- Metodo PCA: SVD con `numpy.linalg.svd`.

## Varianza explicada

{markdown_table(explained[["component", "explained_variance_ratio", "cumulative_explained_variance_ratio"]], max_rows=40)}

## Componentes requeridos

- Componentes para explicar al menos 90% de varianza: {n_components_90}
- Componentes para explicar al menos 95% de varianza: {n_components_95}

## Variables dominantes por componente

{markdown_table(top_loadings_df)}

## Artefactos generados

- `artifacts/scaler_params.csv`
- `artifacts/pca_components.csv`
- `artifacts/pca_metadata.json`
- `data/processed/scaled_features.csv`
- `data/processed/pca_scores.csv`
- `data/processed/pca_scores_90.csv`
- `data/processed/pca_scores_95.csv`

## Decision tecnica

{use_decision}

## Criterio de aceptacion

PCA queda reproducible porque se guardan parametros de escalado, componentes, varianza explicada, scores transformados y metadata del proceso.
"""
    write_markdown(REPORTS_DIR / "pca_report.md", report)


def main() -> None:
    ensure_dirs()
    copy_dataset()
    df = read_dataset()
    run_eda(df)
    run_feature_selection(df)
    run_pca(df)
    print("Fases 2, 3 y 4 completadas.")
    print(f"Reportes: {REPORTS_DIR}")
    print(f"Procesados: {PROCESSED_DIR}")
    print(f"Artefactos: {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
