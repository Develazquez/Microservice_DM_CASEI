# Fase 4 - PCA

## Preparacion

- Variables de entrada: 25
- Registros usados: 1277
- Escalado aplicado: media 0 y desviacion estandar 1 con calculo propio en numpy/pandas.
- Metodo PCA: SVD con `numpy.linalg.svd`.

## Varianza explicada

| component | explained_variance_ratio | cumulative_explained_variance_ratio |
| --- | --- | --- |
| PC1 | 0.3201 | 0.3201 |
| PC2 | 0.1236 | 0.4436 |
| PC3 | 0.08947 | 0.5331 |
| PC4 | 0.07096 | 0.6041 |
| PC5 | 0.05864 | 0.6627 |
| PC6 | 0.05162 | 0.7143 |
| PC7 | 0.04251 | 0.7568 |
| PC8 | 0.04056 | 0.7974 |
| PC9 | 0.03161 | 0.829 |
| PC10 | 0.0296 | 0.8586 |
| PC11 | 0.02792 | 0.8865 |
| PC12 | 0.02524 | 0.9118 |
| PC13 | 0.02361 | 0.9354 |
| PC14 | 0.01933 | 0.9547 |
| PC15 | 0.01699 | 0.9717 |
| PC16 | 0.009654 | 0.9813 |
| PC17 | 0.004597 | 0.9859 |
| PC18 | 0.003999 | 0.9899 |
| PC19 | 0.003499 | 0.9934 |
| PC20 | 0.002531 | 0.996 |
| PC21 | 0.001789 | 0.9978 |
| PC22 | 0.0009099 | 0.9987 |
| PC23 | 0.0005567 | 0.9992 |
| PC24 | 0.0004366 | 0.9997 |
| PC25 | 0.000338 | 1 |

## Componentes requeridos

- Componentes para explicar al menos 90% de varianza: 12
- Componentes para explicar al menos 95% de varianza: 14

## Variables dominantes por componente

| component | top_features |
| --- | --- |
| PC1 | compromisos_pendientes, tutorias_abiertas, porcentaje_asistencia, materias_reprobadas_periodo, materias_reprobadas_acumuladas |
| PC2 | porcentaje_avance, bandera_dato_incompleto, materias_en_curso_periodo, periodos_cursados, creditos_aprobados_periodo |
| PC3 | creditos_inscritos_periodo, compromisos_cumplidos, tutorias_cerradas, materias_en_curso_periodo, bandera_dato_incompleto |
| PC4 | periodos_sin_inscripcion, rezago_materias, promedio_periodo, porcentaje_asistencia, recursamientos |
| PC5 | tutorias_cerradas, creditos_inscritos_periodo, compromisos_cumplidos, varianza_calificaciones, creditos_aprobados_periodo |

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
