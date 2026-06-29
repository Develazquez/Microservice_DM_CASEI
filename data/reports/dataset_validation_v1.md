# Diagnostico Dataset v1

## Resumen

| dataset | records | columns | null_cells | programs | periods | cohorts | avg_grade | avg_attendance | avg_lag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 1000 | 21 | 0 | 4 | 3 | 4 | 78.276 | 77.798 | 1.365 |

## Reglas evaluadas

| check | passed | failing_rows | severity | detail |
| --- | --- | --- | --- | --- |
| unique_student_period | True | 0 | alta | La llave id_estudiante + id_periodo debe ser unica. |
| required_columns | True | 0 | alta | Columnas faltantes: [] |
| range_0_100_promedio_general | True | 0 | alta | promedio_general debe estar entre 0 y 100 cuando aplica. |
| range_0_100_promedio_periodo | True | 0 | alta | promedio_periodo debe estar entre 0 y 100 cuando aplica. |
| range_0_100_porcentaje_asistencia | True | 0 | alta | porcentaje_asistencia debe estar entre 0 y 100 cuando aplica. |
| range_0_100_porcentaje_avance | True | 0 | alta | porcentaje_avance debe estar entre 0 y 100 cuando aplica. |
| non_negative_materias_aprobadas | True | 0 | alta | materias_aprobadas no debe tener valores negativos. |
| non_negative_materias_reprobadas | True | 0 | alta | materias_reprobadas no debe tener valores negativos. |
| non_negative_materias_en_curso | True | 0 | alta | materias_en_curso no debe tener valores negativos. |
| non_negative_faltas | True | 0 | alta | faltas no debe tener valores negativos. |
| non_negative_retardos | True | 0 | alta | retardos no debe tener valores negativos. |
| non_negative_num_tutorias | True | 0 | alta | num_tutorias no debe tener valores negativos. |
| non_negative_num_asesorias | True | 0 | alta | num_asesorias no debe tener valores negativos. |
| non_negative_num_incidencias | True | 0 | alta | num_incidencias no debe tener valores negativos. |
| non_negative_num_permisos | True | 0 | alta | num_permisos no debe tener valores negativos. |
| non_negative_recursamientos | True | 0 | alta | recursamientos no debe tener valores negativos. |
| non_negative_rezago_materias | True | 0 | alta | rezago_materias no debe tener valores negativos. |
| baja_temporal_without_active_load | False | 54 | alta | Baja Temporal no debe tener materias activas si representa baja durante periodo. |
| recursamientos_not_greater_than_failed | False | 100 | alta | Recursamientos no debe exceder materias reprobadas si ambas son acumuladas. |
| lag_not_below_failed_minus_retake | False | 213 | media | Rezago debe cubrir reprobadas no regularizadas. |
