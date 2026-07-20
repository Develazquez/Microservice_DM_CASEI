from __future__ import annotations

from collections import Counter, OrderedDict
import json
import math
import re
import unicodedata

import numpy as np
import pandas as pd

from app.models.config import ACTIVE_INFERENCE_METADATA, ACTIVE_INFERENCE_SNAPSHOT, PROCESSED_DIR, PROJECT_ROOT, RAW_DATASET, REPORTS_DIR, STUDENT_PERIOD_DATASET
from app.models.search_config import BM25_B, BM25_K1, SEARCH_TOP_K, SPANISH_STOPWORDS
from app.views.report_view import markdown_table, write_markdown
from app.services.model_persistence_service import load_persisted_model_bundle


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
REPO_ROOT = PROJECT_ROOT
_INDEX_CACHE: OrderedDict[str, "BM25Index"] = OrderedDict()
_INDEX_CACHE_MAX_SIZE = 8


def normalize_text(value: object) -> str:
    text = str(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in TOKEN_PATTERN.findall(normalize_text(text))
        if token not in SPANISH_STOPWORDS and len(token) > 1
    ]


class BM25Index:
    def __init__(self, documents: pd.DataFrame) -> None:
        self.documents = documents.reset_index(drop=True)
        self.tokens = [tokenize(text) for text in self.documents["search_text"]]
        self.term_frequencies = [Counter(doc_tokens) for doc_tokens in self.tokens]
        self.doc_lengths = np.array([len(doc_tokens) for doc_tokens in self.tokens], dtype=float)
        self.average_doc_length = float(self.doc_lengths.mean()) if len(self.doc_lengths) else 0.0
        self.idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        document_frequency: Counter[str] = Counter()
        for doc_tokens in self.tokens:
            document_frequency.update(set(doc_tokens))

        total_docs = len(self.tokens)
        return {
            term: math.log(1 + (total_docs - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(
        self,
        query: str,
        top_k: int = SEARCH_TOP_K,
        weighted_terms: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        query_terms = {term: 1.0 for term in tokenize(query)}
        for text, weight in (weighted_terms or {}).items():
            for term in tokenize(text):
                query_terms[term] = max(query_terms.get(term, 0.0), float(weight))
        scores = np.array(
            [self._score_document(tf, length, query_terms) for tf, length in zip(self.term_frequencies, self.doc_lengths)]
        )
        positive_indexes = np.flatnonzero(scores > 0)
        ranked_indexes = positive_indexes[np.argsort(-scores[positive_indexes])][:top_k]
        results = self.documents.iloc[ranked_indexes].copy()
        results.insert(0, "rank", range(1, len(results) + 1))
        results.insert(1, "score_bm25", scores[ranked_indexes])
        return results

    def _score_document(
        self,
        term_frequency: Counter[str],
        doc_length: float,
        query_terms: dict[str, float],
    ) -> float:
        score = 0.0
        for term, query_weight in query_terms.items():
            frequency = term_frequency.get(term, 0)
            if frequency == 0:
                continue
            denominator = frequency + BM25_K1 * (
                1 - BM25_B + BM25_B * doc_length / max(self.average_doc_length, 1)
            )
            score += query_weight * self.idf.get(term, 0.0) * frequency * (BM25_K1 + 1) / denominator
        return score


def get_cached_index(documents: pd.DataFrame) -> BM25Index:
    fingerprint_columns = [column for column in ["document_id", "search_text"] if column in documents.columns]
    fingerprint = str(pd.util.hash_pandas_object(documents[fingerprint_columns], index=True).sum())
    cached = _INDEX_CACHE.get(fingerprint)
    if cached is not None:
        _INDEX_CACHE.move_to_end(fingerprint)
        return cached
    index = BM25Index(documents)
    _INDEX_CACHE[fingerprint] = index
    while len(_INDEX_CACHE) > _INDEX_CACHE_MAX_SIZE:
        _INDEX_CACHE.popitem(last=False)
    return index


def clear_index_cache() -> None:
    _INDEX_CACHE.clear()


def numeric_bucket(value: float, thresholds: tuple[float, float], labels: tuple[str, str, str]) -> str:
    if value < thresholds[0]:
        return labels[0]
    if value < thresholds[1]:
        return labels[1]
    return labels[2]


def load_search_documents() -> pd.DataFrame:
    if STUDENT_PERIOD_DATASET.exists():
        raw = pd.read_csv(STUDENT_PERIOD_DATASET)
    else:
        raw = pd.read_csv(RAW_DATASET, encoding="utf-8-sig")
    loaded = load_persisted_model_bundle()
    assignments = loaded["cluster_assignments"].copy()
    if ACTIVE_INFERENCE_SNAPSHOT.exists() and ACTIVE_INFERENCE_METADATA.exists():
        metadata = json.loads(ACTIVE_INFERENCE_METADATA.read_text(encoding="utf-8"))
        if metadata.get("model_version") == loaded["manifest"]["model_version"]:
            assignments = pd.read_csv(ACTIVE_INFERENCE_SNAPSHOT)
    summary = pd.DataFrame(loaded["profile_catalog"])
    if "perfil_sugerido" not in summary.columns and "perfil_academico" in summary.columns:
        summary = summary.rename(columns={"perfil_academico": "perfil_sugerido"})
    summary = summary[["cluster", "perfil_sugerido"]]

    data = raw.merge(
        assignments[["id_estudiante", "id_periodo", "cluster", "membership_score"]],
        on=["id_estudiante", "id_periodo"],
        how="left",
    ).merge(summary, on="cluster", how="left")

    data["document_id"] = data["id_estudiante"] + "::" + data["id_periodo"]
    data["promedio_bucket"] = data["promedio_general"].apply(
        lambda value: numeric_bucket(float(value), (60, 80), ("promedio bajo", "promedio medio", "promedio alto"))
    )
    data["asistencia_bucket"] = data["porcentaje_asistencia"].apply(
        lambda value: numeric_bucket(float(value), (60, 80), ("asistencia baja", "asistencia media", "asistencia alta"))
    )
    data["rezago_bucket"] = data["rezago_materias"].apply(
        lambda value: "sin rezago" if float(value) == 0 else ("rezago moderado" if float(value) < 3 else "rezago alto")
    )
    data["reprobadas_bucket"] = data["materias_reprobadas"].apply(
        lambda value: "sin reprobadas" if float(value) == 0 else ("reprobadas moderadas" if float(value) < 3 else "reprobadas altas")
    )
    data["acompanamiento_bucket"] = data["num_tutorias"].apply(
        lambda value: "sin tutorias" if float(value) == 0 else "con tutorias seguimiento academico"
    )
    data["incidencias_bucket"] = data["num_incidencias"].apply(
        lambda value: "sin incidencias" if float(value) == 0 else "con incidencias"
    )
    data["search_text"] = data.apply(build_document_text, axis=1)
    return data


def build_document_text(row: pd.Series) -> str:
    profile = str(row.get("perfil_sugerido", "sin perfil"))
    signals = []
    if float(row["promedio_general"]) < 60:
        signals.append("critico criticos riesgo bajo promedio reprobacion")
    if float(row["porcentaje_asistencia"]) < 60:
        signals.append("baja asistencia ausentismo asistencias")
    if float(row["rezago_materias"]) >= 3:
        signals.append("rezago rezagos alto atraso academico")
    if float(row["promedio_general"]) < 60 and float(row["rezago_materias"]) >= 4:
        signals.append("estudiantes criticos con rezago alto")
    if float(row["promedio_general"]) >= 85 and float(row["porcentaje_asistencia"]) < 60:
        signals.append("atipico atipicos buen promedio baja asistencia")
    if "regular" in normalize_text(profile):
        signals.append("regular seguimiento preventivo estable")

    return " ".join(
        [
            f"estudiante {row['id_estudiante']}",
            f"periodo {row['id_periodo']}",
            f"programa {row['programa']} {row['programa']} {row['programa']}",
            f"cohorte {row['cohorte']}",
            f"estatus {row['estatus_academico']} {row['estatus_academico']}",
            f"cluster {row['cluster']}",
            f"perfil {profile} {profile} {profile}",
            row["promedio_bucket"],
            row["asistencia_bucket"],
            row["rezago_bucket"],
            row["reprobadas_bucket"],
            row["acompanamiento_bucket"],
            row["incidencias_bucket"],
            " ".join(signals),
        ]
    )


def relevance_mask(documents: pd.DataFrame, query_id: str) -> pd.Series:
    profile = documents["perfil_sugerido"].fillna("").map(normalize_text)
    program = documents["programa"].fillna("").map(normalize_text)
    if query_id == "critical_lag":
        return profile.str.contains("critico") | (
            (documents["rezago_materias"] >= 4) & (documents["promedio_general"] < 60)
        )
    if query_id == "atypical_attendance":
        return profile.str.contains("atipico") | (
            (documents["promedio_general"] >= 85) & (documents["porcentaje_asistencia"] < 60)
        )
    if query_id == "moderate_risk":
        return profile.str.contains("riesgo academico moderado")
    if query_id == "regular_preventive":
        return profile.str.contains("regular")
    if query_id == "software_lag":
        return program.str.contains("desarrollo de software") & (documents["rezago_materias"] >= 3)
    if query_id == "biomedical_low_attendance":
        return program.str.contains("biomedica") & (documents["porcentaje_asistencia"] < 60)
    if query_id == "energy_low_average":
        return program.str.contains("energia") & (documents["promedio_general"] < 60) & (documents["materias_reprobadas"] >= 3)
    if query_id == "agro_high_performance":
        return program.str.contains("agroindustrial") & (documents["promedio_general"] >= 80) & (documents["porcentaje_asistencia"] >= 80)
    raise ValueError(f"Consulta de evaluacion no soportada: {query_id}")


def evaluation_queries() -> list[dict[str, str]]:
    return [
        {"id": "critical_lag", "query": "estudiantes criticos con rezago alto", "intent": "Ubicar alumnos con perfil critico o atraso academico severo."},
        {"id": "atypical_attendance", "query": "buen promedio baja asistencia atipico", "intent": "Encontrar alumnos con desempeno alto pero asistencia baja."},
        {"id": "moderate_risk", "query": "riesgo academico moderado", "intent": "Recuperar estudiantes del perfil de riesgo moderado."},
        {"id": "regular_preventive", "query": "alumnos regulares seguimiento preventivo", "intent": "Recuperar alumnos estables que solo requieren seguimiento preventivo."},
        {"id": "software_lag", "query": "desarrollo de software rezago alto", "intent": "Filtrar casos con rezago dentro de Desarrollo de Software."},
        {"id": "biomedical_low_attendance", "query": "biomedica baja asistencia", "intent": "Localizar baja asistencia dentro de Ingenieria Biomedica."},
        {"id": "energy_low_average", "query": "energia promedio bajo reprobadas", "intent": "Localizar bajo promedio y reprobacion en Energia."},
        {"id": "agro_high_performance", "query": "agroindustrial asistencia alta promedio alto", "intent": "Encontrar alto desempeno en Agroindustrial."},
    ]


def evaluate_search(index: BM25Index, documents: pd.DataFrame, top_k: int = SEARCH_TOP_K) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    sample_rows = []
    for query in evaluation_queries():
        relevant = relevance_mask(documents, query["id"])
        total_relevant = int(relevant.sum())
        results = index.search(query["query"], top_k=top_k)
        result_ids = set(results["document_id"])
        relevant_ids = set(documents.loc[relevant, "document_id"])
        relevance_by_rank = [doc_id in relevant_ids for doc_id in results["document_id"]]
        relevant_found = sum(relevance_by_rank)

        metric_rows.append(
            {
                "query_id": query["id"],
                "query": query["query"],
                "total_relevant": total_relevant,
                f"precision@{top_k}": relevant_found / top_k,
                f"recall@{top_k}": relevant_found / max(total_relevant, 1),
                f"mrr@{top_k}": reciprocal_rank(relevance_by_rank),
                f"ndcg@{top_k}": ndcg(relevance_by_rank, min(total_relevant, top_k)),
            }
        )

        for _, row in results.head(5).iterrows():
            sample_rows.append(
                {
                    "query_id": query["id"],
                    "query": query["query"],
                    "rank": int(row["rank"]),
                    "document_id": row["document_id"],
                    "is_relevant": row["document_id"] in relevant_ids,
                    "score_bm25": float(row["score_bm25"]),
                    "programa": row["programa"],
                    "perfil_sugerido": row["perfil_sugerido"],
                    "promedio_general": row["promedio_general"],
                    "porcentaje_asistencia": row["porcentaje_asistencia"],
                    "rezago_materias": row["rezago_materias"],
                }
            )

    metrics = pd.DataFrame(metric_rows)
    samples = pd.DataFrame(sample_rows)
    return metrics, samples


def reciprocal_rank(relevance_by_rank: list[bool]) -> float:
    for index, is_relevant in enumerate(relevance_by_rank, start=1):
        if is_relevant:
            return 1 / index
    return 0.0


def ndcg(relevance_by_rank: list[bool], ideal_relevant: int) -> float:
    dcg = sum((1.0 if is_relevant else 0.0) / math.log2(rank + 1) for rank, is_relevant in enumerate(relevance_by_rank, start=1))
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_relevant + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def run_search_engine() -> None:
    documents = load_search_documents()
    index = BM25Index(documents)
    metrics, samples = evaluate_search(index, documents)
    metrics_path = REPORTS_DIR / "search_metrics.csv"
    samples_path = REPORTS_DIR / "search_results_sample.csv"
    report_path = REPORTS_DIR / "search_engine_report.md"

    metrics.to_csv(metrics_path, index=False)
    samples.to_csv(samples_path, index=False)
    write_markdown(report_path, build_search_report(documents, metrics, samples))


def build_search_report(documents: pd.DataFrame, metrics: pd.DataFrame, samples: pd.DataFrame) -> str:
    aggregate = pd.DataFrame(
        [
            {
                "queries": len(metrics),
                "documents_indexed": len(documents),
                "mean_precision@10": metrics["precision@10"].mean(),
                "mean_recall@10": metrics["recall@10"].mean(),
                "mean_mrr@10": metrics["mrr@10"].mean(),
                "mean_ndcg@10": metrics["ndcg@10"].mean(),
            }
        ]
    )

    return f"""
# Extra Roadmap - Motor de Busqueda BM25

## Objetivo

Implementar un motor de busqueda por keywords para recuperar alumnos segmentados a partir de consultas academicas en lenguaje natural corto, por ejemplo: `estudiantes criticos con rezago alto` o `buen promedio baja asistencia`.

## Tecnica usada

- Motor: BM25.
- Unidad indexada: un documento por estudiante-periodo.
- Corpus indexado: {len(documents)} documentos.
- Fuente base cruda: `{RAW_DATASET.relative_to(REPO_ROOT)}`.
- Fuente analitica indexada: `{STUDENT_PERIOD_DATASET.relative_to(REPO_ROOT)}`.
- Enriquecimiento: `cluster_assignments.csv` y `cluster_summary.csv`.
- Dependencias: implementacion propia con Python, pandas y numpy.

Cada documento combina metadatos, programa, cohorte, periodo, estatus academico, perfil de segmentacion, cluster y buckets interpretables de promedio, asistencia, rezago, reprobacion, tutorias e incidencias.

## Metricas globales

{markdown_table(aggregate)}

## Metricas por consulta

{markdown_table(metrics, max_rows=20)}

## Resultados de ejemplo

{markdown_table(samples, max_rows=20)}

## Interpretacion

El motor cumple como una capa de recuperacion semantica ligera basada en terminos academicos controlados. Es util para dashboards, filtros inteligentes y busquedas operativas de perfiles de alumnos. Para una version posterior se puede comparar contra embeddings si se cuenta con un corpus textual mas rico, como observaciones tutoriales, notas de seguimiento o descripciones de incidencias.
"""
