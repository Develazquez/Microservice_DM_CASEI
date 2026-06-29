# Fase 2 - Reporte EDA

## Resumen del dataset

- Archivo fuente: `data\raw\dataset_sintetico_alumnos_v2.csv`
- Registros: 1000
- Columnas: 38
- Unidad analitica asumida: un estudiante en un periodo academico.
- Columnas sin nulos: 36 de 38

## Calidad de datos

| variable | dtype | null_count | null_rate | unique_count |
| --- | --- | --- | --- | --- |
| id_estudiante | str | 0 | 0 | 1000 |
| id_periodo | str | 0 | 0 | 6 |
| programa | str | 0 | 0 | 4 |
| cohorte | int64 | 0 | 0 | 5 |
| promedio_general | float64 | 0 | 0 | 882 |
| promedio_periodo | float64 | 36 | 0.036 | 861 |
| materias_aprobadas | int64 | 0 | 0 | 51 |
| materias_reprobadas | int64 | 0 | 0 | 9 |
| materias_en_curso | int64 | 0 | 0 | 7 |
| creditos_acumulados | int64 | 0 | 0 | 250 |
| porcentaje_avance | float64 | 0 | 0 | 594 |
| porcentaje_asistencia | float64 | 0 | 0 | 907 |
| faltas | int64 | 0 | 0 | 33 |
| retardos | int64 | 0 | 0 | 10 |
| num_tutorias | int64 | 0 | 0 | 10 |
| num_asesorias | int64 | 0 | 0 | 10 |
| num_incidencias | int64 | 0 | 0 | 7 |
| num_permisos | int64 | 0 | 0 | 9 |
| recursamientos | int64 | 0 | 0 | 7 |
| rezago_materias | int64 | 0 | 0 | 8 |

## Distribucion de estatus academico

| estatus_academico | registros |
| --- | --- |
| Regular | 854 |
| Baja Temporal | 73 |
| Irregular | 73 |

## Estadistica descriptiva de variables numericas

| variable | mean | std | min | 25% | 50% | 75% | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| promedio_general | 76.01 | 11.24 | 41 | 68.53 | 76.15 | 84.41 | 98 |
| promedio_periodo | 72.55 | 14.59 | 26.1 | 63.06 | 72.56 | 83.19 | 100 |
| materias_aprobadas | 19.47 | 12.23 | 1 | 9 | 19 | 28 | 51 |
| materias_reprobadas | 1.214 | 1.421 | 0 | 0 | 1 | 2 | 8 |
| materias_en_curso | 5.121 | 1.804 | 0 | 4 | 5 | 6 | 8 |
| creditos_acumulados | 125 | 75.58 | 11 | 57 | 123 | 189 | 276 |
| porcentaje_avance | 45.81 | 27.67 | 3.9 | 21.04 | 45.08 | 69.19 | 98.15 |
| porcentaje_asistencia | 63.03 | 23.27 | 0.01 | 49.72 | 66.32 | 80.75 | 99 |
| faltas | 11 | 7.054 | 0 | 6 | 10 | 15 | 32 |
| retardos | 2.093 | 1.536 | 0 | 1 | 2 | 3 | 10 |
| num_tutorias | 2.619 | 1.735 | 0 | 1 | 2 | 4 | 9 |
| num_asesorias | 1.106 | 1.254 | 0 | 0 | 1 | 2 | 9 |
| num_incidencias | 0.345 | 0.6786 | 0 | 0 | 0 | 1 | 6 |
| num_permisos | 1.428 | 1.386 | 0 | 0 | 1 | 2 | 8 |
| recursamientos | 0.629 | 1.009 | 0 | 0 | 0 | 1 | 6 |
| rezago_materias | 1.356 | 1.324 | 0 | 0 | 1 | 2 | 8 |
| creditos_inscritos_periodo | 33.37 | 12.59 | 0 | 28 | 34 | 41 | 56 |
| creditos_aprobados_periodo | 31.04 | 13.06 | 0 | 25 | 32 | 39 | 56 |
| creditos_totales_plan | 272.9 | 6.58 | 264 | 270 | 270 | 282 | 282 |
| periodos_cursados | 5.034 | 2.85 | 1 | 2.75 | 5 | 7 | 12 |
| periodos_sin_inscripcion | 0.274 | 0.5893 | 0 | 0 | 0 | 0 | 4 |
| materias_reprobadas_periodo | 0.382 | 0.8525 | 0 | 0 | 0 | 0 | 7 |
| materias_reprobadas_acumuladas | 1.214 | 1.421 | 0 | 0 | 1 | 2 | 8 |
| materias_en_curso_periodo | 5.121 | 1.804 | 0 | 4 | 5 | 6 | 8 |
| tendencia_promedio | -3.545 | 9.168 | -31.64 | -9.69 | -3.245 | 2.518 | 25.54 |
| varianza_calificaciones | 29.4 | 15.15 | 3.13 | 18.52 | 26.66 | 36.94 | 85 |
| tutorias_abiertas | 1.189 | 1.209 | 0 | 0 | 1 | 2 | 7 |
| tutorias_cerradas | 1.43 | 1.305 | 0 | 0 | 1 | 2 | 8 |
| compromisos_pendientes | 1.146 | 1.368 | 0 | 0 | 1 | 2 | 9 |
| compromisos_cumplidos | 1.716 | 1.714 | 0 | 0 | 1 | 2 | 10 |

## Correlaciones fuertes

Umbral usado: `abs(correlacion) >= 0.85`.

