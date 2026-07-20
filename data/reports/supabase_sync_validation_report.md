# Reporte de validacion de sincronizacion Supabase

Generado: 2026-07-19T04:04:42Z
Hash de fuente: `310fd31b7d440fcb9b8c5f7a537b29d80a9ce00957644ffdee4c527a724b281a`

## Conteos de fuente Supabase

- academic_programs: 4
- carga_academica: 0
- grupos: 0
- historial_academico: 1000
- materias: 128
- periodos: 7
- profile_role_counts: 3
- profiles: 387
- tutor_program_assignments: 1
- tutor_student_scope: 12

## Comparacion local

- Dataset cardex local: 2000 filas, 387 estudiantes.
- Dataset alumno-periodo activo: 1277 registros, 387 estudiantes.
- Preview Supabase alumno-periodo: 654 registros, 199 estudiantes.
- Traslape de estudiantes contra activo: 199 (0.5142).
- Diferencia de registros preview - activo: -623.

## Columnas

- Columnas requeridas faltantes en preview: ninguna.
- Columnas del activo que aun no existen en preview: ninguna.
- Columnas extra del preview: program_id, sexo, student_profile_id.

## Advertencias

- ninguna

## Decision operativa

El dataset activo no fue reemplazado. La salida de Supabase queda como preview hasta validacion academica.
