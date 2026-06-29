# Fase 6 - Entrenamiento K-Means

## Modelo entrenado

- Algoritmo: K-Means.
- Implementacion: numpy, con inicializacion tipo k-means++.
- Representacion usada: `pca_90`.
- K final: 3.
- Registros asignados: 1000.
- Inercia final: 17365.55500.
- Silhouette: 0.17536.
- Calinski-Harabasz: 158.34998.
- Davies-Bouldin: 2.02087.

## Distribucion e interpretacion inicial de clusters

| cluster | registros | promedio_general | porcentaje_asistencia | materias_reprobadas | rezago_materias | variables_distintivas | perfil_sugerido |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 283 | 67.482 | 57.874 | 2.5406 | 1.9965 | promedio_periodo (-14.05), promedio_general (-8.53), tendencia_promedio (-5.43), porcentaje_asistencia (-5.16), varianza_calificaciones (+4.36) | Riesgo academico moderado |
| 1 | 644 | 79.847 | 71.13 | 0.6413 | 0.91925 | porcentaje_asistencia (+8.10), promedio_periodo (+6.11), creditos_aprobados_periodo (+4.91), promedio_general (+3.83), creditos_inscritos_periodo (+2.97) | Regular / seguimiento preventivo |
| 2 | 73 | 75.284 | 11.618 | 1.1233 | 2.726 | porcentaje_asistencia (-51.42), creditos_inscritos_periodo (-33.37), creditos_aprobados_periodo (-31.04), materias_en_curso_periodo (-5.12), porcentaje_avance (-3.94) | Riesgo academico moderado |

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
