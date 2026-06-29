from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from app.models.config import (
    ARTIFACTS_DIR,
    FIGURES_DIR,
    K_MAX,
    K_MIN,
    MAX_ITER,
    METADATA_COLUMNS,
    N_INIT,
    PROCESSED_DIR,
    PROJECT_ROOT,
    RANDOM_SEED,
    REPORTS_DIR,
    TOL,
)


REPO_ROOT = PROJECT_ROOT


def ensure_dirs() -> None:
    for path in [PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, ARTIFACTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


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
        return f"{value:.5g}"
    return str(value).replace("|", "/")


def load_matrix(path: Path) -> tuple[pd.DataFrame, list[str], np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    df = pd.read_csv(path)
    features = [col for col in df.columns if col not in METADATA_COLUMNS]
    if not features:
        raise ValueError(f"No feature columns found in {path}")
    return df, features, df[features].to_numpy(dtype=float)


def squared_distances(x: np.ndarray, centers: np.ndarray) -> np.ndarray:
    return ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)


def initialize_kmeans_pp(x: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    n_samples = x.shape[0]
    centers = np.empty((k, x.shape[1]), dtype=float)
    first = rng.integers(0, n_samples)
    centers[0] = x[first]
    closest_sq = ((x - centers[0]) ** 2).sum(axis=1)

    for center_idx in range(1, k):
        total = closest_sq.sum()
        if total <= 0:
            centers[center_idx] = x[rng.integers(0, n_samples)]
            continue
        probabilities = closest_sq / total
        selected = rng.choice(n_samples, p=probabilities)
        centers[center_idx] = x[selected]
        new_sq = ((x - centers[center_idx]) ** 2).sum(axis=1)
        closest_sq = np.minimum(closest_sq, new_sq)
    return centers


def fit_kmeans_once(
    x: np.ndarray,
    k: int,
    rng: np.random.Generator,
    max_iter: int = MAX_ITER,
    tol: float = TOL,
) -> dict[str, object]:
    centers = initialize_kmeans_pp(x, k, rng)
    labels = np.zeros(x.shape[0], dtype=int)

    for iteration in range(1, max_iter + 1):
        distances = squared_distances(x, centers)
        new_labels = distances.argmin(axis=1)
        new_centers = centers.copy()

        for cluster_id in range(k):
            members = x[new_labels == cluster_id]
            if len(members) == 0:
                farthest = distances.min(axis=1).argmax()
                new_centers[cluster_id] = x[farthest]
            else:
                new_centers[cluster_id] = members.mean(axis=0)

        shift = float(np.sqrt(((new_centers - centers) ** 2).sum(axis=1)).max())
        centers = new_centers
        labels = new_labels
        if shift <= tol:
            break

    final_distances = squared_distances(x, centers)
    labels = final_distances.argmin(axis=1)
    inertia = float(final_distances[np.arange(x.shape[0]), labels].sum())
    return {
        "centers": centers,
        "labels": labels,
        "inertia": inertia,
        "iterations": iteration,
    }


def fit_kmeans(x: np.ndarray, k: int, n_init: int = N_INIT, seed: int = RANDOM_SEED) -> dict[str, object]:
    best: dict[str, object] | None = None
    for init_idx in range(n_init):
        rng = np.random.default_rng(seed + init_idx + k * 1000)
        result = fit_kmeans_once(x, k, rng)
        if best is None or float(result["inertia"]) < float(best["inertia"]):
            best = result
    assert best is not None
    return best


def pairwise_distances(x: np.ndarray) -> np.ndarray:
    diff = x[:, None, :] - x[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def silhouette_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2 or len(unique_labels) >= len(labels):
        return float("nan")

    distances = pairwise_distances(x)
    scores = np.zeros(len(labels), dtype=float)
    for idx, label in enumerate(labels):
        same = labels == label
        same_count = int(same.sum())
        if same_count <= 1:
            a = 0.0
        else:
            a = float(distances[idx, same].sum() / (same_count - 1))

        b_values = []
        for other_label in unique_labels:
            if other_label == label:
                continue
            other = labels == other_label
            b_values.append(float(distances[idx, other].mean()))
        b = min(b_values) if b_values else 0.0
        denominator = max(a, b)
        scores[idx] = 0.0 if denominator == 0 else (b - a) / denominator
    return float(scores.mean())


def calinski_harabasz_score(x: np.ndarray, labels: np.ndarray, centers: np.ndarray) -> float:
    n_samples = x.shape[0]
    k = len(np.unique(labels))
    if k <= 1 or k >= n_samples:
        return float("nan")
    global_mean = x.mean(axis=0)
    between = 0.0
    within = 0.0
    for cluster_id in range(k):
        members = x[labels == cluster_id]
        if len(members) == 0:
            continue
        between += len(members) * float(((centers[cluster_id] - global_mean) ** 2).sum())
        within += float(((members - centers[cluster_id]) ** 2).sum())
    if within == 0:
        return float("inf")
    return float((between / (k - 1)) / (within / (n_samples - k)))


def davies_bouldin_score(x: np.ndarray, labels: np.ndarray, centers: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    k = len(unique_labels)
    if k <= 1:
        return float("nan")

    scatters = np.zeros(k, dtype=float)
    for idx, cluster_id in enumerate(unique_labels):
        members = x[labels == cluster_id]
        if len(members) == 0:
            scatters[idx] = 0.0
        else:
            scatters[idx] = np.sqrt(((members - centers[cluster_id]) ** 2).sum(axis=1)).mean()

    center_distances = np.sqrt(((centers[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2))
    ratios = []
    for i in range(k):
        values = []
        for j in range(k):
            if i == j:
                continue
            distance = center_distances[i, j]
            values.append(float("inf") if distance == 0 else (scatters[i] + scatters[j]) / distance)
        ratios.append(max(values))
    return float(np.mean(ratios))


def cluster_sizes(labels: np.ndarray) -> dict[int, int]:
    values, counts = np.unique(labels, return_counts=True)
    return {int(value): int(count) for value, count in zip(values, counts)}


def evaluate_representation(name: str, x: np.ndarray) -> tuple[pd.DataFrame, dict[int, dict[str, object]]]:
    records = []
    models: dict[int, dict[str, object]] = {}
    for k in range(K_MIN, K_MAX + 1):
        model = fit_kmeans(x, k)
        labels = model["labels"]
        centers = model["centers"]
        assert isinstance(labels, np.ndarray)
        assert isinstance(centers, np.ndarray)
        models[k] = model
        records.append(
            {
                "representation": name,
                "k": k,
                "inertia": float(model["inertia"]),
                "silhouette": silhouette_score(x, labels),
                "calinski_harabasz": calinski_harabasz_score(x, labels, centers),
                "davies_bouldin": davies_bouldin_score(x, labels, centers),
                "min_cluster_size": min(cluster_sizes(labels).values()),
                "max_cluster_size": max(cluster_sizes(labels).values()),
                "n_samples": int(len(labels)),
                "iterations": int(model["iterations"]),
            }
        )
    return pd.DataFrame(records), models


def choose_final_model(metrics: pd.DataFrame) -> dict[str, object]:
    ranked = metrics.copy()
    ranked["cluster_balance_ratio"] = ranked["max_cluster_size"] / ranked["min_cluster_size"]
    ranked["silhouette_rank"] = ranked["silhouette"].rank(ascending=False, method="min")
    ranked["davies_bouldin_rank"] = ranked["davies_bouldin"].rank(ascending=True, method="min")
    ranked["calinski_rank"] = ranked["calinski_harabasz"].rank(ascending=False, method="min")
    ranked["balance_rank"] = ranked["cluster_balance_ratio"].rank(ascending=True, method="min")

    # Use balance as a quality guard, not as the main objective. A small but meaningful
    # profile can be valid in academic segmentation, especially for atypical students.
    sample_count = ranked["n_samples"].replace(0, np.nan)
    minimum_cluster_rate = ranked["min_cluster_size"] / sample_count
    viable = ranked[minimum_cluster_rate >= 0.05].copy()
    if viable.empty:
        viable = ranked.copy()

    viable["combined_rank"] = (
        viable["silhouette_rank"] * 0.50
        + viable["davies_bouldin_rank"] * 0.25
        + viable["calinski_rank"] * 0.20
        + viable["balance_rank"] * 0.05
    )
    viable = viable.sort_values(["combined_rank", "silhouette_rank", "k", "representation"]).reset_index(drop=True)
    return viable.iloc[0].to_dict()


def save_metric_svg(metrics: pd.DataFrame, representation: str, metric: str, path: Path, title: str) -> None:
    subset = metrics[metrics["representation"] == representation].sort_values("k")
    width = 720
    height = 360
    left = 64
    right = 24
    top = 42
    bottom = 52
    plot_w = width - left - right
    plot_h = height - top - bottom
    x_values = subset["k"].to_numpy(dtype=float)
    y_values = subset[metric].to_numpy(dtype=float)
    y_min = float(np.nanmin(y_values))
    y_max = float(np.nanmax(y_values))
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0

    points = []
    circles = []
    labels = []
    for k, y_value in zip(x_values, y_values):
        x = left + ((k - x_values.min()) / (x_values.max() - x_values.min())) * plot_w
        y = top + (1 - ((y_value - y_min) / (y_max - y_min))) * plot_h
        points.append(f"{x:.2f},{y:.2f}")
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#2563eb" />')
        labels.append(f'<text x="{x:.2f}" y="{height - 20}" font-size="11" text-anchor="middle">{int(k)}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="24" font-size="16" font-family="Arial" font-weight="700">{title}</text>
  <line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#111827"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#111827"/>
  <polyline points="{' '.join(points)}" fill="none" stroke="#2563eb" stroke-width="2"/>
  {''.join(circles)}
  {''.join(labels)}
  <text x="{left}" y="{height - 6}" font-size="11" font-family="Arial">K</text>
  <text x="10" y="{top + 16}" font-size="11" font-family="Arial">{metric}</text>
  <text x="{left}" y="{height - 34}" font-size="10" font-family="Arial">min={y_min:.3g}, max={y_max:.3g}</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def save_2d_scatter_svg(scores: pd.DataFrame, labels: np.ndarray, path: Path, title: str) -> None:
    x_values = scores["PC1"].to_numpy(dtype=float)
    y_values = scores["PC2"].to_numpy(dtype=float)
    width = 720
    height = 520
    left = 60
    right = 24
    top = 42
    bottom = 52
    plot_w = width - left - right
    plot_h = height - top - bottom
    x_min, x_max = float(x_values.min()), float(x_values.max())
    y_min, y_max = float(y_values.min()), float(y_values.max())
    palette = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#4b5563", "#ca8a04"]
    circles = []
    for x_val, y_val, label in zip(x_values, y_values, labels):
        x = left + ((x_val - x_min) / (x_max - x_min)) * plot_w
        y = top + (1 - ((y_val - y_min) / (y_max - y_min))) * plot_h
        color = palette[int(label) % len(palette)]
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}" opacity="0.72" />')
    legend = []
    for cluster_id in sorted(np.unique(labels)):
        color = palette[int(cluster_id) % len(palette)]
        lx = left + int(cluster_id) * 92
        ly = height - 18
        legend.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="{color}" />')
        legend.append(f'<text x="{lx + 9}" y="{ly + 4}" font-size="11" font-family="Arial">C{int(cluster_id)}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="24" font-size="16" font-family="Arial" font-weight="700">{title}</text>
  <line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#111827"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#111827"/>
  {''.join(circles)}
  <text x="{left}" y="{height - 34}" font-size="11" font-family="Arial">PC1</text>
  <text x="12" y="{top + 16}" font-size="11" font-family="Arial">PC2</text>
  {''.join(legend)}
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def describe_clusters(
    assignments: pd.DataFrame,
    selected_features: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    merged = assignments[["id_estudiante", "id_periodo", "cluster"]].merge(
        selected_features[["id_estudiante", "id_periodo"] + feature_columns],
        on=["id_estudiante", "id_periodo"],
        how="left",
    )
    summaries = []
    global_means = selected_features[feature_columns].mean()
    failed_column = "materias_reprobadas_acumuladas" if "materias_reprobadas_acumuladas" in feature_columns else "materias_reprobadas"
    for cluster_id, group in merged.groupby("cluster"):
        means = group[feature_columns].mean()
        diffs = (means - global_means).sort_values(key=lambda s: s.abs(), ascending=False)
        dominant = ", ".join([f"{idx} ({value:+.2f})" for idx, value in diffs.head(5).items()])
        summaries.append(
            {
                "cluster": int(cluster_id),
                "registros": int(len(group)),
                "promedio_general": float(means["promedio_general"]),
                "porcentaje_asistencia": float(means["porcentaje_asistencia"]),
                "materias_reprobadas": float(means[failed_column]),
                "rezago_materias": float(means["rezago_materias"]),
                "variables_distintivas": dominant,
            }
        )
    return pd.DataFrame(summaries).sort_values("cluster")


def profile_label(row: pd.Series) -> str:
    if row["porcentaje_asistencia"] < 60 and row["promedio_general"] >= 80:
        return "Atipico / buen promedio con baja asistencia"
    if row["promedio_general"] >= 88 and row["rezago_materias"] <= 0.5 and row["materias_reprobadas"] <= 0.5:
        return "Alto desempeno / avance estable"
    if row["promedio_general"] < 62 or row["rezago_materias"] >= 4:
        return "Critico / rezago alto"
    if row["promedio_general"] < 76 or row["materias_reprobadas"] >= 2:
        return "Riesgo academico moderado"
    return "Regular / seguimiento preventivo"


def run_phase_5_6() -> None:
    ensure_dirs()
    scaled_df, scaled_features, scaled_x = load_matrix(PROCESSED_DIR / "scaled_features.csv")
    pca90_df, pca90_features, pca90_x = load_matrix(PROCESSED_DIR / "pca_scores_90.csv")
    pca2_df, _, _ = load_matrix(PROCESSED_DIR / "pca_scores.csv")
    selected_features_df, selected_feature_columns, _ = load_matrix(PROCESSED_DIR / "selected_features.csv")

    scaled_metrics, scaled_models = evaluate_representation("scaled_features", scaled_x)
    pca90_metrics, pca90_models = evaluate_representation("pca_90", pca90_x)
    metrics = pd.concat([scaled_metrics, pca90_metrics], ignore_index=True)
    best = choose_final_model(metrics)
    metrics.to_csv(REPORTS_DIR / "k_selection_metrics.csv", index=False)

    save_metric_svg(metrics, "scaled_features", "inertia", FIGURES_DIR / "k_inertia_scaled.svg", "Inercia por K - variables escaladas")
    save_metric_svg(metrics, "scaled_features", "silhouette", FIGURES_DIR / "k_silhouette_scaled.svg", "Silhouette por K - variables escaladas")
    save_metric_svg(metrics, "pca_90", "inertia", FIGURES_DIR / "k_inertia_pca90.svg", "Inercia por K - PCA 90")
    save_metric_svg(metrics, "pca_90", "silhouette", FIGURES_DIR / "k_silhouette_pca90.svg", "Silhouette por K - PCA 90")

    final_representation = str(best["representation"])
    final_k = int(best["k"])
    if final_representation == "scaled_features":
        final_df = scaled_df
        final_x = scaled_x
        final_features = scaled_features
        final_model = scaled_models[final_k]
    else:
        final_df = pca90_df
        final_x = pca90_x
        final_features = pca90_features
        final_model = pca90_models[final_k]

    labels = final_model["labels"]
    centers = final_model["centers"]
    assert isinstance(labels, np.ndarray)
    assert isinstance(centers, np.ndarray)

    distances = np.sqrt(squared_distances(final_x, centers))
    assigned_distances = distances[np.arange(len(labels)), labels]
    confidence = 1 / (1 + assigned_distances)

    assignments = final_df[METADATA_COLUMNS].copy()
    assignments["cluster"] = labels.astype(int)
    assignments["distance_to_centroid"] = assigned_distances
    assignments["membership_score"] = confidence
    assignments.to_csv(PROCESSED_DIR / "cluster_assignments.csv", index=False)

    centroids = pd.DataFrame(centers, columns=final_features)
    centroids.insert(0, "cluster", list(range(final_k)))
    centroids.to_csv(ARTIFACTS_DIR / "kmeans_centroids.csv", index=False)

    cluster_summary = describe_clusters(assignments, selected_features_df, selected_feature_columns)
    cluster_summary["perfil_sugerido"] = cluster_summary.apply(profile_label, axis=1)
    cluster_summary.to_csv(REPORTS_DIR / "cluster_summary.csv", index=False)

    model_metadata = {
        "algorithm": "kmeans",
        "implementation": "numpy",
        "random_seed": RANDOM_SEED,
        "n_init": N_INIT,
        "max_iter": MAX_ITER,
        "tol": TOL,
        "selected_representation": final_representation,
        "selected_k": final_k,
        "features": final_features,
        "metrics": {
            "inertia": float(final_model["inertia"]),
            "silhouette": float(best["silhouette"]),
            "calinski_harabasz": float(best["calinski_harabasz"]),
            "davies_bouldin": float(best["davies_bouldin"]),
            "min_cluster_size": int(best["min_cluster_size"]),
            "max_cluster_size": int(best["max_cluster_size"]),
        },
        "outputs": {
            "metrics": str((REPORTS_DIR / "k_selection_metrics.csv").relative_to(REPO_ROOT)),
            "assignments": str((PROCESSED_DIR / "cluster_assignments.csv").relative_to(REPO_ROOT)),
            "centroids": str((ARTIFACTS_DIR / "kmeans_centroids.csv").relative_to(REPO_ROOT)),
            "cluster_summary": str((REPORTS_DIR / "cluster_summary.csv").relative_to(REPO_ROOT)),
        },
    }
    (ARTIFACTS_DIR / "kmeans_metadata.json").write_text(json.dumps(model_metadata, indent=2), encoding="utf-8")

    save_2d_scatter_svg(pca2_df, labels, FIGURES_DIR / "cluster_scatter_pc1_pc2.svg", f"Clusters finales K={final_k} en PC1/PC2")

    best_table = pd.DataFrame([best])[
        [
            "representation",
            "k",
            "inertia",
            "silhouette",
            "calinski_harabasz",
            "davies_bouldin",
            "min_cluster_size",
            "max_cluster_size",
            "combined_rank",
        ]
    ]

    phase_5_report = f"""
# Fase 5 - Seleccion de K

## Configuracion

- Rango evaluado: K={K_MIN} a K={K_MAX}
- Inicializaciones por K: {N_INIT}
- Representaciones comparadas:
  - `scaled_features`: variables seleccionadas y escaladas.
  - `pca_90`: componentes PCA que explican al menos 90% de la varianza.

## Metricas calculadas

- Inercia: menor es mejor, sirve para metodo del codo.
- Silhouette: mayor es mejor, mide separacion y cohesion.
- Calinski-Harabasz: mayor es mejor.
- Davies-Bouldin: menor es mejor.
- Balance de tamanos: evita seleccionar K con clusters residuales demasiado pequenos.

## Resultado recomendado

{markdown_table(best_table)}

## Comparativo completo

{markdown_table(metrics.sort_values(["representation", "k"]), max_rows=30)}

## Graficas generadas

- `data/reports/figures/k_inertia_scaled.svg`
- `data/reports/figures/k_silhouette_scaled.svg`
- `data/reports/figures/k_inertia_pca90.svg`
- `data/reports/figures/k_silhouette_pca90.svg`

## Decision tecnica

Se selecciona `K={final_k}` usando la representacion `{final_representation}`. La decision combina metricas internas y balance de tamanos. Si en una revision academica se prioriza interpretabilidad por encima de compactacion, debe compararse este resultado con `scaled_features` antes de nombrar perfiles definitivos.
"""
    write_markdown(REPORTS_DIR / "k_selection_report.md", phase_5_report)

    phase_6_report = f"""
# Fase 6 - Entrenamiento K-Means

## Modelo entrenado

- Algoritmo: K-Means.
- Implementacion: numpy, con inicializacion tipo k-means++.
- Representacion usada: `{final_representation}`.
- K final: {final_k}.
- Registros asignados: {len(assignments)}.
- Inercia final: {float(final_model["inertia"]):.5f}.
- Silhouette: {float(best["silhouette"]):.5f}.
- Calinski-Harabasz: {float(best["calinski_harabasz"]):.5f}.
- Davies-Bouldin: {float(best["davies_bouldin"]):.5f}.

## Distribucion e interpretacion inicial de clusters

{markdown_table(cluster_summary, max_rows=20)}

## Artefactos generados

- `data/processed/cluster_assignments.csv`
- `artifacts/kmeans_centroids.csv`
- `artifacts/kmeans_metadata.json`
- `data/reports/cluster_summary.csv`
- `data/reports/figures/cluster_scatter_pc1_pc2.svg`

## Uso esperado

`cluster_assignments.csv` es la salida que en fases posteriores podra persistirse como historial de inferencias. Cada fila conserva estudiante, periodo, cluster asignado, distancia al centroide y un score simple de pertenencia.

## Limitacion actual

Las etiquetas de perfil son interpretaciones iniciales basadas en medias de variables academicas. Deben validarse con dominio academico antes de mostrarse a usuarios finales.
"""
    write_markdown(REPORTS_DIR / "kmeans_training_report.md", phase_6_report)

    print("Fases 5 y 6 completadas.")
    print(f"K final: {final_k}")
    print(f"Representacion final: {final_representation}")
    print(f"Reportes: {REPORTS_DIR}")
    print(f"Procesados: {PROCESSED_DIR}")
    print(f"Artefactos: {ARTIFACTS_DIR}")


if __name__ == "__main__":
    run_phase_5_6()
