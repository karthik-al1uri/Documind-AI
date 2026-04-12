"""DocuMind AI — Critic Agent for query refinement and retry logic.

When NLI verification fails (>20% of claims not entailed), the Critic Agent
analyses the failed claims, refines the query to target missing evidence,
and triggers a retrieval-generation retry (max 2 retries per CLAUDE.md).
"""

import logging
import os
from typing import List

from openai import AsyncOpenAI

from models.schemas import Claim

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """You are a query refinement specialist for a document QA system.

The system generated an answer, but some claims could not be verified against
the source documents. Your job is to analyse the failed claims and produce
a refined query that will retrieve better evidence.

Failed claims:
{failed_claims}

Original query: {original_query}

Instructions:
1. Identify what information is missing or poorly supported.
2. Produce a single refined query that is more specific and targeted.
3. Output ONLY the refined query text, nothing else."""


async def analyze_and_refine(
    original_query: str,
    claims: List[Claim],
) -> str:
    """Analyse failed claims and produce a refined query.

    Args:
        original_query: The user's original query string.
        claims: All verified claims — failed ones filtered internally.

    Returns:
        A refined query string for the next retrieval attempt.
    """
    failed = [c for c in claims if c.entailment_label != "entailment"]

    if not failed:
        logger.info("No failed claims; returning original query")
        return original_query

    failed_text = "\n".join(
        f'- "{c.text}" (label={c.entailment_label}, score={c.entailment_score:.3f})'
        for c in failed
    )

    prompt = CRITIC_PROMPT.format(
        failed_claims=failed_text,
        original_query=original_query,
    )

    logger.info("Critic Agent refining query; %d failed claims", len(failed))

    """client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=256,
    )"""
    client = AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=256,
    )

    refined = (response.choices[0].message.content or "").strip()
    logger.info("Refined query: %s", refined)
    return refined if refined else original_query


def should_retry(claims: List[Claim], retry_count: int, max_retries: int = 2) -> bool:
    """Decide whether to retry based on claim verification results.

    Triggers a retry if >20% of claims fail NLI verification and the retry
    budget is not exhausted.

    Args:
        claims: Verified claims with entailment labels.
        retry_count: Number of retries already attempted.
        max_retries: Maximum allowed retries (default 2 per CLAUDE.md).

    Returns:
        True if a retry should be attempted.
    """
    if retry_count >= max_retries:
        logger.info("Retry budget exhausted (%d/%d)", retry_count, max_retries)
        return False
    if not claims:
        return False

    failed = sum(1 for c in claims if c.entailment_label != "entailment")
    fail_ratio = failed / len(claims)
    logger.info("Fail ratio: %.2f (%d/%d), retries=%d", fail_ratio, failed, len(claims), retry_count)
    return fail_ratio > 0.20
