"""DocuMind AI — Full retrieval pipeline orchestration.

Executes the complete retrieval flow for a user query:
1. HyDE query expansion → hypothetical answer
2. Embed the hypothetical answer via BGE-Large-EN
3. FAISS ANN search → top-50 dense results
4. PostgreSQL tsvector BM25 search → top-50 sparse results
5. RRF fusion → merged ranking
6. Cross-encoder reranking → top-5 final results
7. Enrich results with metadata from the chunks table

Returns List[RetrievalResult] for the /retrieve endpoint.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import RetrievalResult, BoundingBox
from utils.database import Chunk, Document
from retrieval.hyde_expander import expand_query
from retrieval.embedder import embed_query
from retrieval.indexer import search as faiss_search
from retrieval.bm25_search import bm25_search
from retrieval.rrf_fusion import fuse_results
from retrieval.reranker import rerank_top_n

logger = logging.getLogger(__name__)


async def run_retrieval_pipeline(
    session: AsyncSession,
    query: str,
    top_k: int = 5,
    document_ids: Optional[List[str]] = None,
) -> List[RetrievalResult]:
    """Execute the full retrieval pipeline for a query.

    Args:
        session: Async database session.
        query: The user's natural language query.
        top_k: Number of final results to return (default 5).
        document_ids: Optional list of document UUIDs to restrict scope.

    Returns:
        List[RetrievalResult]: Top-k retrieval results with full metadata.
    """
    logger.info("Starting retrieval pipeline for query: '%s' (top_k=%d)", query[:80], top_k)

    # Step 1 — HyDE query expansion
    hypothetical_answer = expand_query(query)
    logger.info("HyDE expansion complete (%d chars)", len(hypothetical_answer))

    # Step 2 — Embed the hypothetical answer
    query_embedding = embed_query(hypothetical_answer)
    logger.info("Query embedding generated")

    # Step 3 — FAISS dense search (top-50)
    faiss_results = faiss_search(query_embedding, top_k=50)
    logger.info("FAISS dense search: %d results", len(faiss_results))

    # Map FAISS embedding_id → chunk_id
    dense_chunk_results = await _map_embedding_ids_to_chunks(
        session, faiss_results, document_ids
    )
    logger.info("Dense results mapped to %d chunks", len(dense_chunk_results))

    # Step 4 — BM25 sparse search (top-50)
    sparse_results = await bm25_search(
        session, query, top_k=50, document_ids=document_ids
    )
    logger.info("BM25 sparse search: %d results", len(sparse_results))

    # Step 5 — RRF fusion
    fused_results = fuse_results(dense_chunk_results, sparse_results)
    logger.info("RRF fusion: %d fused results", len(fused_results))

    if not fused_results:
        logger.warning("No results after fusion — returning empty")
        return []

    # Step 6 — Fetch chunk texts for reranking
    chunk_ids = [cid for cid, _ in fused_results]
    chunk_texts = await _fetch_chunk_texts(session, chunk_ids)

    # Build candidates: (chunk_id, text, rrf_score)
    candidates = [
        (cid, chunk_texts.get(cid, ""), score)
        for cid, score in fused_results
        if cid in chunk_texts
    ]

    # Cross-encoder reranking (top-20 → top-k)
    reranked = rerank_top_n(query, candidates, rerank_top=20, return_top=top_k)
    logger.info("Reranking complete: %d final results", len(reranked))

    # Step 7 — Enrich with full metadata
    final_chunk_ids = [cid for cid, _ in reranked]
    score_map = {cid: score for cid, score in reranked}
    results = await _enrich_results(session, final_chunk_ids, score_map)

    logger.info("Retrieval pipeline complete: %d results returned", len(results))
    return results


async def _map_embedding_ids_to_chunks(
    session: AsyncSession,
    faiss_results: List[Tuple[int, float]],
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[str, float]]:
    """Map FAISS embedding IDs back to chunk UUIDs.

    Args:
        session: Async database session.
        faiss_results: List of (embedding_id, score) from FAISS search.
        document_ids: Optional document scope filter.

    Returns:
        List[Tuple[str, float]]: List of (chunk_id, score) tuples.
    """
    if not faiss_results:
        return []

    embedding_ids = [eid for eid, _ in faiss_results]
    score_map = {eid: score for eid, score in faiss_results}

    # Build query to look up chunks by embedding_id
    query = select(Chunk.id, Chunk.embedding_id, Chunk.document_id).where(
        Chunk.embedding_id.in_(embedding_ids)
    )

    if document_ids:
        query = query.where(Chunk.document_id.in_(document_ids))

    result = await session.execute(query)
    rows = result.fetchall()

    chunk_results = []
    for row in rows:
        chunk_id = str(row.id)
        emb_id = row.embedding_id
        score = score_map.get(emb_id, 0.0)
        chunk_results.append((chunk_id, score))

    # Sort by score descending
    chunk_results.sort(key=lambda x: x[1], reverse=True)
    return chunk_results


async def _fetch_chunk_texts(
    session: AsyncSession,
    chunk_ids: List[str],
) -> dict[str, str]:
    """Fetch chunk text content for a list of chunk IDs.

    Args:
        session: Async database session.
        chunk_ids: List of chunk UUID strings.

    Returns:
        dict[str, str]: Mapping of chunk_id → text.
    """
    if not chunk_ids:
        return {}

    result = await session.execute(
        select(Chunk.id, Chunk.text).where(Chunk.id.in_(chunk_ids))
    )
    rows = result.fetchall()
    return {str(row.id): row.text for row in rows}


async def _enrich_results(
    session: AsyncSession,
    chunk_ids: List[str],
    score_map: dict[str, float],
) -> List[RetrievalResult]:
    """Enrich chunk IDs with full metadata for the API response.

    Args:
        session: Async database session.
        chunk_ids: Ordered list of chunk UUID strings.
        score_map: Mapping of chunk_id → final score.

    Returns:
        List[RetrievalResult]: Fully populated retrieval results.
    """
    if not chunk_ids:
        return []

    result = await session.execute(
        select(Chunk, Document.filename).join(
            Document, Chunk.document_id == Document.id
        ).where(Chunk.id.in_(chunk_ids))
    )
    rows = result.fetchall()

    # Build lookup
    chunk_lookup: dict[str, dict] = {}
    for row in rows:
        chunk = row[0]
        filename = row[1]
        cid = str(chunk.id)

        bbox = None
        if chunk.bbox:
            try:
                bbox = BoundingBox(**chunk.bbox)
            except Exception:
                bbox = None

        chunk_lookup[cid] = {
            "chunk_id": cid,
            "document_id": str(chunk.document_id),
            "text": chunk.text,
            "score": score_map.get(cid, 0.0),
            "page_number": chunk.page_number or 0,
            "section_heading": chunk.section_heading,
            "bbox": bbox,
            "source_filename": filename,
        }

    # Return in the order of chunk_ids (preserving rank order)
    results = []
    for cid in chunk_ids:
        if cid in chunk_lookup:
            results.append(RetrievalResult(**chunk_lookup[cid]))

    return results
