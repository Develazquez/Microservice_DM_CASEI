from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from typing import Any, Iterable

import numpy as np
import pandas as pd

from app.models.config import (
    ACTIVE_INFERENCE_METADATA,
    ACTIVE_INFERENCE_SNAPSHOT,
    STUDENT_PERIOD_DATASET,
)
from app.services.model_persistence_service import (
    load_persisted_model_bundle,
    validate_loaded_contract,
)


@dataclass(frozen=True)
class InferenceResult:
    model_version: str
    features: pd.DataFrame
    assignments: pd.DataFrame
    source_records: int
    inferred_records: int
    out_of_distribution_records: int

    def metadata(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "source_records": self.source_records,
            "inferred_records": self.inferred_records,
            "out_of_distribution_records": self.out_of_distribution_records,
        }


def infer_with_active_bundle(
    student_ids: Iterable[str] | None = None,
    dataset: pd.DataFrame | None = None,
    model_version: str | None = None,
) -> InferenceResult:
    loaded = load_persisted_model_bundle(model_version)
    checks = validate_loaded_contract(loaded)
    if not bool(checks["passed"].all()):
        failed = checks.loc[~checks["passed"], ["check", "detail"]]
        raise ValueError("El bundle no cumple el contrato de inferencia:\n" + failed.to_string(index=False))

    source = dataset.copy() if dataset is not None else pd.read_csv(STUDENT_PERIOD_DATASET)
    source_records = len(source)
    selected_ids = {str(value).strip().upper() for value in (student_ids or []) if str(value).strip()}
    if selected_ids:
        source = source[source["id_estudiante"].astype(str).str.strip().str.upper().isin(selected_ids)].copy()
    if source.empty:
        raise ValueError("No existen registros alumno-periodo para el alcance solicitado.")

    manifest = loaded["manifest"]
    input_features = list(manifest["preprocessing"]["input_features"])
    missing = sorted(set(input_features) - set(source.columns))
    if missing:
        raise ValueError("El dataset no cumple el contrato del modelo. Faltan variables: " + ", ".join(missing))

    scaler = loaded["scaler_params"].set_index("feature")
    missing_scaler = sorted(set(input_features) - set(scaler.index.astype(str)))
    if missing_scaler:
        raise ValueError("El escalador no contiene parametros para: " + ", ".join(missing_scaler))

    numeric = source[input_features].apply(pd.to_numeric, errors="coerce")
    means = scaler.loc[input_features, "mean"].astype(float)
    std_column = "std" if "std" in scaler.columns else "scale"
    stds = scaler.loc[input_features, std_column].astype(float).replace(0, 1)
    numeric = numeric.fillna(means.to_dict())
    scaled = (numeric - means) / stds

    representation_name = str(manifest["model"]["selected_representation"])
    representation_features = list(manifest["model"]["features"])
    all_pca = project_pca(scaled, loaded["pca_components"], input_features)
    if representation_name == "pca_90":
        missing_components = sorted(set(representation_features) - set(all_pca.columns))
        if missing_components:
            raise ValueError("El PCA no contiene componentes requeridos: " + ", ".join(missing_components))
        matrix = all_pca[representation_features].to_numpy(dtype=float)
    elif representation_name == "scaled_features":
        missing_scaled = sorted(set(representation_features) - set(scaled.columns))
        if missing_scaled:
            raise ValueError("La representacion escalada no contiene: " + ", ".join(missing_scaled))
        matrix = scaled[representation_features].to_numpy(dtype=float)
    else:
        raise ValueError(f"Representacion del bundle no soportada: {representation_name}")

    centroids_frame = loaded["kmeans_centroids"].sort_values("cluster").reset_index(drop=True)
    centroids = centroids_frame[representation_features].to_numpy(dtype=float)
    distances = np.sqrt(((matrix[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2))
    nearest_position = distances.argmin(axis=1)
    labels = centroids_frame.iloc[nearest_position]["cluster"].astype(int).to_numpy()
    assigned_distances = distances[np.arange(len(source)), nearest_position]

    training_assignments = loaded["cluster_assignments"]
    thresholds = (
        training_assignments.groupby("cluster")["distance_to_centroid"].quantile(0.95).astype(float).to_dict()
    )
    assigned_thresholds = np.array([thresholds.get(int(cluster), np.inf) for cluster in labels], dtype=float)

    assignments = source.copy().reset_index(drop=True)
    assignments["cluster"] = labels
    assignments["distance_to_centroid"] = assigned_distances
    assignments["membership_score"] = 1.0 / (1.0 + assigned_distances)
    assignments["out_of_distribution_threshold"] = assigned_thresholds
    assignments["is_out_of_distribution"] = assigned_distances > assigned_thresholds
    assignments["model_version"] = str(manifest["model_version"])
    if "PC1" in all_pca:
        assignments["PC1"] = all_pca["PC1"].to_numpy()
    if "PC2" in all_pca:
        assignments["PC2"] = all_pca["PC2"].to_numpy()

    profiles = pd.DataFrame(loaded["profile_catalog"])
    profile_columns = [
        column
        for column in [
            "cluster",
            "perfil_academico",
            "prioridad_tutorial",
            "lectura_funcional",
            "acciones_sugeridas",
            "cautela_interpretacion",
        ]
        if column in profiles.columns
    ]
    if profile_columns:
        assignments = assignments.merge(profiles[profile_columns], on="cluster", how="left")

    return InferenceResult(
        model_version=str(manifest["model_version"]),
        features=source.reset_index(drop=True),
        assignments=assignments,
        source_records=source_records,
        inferred_records=len(assignments),
        out_of_distribution_records=int(assignments["is_out_of_distribution"].sum()),
    )


def project_pca(
    scaled: pd.DataFrame,
    components_frame: pd.DataFrame,
    input_features: list[str],
) -> pd.DataFrame:
    components = components_frame.set_index("component")
    missing = sorted(set(input_features) - set(components.columns))
    if missing:
        raise ValueError("La matriz PCA no contiene variables de entrada: " + ", ".join(missing))
    scores = scaled[input_features].to_numpy(dtype=float) @ components[input_features].to_numpy(dtype=float).T
    return pd.DataFrame(scores, columns=components.index.astype(str), index=scaled.index)


def persist_active_inference_snapshot(result: InferenceResult) -> dict[str, Any]:
    ACTIVE_INFERENCE_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_INFERENCE_METADATA.parent.mkdir(parents=True, exist_ok=True)
    loaded = load_persisted_model_bundle(result.model_version)
    baseline = loaded["cluster_assignments"].copy()
    if ACTIVE_INFERENCE_SNAPSHOT.exists() and ACTIVE_INFERENCE_METADATA.exists():
        metadata = json.loads(ACTIVE_INFERENCE_METADATA.read_text(encoding="utf-8"))
        if metadata.get("model_version") == result.model_version:
            baseline = pd.read_csv(ACTIVE_INFERENCE_SNAPSHOT)

    keys = ["id_estudiante", "id_periodo"]
    replacements = result.assignments.copy()
    replacement_keys = set(map(tuple, replacements[keys].astype(str).to_numpy()))
    if not baseline.empty:
        keep = ~baseline[keys].astype(str).apply(tuple, axis=1).isin(replacement_keys)
        combined = pd.concat([baseline.loc[keep], replacements], ignore_index=True, sort=False)
    else:
        combined = replacements
    combined = combined.sort_values(keys).reset_index(drop=True)
    temporary = ACTIVE_INFERENCE_SNAPSHOT.with_suffix(".updating.csv")
    combined.to_csv(temporary, index=False)
    os.replace(temporary, ACTIVE_INFERENCE_SNAPSHOT)
    metadata = {
        "model_version": result.model_version,
        "updated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "records": int(len(combined)),
        "updated_records": int(len(replacements)),
    }
    ACTIVE_INFERENCE_METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata
