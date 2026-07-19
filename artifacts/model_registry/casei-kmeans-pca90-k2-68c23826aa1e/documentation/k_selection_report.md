# Fase 5 - Seleccion de K

## Configuracion

- Rango evaluado: K=2 a K=8
- Inicializaciones por K: 20
- Representaciones comparadas:
  - `scaled_features`: variables seleccionadas y escaladas.
  - `pca_90`: componentes PCA que explican al menos 90% de la varianza.

## Metricas calculadas

- Inercia: menor es mejor, sirve para metodo del codo.
- Silhouette: mayor es mejor, mide separacion y cohesion.
- Calinski-Harabasz: mayor es mejor.
- Davies-Bouldin: menor es mejor.
- Balance de tamanos: evita seleccionar K con clusters residuales demasiado pequenos.

## Resultado recomendado

| representation | k | inertia | silhouette | calinski_harabasz | davies_bouldin | min_cluster_size | max_cluster_size | combined_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pca_90 | 2 | 21597 | 0.34664 | 443.47 | 1.3958 | 244 | 1033 | 1.3 |

## Comparativo completo

| representation | k | inertia | silhouette | calinski_harabasz | davies_bouldin | min_cluster_size | max_cluster_size | n_samples | iterations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pca_90 | 2 | 21597 | 0.34664 | 443.47 | 1.3958 | 244 | 1033 | 1277 | 4 |
| pca_90 | 3 | 18724 | 0.23809 | 353.28 | 1.4378 | 191 | 849 | 1277 | 18 |
| pca_90 | 4 | 17227 | 0.15817 | 292.65 | 1.8537 | 190 | 473 | 1277 | 26 |
| pca_90 | 5 | 15904 | 0.15449 | 264.01 | 1.9195 | 102 | 432 | 1277 | 14 |
| pca_90 | 6 | 15015 | 0.15074 | 238.59 | 1.8602 | 98 | 397 | 1277 | 15 |
| pca_90 | 7 | 14371 | 0.15089 | 217.06 | 1.7864 | 50 | 369 | 1277 | 22 |
| pca_90 | 8 | 13843 | 0.13375 | 199.92 | 1.8569 | 54 | 273 | 1277 | 23 |
| scaled_features | 2 | 24408 | 0.32755 | 392.68 | 1.5137 | 252 | 1025 | 1277 | 8 |
| scaled_features | 3 | 21533 | 0.21474 | 307.43 | 1.5506 | 191 | 849 | 1277 | 11 |
| scaled_features | 4 | 20036 | 0.13726 | 251.8 | 1.9971 | 190 | 467 | 1277 | 10 |
| scaled_features | 5 | 18654 | 0.13436 | 226.23 | 2.0776 | 109 | 431 | 1277 | 22 |
| scaled_features | 6 | 17748 | 0.12734 | 203.05 | 1.9742 | 113 | 328 | 1277 | 14 |
| scaled_features | 7 | 16970 | 0.13272 | 186.52 | 1.9157 | 38 | 369 | 1277 | 21 |
| scaled_features | 8 | 16457 | 0.1366 | 170.39 | 1.9706 | 29 | 385 | 1277 | 13 |

## Graficas generadas

- `data/reports/figures/k_inertia_scaled.svg`
- `data/reports/figures/k_silhouette_scaled.svg`
- `data/reports/figures/k_inertia_pca90.svg`
- `data/reports/figures/k_silhouette_pca90.svg`

## Decision tecnica

Se selecciona `K=2` usando la representacion `pca_90`. La decision combina metricas internas y balance de tamanos. Si en una revision academica se prioriza interpretabilidad por encima de compactacion, debe compararse este resultado con `scaled_features` antes de nombrar perfiles definitivos.
