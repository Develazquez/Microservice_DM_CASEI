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
| promedio_general | Desempeno acumulado del estudiante. | 74.93 | 0.876 |
| promedio_periodo | Desempeno reciente; se imputa cuando no aplica por baja temporal. | 105.3 | 0.876 |
| porcentaje_avance | Lectura academica clara del progreso curricular. | 17.15 | 0.9993 |
| porcentaje_asistencia | Indicador normalizado de compromiso/asistencia. | 119 | 0.9429 |
| retardos | Senal operativa distinta a la asistencia acumulada. | 1.145 | 0.532 |
| num_asesorias | Mide apoyo academico complementario. | 1.67 | 0.6907 |
| num_incidencias | Senal de eventos que pueden afectar trayectoria. | 0.5645 | 0.7822 |
| recursamientos | Historial acumulado de repeticion de materias. | 0.174 | 0.6298 |
| rezago_materias | Indicador central de atraso academico. | 1.718 | 0.7148 |
| creditos_inscritos_periodo | Carga academica real del periodo. | 19.58 | 0.6291 |
| creditos_aprobados_periodo | Desempeno reciente en creditos, no solo materias. | 22.26 | 0.6291 |
| periodos_cursados | Contexto temporal de avance academico. | 1.642 | 0.7161 |
| periodos_sin_inscripcion | Explica rezago y bajas de forma academica. | 4.314 | 0.7148 |
| materias_reprobadas_periodo | Dificultad reciente del periodo. | 0.3032 | 0.9059 |
| materias_reprobadas_acumuladas | Dificultad historica acumulada. | 1.181 | 1 |
| materias_en_curso_periodo | Carga actual validada contra estatus. | 0.2094 | 1 |
| tendencia_promedio | Diferencia recuperacion, deterioro y estabilidad. | 66.02 | 0.5107 |
| varianza_calificaciones | Distingue desempeno estable de desempeno irregular. | 1815 | 0.3844 |
| tutorias_abiertas | Seguimiento tutorial pendiente. | 0.8317 | 0.9372 |
| tutorias_cerradas | Acompanamiento tutorial completado. | 0.6812 | 0.9023 |
| compromisos_pendientes | Accionabilidad tutorial no resuelta. | 1.054 | 0.9372 |
| compromisos_cumplidos | Respuesta del alumno al seguimiento. | 0.7932 | 0.9023 |
| permisos_aprobados | Contextualiza baja asistencia sin asumir abandono. | 1.002 | 0.8869 |
| permisos_rechazados | Senal operativa de ausencias sin soporte. | 0.3526 | 0.6272 |
| bandera_dato_incompleto | Permite que el modelo capture incertidumbre controlada. | 0.1343 | 0.9069 |

## Variables descartadas

| variable | reason | variance | max_abs_correlation |
| --- | --- | --- | --- |
| materias_aprobadas | Variable heredada; en v2 se usa creditos aprobados y avance. | 3.688 | 0.9851 |
| materias_reprobadas | Alias heredado; se reemplaza por periodo y acumulado. | 1.181 | 1 |
| materias_en_curso | Alias heredado; se reemplaza por materias_en_curso_periodo. | 0.2094 | 1 |
| creditos_acumulados | Variable heredada; se reemplaza por creditos_aprobados_periodo y porcentaje_avance. | 125.8 | 0.9993 |
| faltas | Altamente inverso a porcentaje_asistencia; se mantiene el indicador normalizado. | 13.09 | 0.9429 |
| num_tutorias | Alias heredado; en v2 se separa en abiertas y cerradas. | 1.54 | 0.7468 |
| num_permisos | Alias heredado; en v2 se separa en permisos aprobados y rechazados. | 1.588 | 0.8869 |
| creditos_totales_plan | Constante por plan/programa; descriptiva, no debe dominar clustering. | 45.49 | 0.1112 |

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
