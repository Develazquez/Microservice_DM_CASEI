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
| pca_90 | 3 | 17366 | 0.17536 | 158.35 | 2.0209 | 73 | 644 | 2.6 |

## Comparativo completo

| representation | k | inertia | silhouette | calinski_harabasz | davies_bouldin | min_cluster_size | max_cluster_size | n_samples | iterations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pca_90 | 2 | 19794 | 0.24873 | 155.67 | 2.2375 | 216 | 784 | 1000 | 9 |
| pca_90 | 3 | 17366 | 0.17536 | 158.35 | 2.0209 | 73 | 644 | 1000 | 13 |
| pca_90 | 4 | 16243 | 0.10013 | 135.7 | 2.263 | 72 | 394 | 1000 | 16 |
| pca_90 | 5 | 15430 | 0.092839 | 120.12 | 2.177 | 72 | 292 | 1000 | 39 |
| pca_90 | 6 | 14868 | 0.088391 | 107.16 | 2.1999 | 72 | 268 | 1000 | 24 |
| pca_90 | 7 | 14387 | 0.089609 | 97.719 | 2.1041 | 65 | 261 | 1000 | 13 |
| pca_90 | 8 | 13948 | 0.087604 | 90.775 | 2.1313 | 46 | 227 | 1000 | 22 |
| scaled_features | 2 | 21908 | 0.23721 | 140.85 | 2.3568 | 216 | 784 | 1000 | 11 |
| scaled_features | 3 | 19476 | 0.17027 | 141.4 | 2.1192 | 73 | 666 | 1000 | 14 |
| scaled_features | 4 | 18353 | 0.086318 | 120.24 | 2.4125 | 72 | 396 | 1000 | 32 |
| scaled_features | 5 | 17524 | 0.081765 | 106.12 | 2.3187 | 72 | 296 | 1000 | 18 |
| scaled_features | 6 | 16952 | 0.078451 | 94.372 | 2.3193 | 71 | 285 | 1000 | 11 |
| scaled_features | 7 | 16444 | 0.079753 | 86.117 | 2.2159 | 52 | 274 | 1000 | 23 |
| scaled_features | 8 | 15930 | 0.076226 | 80.69 | 2.2992 | 36 | 252 | 1000 | 36 |

## Graficas generadas

- `data/reports/figures/k_inertia_scaled.svg`
- `data/reports/figures/k_silhouette_scaled.svg`
- `data/reports/figures/k_inertia_pca90.svg`
- `data/reports/figures/k_silhouette_pca90.svg`

## Decision tecnica

Se selecciona `K=3` usando la representacion `pca_90`. La decision combina metricas internas y balance de tamanos. Si en una revision academica se prioriza interpretabilidad por encima de compactacion, debe compararse este resultado con `scaled_features` antes de nombrar perfiles definitivos.
