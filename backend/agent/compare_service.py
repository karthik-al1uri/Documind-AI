"""DocuMind AI — Cross-document comparison using retrieval + LLM summarization.

Retrieves top-k chunks per document with a shared focus query, then asks an
LLM to produce aligned diff rows and an executive summary.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import List, Optional, Tuple
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import CompareDifference, CompareResponse, RetrievalResult
from retrieval.retrieval_pipeline import run_retrieval_pipeline
from utils.database import Document

logger = logging.getLogger(__name__)


def _llm_client() -> AsyncOpenAI:
    """Return async OpenAI-compatible client (Groq if key set, else OpenAI)."""
    if os.getenv("GROQ_API_KEY"):
        return AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _default_model() -> str:
    return "llama-3.3-70b-versatile" if os.getenv("GROQ_API_KEY") else "gpt-4o"


async def _fetch_filenames(
    session: AsyncSession, document_ids: List[str]
) -> Tuple[str, str]:
    """Load filenames for two document UUIDs."""
    out: List[str] = []
    for did in document_ids:
        result = await session.execute(select(Document).where(Document.id == UUID(did)))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document not found: {did}")
        out.append(doc.filename)
    return out[0], out[1]


async def run_document_compare(
    session: AsyncSession,
    document_ids: List[str],
    focus: Optional[str],
) -> CompareResponse:
    """Retrieve chunks per document and generate comparison via LLM.

    Args:
        session: Database session.
        document_ids: Exactly two UUID strings.
        focus: Optional topic to steer retrieval and comparison.

    Returns:
        CompareResponse with differences and summary.
    """
    if len(document_ids) != 2:
        raise ValueError("Exactly two document_ids are required")

    fn1, fn2 = await _fetch_filenames(session, document_ids)
    topic_query = (focus or "payment terms obligations parties effective dates").strip()

    results_a = await run_retrieval_pipeline(
        session, topic_query, top_k=5, document_ids=[document_ids[0]]
    )
    results_b = await run_retrieval_pipeline(
        session, topic_query, top_k=5, document_ids=[document_ids[1]]
    )

    block_a = _format_chunks(fn1, results_a)
    block_b = _format_chunks(fn2, results_b)

    differences, summary = await _llm_compare(
        topic_query, fn1, fn2, block_a, block_b
    )

    return CompareResponse(
        comparison_id=str(uuid.uuid4()),
        documents=[fn1, fn2],
        differences=differences,
        summary=summary,
    )


def _format_chunks(filename: str, results: List[RetrievalResult]) -> str:
    """Format retrieval hits as a single text block for the LLM."""
    if not results:
        return f"(No indexed passages retrieved for {filename}.)"
    parts = []
    for i, r in enumerate(results):
        parts.append(
            f"[{i + 1}] page {r.page_number} | {r.text[:1200]}"
        )
    return "\n".join(parts)


async def _llm_compare(
    focus: str,
    name1: str,
    name2: str,
    text_a: str,
    text_b: str,
) -> Tuple[List[CompareDifference], str]:
    """Call LLM to produce structured differences and summary."""
    system = (
        "You compare two document excerpts. Output valid JSON only, no markdown.\n"
        "Schema:\n"
        '{"differences":[{"topic":"string","document_1":"string","document_2":"string",'
        '"similarity_score":number}],"summary":"string"}\n'
        "Use 1–3 difference rows. similarity_score is 0.0–1.0 semantic similarity "
        "for that topic. Be concise."
    )
    user = (
        f"Focus / topic: {focus}\n\n"
        f"=== Document A ({name1}) ===\n{text_a}\n\n"
        f"=== Document B ({name2}) ===\n{text_b}\n"
    )

    client = _llm_client()
    model = _default_model()
    key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key or key == "your_key_here":
        return _fallback_diff(focus, name1, name2, text_a, text_b)

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        diffs = []
        for d in data.get("differences", []):
            diffs.append(
                CompareDifference(
                    topic=str(d.get("topic", focus)),
                    document_1=str(d.get("document_1", ""))[:8000],
                    document_2=str(d.get("document_2", ""))[:8000],
                    similarity_score=float(d.get("similarity_score", 0.5)),
                )
            )
        summary = str(data.get("summary", "")).strip() or _heuristic_summary(
            name1, name2, diffs
        )
        if not diffs:
            return _fallback_diff(focus, name1, name2, text_a, text_b)
        return diffs, summary
    except Exception as exc:
        logger.warning("LLM compare failed: %s — using fallback", exc)
        return _fallback_diff(focus, name1, name2, text_a, text_b)


def _fallback_diff(
    focus: str,
    name1: str,
    name2: str,
    text_a: str,
    text_b: str,
) -> Tuple[List[CompareDifference], str]:
    """Heuristic comparison when LLM is unavailable."""
    d = CompareDifference(
        topic=focus[:120],
        document_1=text_a[:2000],
        document_2=text_b[:2000],
        similarity_score=0.55,
    )
    summary = (
        f"Side-by-side excerpts for «{focus}» from {name1} and {name2}. "
        "LLM comparison was unavailable; showing retrieved passages."
    )
    return [d], summary


def _heuristic_summary(
    name1: str, name2: str, diffs: List[CompareDifference]
) -> str:
    return (
        f"Compared {name1} and {name2} across {len(diffs)} topic(s). "
        "Review the passages below for contractual or factual differences."
    )
