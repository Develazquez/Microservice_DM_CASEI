# Fase 7 - Interpretacion de perfiles academicos

## Objetivo

Traducir los clusters numericos del modelo K-Means a perfiles academicos comprensibles para tutores, coordinadores y analitica institucional.

## Modelo interpretado

- Algoritmo: K-Means.
- Representacion seleccionada: `pca_90`.
- K interpretado: 2.
- Silhouette: 0.32558.
- Davies-Bouldin: 1.46327.
- Calinski-Harabasz: 310.17692.

Los centroides persistidos pertenecen a la representacion PCA seleccionada; por eso la lectura academica se deriva tambien de medias de variables originales contra el promedio global.

## Catalogo provisional de perfiles

| cluster | perfil_academico | prioridad_tutorial | registros | porcentaje_registros | rasgos_dominantes | lectura_funcional | acciones_sugeridas | cautela_interpretacion | promedio_general | promedio_periodo | porcentaje_asistencia | materias_reprobadas_periodo | materias_reprobadas_acumuladas | rezago_materias | recursamientos | periodos_sin_inscripcion | num_incidencias | tutorias_abiertas | compromisos_pendientes | varianza_calificaciones |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Regular / seguimiento preventivo | Baja-media | 812 | 81.28 | compromisos_pendientes bajo (-0.38 DE); materias_reprobadas_periodo bajo (-0.36 DE); tutorias_abiertas bajo (-0.35 DE); materias_reprobadas_acumuladas bajo (-0.34 DE); promedio_periodo alto (+0.33 DE); num_incidencias bajo (-0.33 DE) | Trayectoria mayormente estable; requiere monitoreo ordinario y seguimiento preventivo. | Mantener monitoreo regular, detectar cambios de tendencia y atender outliers de baja pertenencia. | Mantener vigilancia de casos con baja pertenencia al cluster o cambios recientes de tendencia. | 79.041 | 80.69 | 75.47 | 0.0936 | 0.2167 | 1.5443 | 0.3842 | 3.5222 | 0.0369 | 0.3719 | 0.3892 | 15.559 |
| 1 | Riesgo academico moderado | Media-alta | 187 | 18.72 | compromisos_pendientes alto (+1.65 DE); materias_reprobadas_periodo alto (+1.55 DE); tutorias_abiertas alto (+1.51 DE); materias_reprobadas_acumuladas alto (+1.46 DE); num_incidencias alto (+1.44 DE); recursamientos alto (+1.37 DE) | Grupo con senales consistentes de seguimiento: calificaciones menores, baja asistencia o rezago medio. | Programar seguimiento preventivo, revisar asistencia, reprobadas recientes y compromisos pendientes. | Usar como priorizacion de acompanamiento, no como diagnostico definitivo. | 66.58 | 64.793 | 56.539 | 1.4278 | 2.1283 | 1.738 | 2.6524 | 4.4439 | 1.492 | 2.0053 | 2.5027 | 64.457 |

## Centroides del modelo

| cluster | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 | PC7 | PC8 | PC9 | PC10 | PC11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | -1.1125 | 0.0022137 | -0.074494 | 0.0077777 | 0.025575 | 0.0013715 | 0.028225 | -0.0063489 | 0.0057467 | -0.0020121 | 0.020392 |
| 1 | 4.8306 | -0.0096123 | 0.32347 | -0.033773 | -0.11105 | -0.0059554 | -0.12256 | 0.027568 | -0.024953 | 0.0087371 | -0.088547 |

## Variables mas distintivas

