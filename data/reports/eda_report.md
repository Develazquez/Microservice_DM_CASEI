# Fase 2 - Reporte EDA

## Resumen del dataset

- Archivo fuente: `data\raw\dataset_crudo_2000_estudiantes.csv`
- Dataset analitico generado: `data\processed\student_period_features.csv`
- Registros: 999
- Columnas: 38
- Unidad analitica asumida: un estudiante en un periodo academico.
- Columnas sin nulos: 36 de 38

## Calidad de datos

| variable | dtype | null_count | null_rate | unique_count |
| --- | --- | --- | --- | --- |
| id_estudiante | str | 0 | 0 | 387 |
| id_periodo | str | 0 | 0 | 4 |
| programa | str | 0 | 0 | 4 |
| cohorte | int64 | 0 | 0 | 5 |
| promedio_general | float64 | 0 | 0 | 648 |
| promedio_periodo | float64 | 96 | 0.0961 | 556 |
| materias_aprobadas | int64 | 0 | 0 | 10 |
| materias_reprobadas | int64 | 0 | 0 | 8 |
| materias_en_curso | int64 | 0 | 0 | 4 |
| creditos_acumulados | float64 | 0 | 0 | 52 |
| porcentaje_avance | float64 | 0 | 0 | 155 |
| porcentaje_asistencia | float64 | 0 | 0 | 882 |
| faltas | int64 | 0 | 0 | 26 |
| retardos | int64 | 0 | 0 | 6 |
| num_tutorias | int64 | 0 | 0 | 8 |
| num_asesorias | int64 | 0 | 0 | 9 |
| num_incidencias | int64 | 0 | 0 | 5 |
| num_permisos | int64 | 0 | 0 | 9 |
| recursamientos | int64 | 0 | 0 | 10 |
| rezago_materias | int64 | 0 | 0 | 5 |

## Distribucion de estatus academico

| estatus_academico | registros |
| --- | --- |
| Regular | 550 |
| Irregular | 394 |
| Baja Temporal | 32 |
| Egresado | 23 |

## Estadistica descriptiva de variables numericas

| variable | mean | std | min | 25% | 50% | 75% | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| promedio_general | 76.71 | 8.767 | 36.7 | 70.34 | 77.33 | 82.51 | 100 |
| promedio_periodo | 77.42 | 9.802 | 36.7 | 72.47 | 78.4 | 83.82 | 100 |
| materias_aprobadas | 2.279 | 1.937 | 0 | 1 | 2 | 3 | 9 |
| materias_reprobadas | 0.5746 | 1.066 | 0 | 0 | 0 | 1 | 7 |
| materias_en_curso | 0.2312 | 0.5061 | 0 | 0 | 0 | 0 | 3 |
| creditos_acumulados | 13.08 | 11.19 | 0 | 6 | 11 | 18 | 57 |
| porcentaje_avance | 4.812 | 4.13 | 0 | 2.13 | 4.07 | 6.705 | 21.11 |
| porcentaje_asistencia | 71.93 | 11.46 | 12 | 65.74 | 73.46 | 80.53 | 94.11 |
| faltas | 9.023 | 3.885 | 1 | 6 | 9 | 11 | 29 |
| retardos | 1.547 | 1.067 | 0 | 1 | 1 | 2 | 5 |
| num_tutorias | 1.816 | 1.238 | 0 | 1 | 2 | 3 | 7 |
| num_asesorias | 1.491 | 1.36 | 0 | 0 | 1 | 2 | 8 |
| num_incidencias | 0.3093 | 0.8214 | 0 | 0 | 0 | 0 | 4 |
| num_permisos | 2.175 | 1.304 | 0 | 1 | 2 | 3 | 8 |
| recursamientos | 0.8088 | 1.342 | 0 | 0 | 0 | 1 | 9 |
| rezago_materias | 1.581 | 1.571 | 0 | 0 | 1 | 3 | 4 |
| creditos_inscritos_periodo | 11.32 | 7.004 | 4 | 6 | 10 | 14 | 41 |
| creditos_aprobados_periodo | 8.009 | 7.126 | 0 | 4 | 6 | 11 | 41 |
| creditos_totales_plan | 272.2 | 6.711 | 264 | 264 | 270 | 276 | 282 |
| periodos_cursados | 1.953 | 0.9255 | 1 | 1 | 2 | 3 | 4 |
| periodos_sin_inscripcion | 3.695 | 3.238 | 0 | 0 | 3 | 8 | 8 |
| materias_reprobadas_periodo | 0.3433 | 0.7016 | 0 | 0 | 0 | 0.5 | 6 |
| materias_reprobadas_acumuladas | 0.5746 | 1.066 | 0 | 0 | 0 | 1 | 7 |
| materias_en_curso_periodo | 0.2312 | 0.5061 | 0 | 0 | 0 | 0 | 3 |
| tendencia_promedio | 0.1532 | 7.324 | -28.7 | -1.05 | 0 | 1.7 | 31.6 |
| varianza_calificaciones | 24.71 | 51.31 | 0 | 4.41 | 7.5 | 21.44 | 678.6 |
| tutorias_abiertas | 0.6777 | 0.8796 | 0 | 0 | 0 | 1 | 6 |
| tutorias_cerradas | 1.138 | 0.8936 | 0 | 0 | 1 | 2 | 4 |
| compromisos_pendientes | 0.7848 | 1.044 | 0 | 0 | 0 | 1 | 7 |
| compromisos_cumplidos | 1.411 | 1.072 | 0 | 1 | 1 | 2 | 6 |

