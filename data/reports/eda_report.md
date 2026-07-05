# Fase 2 - Reporte EDA

## Resumen del dataset

- Archivo fuente: `data\raw\dataset_crudo_cardex_2000.csv`
- Dataset analitico generado: `data\processed\student_period_features.csv`
- Registros: 1277
- Columnas: 38
- Unidad analitica asumida: un estudiante en un periodo academico.
- Columnas sin nulos: 36 de 38

## Calidad de datos

| variable | dtype | null_count | null_rate | unique_count |
| --- | --- | --- | --- | --- |
| id_estudiante | str | 0 | 0 | 387 |
| id_periodo | str | 0 | 0 | 7 |
| programa | str | 0 | 0 | 4 |
| cohorte | int64 | 0 | 0 | 5 |
| promedio_general | float64 | 0 | 0 | 796 |
| promedio_periodo | float64 | 97 | 0.07596 | 560 |
| materias_aprobadas | int64 | 0 | 0 | 10 |
| materias_reprobadas | int64 | 0 | 0 | 8 |
| materias_en_curso | int64 | 0 | 0 | 4 |
| creditos_acumulados | float64 | 0 | 0 | 52 |
| porcentaje_avance | float64 | 0 | 0 | 165 |
| porcentaje_asistencia | float64 | 0 | 0 | 1056 |
| faltas | int64 | 0 | 0 | 25 |
| retardos | int64 | 0 | 0 | 7 |
| num_tutorias | int64 | 0 | 0 | 8 |
| num_asesorias | int64 | 0 | 0 | 9 |
| num_incidencias | int64 | 0 | 0 | 5 |
| num_permisos | int64 | 0 | 0 | 8 |
| recursamientos | int64 | 0 | 0 | 4 |
| rezago_materias | int64 | 0 | 0 | 9 |

## Distribucion de estatus academico

| estatus_academico | registros |
| --- | --- |
| Regular | 782 |
| Irregular | 422 |
| Baja Temporal | 39 |
| Egresado | 34 |

## Estadistica descriptiva de variables numericas

| variable | mean | std | min | 25% | 50% | 75% | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| promedio_general | 76.75 | 8.656 | 36.7 | 71.1 | 77.57 | 82.45 | 100 |
| promedio_periodo | 77.36 | 10.26 | 19.7 | 72.38 | 78.3 | 84.01 | 100 |
| materias_aprobadas | 2.46 | 1.92 | 0 | 1 | 2 | 3 | 9 |
| materias_reprobadas | 0.6139 | 1.087 | 0 | 0 | 0 | 1 | 7 |
| materias_en_curso | 0.1809 | 0.4576 | 0 | 0 | 0 | 0 | 3 |
| creditos_acumulados | 14.25 | 11.21 | 0 | 6 | 12 | 20 | 57 |
| porcentaje_avance | 5.245 | 4.141 | 0 | 2.17 | 4.35 | 7.25 | 21.11 |
| porcentaje_asistencia | 74.96 | 10.91 | 12 | 70.09 | 77.19 | 82.53 | 94.77 |
| faltas | 8.011 | 3.619 | 1 | 6 | 7 | 10 | 26 |
| retardos | 1.387 | 1.07 | 0 | 1 | 1 | 2 | 6 |
| num_tutorias | 1.558 | 1.241 | 0 | 1 | 1 | 2 | 8 |
| num_asesorias | 1.446 | 1.292 | 0 | 0 | 1 | 2 | 8 |
| num_incidencias | 0.2482 | 0.7513 | 0 | 0 | 0 | 0 | 4 |
| num_permisos | 2.013 | 1.26 | 0 | 1 | 2 | 3 | 8 |
| recursamientos | 0.1425 | 0.4172 | 0 | 0 | 0 | 0 | 3 |
| rezago_materias | 1.37 | 1.311 | 0 | 0 | 1 | 2 | 8 |
| creditos_inscritos_periodo | 8.855 | 4.425 | 4 | 6 | 7 | 12 | 30 |
| creditos_aprobados_periodo | 6.265 | 4.718 | 0 | 4 | 6 | 8 | 29 |
| creditos_totales_plan | 272.2 | 6.745 | 264 | 264 | 270 | 276 | 282 |
| periodos_cursados | 2.411 | 1.281 | 1 | 1 | 2 | 3 | 7 |
| periodos_sin_inscripcion | 2.015 | 2.077 | 0 | 0 | 2 | 4 | 8 |
| materias_reprobadas_periodo | 0.2686 | 0.5506 | 0 | 0 | 0 | 0 | 4 |
| materias_reprobadas_acumuladas | 0.6139 | 1.087 | 0 | 0 | 0 | 1 | 7 |
| materias_en_curso_periodo | 0.1809 | 0.4576 | 0 | 0 | 0 | 0 | 3 |
| tendencia_promedio | 0.2103 | 8.125 | -40.15 | -2.4 | 0 | 3.163 | 31.6 |
| varianza_calificaciones | 18.6 | 42.6 | 0 | 4.19 | 6.86 | 9.69 | 678.6 |
| tutorias_abiertas | 0.4973 | 0.912 | 0 | 0 | 0 | 1 | 6 |
| tutorias_cerradas | 1.061 | 0.8254 | 0 | 0 | 1 | 2 | 3 |
| compromisos_pendientes | 0.5818 | 1.027 | 0 | 0 | 0 | 1 | 6 |
| compromisos_cumplidos | 1.239 | 0.8906 | 0 | 1 | 1 | 2 | 4 |