| cluster | variable | media_cluster | media_global | diferencia | diferencia_estandarizada | lectura |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | compromisos_pendientes | 2.5027 | 0.78478 | 1.7179 | 1.6456 | compromisos pendientes estimados: mas compromisos pendientes |
| 1 | materias_reprobadas_periodo | 1.4278 | 0.34334 | 1.0845 | 1.5465 | reprobadas del periodo: mas reprobadas recientes |
| 1 | tutorias_abiertas | 2.0053 | 0.67768 | 1.3277 | 1.5101 | tutorias abiertas estimadas: mas seguimiento pendiente |
| 1 | materias_reprobadas_acumuladas | 2.1283 | 0.57457 | 1.5538 | 1.4582 | reprobadas acumuladas: mas reprobadas acumuladas |
| 1 | num_incidencias | 1.492 | 0.30931 | 1.1827 | 1.4405 | incidencias estimadas: mas incidencias |
| 1 | recursamientos | 2.6524 | 0.80881 | 1.8436 | 1.3748 | recursamientos: mas recursamientos |
| 1 | porcentaje_asistencia | 56.539 | 71.927 | -15.388 | -1.3433 | asistencia estimada: menor asistencia |
| 1 | num_asesorias | 3.2781 | 1.4915 | 1.7866 | 1.3144 | asesorias estimadas: mas asesorias |
| 1 | promedio_periodo | 64.793 | 77.416 | -12.622 | -1.2884 | promedio del periodo: desempeno reciente menor |
| 1 | promedio_general | 66.58 | 76.709 | -10.129 | -1.1559 | promedio general: desempeno acumulado menor |
| 1 | retardos | 2.4171 | 1.5465 | 0.87057 | 0.81653 | retardos estimados: mas retardos |
| 1 | varianza_calificaciones | 64.457 | 24.712 | 39.745 | 0.77502 | variacion de calificaciones: desempeno mas irregular |
| 1 | permisos_aprobados | 2.3209 | 1.5556 | 0.7653 | 0.74982 | permisos aprobados estimados: mas permisos aprobados |
| 1 | permisos_rechazados | 1.0107 | 0.61962 | 0.39108 | 0.62635 | permisos rechazados estimados: mas permisos rechazados |
| 1 | tendencia_promedio | -3.6987 | 0.15317 | -3.8518 | -0.52624 | tendencia del promedio: tendencia a la baja |
| 1 | creditos_aprobados_periodo | 4.5294 | 8.009 | -3.4796 | -0.48854 | creditos aprobados: menos creditos aprobados |
| 0 | compromisos_pendientes | 0.38916 | 0.78478 | -0.39562 | -0.37897 | compromisos pendientes estimados: menos compromisos pendientes |
| 1 | porcentaje_avance | 3.323 | 4.8124 | -1.4894 | -0.36081 | avance curricular: menor avance del plan |
| 0 | materias_reprobadas_periodo | 0.093596 | 0.34334 | -0.24975 | -0.35616 | reprobadas del periodo: menos reprobadas recientes |
| 0 | tutorias_abiertas | 0.37192 | 0.67768 | -0.30576 | -0.34777 | tutorias abiertas estimadas: menos seguimiento pendiente |

## Outliers candidatos

Se marcan como candidatos los registros en el percentil 95 o superior de distancia al centroide dentro de su propio cluster. Estos casos no son errores automaticamente; son trayectorias que conviene revisar con mayor contexto.

| id_estudiante | id_periodo | programa | cohorte | estatus_academico | cluster | distance_to_centroid | membership_score | promedio_general | porcentaje_asistencia | materias_reprobadas_acumuladas | rezago_materias | tendencia_promedio | perfil_academico | criterio_outlier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IDS20230189 | Septiembre-Diciembre 2023 | Ingeniería en Desarrollo de Software | 2023 | Regular | 0 | 9.306 | 0.097031 | 83.36 | 85.05 | 0 | 0 | 0.84 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20210011 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2021 | Regular | 0 | 8.4319 | 0.10602 | 79.03 | 75.83 | 0 | 2 | 10.01 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20220135 | Septiembre-Diciembre 2023 | Ingeniería Agroindustrial | 2022 | Regular | 0 | 7.7028 | 0.1149 | 79.85 | 80.92 | 0 | 1 | 0.73 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20210270 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2021 | Irregular | 0 | 7.6288 | 0.11589 | 79.78 | 62.65 | 1 | 3 | -4.83 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20220289 | Septiembre-Diciembre 2023 | Ingeniería Agroindustrial | 2022 | Regular | 0 | 7.395 | 0.11912 | 77.33 | 74.35 | 0 | 2 | 0 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20210004 | Septiembre-Diciembre 2023 | Ingeniería Biomédica | 2021 | Irregular | 0 | 7.277 | 0.12082 | 88.15 | 75.46 | 0 | 3 | -1 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20200163 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2020 | Irregular | 0 | 7.2506 | 0.1212 | 86 | 68.81 | 0 | 4 | 2.8 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20240320 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2024 | Baja Temporal | 0 | 7.1432 | 0.1228 | 77.1 | 55.91 | 2 | 0 | 10.89 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IDS20240104 | Septiembre-Diciembre 2023 | Ingeniería en Desarrollo de Software | 2024 | Regular | 0 | 7.0542 | 0.12416 | 77.16 | 84.57 | 1 | 0 | 6.48 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20240370 | Septiembre-Diciembre 2023 | Ingeniería Biomédica | 2024 | Irregular | 0 | 6.9808 | 0.1253 | 59.46 | 85.72 | 4 | 0 | 22.8 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IBM20200056 | Septiembre-Diciembre 2022 | Ingeniería Biomédica | 2020 | Irregular | 0 | 6.9288 | 0.12612 | 70 | 62.43 | 0 | 4 |  | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20220232 | Septiembre-Diciembre 2023 | Ingeniería Agroindustrial | 2022 | Regular | 0 | 6.87 | 0.12706 | 80.39 | 73.41 | 0 | 1 | -0.77 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20240308 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2024 | Regular | 0 | 6.7667 | 0.12875 | 80.66 | 81.7 | 1 | 0 | -7 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20240277 | Septiembre-Diciembre 2023 | Ingeniería Agroindustrial | 2024 | Regular | 0 | 6.7453 | 0.12911 | 80.56 | 81.82 | 0 | 0 | -2.5 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IDS20220005 | Mayo-Agosto 2023 | Ingeniería en Desarrollo de Software | 2022 | Irregular | 0 | 6.7059 | 0.12977 | 52.5 | 67.46 | 2 | 1 | 31.6 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20240275 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2024 | Regular | 0 | 6.6252 | 0.13114 | 79.66 | 76.67 | 1 | 0 | -1.18 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IAG20230261 | Septiembre-Diciembre 2023 | Ingeniería Agroindustrial | 2023 | Regular | 0 | 6.5255 | 0.13288 | 77.76 | 73.59 | 1 | 0 | -4.62 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20200178 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2020 | Irregular | 0 | 6.4955 | 0.13341 | 79.57 | 61.94 | 1 | 4 | -3.4 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20210318 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2021 | Irregular | 0 | 6.4219 | 0.13474 | 90.09 | 75.19 | 0 | 3 | 0.89 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |
| IEN20220173 | Septiembre-Diciembre 2023 | Ingeniería en Energía | 2022 | Regular | 0 | 6.3274 | 0.13647 | 79.6 | 73.48 | 1 | 1 | -11.2 | Regular / seguimiento preventivo | distancia al centroide en el percentil 95 o superior de su cluster |