## Correlaciones fuertes

Umbral usado: `abs(correlacion) >= 0.85`.

| variable_a | variable_b | correlation |
| --- | --- | --- |
| materias_reprobadas | materias_reprobadas_acumuladas | 1 |
| materias_en_curso | materias_en_curso_periodo | 1 |
| creditos_acumulados | porcentaje_avance | 0.9993 |
| materias_aprobadas | creditos_acumulados | 0.9865 |
| materias_aprobadas | porcentaje_avance | 0.9862 |
| porcentaje_asistencia | faltas | -0.95 |
| rezago_materias | periodos_sin_inscripcion | 0.9499 |
| tutorias_abiertas | compromisos_pendientes | 0.9365 |
| promedio_general | promedio_periodo | 0.9261 |
| materias_reprobadas | recursamientos | 0.926 |
| recursamientos | materias_reprobadas_acumuladas | 0.926 |
| materias_en_curso | bandera_dato_incompleto | 0.9025 |
| materias_en_curso_periodo | bandera_dato_incompleto | 0.9025 |
| tutorias_cerradas | compromisos_cumplidos | 0.8952 |
| num_permisos | permisos_aprobados | 0.8834 |

## Outliers por regla IQR

| variable | outlier_count | outlier_rate | lower_bound | upper_bound |
| --- | --- | --- | --- | --- |
| promedio_general | 10 | 0.01001 | 52.09 | 100.8 |
| promedio_periodo | 28 | 0.02803 | 55.45 | 100.8 |
| materias_aprobadas | 47 | 0.04705 | -2 | 6 |
| materias_reprobadas | 59 | 0.05906 | -1.5 | 2.5 |
| materias_en_curso | 194 | 0.1942 | 0 | 0 |
| creditos_acumulados | 51 | 0.05105 | -12 | 36 |
| porcentaje_avance | 50 | 0.05005 | -4.733 | 13.57 |
| porcentaje_asistencia | 25 | 0.02503 | 43.56 | 102.7 |
| faltas | 24 | 0.02402 | -1.5 | 18.5 |
| retardos | 31 | 0.03103 | -0.5 | 3.5 |
| num_tutorias | 1 | 0.001001 | -2 | 6 |
| num_asesorias | 14 | 0.01401 | -3 | 5 |
| num_incidencias | 143 | 0.1431 | 0 | 0 |
| num_permisos | 2 | 0.002002 | -2 | 6 |
| recursamientos | 94 | 0.09409 | -1.5 | 2.5 |
| rezago_materias | 0 | 0 | -4.5 | 7.5 |
| creditos_inscritos_periodo | 46 | 0.04605 | -6 | 26 |
| creditos_aprobados_periodo | 61 | 0.06106 | -6.5 | 21.5 |
| creditos_totales_plan | 0 | 0 | 246 | 294 |
| periodos_cursados | 0 | 0 | -2 | 6 |
| periodos_sin_inscripcion | 0 | 0 | -12 | 20 |
| materias_reprobadas_periodo | 64 | 0.06406 | -0.75 | 1.25 |
| materias_reprobadas_acumuladas | 59 | 0.05906 | -1.5 | 2.5 |
| materias_en_curso_periodo | 194 | 0.1942 | 0 | 0 |
| tendencia_promedio | 266 | 0.2663 | -5.175 | 5.825 |
| varianza_calificaciones | 138 | 0.1381 | -21.13 | 46.98 |
| tutorias_abiertas | 43 | 0.04304 | -1.5 | 2.5 |
| tutorias_cerradas | 0 | 0 | -3 | 5 |
| compromisos_pendientes | 95 | 0.0951 | -1.5 | 2.5 |
| compromisos_cumplidos | 38 | 0.03804 | -0.5 | 3.5 |

## Comparacion por programa

| programa | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| Ingeniería Agroindustrial | 76.43 | 73.27 | 1.38 | 0.62 |
| Ingeniería Biomédica | 75.21 | 71.02 | 1.71 | 0.71 |
| Ingeniería en Desarrollo de Software | 77.23 | 72.18 | 1.54 | 0.51 |
| Ingeniería en Energía | 77.58 | 71.21 | 1.7 | 0.5 |

## Comparacion por cohorte

| cohorte | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| 2020 | 77.17 | 62.53 | 3.74 | 0.52 |
| 2021 | 77.06 | 69.85 | 2.16 | 0.48 |
| 2022 | 76.46 | 73.73 | 0.91 | 0.61 |
| 2023 | 76.06 | 78.82 | 0.03 | 0.58 |
| 2024 | 76.58 | 79.53 | 0 | 0.73 |

## Comparacion por periodo

| id_periodo | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| Enero-Abril 2023 | 77.61 | 72.72 | 1.6 | 0.39 |
| Mayo-Agosto 2023 | 76.96 | 72.32 | 1.58 | 0.64 |
| Septiembre-Diciembre 2022 | 75.04 | 72.11 | 1.61 | 0.21 |
| Septiembre-Diciembre 2023 | 77.31 | 70.69 | 1.54 | 1.07 |

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
