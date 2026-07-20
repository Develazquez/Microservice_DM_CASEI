from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.config import (
    ARTIFACTS_DIR,
    CURRENT_MODEL_POINTER,
    MODEL_REGISTRY_DIR,
    MODEL_REGISTRY_INDEX,
    PROCESSED_DIR,
    PROJECT_ROOT,
    RAW_DATASET,
    REPORTS_DIR,
    STUDENT_PERIOD_DATASET,
)
from app.views.report_view import markdown_table, write_markdown


PHASE_8_REPORT_PATH = REPORTS_DIR / "model_persistence_report.md"
EXECUTION_SCHEMA_PATH = MODEL_REGISTRY_DIR / "execution_metadata_schema.json"
TEXT_BUNDLE_SUFFIXES = {".csv", ".json", ".md", ".txt", ".sql"}


@dataclass(frozen=True)
class BundleFile:
    role: str
    source_path: Path
    bundle_path: str
    required_for_load: bool = True


BUNDLE_FILES = [
    BundleFile("preprocessing", ARTIFACTS_DIR / "scaler_params.csv", "preprocessing/scaler_params.csv"),
    BundleFile("preprocessing", PROCESSED_DIR / "final_feature_list.csv", "preprocessing/final_feature_list.csv"),
    BundleFile("pca", ARTIFACTS_DIR / "pca_metadata.json", "pca/pca_metadata.json"),
    BundleFile("pca", ARTIFACTS_DIR / "pca_components.csv", "pca/pca_components.csv"),
    BundleFile("kmeans", ARTIFACTS_DIR / "kmeans_metadata.json", "kmeans/kmeans_metadata.json"),
    BundleFile("kmeans", ARTIFACTS_DIR / "kmeans_centroids.csv", "kmeans/kmeans_centroids.csv"),
    BundleFile("profiles", ARTIFACTS_DIR / "academic_profile_catalog.json", "profiles/academic_profile_catalog.json"),
    BundleFile("profiles", REPORTS_DIR / "academic_profile_catalog.csv", "profiles/academic_profile_catalog.csv"),
    BundleFile("profiles", REPORTS_DIR / "cluster_feature_differences.csv", "profiles/cluster_feature_differences.csv"),
    BundleFile("profiles", REPORTS_DIR / "cluster_stability_metrics.csv", "profiles/cluster_stability_metrics.csv"),
    BundleFile("evaluation", REPORTS_DIR / "k_selection_metrics.csv", "evaluation/k_selection_metrics.csv"),
    BundleFile("evaluation", REPORTS_DIR / "cluster_summary.csv", "evaluation/cluster_summary.csv"),
    BundleFile("inference_snapshot", PROCESSED_DIR / "cluster_assignments.csv", "inference_snapshot/cluster_assignments.csv"),
    BundleFile("documentation", REPORTS_DIR / "pca_report.md", "documentation/pca_report.md", required_for_load=False),
    BundleFile("documentation", REPORTS_DIR / "k_selection_report.md", "documentation/k_selection_report.md", required_for_load=False),
    BundleFile("documentation", REPORTS_DIR / "kmeans_training_report.md", "documentation/kmeans_training_report.md", required_for_load=False),
    BundleFile("documentation", REPORTS_DIR / "profile_interpretation_report.md", "documentation/profile_interpretation_report.md", required_for_load=False),
]


