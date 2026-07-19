# Extra Roadmap - Motor de Busqueda BM25

## Objetivo

Implementar un motor de busqueda por keywords para recuperar alumnos segmentados a partir de consultas academicas en lenguaje natural corto, por ejemplo: `estudiantes criticos con rezago alto` o `buen promedio baja asistencia`.

## Tecnica usada

- Motor: BM25.
- Unidad indexada: un documento por estudiante-periodo.
- Corpus indexado: 1277 documentos.
- Fuente base cruda: `data\raw\dataset_crudo_cardex_2000.csv`.
- Fuente analitica indexada: `data\processed\student_period_features.csv`.
- Enriquecimiento: `cluster_assignments.csv` y `cluster_summary.csv`.
- Dependencias: implementacion propia con Python, pandas y numpy.

Cada documento combina metadatos, programa, cohorte, periodo, estatus academico, perfil de segmentacion, cluster y buckets interpretables de promedio, asistencia, rezago, reprobacion, tutorias e incidencias.

## Metricas globales

| queries | documents_indexed | mean_precision@10 | mean_recall@10 | mean_mrr@10 | mean_ndcg@10 |
| --- | --- | --- | --- | --- | --- |
| 8 | 1277 | 0.7875 | 0.39745 | 0.82812 | 0.89474 |

## Metricas por consulta

| query_id | query | total_relevant | precision@10 | recall@10 | mrr@10 | ndcg@10 |
| --- | --- | --- | --- | --- | --- | --- |
| critical_lag | estudiantes criticos con rezago alto | 21 | 1 | 0.47619 | 1 | 1 |
| atypical_attendance | buen promedio baja asistencia atipico | 2 | 0.2 | 1 | 1 | 1 |
| moderate_risk | riesgo academico moderado | 244 | 1 | 0.040984 | 1 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 1033 | 1 | 0.0096805 | 1 | 1 |
| software_lag | desarrollo de software rezago alto | 48 | 1 | 0.20833 | 1 | 1 |
| biomedical_low_attendance | biomedica baja asistencia | 30 | 1 | 0.33333 | 1 | 1 |
| energy_low_average | energia promedio bajo reprobadas | 2 | 0.2 | 1 | 0.125 | 0.378 |
| agro_high_performance | agroindustrial asistencia alta promedio alto | 81 | 0.9 | 0.11111 | 0.5 | 0.77991 |

## Resultados de ejemplo

| query_id | query | rank | document_id | is_relevant | score_bm25 | programa | perfil_sugerido | promedio_general | porcentaje_asistencia | rezago_materias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| critical_lag | estudiantes criticos con rezago alto | 1 | IAG20210339::2024-2 | True | 8.8066 | Ingeniería Agroindustrial | Riesgo academico moderado | 59.09 | 63.41 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 2 | IAG20220113::2023-1 | True | 8.8066 | Ingeniería Agroindustrial | Riesgo academico moderado | 59.48 | 65.56 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 3 | IAG20210339::2023-2 | True | 8.8066 | Ingeniería Agroindustrial | Riesgo academico moderado | 58.18 | 60.29 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 4 | IDS20220005::2024-2 | True | 8.728 | Ingeniería en Desarrollo de Software | Riesgo academico moderado | 59.3 | 63.73 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 5 | IEN20240366::2025-1 | True | 8.5752 | Ingeniería en Energía | Riesgo academico moderado | 52.43 | 59.93 | 4 |
| atypical_attendance | buen promedio baja asistencia atipico | 1 | IDS20200065::2022-1 | True | 15.065 | Ingeniería en Desarrollo de Software | Regular / seguimiento preventivo | 94 | 50.89 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 2 | IDS20200065::2022-2 | True | 15.065 | Ingeniería en Desarrollo de Software | Regular / seguimiento preventivo | 89.57 | 47.9 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 3 | IBM20200017::2023-2 | False | 3.914 | Ingeniería Biomédica | Riesgo academico moderado | 74.23 | 41.1 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 4 | IBM20200017::2022-1 | False | 3.914 | Ingeniería Biomédica | Riesgo academico moderado | 73.6 | 44.84 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 5 | IAG20230236::2022-2 | False | 3.914 | Ingeniería Agroindustrial | Riesgo academico moderado | 65.33 | 46.48 | 2 |
| moderate_risk | riesgo academico moderado | 1 | IEN20230123::2022-1 | True | 3.9066 | Ingeniería en Energía | Riesgo academico moderado | 54.9 | 68.78 | 1 |
| moderate_risk | riesgo academico moderado | 2 | IEN20220344::2024-2 | True | 3.9066 | Ingeniería en Energía | Riesgo academico moderado | 57.27 | 60.72 | 1 |
| moderate_risk | riesgo academico moderado | 3 | IEN20220060::2024-1 | True | 3.9066 | Ingeniería en Energía | Riesgo academico moderado | 50.2 | 64.08 | 2 |
| moderate_risk | riesgo academico moderado | 4 | IEN20210159::2022-1 | True | 3.9066 | Ingeniería en Energía | Riesgo academico moderado | 57.1 | 61.95 | 2 |
| moderate_risk | riesgo academico moderado | 5 | IAG20210176::2022-1 | True | 3.9066 | Ingeniería Agroindustrial | Riesgo academico moderado | 58.2 | 61.74 | 2 |
| regular_preventive | alumnos regulares seguimiento preventivo | 1 | IEN20240352::2023-1 | True | 0.36399 | Ingeniería en Energía | Regular / seguimiento preventivo | 76.1 | 80.14 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 2 | IAG20200007::2023-1 | True | 0.36399 | Ingeniería Agroindustrial | Regular / seguimiento preventivo | 85.77 | 80.42 | 2 |
| regular_preventive | alumnos regulares seguimiento preventivo | 3 | IEN20220214::2022-2 | True | 0.36399 | Ingeniería en Energía | Regular / seguimiento preventivo | 89.67 | 90.76 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 4 | IEN20220220::2022-1 | True | 0.36399 | Ingeniería en Energía | Regular / seguimiento preventivo | 80.4 | 83.34 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 5 | IEN20220220::2023-2 | True | 0.36399 | Ingeniería en Energía | Regular / seguimiento preventivo | 79.2 | 81.42 | 1 |

## Interpretacion

El motor cumple como una capa de recuperacion semantica ligera basada en terminos academicos controlados. Es util para dashboards, filtros inteligentes y busquedas operativas de perfiles de alumnos. Para una version posterior se puede comparar contra embeddings si se cuenta con un corpus textual mas rico, como observaciones tutoriales, notas de seguimiento o descripciones de incidencias.
