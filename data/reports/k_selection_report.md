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
| pca_90 | 2 | 17361 | 0.32558 | 310.18 | 1.4633 | 187 | 812 | 1.35 |

## Comparativo completo

| representation | k | inertia | silhouette | calinski_harabasz | davies_bouldin | min_cluster_size | max_cluster_size | n_samples | iterations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pca_90 | 2 | 17361 | 0.32558 | 310.18 | 1.4633 | 187 | 812 | 999 | 6 |
| pca_90 | 3 | 15091 | 0.19879 | 253.17 | 1.5602 | 182 | 630 | 999 | 14 |
| pca_90 | 4 | 13372 | 0.19369 | 232.9 | 1.5906 | 148 | 507 | 999 | 23 |
| pca_90 | 5 | 12150 | 0.18697 | 217.05 | 1.5694 | 108 | 350 | 999 | 10 |
| pca_90 | 6 | 11111 | 0.1868 | 208.25 | 1.5637 | 63 | 305 | 999 | 26 |
| pca_90 | 7 | 10349 | 0.19718 | 198.3 | 1.5375 | 50 | 296 | 999 | 9 |
| pca_90 | 8 | 9881.4 | 0.19853 | 184.54 | 1.5494 | 50 | 296 | 999 | 15 |
| scaled_features | 2 | 19568 | 0.31764 | 275.48 | 1.5504 | 180 | 819 | 999 | 5 |
| scaled_features | 3 | 17295 | 0.17587 | 221.16 | 1.6814 | 178 | 634 | 999 | 9 |
| scaled_features | 4 | 15563 | 0.17114 | 200.57 | 1.7178 | 146 | 509 | 999 | 9 |
| scaled_features | 5 | 14341 | 0.16338 | 184.26 | 1.7165 | 111 | 357 | 999 | 16 |
| scaled_features | 6 | 13309 | 0.16539 | 174.07 | 1.7238 | 102 | 297 | 999 | 13 |
| scaled_features | 7 | 12440 | 0.17268 | 166.6 | 1.673 | 50 | 298 | 999 | 15 |
| scaled_features | 8 | 11974 | 0.17184 | 153.73 | 1.7008 | 50 | 298 | 999 | 19 |

## Graficas generadas

- `data/reports/figures/k_inertia_scaled.svg`
- `data/reports/figures/k_silhouette_scaled.svg`
- `data/reports/figures/k_inertia_pca90.svg`
- `data/reports/figures/k_silhouette_pca90.svg`

## Decision tecnica

Se selecciona `K=2` usando la representacion `pca_90`. La decision combina metricas internas y balance de tamanos. Si en una revision academica se prioriza interpretabilidad por encima de compactacion, debe compararse este resultado con `scaled_features` antes de nombrar perfiles definitivos.
