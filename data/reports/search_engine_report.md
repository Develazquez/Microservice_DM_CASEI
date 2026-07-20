# Extra Roadmap - Motor de Busqueda BM25

## Objetivo

Implementar un motor de busqueda por keywords para recuperar alumnos segmentados a partir de consultas academicas en lenguaje natural corto, por ejemplo: `estudiantes criticos con rezago alto` o `buen promedio baja asistencia`.

## Tecnica usada

- Motor: BM25.
- Unidad indexada: un documento por estudiante-periodo.
- Corpus indexado: 999 documentos.
- Fuente base cruda: `data\raw\dataset_crudo_2000_estudiantes.csv`.
- Fuente analitica indexada: `data\processed\student_period_features.csv`.
- Enriquecimiento: `cluster_assignments.csv` y `cluster_summary.csv`.
- Dependencias: implementacion propia con Python, pandas y numpy.

Cada documento combina metadatos, programa, cohorte, periodo, estatus academico, perfil de segmentacion, cluster y buckets interpretables de promedio, asistencia, rezago, reprobacion, tutorias e incidencias.

## Metricas globales

| queries | documents_indexed | mean_precision@10 | mean_recall@10 | mean_mrr@10 | mean_ndcg@10 |
| --- | --- | --- | --- | --- | --- |
| 8 | 999 | 0.7125 | 0.48053 | 0.91667 | 0.9375 |

## Metricas por consulta

| query_id | query | total_relevant | precision@10 | recall@10 | mrr@10 | ndcg@10 |
| --- | --- | --- | --- | --- | --- | --- |
| critical_lag | estudiantes criticos con rezago alto | 4 | 0.4 | 1 | 1 | 1 |
| atypical_attendance | buen promedio baja asistencia atipico | 2 | 0.2 | 1 | 1 | 1 |
| moderate_risk | riesgo academico moderado | 187 | 1 | 0.053476 | 1 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 812 | 1 | 0.012315 | 1 | 1 |
| software_lag | desarrollo de software rezago alto | 62 | 1 | 0.16129 | 1 | 1 |
| biomedical_low_attendance | biomedica baja asistencia | 26 | 1 | 0.38462 | 1 | 1 |
| energy_low_average | energia promedio bajo reprobadas | 1 | 0.1 | 1 | 0.33333 | 0.5 |
| agro_high_performance | agroindustrial asistencia alta promedio alto | 43 | 1 | 0.23256 | 1 | 1 |

## Resultados de ejemplo

| query_id | query | rank | document_id | is_relevant | score_bm25 | programa | perfil_sugerido | promedio_general | porcentaje_asistencia | rezago_materias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| critical_lag | estudiantes criticos con rezago alto | 1 | IBM20200331::Enero-Abril 2023 | True | 10.117 | Ingeniería Biomédica | Riesgo academico moderado | 58.85 | 49.48 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 2 | IAG20200249::Mayo-Agosto 2023 | True | 10.117 | Ingeniería Agroindustrial | Riesgo academico moderado | 57.5 | 55.35 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 3 | IAG20210083::Septiembre-Diciembre 2023 | True | 10.117 | Ingeniería Agroindustrial | Riesgo academico moderado | 51.82 | 27.11 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 4 | IEN20200224::Septiembre-Diciembre 2022 | True | 9.975 | Ingeniería en Energía | Riesgo academico moderado | 51.5 | 17.14 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 5 | IBM20210147::Septiembre-Diciembre 2023 | False | 3.8617 | Ingeniería Biomédica | Riesgo academico moderado | 59.55 | 45.85 | 3 |
| atypical_attendance | buen promedio baja asistencia atipico | 1 | IDS20200065::Enero-Abril 2023 | True | 14.547 | Ingeniería en Desarrollo de Software | Riesgo academico moderado | 89.57 | 43.67 | 3 |
| atypical_attendance | buen promedio baja asistencia atipico | 2 | IDS20200065::Septiembre-Diciembre 2022 | True | 14.547 | Ingeniería en Desarrollo de Software | Riesgo academico moderado | 94 | 39.34 | 3 |
| atypical_attendance | buen promedio baja asistencia atipico | 3 | IEN20200224::Mayo-Agosto 2023 | False | 3.8657 | Ingeniería en Energía | Riesgo academico moderado | 65.76 | 36.2 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 4 | IAG20230236::Septiembre-Diciembre 2022 | False | 3.8492 | Ingeniería Agroindustrial | Riesgo academico moderado | 61.7 | 34.37 | 0 |
| atypical_attendance | buen promedio baja asistencia atipico | 5 | IAG20230236::Enero-Abril 2023 | False | 3.8492 | Ingeniería Agroindustrial | Riesgo academico moderado | 65.33 | 48.58 | 0 |
| moderate_risk | riesgo academico moderado | 1 | IAG20210176::Septiembre-Diciembre 2022 | True | 4.7033 | Ingeniería Agroindustrial | Riesgo academico moderado | 58.2 | 63.27 | 2 |
| moderate_risk | riesgo academico moderado | 2 | IBM20220362::Mayo-Agosto 2023 | True | 4.7033 | Ingeniería Biomédica | Riesgo academico moderado | 55.4 | 62.71 | 2 |
| moderate_risk | riesgo academico moderado | 3 | IAG20220113::Enero-Abril 2023 | True | 4.7033 | Ingeniería Agroindustrial | Riesgo academico moderado | 57.9 | 67.37 | 1 |
| moderate_risk | riesgo academico moderado | 4 | IAG20220371::Septiembre-Diciembre 2023 | True | 4.7033 | Ingeniería Agroindustrial | Riesgo academico moderado | 48.36 | 63.41 | 1 |
| moderate_risk | riesgo academico moderado | 5 | IBM20210147::Septiembre-Diciembre 2022 | True | 4.7033 | Ingeniería Biomédica | Riesgo academico moderado | 50 | 61.4 | 2 |
| regular_preventive | alumnos regulares seguimiento preventivo | 1 | IEN20240373::Septiembre-Diciembre 2022 | True | 0.38879 | Ingeniería en Energía | Regular / seguimiento preventivo | 70 | 77.45 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 2 | IEN20240251::Septiembre-Diciembre 2022 | True | 0.38879 | Ingeniería en Energía | Regular / seguimiento preventivo | 81.1 | 86.13 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 3 | IEN20240275::Mayo-Agosto 2023 | True | 0.38879 | Ingeniería en Energía | Regular / seguimiento preventivo | 80.55 | 88.5 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 4 | IEN20220214::Septiembre-Diciembre 2022 | True | 0.38879 | Ingeniería en Energía | Regular / seguimiento preventivo | 90.6 | 81.18 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 5 | IEN20220241::Septiembre-Diciembre 2022 | True | 0.38879 | Ingeniería en Energía | Regular / seguimiento preventivo | 70 | 78.85 | 1 |

## Interpretacion

El motor cumple como una capa de recuperacion semantica ligera basada en terminos academicos controlados. Es util para dashboards, filtros inteligentes y busquedas operativas de perfiles de alumnos. Para una version posterior se puede comparar contra embeddings si se cuenta con un corpus textual mas rico, como observaciones tutoriales, notas de seguimiento o descripciones de incidencias.
