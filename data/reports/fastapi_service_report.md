# Fase 9 - Microservicio FastAPI

## Objetivo

Exponer el pipeline y los artefactos locales de segmentacion academica como un microservicio REST independiente, documentado con OpenAPI/Swagger y desacoplado de la web CASEI.

## Fuente actual

- Modelo activo: `casei-kmeans-pca90-k2-68c23826aa1e`
- Puntero local: `artifacts/current_model.json`
- Dataset activo: `data/raw/dataset_crudo_2000_estudiantes.csv`
- Vista alumno-periodo: `data/processed/student_period_features.csv`
- Registros de asignacion: 1,277
- Estudiantes unicos: 387

## Endpoints implementados

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/health` | Health check general del microservicio. |
| GET | `/api/v1/segmentation/health` | Health check bajo el prefijo versionado. |
| POST | `/api/v1/segmentation/run` | Carga/valida el bundle activo o regenera fases 2-8 en local. |
| GET | `/api/v1/segmentation/summary` | Resumen general, metricas del modelo y distribuciones. |
| GET | `/api/v1/segmentation/students` | Lista paginada de estudiantes-periodo con filtros por perfil, programa y cluster. |
| GET | `/api/v1/segmentation/students/{id}` | Detalle historico por estudiante. |
| GET | `/api/v1/segmentation/students/{id}/history` | Historial persistido de inferencias por estudiante. |
| GET | `/api/v1/segmentation/search` | Busqueda BM25 por keywords academicas. |
| GET | `/api/v1/segmentation/clusters` | Catalogo de perfiles, centroides y variables distintivas. |
| GET | `/api/v1/segmentation/history` | Historial persistido de corridas de inferencia. |
| GET | `/api/v1/segmentation/history/{execution_id}` | Detalle paginado de inferencias por corrida. |

## Swagger/OpenAPI

La documentacion interactiva queda disponible al levantar el servidor:

```text
http://127.0.0.1:8000/docs
```

La especificacion OpenAPI queda disponible en:

```text
http://127.0.0.1:8000/openapi.json
```

## Modos de ejecucion

`POST /api/v1/segmentation/run` acepta:

- `load_existing`: valida el bundle activo de Fase 8 sin recalcular el pipeline.
- `retrain_local`: ejecuta fases 2-4, 5-6, 7 y 8 usando los archivos locales actuales.

## Verificacion realizada

- Importacion de `app.main` correcta.
- OpenAPI generado correctamente.
- Prueba con `TestClient` de:
  - `/health`
  - `/api/v1/segmentation/summary`
  - `/api/v1/segmentation/students?limit=2`
  - `/api/v1/segmentation/students/IAG20200007`
  - `/api/v1/segmentation/search?q=riesgo academico&top_k=3`
  - `/api/v1/segmentation/clusters`
  - `/api/v1/segmentation/history`
  - `/api/v1/segmentation/run`
- Compilacion Python completada con `python -m compileall -q app scripts`.
- Servidor local iniciado con `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Verificacion HTTP real:
  - `GET http://127.0.0.1:8000/health` respondio `status=ok`.
  - `GET http://127.0.0.1:8000/api/v1/segmentation/summary` respondio 387 estudiantes unicos y 1,277 registros.
  - `GET http://127.0.0.1:8000/docs` respondio HTTP 200.
- En Fase 10, `POST /api/v1/segmentation/run` registra cada corrida exitosa en SQLite.

## Limitaciones

- El JSONL `data/reports/api_execution_history.jsonl` queda como bitacora ligera; la persistencia formal queda en `data/storage/segmentation_inference_history.sqlite`.
- La API solo usa archivos locales y el bundle versionado; no usa Supabase Storage como fuente actual.
- Los clusters son apoyo tutorial/analitico, no diagnostico automatico definitivo.
