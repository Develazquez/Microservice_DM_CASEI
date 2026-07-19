# Fase 7 - Interpretacion de perfiles academicos

## Objetivo

Traducir los clusters numericos del modelo K-Means a perfiles academicos comprensibles para tutores, coordinadores y analitica institucional.

## Modelo interpretado

- Algoritmo: K-Means.
- Representacion seleccionada: `pca_90`.
- K interpretado: 2.
- Silhouette: 0.34664.
- Davies-Bouldin: 1.39579.
- Calinski-Harabasz: 443.46799.

Los centroides persistidos pertenecen a la representacion PCA seleccionada; por eso la lectura academica se deriva tambien de medias de variables originales contra el promedio global.

## Catalogo provisional de perfiles

| cluster | perfil_academico | prioridad_tutorial | registros | porcentaje_registros | rasgos_dominantes | lectura_funcional | acciones_sugeridas | cautela_interpretacion | promedio_general | promedio_periodo | porcentaje_asistencia | materias_reprobadas_periodo | materias_reprobadas_acumuladas | rezago_materias | recursamientos | periodos_sin_inscripcion | num_incidencias | tutorias_abiertas | compromisos_pendientes | varianza_calificaciones |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Regular / seguimiento preventivo | Baja-media | 1033 | 80.89 | compromisos_pendientes bajo (-0.41 DE); tutorias_abiertas bajo (-0.40 DE); materias_reprobadas_periodo bajo (-0.39 DE); promedio_periodo alto (+0.36 DE); porcentaje_asistencia alto (+0.35 DE); materias_reprobadas_acumuladas bajo (-0.34 DE) | Trayectoria mayormente estable; requiere monitoreo ordinario y seguimiento preventivo. | Mantener monitoreo regular, detectar cambios de tendencia y atender outliers de baja pertenencia. | Mantener vigilancia de casos con baja pertenencia al cluster o cambios recientes de tendencia. | 79.279 | 81.018 | 78.741 | 0.0542 | 0.241 | 1.0581 | 0.0523 | 1.9574 | 0.0348 | 0.1355 | 0.1588 | 12.693 |
| 1 | Riesgo academico moderado | Media-alta | 244 | 19.11 | compromisos_pendientes alto (+1.75 DE); tutorias_abiertas alto (+1.68 DE); materias_reprobadas_periodo alto (+1.65 DE); porcentaje_asistencia bajo (-1.47 DE); materias_reprobadas_acumuladas alto (+1.45 DE); promedio_periodo bajo (-1.37 DE) | Grupo con senales consistentes de seguimiento: calificaciones menores, baja asistencia o rezago medio. | Programar seguimiento preventivo, revisar asistencia, reprobadas recientes y compromisos pendientes. | Usar como priorizacion de acompanamiento, no como diagnostico definitivo. | 66.044 | 63.266 | 58.931 | 1.1762 | 2.1926 | 2.6926 | 0.5246 | 2.2582 | 1.1516 | 2.0287 | 2.373 | 43.617 |

## Centroides del modelo

| cluster | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 | PC7 | PC8 | PC9 | PC10 | PC11 | PC12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | -1.1755 | -0.0055462 | 0.0028546 | -0.077062 | -0.0027066 | -0.018382 | 0.0013251 | 0.0088553 | -0.010302 | 0.013204 | -0.001322 | -0.028775 |
| 1 | 4.9768 | 0.023481 | -0.012085 | 0.32625 | 0.011458 | 0.077821 | -0.0056098 | -0.03749 | 0.043614 | -0.055899 | 0.0055969 | 0.12182 |

## Variables mas distintivas

