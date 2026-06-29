# Criterios de Realismo del Dataset

## Snapshot

La unidad analitica es estudiante-periodo. El dataset v2 representa un corte durante o al cierre del periodo academico. Si `estatus_academico` es `Baja Temporal`, se interpreta como baja efectiva durante el periodo y por eso no debe tener carga activa.

## Reglas verificables

- Llave unica por `id_estudiante` + `id_periodo`.
- Calificaciones, asistencia y avance entre 0 y 100.
- Conteos academicos y operativos no negativos.
- `porcentaje_avance` compatible con creditos acumulados sobre creditos del plan.
- `creditos_aprobados_periodo <= creditos_inscritos_periodo`.
- `Baja Temporal` sin materias activas en el periodo.
- `recursamientos <= materias_reprobadas_acumuladas`.
- `rezago_materias >= max(materias_reprobadas_acumuladas - recursamientos, 0)`.
- Nulos permitidos solo en variables no aplicables por baja temporal.

## Variables latentes usadas

El dataset v2 se genera desde senales no visibles directamente: habilidad academica, habito de asistencia, carga externa, necesidad de apoyo, avance esperado por cohorte y evento del periodo.
