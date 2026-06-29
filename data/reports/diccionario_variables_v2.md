# Diccionario de Variables v2

| variable | descripcion | semantica |
| --- | --- | --- |
| creditos_inscritos_periodo | Carga academica real inscrita en el periodo. | periodo |
| creditos_aprobados_periodo | Creditos aprobados en el periodo. | periodo |
| creditos_totales_plan | Total de creditos del plan sintetico por programa. | plan |
| periodos_cursados | Periodos estimados desde cohorte hasta periodo. | trayectoria |
| periodos_sin_inscripcion | Periodos con interrupcion de inscripcion. | trayectoria |
| materias_reprobadas_periodo | Materias reprobadas en el periodo. | periodo |
| materias_reprobadas_acumuladas | Materias reprobadas historicas acumuladas. | historico |
| materias_en_curso_periodo | Materias activas del periodo. | periodo |
| tendencia_promedio | Promedio del periodo menos promedio general. | derivada |
| varianza_calificaciones | Variabilidad sintetica de desempeno por materias. | derivada |
| tutorias_abiertas | Tutorias pendientes o en seguimiento. | operativa |
| tutorias_cerradas | Tutorias atendidas/cerradas. | operativa |
| compromisos_pendientes | Compromisos tutoriales no resueltos. | operativa |
| compromisos_cumplidos | Compromisos tutoriales cumplidos. | operativa |
| permisos_aprobados | Permisos aceptados que contextualizan ausencias. | operativa |
| permisos_rechazados | Permisos no aceptados. | operativa |
| bandera_dato_incompleto | Indica faltantes controlados por no aplicabilidad. | calidad |

## Variables heredadas

El dataset conserva variables v1 para compatibilidad de reportes, pero el pipeline v2 prioriza las variables nuevas o corregidas definidas en `app/models/config.py`.