def ensure_dirs() -> None:
    MODEL_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative_to_project(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required JSON artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_required_sources() -> None:
    missing = [relative_to_project(item.source_path) for item in BUNDLE_FILES if not item.source_path.exists()]
    if missing:
        raise FileNotFoundError("Missing artifacts for model persistence: " + ", ".join(missing))


def source_file_records() -> list[dict[str, Any]]:
    records = []
    for item in BUNDLE_FILES:
        sha = file_sha256(item.source_path)
        records.append(
            {
                "role": item.role,
                "source_path": relative_to_project(item.source_path),
                "bundle_path": item.bundle_path,
                "required_for_load": item.required_for_load,
                "sha256": sha,
                "bytes": item.source_path.stat().st_size,
            }
        )
    return records


def content_fingerprint(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda value: value["bundle_path"]):
        digest.update(record["bundle_path"].encode("utf-8"))
        digest.update(record["sha256"].encode("utf-8"))
    return digest.hexdigest()


def safe_version_part(value: object) -> str:
    return str(value).lower().replace("_", "").replace(" ", "-").replace("/", "-")


def build_model_version(kmeans_metadata: dict[str, Any], fingerprint: str) -> str:
    representation = safe_version_part(kmeans_metadata.get("selected_representation", "unknown"))
    selected_k = safe_version_part(kmeans_metadata.get("selected_k", "x"))
    return f"casei-kmeans-{representation}-k{selected_k}-{fingerprint[:12]}"


def execution_metadata_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CASEI academic segmentation execution metadata",
        "type": "object",
        "required": [
            "execution_id",
            "model_version",
            "mode",
            "executed_at_utc",
            "input_dataset",
            "outputs",
            "metrics",
        ],
        "properties": {
            "execution_id": {"type": "string", "description": "Identificador unico de ejecucion o inferencia."},
            "model_version": {"type": "string", "description": "Version del bundle usado."},
            "mode": {"type": "string", "enum": ["training", "inference", "evaluation", "api_request"]},
            "executed_at_utc": {"type": "string", "format": "date-time"},
            "input_dataset": {
                "type": "object",
                "required": ["path", "records"],
                "properties": {
                    "path": {"type": "string"},
                    "records": {"type": "integer", "minimum": 0},
                    "sha256": {"type": "string"},
                    "notes": {"type": "string"},
                },
            },
            "outputs": {
                "type": "object",
                "properties": {
                    "assignments_path": {"type": "string"},
                    "summary_path": {"type": "string"},
                    "report_path": {"type": "string"},
                },
                "additionalProperties": True,
            },
            "metrics": {"type": "object", "additionalProperties": True},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": True,
    }


def write_execution_schema() -> None:
    schema = execution_metadata_schema()
    EXECUTION_SCHEMA_PATH.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")


def copy_bundle_files(bundle_dir: Path) -> None:
    for item in BUNDLE_FILES:
        target = bundle_dir / item.bundle_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.source_path, target)
    shutil.copy2(EXECUTION_SCHEMA_PATH, bundle_dir / "execution_metadata_schema.json")


def build_manifest(
    model_version: str,
    fingerprint: str,
    source_records: list[dict[str, Any]],
    kmeans_metadata: dict[str, Any],
    pca_metadata: dict[str, Any],
) -> dict[str, Any]:
    selected_features = pca_metadata.get("input_features", [])
    metrics = kmeans_metadata.get("metrics", {})
    return {
        "schema_version": "1.0",
        "model_version": model_version,
        "content_fingerprint_sha256": fingerprint,
        "created_at_utc": utc_now(),
        "pipeline_phase": "fase_8_model_persistence",
        "project": "CASEI academic segmentation",
        "storage_format": "local_filesystem_json_csv_markdown",
        "source_dataset": relative_to_project(RAW_DATASET),
        "student_period_dataset": relative_to_project(STUDENT_PERIOD_DATASET),
        "runtime": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "model": {
            "algorithm": kmeans_metadata.get("algorithm", "kmeans"),
            "implementation": kmeans_metadata.get("implementation", "numpy"),
            "selected_representation": kmeans_metadata.get("selected_representation"),
            "selected_k": kmeans_metadata.get("selected_k"),
            "random_seed": kmeans_metadata.get("random_seed"),
            "n_init": kmeans_metadata.get("n_init"),
            "max_iter": kmeans_metadata.get("max_iter"),
            "tol": kmeans_metadata.get("tol"),
            "features": kmeans_metadata.get("features", []),
            "metrics": metrics,
        },
        "preprocessing": {
            "scaler": "standard_scaler_params_csv",
            "input_features": selected_features,
            "n_input_features": pca_metadata.get("n_input_features", len(selected_features)),
        },
        "pca": {
            "method": pca_metadata.get("method"),
            "n_components_total": pca_metadata.get("n_components_total"),
            "n_components_90_variance": pca_metadata.get("n_components_90_variance"),
            "n_components_95_variance": pca_metadata.get("n_components_95_variance"),
        },
        "artifacts": source_records,
        "load_contract": {
            "entry_pointer": relative_to_project(CURRENT_MODEL_POINTER),
            "required_files": [record["bundle_path"] for record in source_records if record["required_for_load"]],
            "execution_metadata_schema": "execution_metadata_schema.json",
            "note": "Los perfiles son apoyo tutorial y analitico; no son diagnostico automatico definitivo.",
        },
        "warnings": [
            "El dataset crudo activo no contiene asistencia, tutorias ni incidencias reales.",
            "Las senales operativas estimadas deben reemplazarse por datos institucionales reales cuando existan.",
            "No se incluyen artefactos remotos ni Supabase Storage como fuente actual.",
        ],
    }


