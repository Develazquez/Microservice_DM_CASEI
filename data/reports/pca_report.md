# Fase 4 - PCA

## Preparacion

- Variables de entrada: 25
- Registros usados: 999
- Escalado aplicado: media 0 y desviacion estandar 1 con calculo propio en numpy/pandas.
- Metodo PCA: SVD con `numpy.linalg.svd`.

## Varianza explicada

| component | explained_variance_ratio | cumulative_explained_variance_ratio |
| --- | --- | --- |
| PC1 | 0.3107 | 0.3107 |
| PC2 | 0.1575 | 0.4682 |
| PC3 | 0.1127 | 0.5809 |
| PC4 | 0.07559 | 0.6565 |
| PC5 | 0.05046 | 0.7069 |
| PC6 | 0.04359 | 0.7505 |
| PC7 | 0.04218 | 0.7927 |
| PC8 | 0.03618 | 0.8289 |
| PC9 | 0.02997 | 0.8588 |
| PC10 | 0.02698 | 0.8858 |
| PC11 | 0.02559 | 0.9114 |
| PC12 | 0.02487 | 0.9363 |
| PC13 | 0.01746 | 0.9537 |
| PC14 | 0.01564 | 0.9694 |
| PC15 | 0.01056 | 0.9799 |
| PC16 | 0.004157 | 0.9841 |
| PC17 | 0.003688 | 0.9878 |
| PC18 | 0.003474 | 0.9913 |
| PC19 | 0.002553 | 0.9938 |
| PC20 | 0.002166 | 0.996 |
| PC21 | 0.001572 | 0.9975 |
| PC22 | 0.001136 | 0.9987 |
| PC23 | 0.0005657 | 0.9992 |
| PC24 | 0.0004319 | 0.9997 |
| PC25 | 0.0003188 | 1 |

## Componentes requeridos

- Componentes para explicar al menos 90% de varianza: 11
- Componentes para explicar al menos 95% de varianza: 13

## Variables dominantes por componente

| component | top_features |
| --- | --- |
| PC1 | compromisos_pendientes, tutorias_abiertas, materias_reprobadas_periodo, porcentaje_asistencia, materias_reprobadas_acumuladas |
| PC2 | porcentaje_avance, creditos_aprobados_periodo, compromisos_cumplidos, creditos_inscritos_periodo, bandera_dato_incompleto |
| PC3 | rezago_materias, periodos_sin_inscripcion, porcentaje_asistencia, retardos, recursamientos |
| PC4 | materias_en_curso_periodo, bandera_dato_incompleto, creditos_inscritos_periodo, tutorias_cerradas, compromisos_cumplidos |
| PC5 | tutorias_cerradas, tendencia_promedio, compromisos_cumplidos, creditos_inscritos_periodo, promedio_periodo |

## Artefactos generados

- `artifacts/scaler_params.csv`
- `artifacts/pca_components.csv`
- `artifacts/pca_metadata.json`
- `data/processed/scaled_features.csv`
- `data/processed/pca_scores.csv`
- `data/processed/pca_scores_90.csv`
- `data/processed/pca_scores_95.csv`

## Decision tecnica

PCA puede usarse como entrada compacta para clustering porque alcanza 90% de varianza con una reduccion relevante de dimensiones. Aun asi, se debe comparar contra las variables escaladas originales en la fase de seleccion de K.

## Criterio de aceptacion

PCA queda reproducible porque se guardan parametros de escalado, componentes, varianza explicada, scores transformados y metadata del proceso.
