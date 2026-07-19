# Fase 8 - Persistencia del modelo

## Objetivo

Guardar los artefactos del pipeline de segmentacion academica en un formato local, versionado y verificable para ejecuciones posteriores.

## Version activa

- Version del modelo: `casei-kmeans-pca90-k2-68c23826aa1e`
- Fecha de registro UTC: `2026-07-13T01:57:40Z`
- Formato de almacenamiento: `local_filesystem_json_csv_markdown`
- Dataset fuente activo: `data/raw/dataset_crudo_2000_estudiantes.csv`
- Vista analitica alumno-periodo: `data/processed/student_period_features.csv`

## Modelo persistido

- Algoritmo: kmeans
- Implementacion: numpy
- Representacion seleccionada: `pca_90`
- K seleccionado: 2
- Silhouette: 0.34664
- Davies-Bouldin: 1.39579
- Calinski-Harabasz: 443.46799

## Artefactos incluidos

| role | bundle_path | required_for_load | bytes | sha256 |
| --- | --- | --- | --- | --- |
| preprocessing | preprocessing/scaler_params.csv | True | 1494 | f47447a28f8f |
| preprocessing | preprocessing/final_feature_list.csv | True | 547 | 8119ae4b1605 |
| pca | pca/pca_metadata.json | True | 1461 | feda91228021 |
| pca | pca/pca_components.csv | True | 13568 | 57ab284eb6da |
| kmeans | kmeans/kmeans_metadata.json | True | 866 | 1e16768f89cd |
| kmeans | kmeans/kmeans_centroids.csv | True | 567 | 08a867b845ac |
| profiles | profiles/academic_profile_catalog.json | True | 2552 | 2956e0666c9d |
| profiles | profiles/academic_profile_catalog.csv | True | 1733 | fc472f3763a2 |
| profiles | profiles/cluster_feature_differences.csv | True | 7462 | f3e3678169f5 |
| profiles | profiles/cluster_stability_metrics.csv | True | 1009 | 5a0c49012199 |
| evaluation | evaluation/k_selection_metrics.csv | True | 1603 | cf22e5e8e45e |
| evaluation | evaluation/cluster_summary.csv | True | 646 | 1536e1480352 |
| inference_snapshot | inference_snapshot/cluster_assignments.csv | True | 129839 | 4b30e27b435a |
| documentation | documentation/pca_report.md | False | 2655 | f934e4a714e5 |
| documentation | documentation/k_selection_report.md | False | 2771 | ba7e30c176f6 |
| documentation | documentation/kmeans_training_report.md | False | 1744 | b767edf01677 |
| documentation | documentation/profile_interpretation_report.md | False | 14378 | 9e2cfc52e076 |

## Verificacion de carga posterior

| check | passed | detail |
| --- | --- | --- |
| scaler_feature_count | True | 25 scaler rows vs 25 expected features |
| pca_input_columns | True | PCA component table contains all expected input features |
| kmeans_centroid_count | True | 2 centroids vs K=2 |
| kmeans_component_columns | True | Centroid table contains all selected representation columns |
| profile_catalog_count | True | 2 profiles vs K=2 |
| assignment_clusters | True | All assignment clusters exist in centroid table |

## Registro de versiones

| model_version | created_at_utc | selected_representation | selected_k | silhouette | davies_bouldin | calinski_harabasz | content_fingerprint_sha256 | bundle_dir | manifest_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| casei-kmeans-pca90-k2-68c23826aa1e | 2026-07-13T01:57:40Z | pca_90 | 2 | 0.34664 | 1.3958 | 443.47 | 68c23826aa1eb620a6bae8404a9cdb5674647a4db3304c1faa96876e3527d4b0 | artifacts/model_registry/casei-kmeans-pca90-k2-68c23826aa1e | artifacts/model_registry/casei-kmeans-pca90-k2-68c23826aa1e/manifest.json |

## Contrato de carga

- Punto de entrada de la version activa: `artifacts/current_model.json`
- Manifest de la version: `artifacts/model_registry/casei-kmeans-pca90-k2-68c23826aa1e/manifest.json`
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
