# Fase 6 - Entrenamiento K-Means

## Modelo entrenado

- Algoritmo: K-Means.
- Implementacion: numpy, con inicializacion tipo k-means++.
- Representacion usada: `pca_90`.
- K final: 2.
- Registros asignados: 999.
- Inercia final: 17361.09891.
- Silhouette: 0.32558.
- Calinski-Harabasz: 310.17692.
- Davies-Bouldin: 1.46327.

## Distribucion e interpretacion inicial de clusters

| cluster | registros | promedio_general | porcentaje_asistencia | materias_reprobadas | rezago_materias | variables_distintivas | perfil_sugerido |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 812 | 79.041 | 75.47 | 0.21675 | 1.5443 | varianza_calificaciones (-9.15), porcentaje_asistencia (+3.54), promedio_periodo (+3.27), promedio_general (+2.33), tendencia_promedio (+1.00) | Regular / seguimiento preventivo |
| 1 | 187 | 66.58 | 56.539 | 2.1283 | 1.738 | varianza_calificaciones (+39.74), porcentaje_asistencia (-15.39), promedio_periodo (-12.62), promedio_general (-10.13), tendencia_promedio (-3.85) | Riesgo academico moderado |

## Artefactos generados

- `data/processed/cluster_assignments.csv`
- `artifacts/kmeans_centroids.csv`
- `artifacts/kmeans_metadata.json`
- `data/reports/cluster_summary.csv`
- `data/reports/figures/cluster_scatter_pc1_pc2.svg`

## Uso esperado

`cluster_assignments.csv` es la salida que en fases posteriores podra persistirse como historial de inferencias. Cada fila conserva estudiante, periodo, cluster asignado, distancia al centroide y un score simple de pertenencia.

## Limitacion actual

Las etiquetas de perfil son interpretaciones iniciales basadas en medias de variables academicas. Deben validarse con dominio academico antes de mostrarse a usuarios finales.
