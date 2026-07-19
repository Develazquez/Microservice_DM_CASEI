from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.models.config import ARTIFACTS_DIR, METADATA_COLUMNS, PROCESSED_DIR, REPORTS_DIR, RANDOM_SEED
from app.services.clustering_training_evaluation_service import fit_kmeans, squared_distances
from app.views.report_view import markdown_table, write_markdown


REPO_ROOT = Path(__file__).resolve().parents[2]

ASSIGNMENTS_PATH = PROCESSED_DIR / "cluster_assignments.csv"
SELECTED_FEATURES_PATH = PROCESSED_DIR / "selected_features.csv"
PCA90_PATH = PROCESSED_DIR / "pca_scores_90.csv"
CENTROIDS_PATH = ARTIFACTS_DIR / "kmeans_centroids.csv"
METADATA_PATH = ARTIFACTS_DIR / "kmeans_metadata.json"

PROFILE_CATALOG_PATH = REPORTS_DIR / "academic_profile_catalog.csv"
FEATURE_DIFFERENCES_PATH = REPORTS_DIR / "cluster_feature_differences.csv"
OUTLIERS_PATH = REPORTS_DIR / "cluster_outlier_candidates.csv"
STABILITY_PATH = REPORTS_DIR / "cluster_stability_metrics.csv"
INTERPRETATION_REPORT_PATH = REPORTS_DIR / "profile_interpretation_report.md"
PROFILE_CATALOG_JSON_PATH = ARTIFACTS_DIR / "academic_profile_catalog.json"

KEY_RISK_COLUMNS = [
    "promedio_general",
    "promedio_periodo",
    "porcentaje_asistencia",
    "materias_reprobadas_periodo",
    "materias_reprobadas_acumuladas",
    "rezago_materias",
    "recursamientos",
    "periodos_sin_inscripcion",
    "num_incidencias",
    "tutorias_abiertas",
    "compromisos_pendientes",
    "varianza_calificaciones",
]

FEATURE_READINGS = {
    "promedio_general": ("promedio general", "mejor desempeno acumulado", "desempeno acumulado menor"),
    "promedio_periodo": ("promedio del periodo", "mejor desempeno reciente", "desempeno reciente menor"),
    "porcentaje_avance": ("avance curricular", "mayor avance del plan", "menor avance del plan"),
    "porcentaje_asistencia": ("asistencia estimada", "mayor asistencia", "menor asistencia"),
    "retardos": ("retardos estimados", "mas retardos", "menos retardos"),
    "num_asesorias": ("asesorias estimadas", "mas asesorias", "menos asesorias"),
    "num_incidencias": ("incidencias estimadas", "mas incidencias", "menos incidencias"),
    "recursamientos": ("recursamientos", "mas recursamientos", "menos recursamientos"),
    "rezago_materias": ("rezago en materias", "mayor rezago", "menor rezago"),
    "creditos_inscritos_periodo": ("creditos inscritos", "mayor carga inscrita", "menor carga inscrita"),
    "creditos_aprobados_periodo": ("creditos aprobados", "mas creditos aprobados", "menos creditos aprobados"),
    "periodos_cursados": ("periodos cursados", "mas periodos cursados", "menos periodos cursados"),
    "periodos_sin_inscripcion": ("periodos sin inscripcion", "mas periodos sin inscripcion", "menos periodos sin inscripcion"),
    "materias_reprobadas_periodo": ("reprobadas del periodo", "mas reprobadas recientes", "menos reprobadas recientes"),
    "materias_reprobadas_acumuladas": ("reprobadas acumuladas", "mas reprobadas acumuladas", "menos reprobadas acumuladas"),
    "materias_en_curso_periodo": ("materias en curso", "mas materias en curso", "menos materias en curso"),
    "tendencia_promedio": ("tendencia del promedio", "tendencia al alza", "tendencia a la baja"),
    "varianza_calificaciones": ("variacion de calificaciones", "desempeno mas irregular", "desempeno mas estable"),
    "tutorias_abiertas": ("tutorias abiertas estimadas", "mas seguimiento pendiente", "menos seguimiento pendiente"),
    "tutorias_cerradas": ("tutorias cerradas estimadas", "mas seguimiento cerrado", "menos seguimiento cerrado"),
    "compromisos_pendientes": ("compromisos pendientes estimados", "mas compromisos pendientes", "menos compromisos pendientes"),
    "compromisos_cumplidos": ("compromisos cumplidos estimados", "mas compromisos cumplidos", "menos compromisos cumplidos"),
    "permisos_aprobados": ("permisos aprobados estimados", "mas permisos aprobados", "menos permisos aprobados"),
    "permisos_rechazados": ("permisos rechazados estimados", "mas permisos rechazados", "menos permisos rechazados"),
    "bandera_dato_incompleto": ("dato incompleto", "mas registros con dato incompleto", "menos registros con dato incompleto"),
}


def ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return pd.read_csv(path)


def feature_columns(selected_features: pd.DataFrame) -> list[str]:
    return [column for column in selected_features.columns if column not in METADATA_COLUMNS]


def merge_assignments_with_features(assignments: pd.DataFrame, selected_features: pd.DataFrame) -> pd.DataFrame:
    columns = ["id_estudiante", "id_periodo"] + feature_columns(selected_features)
    merged = assignments.merge(
        selected_features[columns],
        on=["id_estudiante", "id_periodo"],
        how="left",
        indicator=True,
    )
    if (merged["_merge"] != "both").any():
        raise ValueError("Cluster assignments and selected features could not be fully joined.")
    merged = merged.drop(columns="_merge")
    return merged


def describe_feature(feature: str, z_delta: float) -> str:
    label, high_text, low_text = FEATURE_READINGS.get(feature, (feature, f"{feature} mayor", f"{feature} menor"))
    direction = high_text if z_delta > 0 else low_text
    return f"{label}: {direction}"


def cluster_feature_differences(merged: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    global_means = merged[features].mean()
    global_stds = merged[features].std(ddof=0).replace(0, np.nan)
    records = []

    for cluster_id, group in merged.groupby("cluster"):
        cluster_means = group[features].mean()
        for feature in features:
            delta = float(cluster_means[feature] - global_means[feature])
            z_delta = float(delta / global_stds[feature]) if pd.notna(global_stds[feature]) else 0.0
            records.append(
                {
                    "cluster": int(cluster_id),
                    "variable": feature,
                    "media_cluster": float(cluster_means[feature]),
                    "media_global": float(global_means[feature]),
                    "diferencia": delta,
                    "diferencia_estandarizada": z_delta,
                    "lectura": describe_feature(feature, z_delta),
                }
            )

    result = pd.DataFrame(records)
    result["magnitud_diferencia"] = result["diferencia_estandarizada"].abs()
    result = result.sort_values(["cluster", "magnitud_diferencia"], ascending=[True, False])
    return result.drop(columns="magnitud_diferencia")


def summarize_dominant_features(differences: pd.DataFrame, cluster_id: int, top_n: int = 6) -> str:
    subset = differences[differences["cluster"] == cluster_id].copy()
    subset = subset.reindex(subset["diferencia_estandarizada"].abs().sort_values(ascending=False).index)
    readings = []
    for _, row in subset.head(top_n).iterrows():
        direction = "alto" if row["diferencia_estandarizada"] > 0 else "bajo"
        readings.append(f"{row['variable']} {direction} ({row['diferencia_estandarizada']:+.2f} DE)")
    return "; ".join(readings)


def choose_profile_name(row: pd.Series) -> tuple[str, str, str, str]:
    average = float(row.get("promedio_general", 0))
    period_average = float(row.get("promedio_periodo", average))
    attendance = float(row.get("porcentaje_asistencia", 100))
    failed = float(row.get("materias_reprobadas_acumuladas", row.get("materias_reprobadas_periodo", 0)))
    recent_failed = float(row.get("materias_reprobadas_periodo", 0))
    lag = float(row.get("rezago_materias", 0))
    pending = float(row.get("compromisos_pendientes", 0))
    incidents = float(row.get("num_incidencias", 0))

    if average >= 80 and attendance < 65 and lag <= 2:
        return (
            "Atipico / buen promedio con baja asistencia",
            "Media",
            "Buen desempeno aparente con senales de baja asistencia; conviene revisar permisos, carga y contexto.",
            "Verificar asistencia real y motivos de ausencia antes de clasificarlo como riesgo academico.",
        )

    if average < 65 or lag >= 4 or failed >= 4:
        return (
            "Critico / rezago alto",
            "Alta",
            "Trayectoria con rezago o desempeno bajo que requiere revision tutorial prioritaria.",
            "No asumir causa unica; cruzar con historial, disponibilidad de materias y condiciones institucionales.",
        )

    if average < 74 or attendance < 68 or failed >= 2 or recent_failed >= 1.5 or pending >= 2 or incidents >= 1.5:
        return (
            "Riesgo academico moderado",
            "Media-alta",
            "Grupo con senales consistentes de seguimiento: calificaciones menores, baja asistencia o rezago medio.",
            "Usar como priorizacion de acompanamiento, no como diagnostico definitivo.",
        )

    return (
        "Regular / seguimiento preventivo",
        "Baja-media",
        "Trayectoria mayormente estable; requiere monitoreo ordinario y seguimiento preventivo.",
        "Mantener vigilancia de casos con baja pertenencia al cluster o cambios recientes de tendencia.",
    )


def action_rules(profile_name: str) -> str:
    if profile_name.startswith("Critico"):
        return "Priorizar entrevista tutorial, revisar materias reprobadas/rezago y acordar plan de recuperacion."
    if profile_name.startswith("Riesgo"):
        return "Programar seguimiento preventivo, revisar asistencia, reprobadas recientes y compromisos pendientes."
    if profile_name.startswith("Atipico"):
        return "Validar permisos/asistencia real y evitar sancionar si el desempeno academico sigue siendo adecuado."
    return "Mantener monitoreo regular, detectar cambios de tendencia y atender outliers de baja pertenencia."


def build_profile_catalog(merged: pd.DataFrame, differences: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    total_records = len(merged)
    rows = []
    risk_columns = [column for column in KEY_RISK_COLUMNS if column in features]

    for cluster_id, group in merged.groupby("cluster"):
        means = group[features].mean()
        profile_name, priority, functional_reading, caution = choose_profile_name(means)
        row = {
            "cluster": int(cluster_id),
            "perfil_academico": profile_name,
            "prioridad_tutorial": priority,
            "registros": int(len(group)),
            "porcentaje_registros": round((len(group) / total_records) * 100, 2),
            "rasgos_dominantes": summarize_dominant_features(differences, int(cluster_id)),
            "lectura_funcional": functional_reading,
            "acciones_sugeridas": action_rules(profile_name),
            "cautela_interpretacion": caution,
        }
        for column in risk_columns:
            row[column] = round(float(means[column]), 4)
        rows.append(row)

    return pd.DataFrame(rows).sort_values("cluster")


def identify_outliers(merged: pd.DataFrame, profile_catalog: pd.DataFrame) -> pd.DataFrame:
    records = []
    profile_lookup = profile_catalog.set_index("cluster")["perfil_academico"].to_dict()
    selected_columns = [
        "id_estudiante",
        "id_periodo",
        "programa",
        "cohorte",
        "estatus_academico",
        "cluster",
        "distance_to_centroid",
        "membership_score",
        "promedio_general",
        "porcentaje_asistencia",
        "materias_reprobadas_acumuladas",
        "rezago_materias",
        "tendencia_promedio",
    ]
    selected_columns = [column for column in selected_columns if column in merged.columns]

    for cluster_id, group in merged.groupby("cluster"):
        threshold = float(group["distance_to_centroid"].quantile(0.95))
        candidates = group[group["distance_to_centroid"] >= threshold].copy()
        candidates = candidates.sort_values("distance_to_centroid", ascending=False)
        for _, row in candidates.iterrows():
            record = {column: row[column] for column in selected_columns}
            record["perfil_academico"] = profile_lookup.get(int(cluster_id), "")
            record["criterio_outlier"] = "distancia al centroide en el percentil 95 o superior de su cluster"
            records.append(record)

    return pd.DataFrame(records)


def adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    labels_true = np.asarray(labels_true)
    labels_pred = np.asarray(labels_pred)
    if labels_true.shape[0] != labels_pred.shape[0]:
        raise ValueError("Label arrays must have the same length.")
    n = labels_true.shape[0]
    if n < 2:
        return 1.0

    contingency = pd.crosstab(labels_true, labels_pred).to_numpy(dtype=float)
    sum_comb = np.sum(contingency * (contingency - 1) / 2)
    row_sums = contingency.sum(axis=1)
    col_sums = contingency.sum(axis=0)
    sum_comb_rows = np.sum(row_sums * (row_sums - 1) / 2)
    sum_comb_cols = np.sum(col_sums * (col_sums - 1) / 2)
    total_pairs = n * (n - 1) / 2
    if total_pairs == 0:
        return 1.0
    expected_index = (sum_comb_rows * sum_comb_cols) / total_pairs
    max_index = 0.5 * (sum_comb_rows + sum_comb_cols)
    denominator = max_index - expected_index
    if denominator == 0:
        return 1.0
    return float((sum_comb - expected_index) / denominator)


def cluster_size_text(labels: np.ndarray) -> str:
    values, counts = np.unique(labels, return_counts=True)
    return "; ".join([f"C{int(value)}={int(count)}" for value, count in zip(values, counts)])


def load_pca_matrix(assignments: pd.DataFrame) -> tuple[pd.DataFrame, list[str], np.ndarray, np.ndarray]:
    pca_scores = read_required_csv(PCA90_PATH)
    pca_features = [column for column in pca_scores.columns if column not in METADATA_COLUMNS]
    matrix = assignments[["id_estudiante", "id_periodo", "cluster"]].merge(
        pca_scores[["id_estudiante", "id_periodo"] + pca_features],
        on=["id_estudiante", "id_periodo"],
        how="left",
        indicator=True,
    )
    if (matrix["_merge"] != "both").any():
        raise ValueError("Cluster assignments and PCA scores could not be fully joined.")
    matrix = matrix.drop(columns="_merge")
    x = matrix[pca_features].to_numpy(dtype=float)
    labels = matrix["cluster"].to_numpy(dtype=int)
    return matrix, pca_features, x, labels


def evaluate_stability(assignments: pd.DataFrame, metadata: dict[str, object]) -> pd.DataFrame:
    matrix, _, x, baseline_labels = load_pca_matrix(assignments)
    selected_k = int(metadata.get("selected_k", len(np.unique(baseline_labels))))
    records = []

    for seed in [7, 13, 21, 42, 99]:
        model = fit_kmeans(x, selected_k, n_init=10, seed=seed)
        labels = model["labels"]
        assert isinstance(labels, np.ndarray)
        records.append(
            {
                "validacion": "semilla",
                "detalle": f"seed={seed}",
                "n_registros": len(labels),
                "ari_vs_base": adjusted_rand_index(baseline_labels, labels),
                "distribucion_clusters": cluster_size_text(labels),
            }
        )

    for index, seed in enumerate([101, 202, 303, 404, 505], start=1):
        rng = np.random.default_rng(seed)
        sample_size = max(selected_k * 20, int(len(x) * 0.8))
        sample_indices = np.sort(rng.choice(len(x), size=sample_size, replace=False))
        model = fit_kmeans(x[sample_indices], selected_k, n_init=10, seed=RANDOM_SEED + index)
        centers = model["centers"]
        assert isinstance(centers, np.ndarray)
        labels = squared_distances(x, centers).argmin(axis=1)
        records.append(
            {
                "validacion": "submuestra_80",
                "detalle": f"seed={seed}",
                "n_registros": sample_size,
                "ari_vs_base": adjusted_rand_index(baseline_labels, labels),
                "distribucion_clusters": cluster_size_text(labels),
            }
        )

    for period, period_group in matrix.groupby("id_periodo"):
        if len(period_group) < max(30, selected_k * 10):
            continue
        period_x = period_group[[column for column in matrix.columns if column.startswith("PC")]].to_numpy(dtype=float)
        period_baseline = period_group["cluster"].to_numpy(dtype=int)
        model = fit_kmeans(period_x, selected_k, n_init=10, seed=RANDOM_SEED)
        labels = model["labels"]
        assert isinstance(labels, np.ndarray)
        records.append(
            {
                "validacion": "periodo",
                "detalle": str(period),
                "n_registros": len(period_group),
                "ari_vs_base": adjusted_rand_index(period_baseline, labels),
                "distribucion_clusters": cluster_size_text(labels),
            }
        )

    return pd.DataFrame(records)


def stability_summary(stability: pd.DataFrame) -> pd.DataFrame:
    if stability.empty:
        return pd.DataFrame()
    summary = (
        stability.groupby("validacion")
        .agg(
            pruebas=("ari_vs_base", "count"),
            ari_promedio=("ari_vs_base", "mean"),
            ari_minimo=("ari_vs_base", "min"),
            ari_maximo=("ari_vs_base", "max"),
        )
        .reset_index()
    )
    return summary


def stability_level(mean_ari: float) -> str:
    if mean_ari >= 0.85:
        return "Alta"
    if mean_ari >= 0.65:
        return "Aceptable"
    return "Baja"


def stability_notes(stability: pd.DataFrame) -> str:
    if stability.empty:
        return "- No se generaron pruebas de estabilidad."

    notes = []
    for validation_type, group in stability.groupby("validacion"):
        mean_ari = float(group["ari_vs_base"].mean())
        notes.append(f"- `{validation_type}`: estabilidad {stability_level(mean_ari).lower()} promedio (ARI medio {mean_ari:.4f}).")

    weak_cases = stability[stability["ari_vs_base"] < 0.65].sort_values("ari_vs_base")
    if not weak_cases.empty:
        worst = weak_cases.iloc[0]
        notes.append(
            "- Cautela: la prueba mas debil fue "
            f"`{worst['validacion']}` / `{worst['detalle']}` con ARI {float(worst['ari_vs_base']):.4f}; "
            "conviene revisar ese corte antes de usar el perfil como etiqueta estable."
        )

    return "\n".join(notes)


def build_report(
    profile_catalog: pd.DataFrame,
    differences: pd.DataFrame,
    outliers: pd.DataFrame,
    stability: pd.DataFrame,
    metadata: dict[str, object],
    centroids: pd.DataFrame,
) -> str:
    metrics = metadata.get("metrics", {})
    selected_k = metadata.get("selected_k", profile_catalog["cluster"].nunique())
    representation = metadata.get("selected_representation", "desconocida")
    stability_by_type = stability_summary(stability)
    stability_by_type["lectura"] = stability_by_type["ari_promedio"].apply(stability_level) if not stability_by_type.empty else []

    centroid_note = (
        "Los centroides persistidos pertenecen a la representacion PCA seleccionada; por eso la lectura academica "
        "se deriva tambien de medias de variables originales contra el promedio global."
    )

    top_differences = differences.copy()
    top_differences = top_differences.reindex(top_differences["diferencia_estandarizada"].abs().sort_values(ascending=False).index)

    return f"""
# Fase 7 - Interpretacion de perfiles academicos

## Objetivo

Traducir los clusters numericos del modelo K-Means a perfiles academicos comprensibles para tutores, coordinadores y analitica institucional.

## Modelo interpretado

- Algoritmo: K-Means.
- Representacion seleccionada: `{representation}`.
- K interpretado: {selected_k}.
- Silhouette: {float(metrics.get("silhouette", 0)):.5f}.
- Davies-Bouldin: {float(metrics.get("davies_bouldin", 0)):.5f}.
- Calinski-Harabasz: {float(metrics.get("calinski_harabasz", 0)):.5f}.

{centroid_note}

## Catalogo provisional de perfiles

{markdown_table(profile_catalog, max_rows=20)}

## Centroides del modelo

{markdown_table(centroids, max_rows=20)}

## Variables mas distintivas

{markdown_table(top_differences.head(20), max_rows=20)}

## Outliers candidatos

Se marcan como candidatos los registros en el percentil 95 o superior de distancia al centroide dentro de su propio cluster. Estos casos no son errores automaticamente; son trayectorias que conviene revisar con mayor contexto.

{markdown_table(outliers.head(20), max_rows=20)}

## Estabilidad

Se calculo estabilidad con Indice Rand Ajustado (ARI) contra las asignaciones base. El ARI es invariante al cambio de nombre de etiquetas entre clusters.

{stability_notes(stability)}

{markdown_table(stability_by_type, max_rows=20)}

Detalle de pruebas:

{markdown_table(stability, max_rows=30)}

## Reglas de lectura para tutores

- Usar el perfil como priorizacion de seguimiento, no como diagnostico automatico.
- Revisar primero estudiantes con prioridad tutorial alta o media-alta y baja pertenencia al cluster.
- Confirmar con informacion real de tutorias, asistencia e incidencias cuando exista, porque algunas senales actuales son estimadas desde cardex.
- En outliers, revisar la trayectoria individual antes de aplicar reglas generales del perfil.

## Reglas de lectura para coordinadores

- Interpretar K={selected_k} como segmentacion operativa amplia; no fuerza todavia los cuatro perfiles visibles del dashboard.
- Comparar distribucion por programa, cohorte y periodo antes de tomar decisiones institucionales.
- Usar perfiles para planeacion de acompanamiento, carga tutorial y analitica, no para sanciones academicas.
- Validar nombres y acciones con dominio academico antes de exponerlos como etiquetas definitivas.

## Limitaciones

- El dataset crudo activo no contiene asistencia real, tutorias reales ni incidencias institucionales reales.
- Las senales operativas estimadas mantienen el pipeline funcionando como prototipo local, pero deben reemplazarse por columnas institucionales cuando existan.
- La interpretacion depende de medias y diferencias contra el promedio global; no explica causalidad.

## Artefactos generados

- `data/reports/academic_profile_catalog.csv`
- `data/reports/cluster_feature_differences.csv`
- `data/reports/cluster_outlier_candidates.csv`
- `data/reports/cluster_stability_metrics.csv`
- `data/reports/profile_interpretation_report.md`
- `artifacts/academic_profile_catalog.json`
"""


def run_phase_7() -> None:
    ensure_dirs()
    assignments = read_required_csv(ASSIGNMENTS_PATH)
    selected_features = read_required_csv(SELECTED_FEATURES_PATH)
    centroids = read_required_csv(CENTROIDS_PATH)
    metadata = load_json(METADATA_PATH)

    features = feature_columns(selected_features)
    merged = merge_assignments_with_features(assignments, selected_features)
    differences = cluster_feature_differences(merged, features)
    profile_catalog = build_profile_catalog(merged, differences, features)
    outliers = identify_outliers(merged, profile_catalog)
    stability = evaluate_stability(assignments, metadata)

    profile_catalog.to_csv(PROFILE_CATALOG_PATH, index=False)
    differences.to_csv(FEATURE_DIFFERENCES_PATH, index=False)
    outliers.to_csv(OUTLIERS_PATH, index=False)
    stability.to_csv(STABILITY_PATH, index=False)
    PROFILE_CATALOG_JSON_PATH.write_text(
        json.dumps(profile_catalog.to_dict(orient="records"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = build_report(profile_catalog, differences, outliers, stability, metadata, centroids)
    write_markdown(INTERPRETATION_REPORT_PATH, report)

    print("Fase 7 completada.")
    print(f"Catalogo de perfiles: {PROFILE_CATALOG_PATH}")
    print(f"Reporte de interpretacion: {INTERPRETATION_REPORT_PATH}")
    print(f"Outliers candidatos: {OUTLIERS_PATH}")
    print(f"Metricas de estabilidad: {STABILITY_PATH}")


if __name__ == "__main__":
    run_phase_7()
