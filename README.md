# Academic Segmentation Service
Microservicio independiente en construccion para segmentacion academica no supervisada de estudiantes.

## Alcance actual

Este modulo contiene los entregables iniciales de analisis del pipeline:

- Fase 1: diagnostico y validacion del dataset v1.
- Fase 2 actualizada: criterios de realismo academico.
- Fase 3 actualizada: generacion reproducible de dataset sintetico v2.
- Fase 4 actualizada: validacion estadistica y academica automatizada del dataset v2.
- Fase 2: EDA del dataset academico.
- Fase 3: seleccion de variables para clustering.
- Fase 4: PCA reproducible con numpy.
- Fase 5: seleccion de K con metricas internas.
- Fase 6: entrenamiento K-Means y asignacion de clusters.
- Extra roadmap: motor de busqueda academica BM25 con metricas de recuperacion.

La API REST con FastAPI queda para fases posteriores del plan de ejecucion.

## Requisitos

```bash
pip install -r requirements.txt
```

Dependencias minimas:

- Python 3.10+
- pandas
- numpy

## Dataset

El dataset sintetico base se toma desde:

```text
data/raw/dataset_sintetico_alumnos_v2.csv
```

El dataset v1 se conserva como evidencia historica en:

```text
data/raw/dataset_sintetico_alumnos.csv
```

El dataset v2 se genera de forma reproducible con variables latentes, reglas de coherencia academica y nulos controlados.


## Ejecucion

Desde la raiz de este repositorio/carpeta:

```bash
python scripts/run_dataset_v2.py
python scripts/run_phase_2_4.py
python scripts/run_phase_5_6.py
python scripts/run_search_engine.py
```

## Arquitectura MVC

```text
app/
├── controllers/   # Orquestan casos de uso ejecutados por scripts o futura API
├── models/        # Configuracion, rutas y constantes del dominio
├── services/      # Logica de EDA, PCA, seleccion de K, K-Means y busqueda BM25
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
data/reports/criterios_realismo_dataset.md
data/reports/diccionario_variables_v2.md
data/reports/dataset_validation_v1.md
data/reports/dataset_validation_v2.md
data/reports/dataset_v1_vs_v2.md
data/reports/feature_selection.md
data/reports/pca_report.md
data/reports/k_selection_report.md
data/reports/kmeans_training_report.md
data/reports/search_engine_report.md
data/reports/search_metrics.csv
data/reports/search_results_sample.csv
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
```

## Decision tecnica

La version actual usa pandas y numpy para evitar depender de paquetes externos no disponibles en el runtime local. El dataset v2 reduce contradicciones detectadas en v1, separa variables de periodo e historicas y deja evidencia reproducible antes de avanzar a FastAPI.

La API REST con FastAPI debe implementarse despues de validar academicamente los perfiles y contratos de inferencia.
# Microservice_DM_CASEI
# Microservice_DM_CASEI
