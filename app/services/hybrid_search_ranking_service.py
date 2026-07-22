from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.search_config import RRF_K


def reciprocal_rank_fusion(
    documents: pd.DataFrame,
    bm25_results: pd.DataFrame,
    semantic_results: pd.DataFrame,
    top_k: int,
    rrf_k: int = RRF_K,
) -> pd.DataFrame:
    if bm25_results.empty and semantic_results.empty:
        return documents.iloc[0:0].copy()
    if semantic_results.empty:
        return bm25_results.head(top_k).copy()
    if bm25_results.empty:
        result = semantic_results.head(top_k).copy()
        result.insert(0, "rank", range(1, len(result) + 1))
        result["score_hybrid"] = [1.0 / (rrf_k + rank) for rank in range(1, len(result) + 1)]
        return result

    bm25_ranks = {
        str(row["document_id"]): int(row["rank"])
        for _, row in bm25_results.iterrows()
    }
    semantic_ranks = {
        str(row["document_id"]): int(row["rank_semantic"])
        for _, row in semantic_results.iterrows()
    }
    bm25_scores = {
        str(row["document_id"]): float(row["score_bm25"])
        for _, row in bm25_results.iterrows()
    }
    semantic_scores = {
        str(row["document_id"]): float(row["score_semantic"])
        for _, row in semantic_results.iterrows()
    }

    candidate_ids = set(bm25_ranks) | set(semantic_ranks)
    fused_scores = {
        document_id: (
            (1.0 / (rrf_k + bm25_ranks[document_id]) if document_id in bm25_ranks else 0.0)
            + (1.0 / (rrf_k + semantic_ranks[document_id]) if document_id in semantic_ranks else 0.0)
        )
        for document_id in candidate_ids
    }
    ordered_ids = sorted(candidate_ids, key=lambda item: (-fused_scores[item], item))[:top_k]
    indexed = documents.drop_duplicates("document_id").set_index("document_id", drop=False)
    rows = [indexed.loc[document_id].to_dict() for document_id in ordered_ids if document_id in indexed.index]
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result.insert(0, "rank", range(1, len(result) + 1))
    result.insert(1, "score_hybrid", [fused_scores[str(value)] for value in result["document_id"]])
    result.insert(2, "score_bm25", [bm25_scores.get(str(value), np.nan) for value in result["document_id"]])
    result.insert(3, "score_semantic", [semantic_scores.get(str(value), np.nan) for value in result["document_id"]])
    return result