| cluster | variable | media_cluster | media_global | diferencia | diferencia_estandarizada | lectura |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | compromisos_pendientes | 2.373 | 0.58183 | 1.7911 | 1.7454 | compromisos pendientes estimados: mas compromisos pendientes |
| 1 | tutorias_abiertas | 2.0287 | 0.49726 | 1.5314 | 1.6799 | tutorias abiertas estimadas: mas seguimiento pendiente |
| 1 | materias_reprobadas_periodo | 1.1762 | 0.2686 | 0.90763 | 1.649 | reprobadas del periodo: mas reprobadas recientes |
| 1 | porcentaje_asistencia | 58.931 | 74.956 | -16.025 | -1.4697 | asistencia estimada: menor asistencia |
| 1 | materias_reprobadas_acumuladas | 2.1926 | 0.61394 | 1.5787 | 1.4534 | reprobadas acumuladas: mas reprobadas acumuladas |
| 1 | promedio_periodo | 63.266 | 77.363 | -14.097 | -1.3744 | promedio del periodo: desempeno reciente menor |
| 1 | num_asesorias | 3.127 | 1.4456 | 1.6815 | 1.3015 | asesorias estimadas: mas asesorias |
| 1 | promedio_general | 66.044 | 76.75 | -10.706 | -1.2373 | promedio general: desempeno acumulado menor |
| 1 | num_incidencias | 1.1516 | 0.24824 | 0.9034 | 1.2029 | incidencias estimadas: mas incidencias |
| 1 | rezago_materias | 2.6926 | 1.3704 | 1.3222 | 1.0093 | rezago en materias: mayor rezago |
| 1 | recursamientos | 0.52459 | 0.14252 | 0.38207 | 0.91622 | recursamientos: mas recursamientos |
| 1 | creditos_aprobados_periodo | 2.3279 | 6.2655 | -3.9376 | -0.83495 | creditos aprobados: menos creditos aprobados |
| 1 | permisos_aprobados | 2.2418 | 1.419 | 0.82285 | 0.82225 | permisos aprobados estimados: mas permisos aprobados |
| 1 | retardos | 2.2459 | 1.3868 | 0.85906 | 0.80317 | retardos estimados: mas retardos |
| 1 | tendencia_promedio | -4.7826 | 0.2103 | -4.9929 | -0.61477 | tendencia del promedio: tendencia a la baja |
| 1 | varianza_calificaciones | 43.616 | 18.601 | 25.015 | 0.58742 | variacion de calificaciones: desempeno mas irregular |
| 1 | permisos_rechazados | 0.92213 | 0.59436 | 0.32777 | 0.55222 | permisos rechazados estimados: mas permisos rechazados |
| 1 | porcentaje_avance | 3.2187 | 5.2452 | -2.0265 | -0.48957 | avance curricular: menor avance del plan |
| 0 | compromisos_pendientes | 0.15876 | 0.58183 | -0.42307 | -0.41228 | compromisos pendientes estimados: menos compromisos pendientes |
| 0 | tutorias_abiertas | 0.13553 | 0.49726 | -0.36173 | -0.3968 | tutorias abiertas estimadas: menos seguimiento pendiente |

## Outliers candidatos

Se marcan como candidatos los registros en el percentil 95 o superior de distancia al centroide dentro de su propio cluster. Estos casos no son errores automaticamente; son trayectorias que conviene revisar con mayor contexto.

