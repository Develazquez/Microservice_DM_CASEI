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

- Corridas registradas: 2
- Inferencias estudiante-periodo registradas: 2554
- Estudiantes con historial: 387

## Ultima corrida registrada

| execution_id | run_type | status | model_version | selected_representation | selected_k | started_at_utc | finished_at_utc | duration_seconds | dataset_path | dataset_records | assignments_count | students_count | notes | created_at_utc | parameters | metrics |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5b27ab78-0573-46b7-a6b0-0d065fb15d8b | api_load_existing | completed | casei-kmeans-pca90-k2-68c23826aa1e | pca_90 | 2 | 2026-07-06T06:15:52Z | 2026-07-06T06:15:52Z | 0.424 | data/processed/student_period_features.csv | 1277 | 1277 | 387 | phase 10 persistence smoke test | 2026-07-06T06:15:52Z | {'mode': 'load_existing', 'persist_model': True, 'refresh_search_index': False, 'steps': ['load_current_model']} | {'inertia': 21596.523310054, 'silhouette': 0.3466360623521399, 'calinski_harabasz': 443.46798797095164, 'davies_bouldin': 1.3957850999644126, 'min_cluster_size': 244, 'max_cluster_size': 1033} |

## Consulta historica

La API expone:

- `GET /api/v1/segmentation/history`
- `GET /api/v1/segmentation/history/{execution_id}`
- `GET /api/v1/segmentation/students/{id}/history`

## Verificacion HTTP

- `GET /api/v1/segmentation/history` respondio 2 corridas y 2,554 inferencias persistidas.
- `GET /api/v1/segmentation/history/{execution_id}?limit=2` respondio 1,277 inferencias totales para la corrida consultada.
- `GET /api/v1/segmentation/students/IAG20200007/history` respondio 6 registros historicos, equivalentes a 3 periodos en 2 corridas.
- Swagger sigue disponible en `http://127.0.0.1:8000/docs`.

## Reglas de trazabilidad

- Cada corrida queda identificada por `execution_id`.
- Cada inferencia queda asociada a `execution_id`, `id_estudiante`, `id_periodo`, cluster, perfil y version de modelo.
- Se registra `model_version`, representacion, K, fechas UTC, parametros y metricas.
- Los perfiles siguen siendo apoyo tutorial/analitico, no diagnostico automatico definitivo.
