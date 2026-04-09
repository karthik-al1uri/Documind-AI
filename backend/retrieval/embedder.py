"""DocuMind AI — BGE-Large-EN embedding generation.

Loads the BAAI/bge-large-en-v1.5 model via sentence-transformers and
generates dense vector embeddings (d=1024) for text chunks and queries.
Supports instruction-prefixed encoding per the BGE model specification.
"""

import os
import logging
from typing import List

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
HF_CACHE_DIR = os.getenv("HF_CACHE_DIR", "./models")
EMBEDDING_DIM = 1024

# BGE models use instruction prefixes for asymmetric retrieval
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
PASSAGE_PREFIX = ""

# Lazy-loaded model
_model = None


def _get_model():
    """Lazy-initialize the sentence-transformer embedding model.

    Returns:
        SentenceTransformer: The loaded embedding model.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(
            EMBEDDING_MODEL,
            cache_folder=HF_CACHE_DIR,
        )
        logger.info("Embedding model loaded (dim=%d)", EMBEDDING_DIM)
    return _model


def embed_texts(texts: List[str], is_query: bool = False) -> np.ndarray:
    """Generate embeddings for a list of text strings.

    Args:
        texts: List of text strings to embed.
        is_query: If True, prepend the BGE query instruction prefix.
            Use True for queries and False for passages/chunks.

    Returns:
        np.ndarray: Array of shape (len(texts), EMBEDDING_DIM) with float32
            normalized embeddings.
    """
    if not texts:
        return np.array([], dtype=np.float32).reshape(0, EMBEDDING_DIM)

    model = _get_model()

    # Apply instruction prefix for queries per BGE specification
    if is_query:
        prefixed = [QUERY_PREFIX + t for t in texts]
    else:
        prefixed = [PASSAGE_PREFIX + t for t in texts]

    embeddings = model.encode(
        prefixed,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )

    result = np.array(embeddings, dtype=np.float32)
    logger.info(
        "Embedded %d texts (is_query=%s), shape=%s",
        len(texts), is_query, result.shape,
    )
    return result


def embed_query(query: str) -> np.ndarray:
    """Generate an embedding for a single query string.

    Args:
        query: The query text.

    Returns:
        np.ndarray: 1D array of shape (EMBEDDING_DIM,) with the query embedding.
    """
    result = embed_texts([query], is_query=True)
    return result[0]


def embed_chunks(texts: List[str]) -> np.ndarray:
    """Generate embeddings for a list of document chunks (passages).

    Args:
        texts: List of chunk text strings.

    Returns:
        np.ndarray: Array of shape (len(texts), EMBEDDING_DIM).
    """
    return embed_texts(texts, is_query=False)