| id_estudiante | id_periodo | programa | cohorte | estatus_academico | cluster | distance_to_centroid | membership_score | promedio_general | porcentaje_asistencia | materias_reprobadas_acumuladas | rezago_materias | tendencia_promedio | perfil_academico | criterio_outlier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IDS20230189 | 2025-1 | Ingeniería en Desarrollo de Software | 2023 | Regular | 0 | 8.1776 | 0.10896 | 83.36 | 86.92 | 0 | 0 | -1.97 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20240225 | 2022-2 | Ingeniería en Energía | 2024 | Regular | 0 | 7.8771 | 0.11265 | 81.38 | 88.58 | 0 | 0 | 1.78 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20240370 | 2023-2 | Ingeniería Biomédica | 2024 | Irregular | 0 | 7.5229 | 0.11733 | 59.46 | 81.21 | 4 | 2 | 22.8 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20240149 | 2022-2 | Ingeniería en Energía | 2024 | Regular | 0 | 7.3281 | 0.12008 | 81.55 | 70.06 | 1 | 1 | -6.2 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IDS20200065 | 2022-1 | Ingeniería en Desarrollo de Software | 2020 | Baja Temporal | 0 | 7.2028 | 0.12191 | 94 | 50.89 | 0 | 2 | 0 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20200039 | 2025-1 | Ingeniería Agroindustrial | 2020 | Irregular | 0 | 7.1829 | 0.12221 | 87.89 | 74.82 | 0 | 3 | 1.23 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20220241 | 2022-1 | Ingeniería en Energía | 2022 | Regular | 0 | 7.1429 | 0.12281 | 70 | 77.86 | 0 | 0 |  | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20220218 | 2025-1 | Ingeniería Biomédica | 2022 | Baja Temporal | 0 | 7.0618 | 0.12404 | 82.19 | 51.5 | 1 | 2 | 4.63 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20200056 | 2022-1 | Ingeniería Biomédica | 2020 | Regular | 0 | 6.9065 | 0.12648 | 70 | 71.8 | 0 | 2 |  | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20220280 | 2023-1 | Ingeniería Agroindustrial | 2022 | Regular | 0 | 6.695 | 0.12995 | 80.48 | 88.91 | 1 | 0 | 1.33 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20200127 | 2023-1 | Ingeniería Agroindustrial | 2020 | Irregular | 0 | 6.6044 | 0.1315 | 85.33 | 72.75 | 0 | 3 | 0 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20200369 | 2025-1 | Ingeniería Agroindustrial | 2020 | Irregular | 0 | 6.5672 | 0.13215 | 83.3 | 69.23 | 0 | 3 | -1.6 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20200039 | 2022-2 | Ingeniería Agroindustrial | 2020 | Regular | 0 | 6.4604 | 0.13404 | 87.4 | 74.71 | 0 | 2 | 0 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20210083 | 2024-1 | Ingeniería Agroindustrial | 2021 | Irregular | 0 | 6.4431 | 0.13435 | 60.67 | 67.86 | 2 | 2 | 19.55 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20220232 | 2025-1 | Ingeniería Agroindustrial | 2022 | Irregular | 0 | 6.3438 | 0.13617 | 80.39 | 75.76 | 0 | 1 | 6.41 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20200231 | 2023-1 | Ingeniería en Energía | 2020 | Regular | 0 | 6.3185 | 0.13664 | 90.32 | 79.41 | 0 | 2 | -0.65 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20240302 | 2022-1 | Ingeniería Agroindustrial | 2024 | Irregular | 0 | 6.2946 | 0.13709 | 65.5 | 74.56 | 1 | 1 | 0 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20210004 | 2025-1 | Ingeniería Biomédica | 2021 | Regular | 0 | 6.2565 | 0.13781 | 88.15 | 74.82 | 0 | 2 | -5.35 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20220276 | 2023-1 | Ingeniería Agroindustrial | 2022 | Baja Temporal | 0 | 6.2366 | 0.13819 | 78.9 | 56.04 | 0 | 0 | -1.2 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20210271 | 2025-1 | Ingeniería en Energía | 2021 | Regular | 0 | 6.1693 | 0.13948 | 78.33 | 74.88 | 0 | 2 | 1.51 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |

## Estabilidad

Se calculo estabilidad con Indice Rand Ajustado (ARI) contra las asignaciones base. El ARI es invariante al cambio de nombre de etiquetas entre clusters.

- `periodo`: estabilidad aceptable promedio (ARI medio 0.7508).
- `semilla`: estabilidad alta promedio (ARI medio 0.9941).
- `submuestra_80`: estabilidad alta promedio (ARI medio 0.9653).
- Cautela: la prueba mas debil fue `periodo` / `2022-1` con ARI 0.0259; conviene revisar ese corte antes de usar el perfil como etiqueta estable.

