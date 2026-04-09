"""DocuMind AI — Reciprocal Rank Fusion (RRF) implementation.

Merges ranked result lists from multiple retrieval sources (dense FAISS
and sparse BM25) into a single fused ranking using the RRF formula
from Cormack et al. (2009).

Formula: score(d) = Σ 1 / (k + rank(d) + 1) for each ranked list
Default k = 60 as specified in CLAUDE.md.
"""

import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

DEFAULT_K = 60


def rrf_score(rankings: List[List[str]], k: int = DEFAULT_K) -> Dict[str, float]:
    """Compute Reciprocal Rank Fusion scores across multiple ranked lists.

    Args:
        rankings: List of ranked lists, where each inner list contains
            item IDs (chunk_ids) ordered by rank (best first).
        k: The RRF constant. Higher values reduce the impact of rank
            position differences. Default is 60.

    Returns:
        Dict[str, float]: Mapping of item IDs to their fused RRF scores,
            sorted by descending score.
    """
    scores: Dict[str, float] = {}

    for ranked_list in rankings:
        for rank, doc_id in enumerate(ranked_list):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

    # Sort by descending score
    sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

    logger.info(
        "RRF fusion: %d input lists, %d unique items fused",
        len(rankings), len(sorted_scores),
    )
    return sorted_scores


def fuse_results(
    dense_results: List[Tuple[str, float]],
    sparse_results: List[Tuple[str, float]],
    k: int = DEFAULT_K,
) -> List[Tuple[str, float]]:
    """Fuse dense (FAISS) and sparse (BM25) retrieval results using RRF.

    Takes scored results from both retrieval sources, extracts their rank
    orderings, applies RRF, and returns the fused ranking.

    Args:
        dense_results: List of (chunk_id, score) from FAISS dense search,
            already sorted by descending score.
        sparse_results: List of (chunk_id, score) from BM25 sparse search,
            already sorted by descending score.
        k: RRF constant (default 60).

    Returns:
        List[Tuple[str, float]]: Fused results as (chunk_id, rrf_score)
            sorted by descending RRF score.
    """
    # Extract ranked lists of IDs
    dense_ranking = [chunk_id for chunk_id, _ in dense_results]
    sparse_ranking = [chunk_id for chunk_id, _ in sparse_results]

    rankings = []
    if dense_ranking:
        rankings.append(dense_ranking)
    if sparse_ranking:
        rankings.append(sparse_ranking)

    if not rankings:
        logger.warning("No results from either dense or sparse retrieval")
        return []

    fused_scores = rrf_score(rankings, k=k)

    results = [(chunk_id, score) for chunk_id, score in fused_scores.items()]

    logger.info(
        "Fused %d dense + %d sparse → %d results",
        len(dense_results), len(sparse_results), len(results),
    )
    return results
