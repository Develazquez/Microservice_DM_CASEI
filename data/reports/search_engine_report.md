# Extra Roadmap - Motor de Busqueda BM25

## Objetivo

Implementar un motor de busqueda por keywords para recuperar alumnos segmentados a partir de consultas academicas en lenguaje natural corto, por ejemplo: `estudiantes criticos con rezago alto` o `buen promedio baja asistencia`.

## Tecnica usada

- Motor: BM25.
- Unidad indexada: un documento por estudiante-periodo.
- Corpus indexado: 1000 documentos.
- Fuente base: `data\raw\dataset_sintetico_alumnos_v2.csv`.
- Enriquecimiento: `cluster_assignments.csv` y `cluster_summary.csv`.
- Dependencias: implementacion propia con Python, pandas y numpy.

Cada documento combina metadatos, programa, cohorte, periodo, estatus academico, perfil de segmentacion, cluster y buckets interpretables de promedio, asistencia, rezago, reprobacion, tutorias e incidencias.

## Metricas globales

| queries | documents_indexed | mean_precision@10 | mean_recall@10 | mean_mrr@10 | mean_ndcg@10 |
| --- | --- | --- | --- | --- | --- |
| 8 | 1000 | 0.875 | 0.24144 | 0.9375 | 0.88091 |

## Metricas por consulta

| query_id | query | total_relevant | precision@10 | recall@10 | mrr@10 | ndcg@10 |
| --- | --- | --- | --- | --- | --- | --- |
| critical_lag | estudiantes criticos con rezago alto | 15 | 1 | 0.66667 | 1 | 1 |
| atypical_attendance | buen promedio baja asistencia atipico | 79 | 1 | 0.12658 | 1 | 1 |
| moderate_risk | riesgo academico moderado | 356 | 1 | 0.02809 | 1 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 644 | 1 | 0.015528 | 1 | 1 |
| software_lag | desarrollo de software rezago alto | 61 | 1 | 0.16393 | 1 | 1 |
| biomedical_low_attendance | biomedica baja asistencia | 87 | 1 | 0.11494 | 1 | 1 |
| energy_low_average | energia promedio bajo reprobadas | 8 | 0.4 | 0.5 | 1 | 0.52069 |
| agro_high_performance | agroindustrial asistencia alta promedio alto | 19 | 0.6 | 0.31579 | 0.5 | 0.52661 |

## Resultados de ejemplo