| variable_a | variable_b | correlation |
| --- | --- | --- |
| materias_reprobadas | materias_reprobadas_acumuladas | 1 |
| materias_en_curso | materias_en_curso_periodo | 1 |
| creditos_acumulados | porcentaje_avance | 0.9989 |
| materias_aprobadas | creditos_acumulados | 0.9659 |
| materias_aprobadas | porcentaje_avance | 0.9653 |
| porcentaje_avance | periodos_cursados | 0.9534 |
| creditos_acumulados | periodos_cursados | 0.9516 |
| num_permisos | permisos_aprobados | 0.9454 |
| porcentaje_asistencia | faltas | -0.9342 |
| creditos_inscritos_periodo | materias_en_curso_periodo | 0.9278 |
| materias_en_curso | creditos_inscritos_periodo | 0.9278 |
| materias_aprobadas | periodos_cursados | 0.917 |
| creditos_inscritos_periodo | creditos_aprobados_periodo | 0.9096 |

## Outliers por regla IQR

| variable | outlier_count | outlier_rate | lower_bound | upper_bound |
| --- | --- | --- | --- | --- |
| promedio_general | 3 | 0.003 | 44.72 | 108.2 |
| promedio_periodo | 5 | 0.005 | 32.87 | 113.4 |
| materias_aprobadas | 0 | 0 | -19.5 | 56.5 |
| materias_reprobadas | 18 | 0.018 | -3 | 5 |
| materias_en_curso | 73 | 0.073 | 1 | 9 |
| creditos_acumulados | 0 | 0 | -141 | 387 |
| porcentaje_avance | 0 | 0 | -51.19 | 141.4 |
| porcentaje_asistencia | 8 | 0.008 | 3.172 | 127.3 |
| faltas | 18 | 0.018 | -7.5 | 28.5 |
| retardos | 13 | 0.013 | -2 | 6 |
| num_tutorias | 1 | 0.001 | -3.5 | 8.5 |
| num_asesorias | 10 | 0.01 | -3 | 5 |
| num_incidencias | 15 | 0.015 | -1.5 | 2.5 |
| num_permisos | 16 | 0.016 | -3 | 5 |
| recursamientos | 62 | 0.062 | -1.5 | 2.5 |
| rezago_materias | 9 | 0.009 | -3 | 5 |
| creditos_inscritos_periodo | 73 | 0.073 | 8.5 | 60.5 |
| creditos_aprobados_periodo | 79 | 0.079 | 4 | 60 |
| creditos_totales_plan | 0 | 0 | 252 | 300 |
| periodos_cursados | 0 | 0 | -3.625 | 13.38 |
| periodos_sin_inscripcion | 214 | 0.214 | 0 | 0 |
| materias_reprobadas_periodo | 235 | 0.235 | 0 | 0 |
| materias_reprobadas_acumuladas | 18 | 0.018 | -3 | 5 |
| materias_en_curso_periodo | 73 | 0.073 | 1 | 9 |
| tendencia_promedio | 6 | 0.006 | -28 | 20.83 |
| varianza_calificaciones | 29 | 0.029 | -9.126 | 64.58 |
| tutorias_abiertas | 5 | 0.005 | -3 | 5 |
| tutorias_cerradas | 16 | 0.016 | -3 | 5 |
| compromisos_pendientes | 13 | 0.013 | -3 | 5 |
| compromisos_cumplidos | 43 | 0.043 | -3 | 5 |

## Comparacion por programa

| programa | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| Ingenieria Agroindustrial | 75.13 | 62.07 | 1.5 | 1.24 |
| Ingenieria Biomedica | 76.42 | 65.37 | 1.3 | 1.17 |
| Ingenieria en Desarrollo de Software | 76.47 | 61.75 | 1.36 | 1.2 |
| Ingenieria en Energia | 75.55 | 63.1 | 1.3 | 1.27 |

## Comparacion por cohorte

| cohorte | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| 2020 | 74.71 | 64.68 | 1.54 | 1.75 |
| 2021 | 75.36 | 60.85 | 1.49 | 1.48 |
| 2022 | 76.3 | 62.57 | 1.42 | 1.24 |
| 2023 | 77.44 | 63.34 | 1.14 | 0.82 |
| 2024 | 75.74 | 64.65 | 1.19 | 0.81 |

## Comparacion por periodo

| id_periodo | promedio_general | porcentaje_asistencia | rezago_materias | materias_reprobadas |
| --- | --- | --- | --- | --- |
| 2022-2 | 75.76 | 62.08 | 1.15 | 0.92 |
| 2023-1 | 76.1 | 62.84 | 1.14 | 0.88 |
| 2023-2 | 74.67 | 63.17 | 1.3 | 1.11 |
| 2024-1 | 76.16 | 63.38 | 1.4 | 1.27 |
| 2024-2 | 76.62 | 63.67 | 1.42 | 1.3 |
| 2025-1 | 76.61 | 62.29 | 1.56 | 1.58 |

## Graficas generadas

- `data/reports/figures/hist_promedio_general.svg`
- `data/reports/figures/hist_porcentaje_asistencia.svg`
- `data/reports/figures/hist_rezago_materias.svg`
- `data/reports/figures/correlation_heatmap.svg`

## Hallazgos accionables

- El dataset sintetico no presenta nulos, por lo que la primera version del pipeline puede enfocarse en escalado, colinealidad y seleccion de variables.
- `materias_aprobadas`, `creditos_acumulados` y `porcentaje_avance` son variables derivadas entre si. Conviene conservar solo una para clustering.
- `porcentaje_asistencia` y `faltas` describen dimensiones muy cercanas en sentido inverso. Para la primera version se conserva el porcentaje por ser normalizado e interpretable.
- Las variables de acompanamiento (`num_tutorias`, `num_asesorias`) e incidencias deben mantenerse porque ayudan a diferenciar perfiles academicos mas alla del promedio.