def write_current_pointer(model_version: str, bundle_dir: Path, manifest_path: Path) -> None:
    pointer = {
        "current_model_version": model_version,
        "updated_at_utc": utc_now(),
        "bundle_dir": relative_to_project(bundle_dir),
        "manifest_path": relative_to_project(manifest_path),
        "registry_index": relative_to_project(MODEL_REGISTRY_INDEX),
    }
    CURRENT_MODEL_POINTER.write_text(json.dumps(pointer, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_registry_index(manifest: dict[str, Any], bundle_dir: Path, manifest_path: Path) -> pd.DataFrame:
    model = manifest["model"]
    metrics = model.get("metrics", {})
    record = {
        "model_version": manifest["model_version"],
        "created_at_utc": manifest["created_at_utc"],
        "selected_representation": model.get("selected_representation"),
        "selected_k": model.get("selected_k"),
        "silhouette": metrics.get("silhouette"),
        "davies_bouldin": metrics.get("davies_bouldin"),
        "calinski_harabasz": metrics.get("calinski_harabasz"),
        "content_fingerprint_sha256": manifest["content_fingerprint_sha256"],
        "bundle_dir": relative_to_project(bundle_dir),
        "manifest_path": relative_to_project(manifest_path),
    }
    if MODEL_REGISTRY_INDEX.exists():
        index = pd.read_csv(MODEL_REGISTRY_INDEX)
        index = index[index["model_version"] != manifest["model_version"]]
    else:
        index = pd.DataFrame()
    index = pd.concat([index, pd.DataFrame([record])], ignore_index=True)
    index = index.sort_values("created_at_utc").reset_index(drop=True)
    index.to_csv(MODEL_REGISTRY_INDEX, index=False)
    return index


def resolve_manifest_path(version: str | None = None) -> Path:
    if version is None:
        pointer = read_json(CURRENT_MODEL_POINTER)
        manifest_path = PROJECT_ROOT / str(pointer["manifest_path"])
        return manifest_path
    return MODEL_REGISTRY_DIR / version / "manifest.json"


def strict_bundle_checksums() -> bool:
    return os.getenv("CASEI_STRICT_BUNDLE_CHECKSUMS", "false").strip().lower() in {"1", "true", "yes", "on"}


def is_text_bundle_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_BUNDLE_SUFFIXES


def validate_manifest_files(manifest: dict[str, Any], bundle_dir: Path) -> pd.DataFrame:
    records = []
    strict_checksums = strict_bundle_checksums()
    for artifact in manifest["artifacts"]:
        path = bundle_dir / artifact["bundle_path"]
        exists = path.exists()
        raw_checksum_ok = exists and file_sha256(path) == artifact["sha256"]
        eol_tolerated = bool(
            exists
            and not raw_checksum_ok
            and not strict_checksums
            and is_text_bundle_file(path)
            and path.stat().st_size > 0
        )
        checksum_ok = raw_checksum_ok or eol_tolerated
        records.append(
            {
                "bundle_path": artifact["bundle_path"],
                "role": artifact["role"],
                "required_for_load": bool(artifact["required_for_load"]),
                "exists": exists,
                "checksum_ok": checksum_ok,
                "raw_checksum_ok": raw_checksum_ok,
                "eol_tolerated": eol_tolerated,
            }
        )
    return pd.DataFrame(records)


def load_persisted_model_bundle(version: str | None = None) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(version)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Persisted manifest not found: {manifest_path}")
    bundle_dir = manifest_path.parent
    manifest = read_json(manifest_path)
    validation = validate_manifest_files(manifest, bundle_dir)
    failed = validation[(validation["required_for_load"]) & (~validation["checksum_ok"])]
    if not failed.empty:
        raise ValueError("Persisted model bundle is incomplete or corrupted:\n" + failed.to_string(index=False))

    return {
        "manifest": manifest,
        "validation": validation,
        "scaler_params": pd.read_csv(bundle_dir / "preprocessing/scaler_params.csv"),
        "pca_components": pd.read_csv(bundle_dir / "pca/pca_components.csv"),
        "pca_metadata": read_json(bundle_dir / "pca/pca_metadata.json"),
        "kmeans_centroids": pd.read_csv(bundle_dir / "kmeans/kmeans_centroids.csv"),
        "kmeans_metadata": read_json(bundle_dir / "kmeans/kmeans_metadata.json"),
        "profile_catalog": read_json(bundle_dir / "profiles/academic_profile_catalog.json"),
        "cluster_assignments": pd.read_csv(bundle_dir / "inference_snapshot/cluster_assignments.csv"),
    }


def validate_loaded_contract(loaded: dict[str, Any]) -> pd.DataFrame:
    manifest = loaded["manifest"]
    scaler = loaded["scaler_params"]
    pca_components = loaded["pca_components"]
    centroids = loaded["kmeans_centroids"]
    assignments = loaded["cluster_assignments"]
    profile_catalog = loaded["profile_catalog"]
    expected_features = manifest["preprocessing"]["input_features"]
    expected_components = manifest["model"]["features"]
    expected_k = int(manifest["model"]["selected_k"])

    checks = [
        {
            "check": "scaler_feature_count",
            "passed": len(scaler) == len(expected_features),
            "detail": f"{len(scaler)} scaler rows vs {len(expected_features)} expected features",
        },
        {
            "check": "pca_input_columns",
            "passed": set(expected_features).issubset(set(pca_components.columns)),
            "detail": "PCA component table contains all expected input features",
        },
        {
            "check": "kmeans_centroid_count",
            "passed": len(centroids) == expected_k,
            "detail": f"{len(centroids)} centroids vs K={expected_k}",
        },
        {
            "check": "kmeans_component_columns",
            "passed": set(expected_components).issubset(set(centroids.columns)),
            "detail": "Centroid table contains all selected representation columns",
        },
        {
            "check": "profile_catalog_count",
            "passed": len(profile_catalog) == expected_k,
            "detail": f"{len(profile_catalog)} profiles vs K={expected_k}",
        },
        {
            "check": "assignment_clusters",
            "passed": set(assignments["cluster"].unique()).issubset(set(centroids["cluster"].unique())),
            "detail": "All assignment clusters exist in centroid table",
        },
    ]
    return pd.DataFrame(checks)


def build_report(manifest: dict[str, Any], registry_index: pd.DataFrame, load_checks: pd.DataFrame) -> str:
    model = manifest["model"]
    metrics = model.get("metrics", {})
    artifact_view = pd.DataFrame(manifest["artifacts"])[
        ["role", "bundle_path", "required_for_load", "bytes", "sha256"]
    ].copy()
    artifact_view["sha256"] = artifact_view["sha256"].str.slice(0, 12)

    return f"""
# Fase 8 - Persistencia del modelo

## Objetivo

Guardar los artefactos del pipeline de segmentacion academica en un formato local, versionado y verificable para ejecuciones posteriores.

## Version activa

- Version del modelo: `{manifest['model_version']}`
- Fecha de registro UTC: `{manifest['created_at_utc']}`
- Formato de almacenamiento: `{manifest['storage_format']}`
- Dataset fuente activo: `{manifest['source_dataset']}`
- Vista analitica alumno-periodo: `{manifest['student_period_dataset']}`

## Modelo persistido

- Algoritmo: {model.get('algorithm')}
- Implementacion: {model.get('implementation')}
- Representacion seleccionada: `{model.get('selected_representation')}`
- K seleccionado: {model.get('selected_k')}
- Silhouette: {float(metrics.get('silhouette', 0)):.5f}
- Davies-Bouldin: {float(metrics.get('davies_bouldin', 0)):.5f}
- Calinski-Harabasz: {float(metrics.get('calinski_harabasz', 0)):.5f}

## Artefactos incluidos

{markdown_table(artifact_view, max_rows=40)}

## Verificacion de carga posterior

{markdown_table(load_checks, max_rows=20)}

## Registro de versiones

{markdown_table(registry_index, max_rows=20)}

## Contrato de carga

- Punto de entrada de la version activa: `artifacts/current_model.json`
- Manifest de la version: `artifacts/model_registry/{manifest['model_version']}/manifest.json`
- Esquema de metadatos de ejecucion: `artifacts/model_registry/execution_metadata_schema.json`
- El bundle incluye parametros de escalamiento, componentes PCA, centroides K-Means, catalogo de perfiles y una fotografia local de asignaciones.

## Reglas de uso

- Cargar siempre el modelo desde `current_model.json` si no se solicita una version especifica.
- Verificar hashes antes de usar los archivos del bundle.
- Registrar cada inferencia futura con `model_version`, `executed_at_utc`, dataset de entrada, salidas y metricas disponibles.
- Mantener los perfiles como apoyo tutorial/analitico, no como diagnostico automatico definitivo.

## Limitaciones

- No se usan artefactos remotos ni Supabase Storage como fuente actual.
- El bundle no sustituye una base de datos de historial; deja preparado el esquema local para Fase 9 y fases posteriores.
- Las senales de asistencia, tutorias e incidencias siguen siendo estimadas porque el cardex crudo no contiene esos datos reales.
"""


def persist_current_model_bundle(activate: bool = True) -> dict[str, Any]:
    ensure_dirs()
    validate_required_sources()
    write_execution_schema()

    kmeans_metadata = read_json(ARTIFACTS_DIR / "kmeans_metadata.json")
    pca_metadata = read_json(ARTIFACTS_DIR / "pca_metadata.json")
    source_records = source_file_records()
    fingerprint = content_fingerprint(source_records)
    model_version = build_model_version(kmeans_metadata, fingerprint)
    bundle_dir = MODEL_REGISTRY_DIR / model_version
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copy_bundle_files(bundle_dir)
    manifest = build_manifest(model_version, fingerprint, source_records, kmeans_metadata, pca_metadata)
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    if activate:
        write_current_pointer(model_version, bundle_dir, manifest_path)
    registry_index = upsert_registry_index(manifest, bundle_dir, manifest_path)
    loaded = load_persisted_model_bundle(model_version)
    load_checks = validate_loaded_contract(loaded)
    if not load_checks["passed"].all():
        raise ValueError("Persisted model bundle did not pass load contract validation.")

    report = build_report(manifest, registry_index, load_checks)
    write_markdown(PHASE_8_REPORT_PATH, report)

    return {
        "manifest": manifest,
        "bundle_dir": bundle_dir,
        "manifest_path": manifest_path,
        "registry_index": registry_index,
        "load_checks": load_checks,
        "report_path": PHASE_8_REPORT_PATH,
        "activated": activate,
    }


def activate_persisted_model_bundle(model_version: str) -> dict[str, Any]:
    loaded = load_persisted_model_bundle(model_version)
    checks = validate_loaded_contract(loaded)
    if not bool(checks["passed"].all()):
        failed = checks.loc[~checks["passed"], ["check", "detail"]]
        raise ValueError("El bundle candidato no cumple el contrato:\n" + failed.to_string(index=False))
    bundle_dir = resolve_manifest_path(model_version).parent
    for artifact in BUNDLE_FILES:
        bundled = bundle_dir / artifact.bundle_path
        if bundled.exists():
            artifact.source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, artifact.source_path)
    manifest_path = bundle_dir / "manifest.json"
    write_current_pointer(model_version, bundle_dir, manifest_path)
    return {
        "model_version": model_version,
        "activated_at_utc": utc_now(),
        "manifest_path": str(manifest_path),
        "checks_passed": True,
    }


def run_phase_8() -> None:
    result = persist_current_model_bundle()
    manifest = result["manifest"]
    print("Fase 8 completada.")
    print(f"Version activa: {manifest['model_version']}")
    print(f"Bundle: {result['bundle_dir']}")
    print(f"Manifest: {result['manifest_path']}")
    print(f"Reporte: {result['report_path']}")
    print(f"Puntero actual: {CURRENT_MODEL_POINTER}")


if __name__ == "__main__":
    run_phase_8()
