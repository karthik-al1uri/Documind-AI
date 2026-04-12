"""DocuMind AI — PostgreSQL tsvector BM25 retrieval.

Performs keyword-based search against the chunks table using PostgreSQL's
built-in full-text search (tsvector/tsquery). The text_search column is a
GENERATED ALWAYS stored tsvector so no manual indexing is needed.
"""

import logging
import re
from typing import List, Tuple, Optional

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _tsquery_or_terms(query: str) -> str:
    """Build a tsquery with OR across alphabetic terms (not AND).

    plainto_tsquery('a b c') becomes 'a' & 'b' & 'c', which often matches
    nothing when chunks lack a digit like ``30``. OR-ing keywords fixes BM25.
    """
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", query) if len(w) > 1]
    if not words:
        return ""
    # Dedupe while preserving order
    seen = set()
    uniq = []
    for w in words:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return " | ".join(uniq[:24])


async def bm25_search(
    session: AsyncSession,
    query: str,
    top_k: int = 50,
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[str, float]]:
    """Search chunks using PostgreSQL tsvector full-text search.

    Converts the query into a tsquery using plainto_tsquery and ranks
    results using ts_rank_cd (cover density ranking).

    Args:
        session: Async database session.
        query: The raw search query string.
        top_k: Maximum number of results to return.
        document_ids: Optional list of document UUID strings to restrict
            the search scope.

    Returns:
        List[Tuple[str, float]]: List of (chunk_id, rank_score) tuples
            sorted by descending rank.
    """
    if not query or not query.strip():
        logger.warning("Empty query for BM25 search")
        return []

    tsq = _tsquery_or_terms(query)
    if not tsq:
        logger.warning("No alphabetic terms in BM25 query")
        return []

    # Build the SQL query (OR-based tsquery for recall)
    if document_ids:
        placeholders = ", ".join(f":doc_id_{i}" for i in range(len(document_ids)))
        sql = sql_text(f"""
            SELECT
                id::text AS chunk_id,
                ts_rank_cd(text_search, to_tsquery('english', :tsq)) AS rank
            FROM chunks
            WHERE text_search @@ to_tsquery('english', :tsq)
              AND document_id::text IN ({placeholders})
            ORDER BY rank DESC
            LIMIT :top_k
        """)
        params = {"tsq": tsq, "top_k": top_k}
        for i, doc_id in enumerate(document_ids):
            params[f"doc_id_{i}"] = doc_id
    else:
        sql = sql_text("""
            SELECT
                id::text AS chunk_id,
                ts_rank_cd(text_search, to_tsquery('english', :tsq)) AS rank
            FROM chunks
            WHERE text_search @@ to_tsquery('english', :tsq)
            ORDER BY rank DESC
            LIMIT :top_k
        """)
        params = {"tsq": tsq, "top_k": top_k}

    result = await session.execute(sql, params)
    rows = result.fetchall()

    results = [(row.chunk_id, float(row.rank)) for row in rows]

    logger.info(
        "BM25 search for '%s': %d results (top_k=%d, doc_filter=%s)",
        query[:50], len(results), top_k, bool(document_ids),
    )
    return results