## Correlaciones fuertes

Umbral usado: `abs(correlacion) >= 0.85`.

| variable_a | variable_b | correlation |
| --- | --- | --- |
| materias_en_curso | materias_en_curso_periodo | 1 |
| materias_reprobadas | materias_reprobadas_acumuladas | 1 |
| creditos_acumulados | porcentaje_avance | 0.9993 |
| materias_aprobadas | creditos_acumulados | 0.9851 |
| materias_aprobadas | porcentaje_avance | 0.9849 |
| porcentaje_asistencia | faltas | -0.9429 |
| tutorias_abiertas | compromisos_pendientes | 0.9372 |
| materias_en_curso | bandera_dato_incompleto | 0.9069 |
| materias_en_curso_periodo | bandera_dato_incompleto | 0.9069 |
| materias_reprobadas_periodo | tutorias_abiertas | 0.9059 |
| tutorias_cerradas | compromisos_cumplidos | 0.9023 |
| num_permisos | permisos_aprobados | 0.8869 |
| promedio_general | promedio_periodo | 0.876 |
| materias_reprobadas_periodo | compromisos_pendientes | 0.8519 |

## Outliers por regla IQR

| variable | outlier_count | outlier_rate | lower_bound | upper_bound |
| --- | --- | --- | --- | --- |
| promedio_general | 19 | 0.01488 | 54.07 | 99.48 |
| promedio_periodo | 38 | 0.02976 | 54.92 | 101.5 |
| materias_aprobadas | 57 | 0.04464 | -2 | 6 |
| materias_reprobadas | 83 | 0.065 | -1.5 | 2.5 |
| materias_en_curso | 194 | 0.1519 | 0 | 0 |
| creditos_acumulados | 34 | 0.02662 | -15 | 41 |
| porcentaje_avance | 40 | 0.03132 | -5.45 | 14.87 |
| porcentaje_asistencia | 50 | 0.03915 | 51.43 | 101.2 |
| faltas | 39 | 0.03054 | 0 | 16 |
| retardos | 28 | 0.02193 | -0.5 | 3.5 |
| num_tutorias | 98 | 0.07674 | -0.5 | 3.5 |
| num_asesorias | 12 | 0.009397 | -3 | 5 |
| num_incidencias | 140 | 0.1096 | 0 | 0 |
| num_permisos | 2 | 0.001566 | -2 | 6 |
| recursamientos | 151 | 0.1182 | 0 | 0 |
| rezago_materias | 8 | 0.006265 | -3 | 5 |
| creditos_inscritos_periodo | 22 | 0.01723 | -3 | 21 |
| creditos_aprobados_periodo | 65 | 0.0509 | -2 | 14 |
| creditos_totales_plan | 0 | 0 | 246 | 294 |
| periodos_cursados | 1 | 0.0007831 | -2 | 6 |
| periodos_sin_inscripcion | 0 | 0 | -6 | 10 |
| materias_reprobadas_periodo | 283 | 0.2216 | 0 | 0 |
| materias_reprobadas_acumuladas | 83 | 0.065 | -1.5 | 2.5 |
| materias_en_curso_periodo | 194 | 0.1519 | 0 | 0 |
| tendencia_promedio | 186 | 0.1457 | -10.74 | 11.51 |
| varianza_calificaciones | 225 | 0.1762 | -4.06 | 17.94 |
| tutorias_abiertas | 64 | 0.05012 | -1.5 | 2.5 |
| tutorias_cerradas | 0 | 0 | -3 | 5 |
| compromisos_pendientes | 107 | 0.08379 | -1.5 | 2.5 |
| compromisos_cumplidos | 20 | 0.01566 | -0.5 | 3.5 |

