"""DocuMind AI — LLM answer generation with grounded citations.

Takes retrieved chunks and a user query, generates an answer using GPT-4o,
and extracts individual claims with source annotations. Each claim is mapped
back to the chunk that supports it.
"""

import json
import logging
import os
from typing import List, Tuple

from openai import AsyncOpenAI

from models.schemas import Claim, RetrievalResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a document analysis assistant for DocuMind AI.
Given a user query and a set of retrieved source passages, generate a precise,
factual answer grounded ONLY in the provided sources.

Rules:
1. Every factual statement must be supported by at least one source passage.
2. After your answer, output a JSON array of claims. Each claim has:
   - "text": the exact claim sentence
   - "source_index": the 0-based index of the source passage that supports it
   - "confidence": your confidence from 0.0 to 1.0
3. If no source supports the query, say "I cannot answer this based on the provided documents."
4. Never fabricate information not present in the sources.
5. Wrap your answer in <answer> tags and claims in <claims> tags.

Example output format:
<answer>
The contract was signed on January 15, 2024. The total value is $1.2M.
</answer>
<claims>
[
  {"text": "The contract was signed on January 15, 2024.", "source_index": 0, "confidence": 0.95},
  {"text": "The total value is $1.2M.", "source_index": 2, "confidence": 0.88}
]
</claims>"""


def _build_context(results: List[RetrievalResult]) -> str:
    """Format retrieval results into a numbered context block.

    Args:
        results: Ranked list of retrieval hits.

    Returns:
        Formatted string with one passage per source.
    """
    parts = []
    for i, r in enumerate(results):
        parts.append(
            f"[Source {i}] (file: {r.source_filename}, page: {r.page_number})\n{r.text}"
        )
    return "\n\n".join(parts)


def _parse_response(raw: str, sources: List[RetrievalResult]) -> Tuple[str, List[Claim]]:
    """Parse the LLM response into answer text and structured claims.

    Args:
        raw: Raw LLM output containing <answer> and <claims> blocks.
        sources: The retrieval results used as context.

    Returns:
        Tuple of (answer_text, list_of_claims).
    """
    answer = ""
    claims: List[Claim] = []

    if "<answer>" in raw and "</answer>" in raw:
        answer = raw.split("<answer>")[1].split("</answer>")[0].strip()
    else:
        answer = raw.strip()

    if "<claims>" in raw and "</claims>" in raw:
        claims_json = raw.split("<claims>")[1].split("</claims>")[0].strip()
        try:
            raw_claims = json.loads(claims_json)
            for rc in raw_claims:
                source_idx = rc.get("source_index", 0)
                citation = sources[source_idx] if source_idx < len(sources) else None
                claims.append(
                    Claim(
                        text=rc["text"],
                        confidence=rc.get("confidence", 0.5),
                        citation=citation,
                    )
                )
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Failed to parse claims JSON: %s", exc)

    return answer, claims


async def generate_answer(
    query: str,
    retrieval_results: List[RetrievalResult],
    #model: str = "gpt-4o",
    model: str = "llama-3.3-70b-versatile",
) -> Tuple[str, List[Claim]]:
    """Generate a grounded answer with per-claim citations.

    Args:
        query: The user's natural-language question.
        retrieval_results: Top-k retrieval hits from the retrieval pipeline.
        model: OpenAI model identifier. Defaults to gpt-4o.

    Returns:
        Tuple of (answer_text, list_of_structured_claims).
    """
    #client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    client = AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    context = _build_context(retrieval_results)
    user_prompt = f"Query: {query}\n\nSources:\n{context}"

    logger.info("Generating answer (model=%s, sources=%d)", model, len(retrieval_results))

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=2048,
    )

    raw_output = response.choices[0].message.content or ""
    answer, claims = _parse_response(raw_output, retrieval_results)

    logger.info("Generated answer with %d claims", len(claims))
    return answer, claims
