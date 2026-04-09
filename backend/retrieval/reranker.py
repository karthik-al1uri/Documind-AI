"""DocuMind AI — Cross-encoder reranking using MS-MARCO MiniLM.

Takes candidate chunks from the RRF fusion stage and re-scores them using
a cross-encoder model that jointly encodes the query–passage pair for
higher-quality relevance estimation.
"""

import os
import logging
from typing import List, Tuple

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
HF_CACHE_DIR = os.getenv("HF_CACHE_DIR", "./models")

# Lazy-loaded cross-encoder
_reranker = None


def _get_reranker():
    """Lazy-initialize the cross-encoder reranker model.

    Returns:
        CrossEncoder: The loaded cross-encoder model.
    """
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading reranker model: %s", RERANKER_MODEL)
        _reranker = CrossEncoder(RERANKER_MODEL)
        logger.info("Reranker model loaded")
    return _reranker


def rerank(
    query: str,
    candidates: List[Tuple[str, str, float]],
    top_k: int = 5,
) -> List[Tuple[str, float]]:
    """Rerank candidate chunks using the cross-encoder model.

    Args:
        query: The original user query.
        candidates: List of (chunk_id, chunk_text, initial_score) tuples
            from the RRF fusion stage.
        top_k: Number of top results to return after reranking.

    Returns:
        List[Tuple[str, float]]: List of (chunk_id, reranker_score) tuples
            sorted by descending cross-encoder score, limited to top_k.
    """
    if not candidates:
        logger.warning("No candidates to rerank")
        return []

    reranker = _get_reranker()

    # Build query-passage pairs for the cross-encoder
    pairs = [(query, text) for _, text, _ in candidates]
    chunk_ids = [chunk_id for chunk_id, _, _ in candidates]

    # Score all pairs
    scores = reranker.predict(pairs, show_progress_bar=False)

    # Pair IDs with scores and sort
    scored = list(zip(chunk_ids, [float(s) for s in scores]))
    scored.sort(key=lambda x: x[1], reverse=True)

    # Take top_k
    results = scored[:top_k]

    logger.info(
        "Reranked %d candidates → top %d (query: '%s')",
        len(candidates), len(results), query[:50],
    )
    return results


def rerank_top_n(
    query: str,
    candidates: List[Tuple[str, str, float]],
    rerank_top: int = 20,
    return_top: int = 5,
) -> List[Tuple[str, float]]:
    """Rerank the top-N candidates and return the best results.

    First selects the top rerank_top candidates by initial score, then
    applies the cross-encoder, and returns the top return_top.

    Args:
        query: The original user query.
        candidates: Full list of (chunk_id, chunk_text, initial_score) tuples.
        rerank_top: Number of candidates to pass through the cross-encoder.
        return_top: Number of final results to return.

    Returns:
        List[Tuple[str, float]]: Top results after reranking.
    """
    # Sort by initial score and take top-N for reranking
    sorted_candidates = sorted(candidates, key=lambda x: x[2], reverse=True)
    to_rerank = sorted_candidates[:rerank_top]

    logger.info(
        "Reranking top %d of %d candidates (returning top %d)",
        len(to_rerank), len(candidates), return_top,
    )

    return rerank(query, to_rerank, top_k=return_top)
