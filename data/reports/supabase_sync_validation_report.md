# Reporte de validacion de sincronizacion Supabase

Generado: 2026-07-12T04:46:24Z
Hash de fuente: `1a7f1053ded6cc8f306936a6705a07c995aa99474f99d1b1f0621552b08f4cc5`

## Conteos de fuente Supabase

- academic_programs: 0
- carga_academica: 0
- grupos: 0
- historial_academico: 0
- materias: 0
- periodos: 0
- profile_role_counts: 1
- profiles: 0
- tutor_program_assignments: 0
- tutor_student_scope: 0

## Comparacion local

- Dataset cardex local: 2000 filas, 387 estudiantes.
- Dataset alumno-periodo activo: 1277 registros, 387 estudiantes.
- Preview Supabase alumno-periodo: 0 registros, 0 estudiantes.
- Traslape de estudiantes contra activo: 0 (0.0).
- Diferencia de registros preview - activo: -1277.

## Columnas

- Columnas requeridas faltantes en preview: ninguna.
- Columnas del activo que aun no existen en preview: compromisos_cumplidos, compromisos_pendientes, creditos_acumulados, creditos_totales_plan, faltas, materias_en_curso, materias_en_curso_periodo, materias_reprobadas, num_asesorias, num_incidencias, num_permisos, num_tutorias, periodos_cursados, periodos_sin_inscripcion, permisos_aprobados, permisos_rechazados, porcentaje_asistencia, recursamientos, retardos, rezago_materias, tendencia_promedio, tutorias_abiertas, tutorias_cerradas, varianza_calificaciones.
- Columnas extra del preview: program_id, sexo, student_profile_id.

## Advertencias

- Supabase no devolvio perfiles con rol=alumno; no se puede construir una vista alumno-periodo real.
- Supabase no devolvio historial_academico ni carga_academica; faltan registros academicos base.
- Supabase no devolvio materias; creditos y nombres de asignatura quedan incompletos.
- Supabase no devolvio periodos; los IDs de periodo no pueden normalizarse.
- El preview alumno-periodo quedo vacio; el dataset local activo se conserva sin cambios.


## Decision operativa

El dataset activo no fue reemplazado. La salida de Supabase queda como preview hasta validacion academica.
