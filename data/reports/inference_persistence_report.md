# Fase 10 - Persistencia de inferencias

## Objetivo

Guardar cada corrida de inferencia y conservar trazabilidad por estudiante, periodo, version de modelo y parametros de ejecucion.

## Almacenamiento local

- Motor: SQLite (`sqlite3`, libreria estandar de Python).
- Base local: `data/storage/segmentation_inference_history.sqlite`
- Esquema SQL: `data/storage/segmentation_inference_schema.sql`

## Esquema

| tabla | proposito | llave |
| --- | --- | --- |
| inference_runs | Una fila por corrida identificable de inferencia/segmentacion. | execution_id |
| student_inferences | Asignaciones cluster por estudiante-periodo para cada corrida. | id autoincremental; unique(execution_id, id_estudiante, id_periodo) |

## Estado actual

- Corridas registradas: 3
- Inferencias estudiante-periodo registradas: 3553
- Estudiantes con historial: 387

## Ultima corrida registrada

| execution_id | run_type | status | model_version | selected_representation | selected_k | started_at_utc | finished_at_utc | duration_seconds | dataset_path | dataset_records | assignments_count | students_count | notes | created_at_utc | parameters | metrics |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 506ce975-2311-46a7-9104-ec2cde2f2efe | phase_10_snapshot | completed | casei-kmeans-pca90-k2-b0c92e1bd722 | pca_90 | 2 | 2026-07-19T16:57:26Z | 2026-07-19T16:57:26Z | 0.032 | data/processed/student_period_features.csv | 999 | 999 | 387 | Snapshot inicial de persistencia formal de inferencias. | 2026-07-19T16:57:26Z | {'source': 'current_model_bundle', 'phase': 10} | {'inertia': 17361.098914344308, 'silhouette': 0.3255789062232767, 'calinski_harabasz': 310.1769170943589, 'davies_bouldin': 1.4632741329176733, 'min_cluster_size': 187, 'max_cluster_size': 812} |

## Consulta historica

La API expone:

- `GET /cacei/segmentation/history`
- `GET /cacei/segmentation/history/{execution_id}`
- `GET /cacei/segmentation/students/{id}/history`

## Reglas de trazabilidad

- Cada corrida queda identificada por `execution_id`.
- Cada inferencia queda asociada a `execution_id`, `id_estudiante`, `id_periodo`, cluster, perfil y version de modelo.
- Se registra `model_version`, representacion, K, fechas UTC, parametros y metricas.
- Los perfiles siguen siendo apoyo tutorial/analitico, no diagnostico automatico definitivo.
