# Fase 3 - Seleccion de Variables

## Criterios aplicados

- Excluir identificadores y metadatos operativos del entrenamiento: `id_estudiante`, `id_periodo`, `programa`, `cohorte`, `estatus_academico`.
- Mantener variables explicables para tutores y coordinadores.
- Reducir colinealidad evidente en variables derivadas.
- Mantener indicadores de desempeno, avance, asistencia, acompanamiento e incidencias.

## Variables finales para clustering

| feature |
| --- |
| promedio_general |
| promedio_periodo |
| porcentaje_avance |
| porcentaje_asistencia |
| retardos |
| num_asesorias |
| num_incidencias |
| recursamientos |
| rezago_materias |
| creditos_inscritos_periodo |
| creditos_aprobados_periodo |
| periodos_cursados |
| periodos_sin_inscripcion |
| materias_reprobadas_periodo |
| materias_reprobadas_acumuladas |
| materias_en_curso_periodo |
| tendencia_promedio |
| varianza_calificaciones |
| tutorias_abiertas |
| tutorias_cerradas |
| compromisos_pendientes |
| compromisos_cumplidos |
| permisos_aprobados |
| permisos_rechazados |
| bandera_dato_incompleto |

## Variables incluidas

| variable | reason | variance | max_abs_correlation |
| --- | --- | --- | --- |
| promedio_general | Desempeno acumulado del estudiante. | 76.86 | 0.9261 |
| promedio_periodo | Desempeno reciente; se imputa cuando no aplica por baja temporal. | 96.09 | 0.9261 |
| porcentaje_avance | Lectura academica clara del progreso curricular. | 17.06 | 0.9993 |
| porcentaje_asistencia | Indicador normalizado de compromiso/asistencia. | 131.4 | 0.95 |
| retardos | Senal operativa distinta a la asistencia acumulada. | 1.138 | 0.5861 |
| num_asesorias | Mide apoyo academico complementario. | 1.849 | 0.7429 |
| num_incidencias | Senal de eventos que pueden afectar trayectoria. | 0.6748 | 0.7959 |
| recursamientos | Historial acumulado de repeticion de materias. | 1.8 | 0.926 |
| rezago_materias | Indicador central de atraso academico. | 2.468 | 0.9499 |
| creditos_inscritos_periodo | Carga academica real del periodo. | 49.06 | 0.7838 |
| creditos_aprobados_periodo | Desempeno reciente en creditos, no solo materias. | 50.78 | 0.8102 |
| periodos_cursados | Contexto temporal de avance academico. | 0.8565 | 0.6132 |
| periodos_sin_inscripcion | Explica rezago y bajas de forma academica. | 10.49 | 0.9499 |
| materias_reprobadas_periodo | Dificultad reciente del periodo. | 0.4922 | 0.8439 |
| materias_reprobadas_acumuladas | Dificultad historica acumulada. | 1.136 | 1 |
| materias_en_curso_periodo | Carga actual validada contra estatus. | 0.2561 | 1 |
| tendencia_promedio | Diferencia recuperacion, deterioro y estabilidad. | 53.63 | 0.4078 |
| varianza_calificaciones | Distingue desempeno estable de desempeno irregular. | 2632 | 0.4742 |
| tutorias_abiertas | Seguimiento tutorial pendiente. | 0.7738 | 0.9365 |
| tutorias_cerradas | Acompanamiento tutorial completado. | 0.7985 | 0.8952 |
| compromisos_pendientes | Accionabilidad tutorial no resuelta. | 1.091 | 0.9365 |
| compromisos_cumplidos | Respuesta del alumno al seguimiento. | 1.15 | 0.8952 |
| permisos_aprobados | Contextualiza baja asistencia sin asumir abandono. | 1.043 | 0.8834 |
| permisos_rechazados | Senal operativa de ausencias sin soporte. | 0.3902 | 0.6429 |
| bandera_dato_incompleto | Permite que el modelo capture incertidumbre controlada. | 0.1627 | 0.9025 |

## Variables descartadas

| variable | reason | variance | max_abs_correlation |
| --- | --- | --- | --- |
| materias_aprobadas | Variable heredada; en v2 se usa creditos aprobados y avance. | 3.753 | 0.9865 |
| materias_reprobadas | Alias heredado; se reemplaza por periodo y acumulado. | 1.136 | 1 |
| materias_en_curso | Alias heredado; se reemplaza por materias_en_curso_periodo. | 0.2561 | 1 |
| creditos_acumulados | Variable heredada; se reemplaza por creditos_aprobados_periodo y porcentaje_avance. | 125.2 | 0.9993 |
| faltas | Altamente inverso a porcentaje_asistencia; se mantiene el indicador normalizado. | 15.1 | 0.95 |
| num_tutorias | Alias heredado; en v2 se separa en abiertas y cerradas. | 1.533 | 0.704 |
| num_permisos | Alias heredado; en v2 se separa en permisos aprobados y rechazados. | 1.7 | 0.8834 |
| creditos_totales_plan | Constante por plan/programa; descriptiva, no debe dominar clustering. | 45.03 | 0.09765 |

## Matriz de seleccion

La matriz completa queda en:

```text
data/reports/feature_selection_matrix.csv
```

## Dataset resultante

El dataset con metadatos y variables finales queda en:

```text
data/processed/selected_features.csv
```

## Decision tecnica

El primer feature set queda compuesto por 25 variables numericas. Es suficientemente compacto para una primera segmentacion y conserva las dimensiones academicas mas importantes: desempeno, avance, carga, asistencia, acompanamiento, incidencias y rezago.
