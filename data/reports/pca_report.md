# Fase 4 - PCA

## Preparacion

- Variables de entrada: 25
- Registros usados: 1000
- Escalado aplicado: media 0 y desviacion estandar 1 con calculo propio en numpy/pandas.
- Metodo PCA: SVD con `numpy.linalg.svd`.

## Varianza explicada

| component | explained_variance_ratio | cumulative_explained_variance_ratio |
| --- | --- | --- |
| PC1 | 0.1923 | 0.1923 |
| PC2 | 0.1398 | 0.3321 |
| PC3 | 0.08559 | 0.4177 |
| PC4 | 0.06503 | 0.4827 |
| PC5 | 0.06271 | 0.5454 |
| PC6 | 0.05651 | 0.6019 |
| PC7 | 0.048 | 0.6499 |
| PC8 | 0.04511 | 0.6951 |
| PC9 | 0.03912 | 0.7342 |
| PC10 | 0.03673 | 0.7709 |
| PC11 | 0.03444 | 0.8053 |
| PC12 | 0.03076 | 0.8361 |
| PC13 | 0.02828 | 0.8644 |
| PC14 | 0.02618 | 0.8906 |
| PC15 | 0.02471 | 0.9153 |
| PC16 | 0.01857 | 0.9338 |
| PC17 | 0.01794 | 0.9518 |
| PC18 | 0.01481 | 0.9666 |
| PC19 | 0.01318 | 0.9798 |
| PC20 | 0.01188 | 0.9916 |
| PC21 | 0.00343 | 0.9951 |
| PC22 | 0.002764 | 0.9978 |
| PC23 | 0.001275 | 0.9991 |
| PC24 | 0.0006015 | 0.9997 |
| PC25 | 0.000289 | 1 |

## Componentes requeridos

- Componentes para explicar al menos 90% de varianza: 15
- Componentes para explicar al menos 95% de varianza: 17

## Variables dominantes por componente

| component | top_features |
| --- | --- |
| PC1 | creditos_aprobados_periodo, materias_reprobadas_acumuladas, materias_reprobadas_periodo, porcentaje_asistencia, rezago_materias |
| PC2 | materias_en_curso_periodo, creditos_inscritos_periodo, materias_reprobadas_acumuladas, promedio_periodo, bandera_dato_incompleto |
| PC3 | porcentaje_avance, periodos_cursados, promedio_periodo, materias_reprobadas_acumuladas, recursamientos |
| PC4 | tutorias_cerradas, compromisos_cumplidos, tutorias_abiertas, compromisos_pendientes, materias_reprobadas_periodo |
| PC5 | compromisos_pendientes, tutorias_abiertas, compromisos_cumplidos, tutorias_cerradas, tendencia_promedio |

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
