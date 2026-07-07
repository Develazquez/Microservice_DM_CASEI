# Academic Segmentation Service
Microservicio independiente en construccion para segmentacion academica no supervisada de estudiantes.

## Alcance actual

Este modulo contiene los entregables iniciales de analisis del pipeline:

- Fase 2: EDA del dataset academico crudo tipo cardex.
- Fase 3: seleccion de variables para clustering.
- Fase 4: PCA reproducible con numpy.
- Fase 5: seleccion de K con metricas internas.
- Fase 6: entrenamiento K-Means y asignacion de clusters.
- Fase 7: interpretacion de perfiles academicos, outliers candidatos y estabilidad.
- Fase 8: persistencia local del modelo en bundle versionado y verificable.
- Fase 9: API REST local con FastAPI y documentacion OpenAPI/Swagger.
- Fase 10: persistencia local de inferencias con historial por corrida y estudiante.
- Extra roadmap: motor de busqueda academica BM25 con metricas de recuperacion.

## Requisitos

```bash
pip install -r requirements.txt
```

Dependencias minimas:

- Python 3.10+
- pandas
- numpy
- fastapi
- uvicorn

## Dataset activo

El dataset crudo activo se toma desde:

```text
data/raw/dataset_crudo_2000_estudiantes.csv
```

Este archivo tiene estructura tipo cardex/sabana y se transforma a una vista analitica alumno-periodo en:

```text
data/processed/student_period_features.csv
```

Los datasets sinteticos anteriores se conservan solo como evidencia historica y no deben usarse como fuente principal.

Nota: el dataset crudo actual no contiene asistencia real, tutorias reales ni incidencias institucionales reales. Para mantener el prototipo local funcionando, algunas senales operativas se estiman desde calificaciones, creditos, reprobadas, estatus y rezago.


## Ejecucion

Desde la raiz de este repositorio/carpeta:

```bash
python scripts/run_phase_2_4.py
python scripts/run_phase_5_6.py
python scripts/run_phase_7.py
python scripts/run_phase_8.py
python scripts/run_phase_10.py
python scripts/run_search_engine.py
```

Para levantar la API local:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Tambien existe el entrypoint local:

```bash
python scripts/run_api.py
```

## Arquitectura MVC

```text
app/
├── controllers/   # Orquestan casos de uso ejecutados por scripts o futura API
├── models/        # Configuracion, rutas y constantes del dominio
├── services/      # Logica de EDA, PCA, K-Means, perfiles y busqueda BM25
├── views/         # Utilidades de reporte Markdown y visualizacion
└── utils/         # Utilidades compartidas futuras
scripts/           # Entrypoints CLI delgados
data/              # Dataset, procesados, reportes y figuras
artifacts/         # Parametros, centroides y metadata de modelos
```

Flujo actual:

```text
scripts -> controllers -> services -> data/artifacts/reports
```

## Salidas principales

```text
data/reports/eda_report.md
data/reports/feature_selection.md
data/reports/pca_report.md
data/reports/k_selection_report.md
data/reports/k_selection_metrics.csv
data/reports/kmeans_training_report.md
data/reports/cluster_summary.csv
data/reports/profile_interpretation_report.md
data/reports/academic_profile_catalog.csv
data/reports/cluster_feature_differences.csv
data/reports/cluster_outlier_candidates.csv
data/reports/cluster_stability_metrics.csv
data/reports/model_persistence_report.md
data/reports/fastapi_service_report.md
data/reports/inference_persistence_report.md
data/reports/api_execution_history.jsonl
data/reports/search_engine_report.md
data/reports/search_metrics.csv
data/reports/search_results_sample.csv
data/storage/segmentation_inference_history.sqlite
data/storage/segmentation_inference_schema.sql
data/processed/student_period_features.csv
data/processed/selected_features.csv
data/processed/scaled_features.csv
data/processed/pca_scores.csv
data/processed/pca_scores_90.csv
data/processed/pca_scores_95.csv
data/processed/cluster_assignments.csv
artifacts/pca_metadata.json
artifacts/pca_components.csv
artifacts/scaler_params.csv
artifacts/kmeans_metadata.json
artifacts/kmeans_centroids.csv
artifacts/academic_profile_catalog.json
artifacts/current_model.json
artifacts/model_registry/registry_index.csv
artifacts/model_registry/execution_metadata_schema.json
artifacts/model_registry/<model_version>/manifest.json
```

## API REST local

La Fase 9 expone los artefactos locales versionados por FastAPI. Swagger queda disponible en:

```text
http://127.0.0.1:8000/docs
```

Endpoints principales:

```text
GET  /health
POST /api/v1/segmentation/run
GET  /api/v1/segmentation/summary
GET  /api/v1/segmentation/students
GET  /api/v1/segmentation/students/{id}
GET  /api/v1/segmentation/students/{id}/history
GET  /api/v1/segmentation/search
GET  /api/v1/segmentation/clusters
GET  /api/v1/segmentation/history
GET  /api/v1/segmentation/history/{execution_id}
```

`POST /api/v1/segmentation/run` acepta dos modos:

- `load_existing`: valida y carga el bundle activo registrado en `artifacts/current_model.json`.
- `retrain_local`: regenera fases 2-8 usando el dataset crudo local activo.

La API no usa Supabase Storage como fuente actual. Solo lee archivos locales y el bundle versionado de Fase 8.

## Historial de inferencias

La Fase 10 persiste cada corrida exitosa de inferencia en SQLite:

```text
data/storage/segmentation_inference_history.sqlite
```

Tablas principales:

- `inference_runs`: una fila por corrida identificable.
- `student_inferences`: asignaciones por estudiante-periodo asociadas a `execution_id`.

Cada registro conserva version del modelo, representacion, K, fechas UTC, parametros, metricas, cluster, perfil, score de pertenencia y senales academicas clave.

## Persistencia del modelo

La Fase 8 registra la version activa del modelo en:

```text
artifacts/current_model.json
```

Ese puntero carga el bundle local versionado ubicado en:

```text
artifacts/model_registry/<model_version>/
```

El bundle conserva parametros de escalamiento, componentes PCA, centroides K-Means, catalogo de perfiles, metricas, snapshot local de asignaciones y hashes SHA-256 para validar integridad antes de usarlo en una corrida posterior.

## Decision tecnica

La version actual usa pandas y numpy para evitar depender de paquetes externos no disponibles en el runtime local. El pipeline parte del cardex crudo, genera una vista alumno-periodo, entrena K-Means sobre `pca_90` y produce una lectura academica provisional de los clusters.

Los perfiles son apoyo tutorial y analitico, no diagnostico automatico definitivo. La API REST local carga el bundle versionado y conserva la web desacoplada del microservicio.
