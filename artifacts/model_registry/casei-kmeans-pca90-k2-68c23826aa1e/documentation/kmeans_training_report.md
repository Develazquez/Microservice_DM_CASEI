# Fase 6 - Entrenamiento K-Means

## Modelo entrenado

- Algoritmo: K-Means.
- Implementacion: numpy, con inicializacion tipo k-means++.
- Representacion usada: `pca_90`.
- K final: 2.
- Registros asignados: 1277.
- Inercia final: 21596.52331.
- Silhouette: 0.34664.
- Calinski-Harabasz: 443.46799.
- Davies-Bouldin: 1.39579.

## Distribucion e interpretacion inicial de clusters

| cluster | registros | promedio_general | porcentaje_asistencia | materias_reprobadas | rezago_materias | variables_distintivas | perfil_sugerido |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1033 | 79.279 | 78.741 | 0.24105 | 1.0581 | varianza_calificaciones (-5.91), porcentaje_asistencia (+3.79), promedio_periodo (+3.66), promedio_general (+2.53), tendencia_promedio (+1.29) | Regular / seguimiento preventivo |
| 1 | 244 | 66.044 | 58.931 | 2.1926 | 2.6926 | varianza_calificaciones (+25.02), porcentaje_asistencia (-16.03), promedio_periodo (-14.10), promedio_general (-10.71), tendencia_promedio (-4.99) | Riesgo academico moderado |

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
