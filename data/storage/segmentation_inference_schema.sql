PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS inference_runs (
    execution_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    model_version TEXT NOT NULL,
    selected_representation TEXT,
    selected_k INTEGER,
    started_at_utc TEXT NOT NULL,
    finished_at_utc TEXT NOT NULL,
    duration_seconds REAL,
    dataset_path TEXT,
    dataset_records INTEGER,
    assignments_count INTEGER NOT NULL,
    students_count INTEGER NOT NULL,
    parameters_json TEXT,
    metrics_json TEXT,
    notes TEXT,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_inferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    id_estudiante TEXT NOT NULL,
    id_periodo TEXT NOT NULL,
    programa TEXT,
    cohorte TEXT,
    estatus_academico TEXT,
    cluster INTEGER NOT NULL,
    perfil_academico TEXT,
    prioridad_tutorial TEXT,
    distance_to_centroid REAL,
    membership_score REAL,
    promedio_general REAL,
    porcentaje_asistencia REAL,
    rezago_materias REAL,
    materias_reprobadas_periodo REAL,
    materias_reprobadas_acumuladas REAL,
    tendencia_promedio REAL,
    pc1 REAL,
    pc2 REAL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (execution_id) REFERENCES inference_runs(execution_id) ON DELETE CASCADE,
    UNIQUE (execution_id, id_estudiante, id_periodo)
);

CREATE INDEX IF NOT EXISTS idx_inference_runs_model_version
    ON inference_runs(model_version);

CREATE INDEX IF NOT EXISTS idx_inference_runs_started
    ON inference_runs(started_at_utc);

CREATE INDEX IF NOT EXISTS idx_student_inferences_student
    ON student_inferences(id_estudiante);

CREATE INDEX IF NOT EXISTS idx_student_inferences_period
    ON student_inferences(id_periodo);

CREATE INDEX IF NOT EXISTS idx_student_inferences_cluster
    ON student_inferences(cluster);
