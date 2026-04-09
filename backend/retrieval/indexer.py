"""DocuMind AI — FAISS index management for dense vector storage and retrieval.

Maintains a flat FAISS index for storing chunk embeddings and performing
approximate nearest-neighbour (ANN) searches. Supports saving/loading
the index to/from disk.
"""

import os
import logging
from typing import List, Tuple, Optional
from pathlib import Path

import numpy as np
import faiss
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./storage/faiss.index")
EMBEDDING_DIM = 1024

# Module-level index
_index: Optional[faiss.IndexFlatIP] = None


def _get_index() -> faiss.IndexFlatIP:
    """Get or initialize the FAISS index.

    Loads from disk if an index file exists, otherwise creates a new
    flat inner-product index (IndexFlatIP) for cosine similarity on
    L2-normalised vectors.

    Returns:
        faiss.IndexFlatIP: The FAISS index.
    """
    global _index
    if _index is not None:
        return _index

    if os.path.exists(FAISS_INDEX_PATH):
        logger.info("Loading FAISS index from %s", FAISS_INDEX_PATH)
        _index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info("FAISS index loaded: %d vectors", _index.ntotal)
    else:
        logger.info("Creating new FAISS flat inner-product index (dim=%d)", EMBEDDING_DIM)
        _index = faiss.IndexFlatIP(EMBEDDING_DIM)

    return _index


def save_index() -> None:
    """Persist the current FAISS index to disk.

    Creates parent directories if they do not exist.
    """
    index = _get_index()
    os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
    faiss.write_index(index, FAISS_INDEX_PATH)
    logger.info("FAISS index saved to %s (%d vectors)", FAISS_INDEX_PATH, index.ntotal)


def add_vectors(embeddings: np.ndarray) -> List[int]:
    """Add embedding vectors to the FAISS index.

    Args:
        embeddings: Array of shape (n, EMBEDDING_DIM) with float32 vectors.
            Vectors should be L2-normalised for correct cosine similarity.

    Returns:
        List[int]: List of integer IDs (positions) assigned to the vectors
            in the FAISS index. These correspond to embedding_id in the
            chunks table.
    """
    index = _get_index()
    start_id = index.ntotal
    n = embeddings.shape[0]

    # Ensure float32
    if embeddings.dtype != np.float32:
        embeddings = embeddings.astype(np.float32)

    index.add(embeddings)
    ids = list(range(start_id, start_id + n))

    logger.info("Added %d vectors to FAISS index (total now: %d)", n, index.ntotal)
    save_index()
    return ids


def search(query_vector: np.ndarray, top_k: int = 50) -> List[Tuple[int, float]]:
    """Search the FAISS index for the nearest neighbours of a query vector.

    Args:
        query_vector: 1D array of shape (EMBEDDING_DIM,) or 2D array of
            shape (1, EMBEDDING_DIM).
        top_k: Number of nearest neighbours to return.

    Returns:
        List[Tuple[int, float]]: List of (embedding_id, score) tuples sorted
            by descending similarity score.
    """
    index = _get_index()

    if index.ntotal == 0:
        logger.warning("FAISS index is empty — returning no results")
        return []

    # Reshape to 2D if necessary
    if query_vector.ndim == 1:
        query_vector = query_vector.reshape(1, -1)

    if query_vector.dtype != np.float32:
        query_vector = query_vector.astype(np.float32)

    # Clamp top_k to available vectors
    actual_k = min(top_k, index.ntotal)

    scores, indices = index.search(query_vector, actual_k)

    results: List[Tuple[int, float]] = []
    for i in range(actual_k):
        idx = int(indices[0][i])
        score = float(scores[0][i])
        if idx >= 0:
            results.append((idx, score))

    logger.info("FAISS search returned %d results (top_k=%d)", len(results), top_k)
    return results


def get_index_size() -> int:
    """Get the current number of vectors in the FAISS index.

    Returns:
        int: Number of vectors stored.
    """
    return _get_index().ntotal


def reset_index() -> None:
    """Reset the FAISS index to empty. Use with caution.

    Intended for development and testing only.
    """
    global _index
    _index = faiss.IndexFlatIP(EMBEDDING_DIM)
    save_index()
    logger.warning("FAISS index reset to empty")