| query_id | query | rank | document_id | is_relevant | score_bm25 | programa | perfil_sugerido | promedio_general | porcentaje_asistencia | rezago_materias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| critical_lag | estudiantes criticos con rezago alto | 1 | e1241cb7-7ac0-597b-9c9a-814944fc3848::2024-1 | True | 8.3032 | Ingenieria Agroindustrial | Riesgo academico moderado | 54.52 | 61.18 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 2 | 8206b723-1395-5758-9f04-ff867caee093::2025-1 | True | 8.3032 | Ingenieria en Energia | Riesgo academico moderado | 58.85 | 66.1 | 5 |
| critical_lag | estudiantes criticos con rezago alto | 3 | 3369ead0-9955-5a30-9a64-4a6d1203b8a4::2023-2 | True | 8.2354 | Ingenieria Biomedica | Riesgo academico moderado | 56.01 | 64.42 | 5 |
| critical_lag | estudiantes criticos con rezago alto | 4 | b83ee102-f433-5778-a609-3a02d4940f0a::2024-2 | True | 8.2354 | Ingenieria Agroindustrial | Riesgo academico moderado | 58.31 | 70.93 | 4 |
| critical_lag | estudiantes criticos con rezago alto | 5 | 4ffe17c7-3413-5bb2-acfd-c6e809a577f1::2025-1 | True | 8.0387 | Ingenieria Agroindustrial | Riesgo academico moderado | 58.91 | 44.34 | 5 |
| atypical_attendance | buen promedio baja asistencia atipico | 1 | abc180cf-9427-5a78-8b50-34004de499b2::2023-2 | True | 6.624 | Ingenieria Agroindustrial | Riesgo academico moderado | 95.13 | 5.82 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 2 | 10c3353b-a997-571c-b026-d74c4f401898::2024-1 | True | 6.5079 | Ingenieria Biomedica | Riesgo academico moderado | 86.68 | 19.85 | 1 |
| atypical_attendance | buen promedio baja asistencia atipico | 3 | e11c0b9e-076d-5108-812c-8755d31ffa8f::2024-2 | True | 6.5079 | Ingenieria Biomedica | Riesgo academico moderado | 98 | 11.12 | 1 |
| atypical_attendance | buen promedio baja asistencia atipico | 4 | 84ccd916-7b10-5ef4-ab9f-c5bad860eaf6::2023-2 | True | 6.5079 | Ingenieria Biomedica | Riesgo academico moderado | 90.92 | 12.53 | 2 |
| atypical_attendance | buen promedio baja asistencia atipico | 5 | c5573e84-ed49-5c9c-9e05-24c17cb07c68::2024-2 | True | 6.5079 | Ingenieria en Desarrollo de Software | Riesgo academico moderado | 94.67 | 3.62 | 2 |
| moderate_risk | riesgo academico moderado | 1 | 55209b4f-7be2-5174-a5c8-3c409d72c6d7::2022-2 | True | 2.3839 | Ingenieria en Energia | Riesgo academico moderado | 58.62 | 62.77 | 1 |
| moderate_risk | riesgo academico moderado | 2 | 1f10260b-2e59-585d-b350-76fcc56c446d::2023-2 | True | 2.3839 | Ingenieria Biomedica | Riesgo academico moderado | 55.67 | 70.47 | 1 |
| moderate_risk | riesgo academico moderado | 3 | b0b66310-071b-56cc-82f2-c6a88d25ceae::2023-2 | True | 2.3839 | Ingenieria en Energia | Riesgo academico moderado | 54.95 | 62.8 | 1 |
| moderate_risk | riesgo academico moderado | 4 | 21fd4fdd-1301-525a-855b-896ceb7156e1::2025-1 | True | 2.3697 | Ingenieria Biomedica | Riesgo academico moderado | 54.71 | 63.13 | 2 |
| moderate_risk | riesgo academico moderado | 5 | 77f72c00-b1d2-521c-b3d6-1dea719a01eb::2024-2 | True | 2.3697 | Ingenieria en Energia | Riesgo academico moderado | 52.35 | 68.46 | 2 |
| regular_preventive | alumnos regulares seguimiento preventivo | 1 | 49ec7b01-ea08-5161-9647-b1833dc2cd51::2024-2 | True | 0.79255 | Ingenieria Biomedica | Regular / seguimiento preventivo | 81.36 | 74.39 | 0 |
| regular_preventive | alumnos regulares seguimiento preventivo | 2 | 2dd01f57-36ae-5311-b456-ebefe5e93dac::2024-1 | True | 0.79255 | Ingenieria Agroindustrial | Regular / seguimiento preventivo | 91.29 | 81.03 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 3 | 0035c4bd-a5e6-5422-bf32-c9f355da5b94::2022-2 | True | 0.79255 | Ingenieria en Energia | Regular / seguimiento preventivo | 90.76 | 76.04 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 4 | 606705c4-d6ca-5314-966c-b70eedf15cfb::2024-2 | True | 0.79255 | Ingenieria Biomedica | Regular / seguimiento preventivo | 72.27 | 87.12 | 1 |
| regular_preventive | alumnos regulares seguimiento preventivo | 5 | 2b638b4a-0c5d-5373-844c-fcc223d319fe::2024-1 | True | 0.79255 | Ingenieria Biomedica | Regular / seguimiento preventivo | 83.37 | 99 | 1 |

## Interpretacion

El motor cumple como una capa de recuperacion semantica ligera basada en terminos academicos controlados. Es util para dashboards, filtros inteligentes y busquedas operativas de perfiles de alumnos. Para una version posterior se puede comparar contra embeddings si se cuenta con un corpus textual mas rico, como observaciones tutoriales, notas de seguimiento o descripciones de incidencias.
