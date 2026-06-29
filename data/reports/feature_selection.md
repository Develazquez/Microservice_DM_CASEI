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
| promedio_general | Desempeno acumulado del estudiante. | 126.3 | 0.778 |
| promedio_periodo | Desempeno reciente; se imputa cuando no aplica por baja temporal. | 212.8 | 0.778 |
| porcentaje_avance | Lectura academica clara del progreso curricular. | 765.6 | 0.9989 |
| porcentaje_asistencia | Indicador normalizado de compromiso/asistencia. | 541.7 | 0.9342 |
| retardos | Senal operativa distinta a la asistencia acumulada. | 2.359 | 0.2921 |
| num_asesorias | Mide apoyo academico complementario. | 1.572 | 0.5679 |
| num_incidencias | Senal de eventos que pueden afectar trayectoria. | 0.4604 | 0.2692 |
| recursamientos | Historial acumulado de repeticion de materias. | 1.018 | 0.7397 |
| rezago_materias | Indicador central de atraso academico. | 1.753 | 0.5284 |
| creditos_inscritos_periodo | Carga academica real del periodo. | 158.4 | 0.9278 |
| creditos_aprobados_periodo | Desempeno reciente en creditos, no solo materias. | 170.6 | 0.9096 |
| periodos_cursados | Contexto temporal de avance academico. | 8.123 | 0.9534 |
| periodos_sin_inscripcion | Explica rezago y bajas de forma academica. | 0.3473 | 0.5341 |
| materias_reprobadas_periodo | Dificultad reciente del periodo. | 0.7268 | 0.6449 |
| materias_reprobadas_acumuladas | Dificultad historica acumulada. | 2.018 | 1 |
| materias_en_curso_periodo | Carga actual validada contra estatus. | 3.254 | 1 |
| tendencia_promedio | Diferencia recuperacion, deterioro y estabilidad. | 84.05 | 0.6445 |
| varianza_calificaciones | Distingue desempeno estable de desempeno irregular. | 229.6 | 0.2273 |
| tutorias_abiertas | Seguimiento tutorial pendiente. | 1.461 | 0.6599 |
| tutorias_cerradas | Acompanamiento tutorial completado. | 1.703 | 0.7181 |
| compromisos_pendientes | Accionabilidad tutorial no resuelta. | 1.871 | 0.604 |
| compromisos_cumplidos | Respuesta del alumno al seguimiento. | 2.938 | 0.6275 |
| permisos_aprobados | Contextualiza baja asistencia sin asumir abandono. | 1.731 | 0.9454 |
| permisos_rechazados | Senal operativa de ausencias sin soporte. | 0.2041 | 0.3144 |
| bandera_dato_incompleto | Permite que el modelo capture incertidumbre controlada. | 0.03474 | 0.5489 |

## Variables descartadas

| variable | reason | variance | max_abs_correlation |
| --- | --- | --- | --- |
| materias_aprobadas | Variable heredada; en v2 se usa creditos aprobados y avance. | 149.7 | 0.9659 |
| materias_reprobadas | Alias heredado; se reemplaza por periodo y acumulado. | 2.018 | 1 |
| materias_en_curso | Alias heredado; se reemplaza por materias_en_curso_periodo. | 3.254 | 1 |
| creditos_acumulados | Variable heredada; se reemplaza por creditos_aprobados_periodo y porcentaje_avance. | 5712 | 0.9989 |
| faltas | Altamente inverso a porcentaje_asistencia; se mantiene el indicador normalizado. | 49.75 | 0.9342 |
| num_tutorias | Alias heredado; en v2 se separa en abiertas y cerradas. | 3.009 | 0.7181 |
| num_permisos | Alias heredado; en v2 se separa en permisos aprobados y rechazados. | 1.921 | 0.9454 |
| creditos_totales_plan | Constante por plan/programa; descriptiva, no debe dominar clustering. | 43.29 | 0.06578 |

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