## Comparacion por programa

| programa | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| Ingeniería Agroindustrial | 76.41 | 75.79 | 1.27 | 0.65 |
| Ingeniería Biomédica | 75.14 | 73.72 | 1.6 | 0.76 |
| Ingeniería en Desarrollo de Software | 77.23 | 75.28 | 1.27 | 0.56 |
| Ingeniería en Energía | 77.79 | 74.87 | 1.37 | 0.52 |

## Comparacion por cohorte

| cohorte | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| 2020 | 77.39 | 69.12 | 2.65 | 0.56 |
| 2021 | 77 | 74.07 | 1.66 | 0.52 |
| 2022 | 76.35 | 76.19 | 0.9 | 0.65 |
| 2023 | 76.1 | 78.91 | 0.55 | 0.6 |
| 2024 | 76.68 | 78.85 | 0.6 | 0.77 |

## Comparacion por periodo

| id_periodo | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| 2022-1 | 75.04 | 76.05 | 0.89 | 0.21 |
| 2022-2 | 77.61 | 76.37 | 1.06 | 0.39 |
| 2023-1 | 76.96 | 74.9 | 1.29 | 0.64 |
| 2023-2 | 77.24 | 75 | 1.41 | 0.77 |
| 2024-1 | 76.5 | 73.98 | 1.75 | 0.97 |
| 2024-2 | 77.59 | 72.64 | 2.05 | 0.9 |
| 2025-1 | 77.17 | 72.51 | 2.19 | 1.08 |

## Graficas generadas

- `data/reports/figures/hist_promedio_general.svg`
- `data/reports/figures/hist_porcentaje_asistencia.svg`
- `data/reports/figures/hist_rezago_materias.svg`
- `data/reports/figures/correlation_heatmap.svg`

## Hallazgos accionables

- El dataset fuente es cardex crudo por materia. El pipeline lo agrega a estudiante-periodo antes del EDA, seleccion de variables, PCA y clustering.
- Como el cardex no contiene asistencia ni seguimiento tutorial directo, esas senales se estiman de forma deterministica a partir de calificaciones, estatus, creditos, reprobadas y rezago. En una integracion institucional real se recomienda sustituirlas por datos operativos reales.
- `materias_aprobadas`, `creditos_acumulados` y `porcentaje_avance` son variables derivadas entre si. Conviene conservar solo una para clustering.
- `porcentaje_asistencia` y `faltas` describen dimensiones muy cercanas en sentido inverso. Para la primera version se conserva el porcentaje por ser normalizado e interpretable.
- Las variables de acompanamiento (`num_tutorias`, `num_asesorias`) e incidencias deben mantenerse porque ayudan a diferenciar perfiles academicos mas alla del promedio.