| validacion | pruebas | ari_promedio | ari_minimo | ari_maximo | lectura |
| --- | --- | --- | --- | --- | --- |
| periodo | 7 | 0.75078 | 0.025948 | 1 | Aceptable |
| semilla | 5 | 0.99413 | 0.99266 | 1 | Alta |
| submuestra_80 | 5 | 0.96529 | 0.93935 | 0.98899 | Alta |

Detalle de pruebas:

| validacion | detalle | n_registros | ari_vs_base | distribucion_clusters |
| --- | --- | --- | --- | --- |
| semilla | seed=7 | 1277 | 0.99266 | C0=1035; C1=242 |
| semilla | seed=13 | 1277 | 0.99266 | C0=1035; C1=242 |
| semilla | seed=21 | 1277 | 0.99266 | C0=1035; C1=242 |
| semilla | seed=42 | 1277 | 1 | C0=1033; C1=244 |
| semilla | seed=99 | 1277 | 0.99266 | C0=242; C1=1035 |
| submuestra_80 | seed=101 | 1021 | 0.98165 | C0=239; C1=1038 |
| submuestra_80 | seed=202 | 1021 | 0.95684 | C0=256; C1=1021 |
| submuestra_80 | seed=303 | 1021 | 0.98899 | C0=1036; C1=241 |
| submuestra_80 | seed=404 | 1021 | 0.93935 | C0=1016; C1=261 |
| submuestra_80 | seed=505 | 1021 | 0.95961 | C0=1044; C1=233 |
| periodo | 2022-1 | 270 | 0.025948 | C0=128; C1=142 |
| periodo | 2022-2 | 263 | 0.64485 | C0=201; C1=62 |
| periodo | 2023-1 | 196 | 0.93495 | C0=49; C1=147 |
| periodo | 2023-2 | 185 | 1 | C0=42; C1=143 |
| periodo | 2024-1 | 141 | 0.96846 | C0=111; C1=30 |
| periodo | 2024-2 | 109 | 0.8376 | C0=89; C1=20 |
| periodo | 2025-1 | 113 | 0.84365 | C0=92; C1=21 |

## Reglas de lectura para tutores

- Usar el perfil como priorizacion de seguimiento, no como diagnostico automatico.
- Revisar primero estudiantes con prioridad tutorial alta o media-alta y baja pertenencia al cluster.
- Confirmar con informacion real de tutorias, asistencia e incidencias cuando exista, porque algunas senales actuales son estimadas desde cardex.
- En outliers, revisar la trayectoria individual antes de aplicar reglas generales del perfil.

## Reglas de lectura para coordinadores

- Interpretar K=2 como segmentacion operativa amplia; no fuerza todavia los cuatro perfiles visibles del dashboard.
- Comparar distribucion por programa, cohorte y periodo antes de tomar decisiones institucionales.
- Usar perfiles para planeacion de acompanamiento, carga tutorial y analitica, no para sanciones academicas.
- Validar nombres y acciones con dominio academico antes de exponerlos como etiquetas definitivas.

## Limitaciones

- El dataset crudo activo no contiene asistencia real, tutorias reales ni incidencias institucionales reales.
- Las senales operativas estimadas mantienen el pipeline funcionando como prototipo local, pero deben reemplazarse por columnas institucionales cuando existan.
- La interpretacion depende de medias y diferencias contra el promedio global; no explica causalidad.

## Artefactos generados

- `data/reports/academic_profile_catalog.csv`
- `data/reports/cluster_feature_differences.csv`
- `data/reports/cluster_outlier_candidates.csv`
- `data/reports/cluster_stability_metrics.csv`
- `data/reports/profile_interpretation_report.md`
- `artifacts/academic_profile_catalog.json`
