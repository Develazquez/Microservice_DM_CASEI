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
- Fase 11: documentacion formal Swagger/OpenAPI con modelos request/response.
- Fase 12: suite automatizada de pruebas unitarias, integracion, endpoints, datos y regresion.
- Fase 15: contrato de contexto controlado para futura integracion con LLM/RAG.
- Integracion Supabase inicial: repositorios y sincronizacion preliminar desde Supabase PostgreSQL.
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

Para ejecutar pruebas:

```bash
python -m unittest discover -s tests -v
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
docs/openapi_casei_segmentation.json
docs/openapi_reference.md
docs/testing_reference.md
docs/CONTRATO_CONTEXTO_LLM_RAG.md
docs/DISENO_MICROSERVICIO_CLUSTERING_ACADEMICO.md
docs/GUIA_USO_MICROSERVICIO_CLUSTERING_ACADEMICO.md
docs/BITACORA_DECISIONES_DISENO.md
tests/
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
POST /cacei/segmentation/run
GET  /cacei/segmentation/summary
GET  /cacei/segmentation/context/contract
GET  /cacei/segmentation/sync/status
POST /cacei/segmentation/sync/from-supabase
GET  /cacei/segmentation/students
GET  /cacei/segmentation/students/{id}
GET  /cacei/segmentation/students/{id}/llm-context
GET  /cacei/segmentation/students/{id}/history
GET  /cacei/segmentation/search
GET  /cacei/segmentation/rag/documents
GET  /cacei/segmentation/clusters
GET  /cacei/segmentation/history
GET  /cacei/segmentation/history/{execution_id}
```

`POST /cacei/segmentation/run` acepta dos modos:

- `load_existing`: valida y carga el bundle activo registrado en `artifacts/current_model.json`.
- `retrain_local`: regenera fases 2-8 usando el dataset crudo local activo.

La API no usa Supabase Storage como fuente actual. Solo lee archivos locales y el bundle versionado de Fase 8.

La especificacion OpenAPI exportada queda en:

```text
docs/openapi_casei_segmentation.json
```

La referencia tecnica resumida queda en:

```text
docs/openapi_reference.md
```

## Documentacion tecnica final

La Fase 13 concentra la documentacion tecnica y operativa en:

```text
docs/DISENO_MICROSERVICIO_CLUSTERING_ACADEMICO.md
docs/GUIA_USO_MICROSERVICIO_CLUSTERING_ACADEMICO.md
docs/BITACORA_DECISIONES_DISENO.md
```

La preparacion LLM/RAG queda documentada en:

```text
docs/CONTRATO_CONTEXTO_LLM_RAG.md
```

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

## Despliegue en Vercel

El microservicio incluye compatibilidad basica para Vercel mediante:

```text
api/index.py
vercel.json
```

`api/index.py` expone la aplicacion ASGI de FastAPI y `vercel.json` redirige las rutas publicas hacia esa funcion serverless.

Variables recomendadas en Vercel para la API:

```text
CASEI_API_PUBLIC_URL=https://<tu-api>.vercel.app
CASEI_WEB_URL=https://<tu-web>.vercel.app
CASEI_CORS_ORIGINS=https://<tu-web>.vercel.app,http://localhost:3000
CASEI_DB_MODE=local
```

Si se habilita lectura/escritura directa contra Supabase PostgreSQL desde la API, agregar tambien:

```text
CASEI_DB_MODE=supabase
CASEI_SUPABASE_URL=<url-del-proyecto>
CASEI_SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

No usar Supabase Storage como fuente actual de artefactos. La API sigue cargando el bundle local versionado y los archivos locales incluidos en el despliegue.

En la web CASEI, configurar la URL publica de la API con:

```text
ACADEMIC_SEGMENTATION_API_URL=https://<tu-api>.vercel.app
```

Notas operativas:

- Los endpoints de consulta (`/health`, `/summary`, `/students`, `/clusters`, `/search`) son los mas adecuados para Vercel.
- Los endpoints que reentrenan o regeneran artefactos pueden exceder limites serverless; para produccion conviene ejecutarlos en un job externo y sincronizar resultados a Supabase PostgreSQL.
- Mantener `CASEI_CORS_ORIGINS` restringido a los dominios reales de la web, no usar comodin si se envian credenciales.
