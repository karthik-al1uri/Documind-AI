"""DocuMind AI — HyDE (Hypothetical Document Embedding) query expansion.

Generates a hypothetical answer to the user's query using an LLM, then embeds
that hypothetical answer to produce a query vector that is closer in embedding
space to relevant passages than the original query alone.

Uses OpenAI GPT-4o by default; can be swapped for local Llama 3 8B.
"""

import os
import logging
from typing import Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Lazy-loaded OpenAI client
_client = None

HYDE_SYSTEM_PROMPT = (
    "You are a helpful document analyst. Given a user's question, write a "
    "short, factual paragraph that would appear in a document answering the "
    "question. Do not include any preamble. Just write the answer passage."
)


def _get_openai_client():
    """Lazy-initialize the OpenAI client.

    Returns:
        openai.OpenAI: The OpenAI client instance.
    """
    global _client
    if _client is None:
        import openai
        _client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized for HyDE expansion")
    return _client


def generate_hypothetical_answer(query: str) -> str:
    """Generate a hypothetical answer passage for a query using the LLM.

    Args:
        query: The user's original query.

    Returns:
        str: A synthetic passage that answers the query.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_key_here":
        logger.warning("No OpenAI API key configured — returning query as-is for HyDE")
        return query

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": HYDE_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=256,
            temperature=0.3,
        )
        hypothetical = response.choices[0].message.content.strip()
        logger.info(
            "HyDE generated hypothetical answer (%d chars) for query: '%s'",
            len(hypothetical), query[:60],
        )
        return hypothetical
    except Exception as e:
        logger.error("HyDE generation failed: %s — falling back to original query", e)
        return query


def expand_query(query: str) -> str:
    """Expand a query using HyDE for improved retrieval.

    Generates a hypothetical answer and returns it. The caller should embed
    this hypothetical answer instead of (or in addition to) the original query.

    Args:
        query: The user's original query.

    Returns:
        str: The hypothetical answer text to embed for retrieval.
    """
    hypothetical = generate_hypothetical_answer(query)
    logger.info("Query expanded via HyDE: original=%d chars → hypothetical=%d chars",
                len(query), len(hypothetical))
    return hypothetical