## Estabilidad

Se calculo estabilidad con Indice Rand Ajustado (ARI) contra las asignaciones base. El ARI es invariante al cambio de nombre de etiquetas entre clusters.

- `periodo`: estabilidad baja promedio (ARI medio 0.6297).
- `semilla`: estabilidad alta promedio (ARI medio 0.9953).
- `submuestra_80`: estabilidad alta promedio (ARI medio 0.9271).
- Cautela: la prueba mas debil fue `periodo` / `Septiembre-Diciembre 2022` con ARI 0.2501; conviene revisar ese corte antes de usar el perfil como etiqueta estable.

| validacion | pruebas | ari_promedio | ari_minimo | ari_maximo | lectura |
| --- | --- | --- | --- | --- | --- |
| periodo | 4 | 0.62967 | 0.25006 | 0.80089 | Baja |
| semilla | 5 | 0.99528 | 0.99528 | 0.99528 | Alta |
| submuestra_80 | 5 | 0.92705 | 0.87154 | 0.99054 | Alta |

Detalle de pruebas:

| validacion | detalle | n_registros | ari_vs_base | distribucion_clusters |
| --- | --- | --- | --- | --- |
| semilla | seed=7 | 999 | 0.99528 | C0=811; C1=188 |
| semilla | seed=13 | 999 | 0.99528 | C0=811; C1=188 |
| semilla | seed=21 | 999 | 0.99528 | C0=188; C1=811 |
| semilla | seed=42 | 999 | 0.99528 | C0=188; C1=811 |
| semilla | seed=99 | 999 | 0.99528 | C0=811; C1=188 |
| submuestra_80 | seed=101 | 799 | 0.94018 | C0=200; C1=799 |
| submuestra_80 | seed=202 | 799 | 0.87154 | C0=839; C1=160 |
| submuestra_80 | seed=303 | 799 | 0.91367 | C0=206; C1=793 |
| submuestra_80 | seed=404 | 799 | 0.99054 | C0=185; C1=814 |
| submuestra_80 | seed=505 | 799 | 0.91932 | C0=170; C1=829 |
| periodo | Enero-Abril 2023 | 263 | 0.68127 | C0=64; C1=199 |
| periodo | Mayo-Agosto 2023 | 196 | 0.78646 | C0=49; C1=147 |
| periodo | Septiembre-Diciembre 2022 | 270 | 0.25006 | C0=173; C1=97 |
| periodo | Septiembre-Diciembre 2023 | 270 | 0.80089 | C0=57; C1=213 |

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
