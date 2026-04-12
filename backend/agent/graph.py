"""DocuMind AI — LangGraph agent graph for the agentic RAG pipeline.

Defines a stateful graph that orchestrates retrieval, generation, NLI
verification, and critic-driven retry:

1. Retrieve — call the retrieval pipeline for top-k chunks
2. Generate — produce a grounded answer with per-claim citations
3. Verify  — run NLI entailment on each claim
4. Decide  — if >20% claims fail and retries remain, refine and loop
5. Output  — assemble AnswerResponse with confidence badges
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from agent.llm_generator import generate_answer
from agent.nli_verifier import verify_claims, check_verification_threshold
from agent.critic_agent import analyze_and_refine, should_retry
from models.schemas import AnswerResponse, Claim, RetrievalResult
from retrieval.retrieval_pipeline import run_retrieval_pipeline
from utils.database import async_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

async def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Call the retrieval pipeline to fetch relevant chunks.

    Args:
        state: Current agent state dict.

    Returns:
        Updated state with retrieval_results populated.
    """
    query = state.get("refined_query") or state["query"]
    top_k = state.get("top_k", 5)
    document_ids = state.get("document_ids")

    logger.info("Retrieve node: query='%s', top_k=%d", query, top_k)

    async with async_session() as session:
        results = await run_retrieval_pipeline(
            session=session,
            query=query,
            top_k=top_k,
            document_ids=document_ids,
        )

    logger.info("Retrieved %d chunks", len(results))
    return {**state, "retrieval_results": results}


async def generate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a grounded answer from retrieved chunks.

    Args:
        state: Current agent state with retrieval_results.

    Returns:
        Updated state with generated_answer and claims.
    """
    query = state.get("refined_query") or state["query"]
    results: List[RetrievalResult] = state.get("retrieval_results", [])

    if not results:
        logger.warning("No retrieval results; returning fallback answer")
        return {
            **state,
            "generated_answer": "I cannot answer this based on the provided documents.",
            "claims": [],
        }

    answer, claims = await generate_answer(query, results)
    return {**state, "generated_answer": answer, "claims": claims}


async def verify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run NLI verification on all claims.

    Args:
        state: Current agent state with claims.

    Returns:
        Updated state with verified claims and verification_passed flag.
    """
    claims: List[Claim] = state.get("claims", [])
    if not claims:
        return {**state, "verification_passed": True}

    verified = verify_claims(claims)
    passed = check_verification_threshold(verified, threshold=0.80)
    return {**state, "claims": verified, "verification_passed": passed}


async def critic_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Refine the query when verification fails.

    Args:
        state: Current agent state.

    Returns:
        Updated state with refined_query and incremented retry_count.
    """
    claims: List[Claim] = state.get("claims", [])
    retry_count = state.get("retry_count", 0)

    refined = await analyze_and_refine(state["query"], claims)
    return {**state, "refined_query": refined, "retry_count": retry_count + 1}


async def output_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the final AnswerResponse.

    Args:
        state: Final agent state.

    Returns:
        State with assembled answer_response.
    """
    query_id = state.get("query_id") or str(uuid.uuid4())

    claims_dicts = []
    for c in state.get("claims", []):
        claim_dict: Dict[str, Any] = {
            "text": c.text,
            "confidence": c.confidence,
            "entailment_label": c.entailment_label,
            "entailment_score": c.entailment_score,
        }
        if c.citation:
            claim_dict["citation"] = {
                "chunk_id": c.citation.chunk_id,
                "document_id": c.citation.document_id,
                "page_number": c.citation.page_number,
                "source_filename": c.citation.source_filename,
            }
        claims_dicts.append(claim_dict)

    results: List[RetrievalResult] = state.get("retrieval_results", [])

    response = AnswerResponse(
        answer=state.get("generated_answer", ""),
        claims=claims_dicts,
        sources=results,
        query_id=query_id,
    )
    return {**state, "answer_response": response, "query_id": query_id}


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def decide_after_verify(state: Dict[str, Any]) -> str:
    """Route after verification: retry via critic or proceed to output.

    Args:
        state: Current agent state.

    Returns:
        Next node name: 'critic' or 'output'.
    """
    if state.get("verification_passed", False):
        return "output"

    claims = state.get("claims", [])
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if should_retry(claims, retry_count, max_retries):
        logger.info("Verification failed; routing to critic (retry %d)", retry_count + 1)
        return "critic"

    logger.info("Verification failed but retries exhausted; proceeding to output")
    return "output"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_agent_graph() -> StateGraph:
    """Construct and compile the LangGraph agent graph.

    Returns:
        Compiled StateGraph ready for async invocation.
    """
    graph = StateGraph(dict)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("verify", verify_node)
    graph.add_node("critic", critic_node)
    graph.add_node("output", output_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges("verify", decide_after_verify, {
        "critic": "critic",
        "output": "output",
    })
    graph.add_edge("critic", "retrieve")
    graph.add_edge("output", END)

    return graph.compile()


# Module-level compiled graph
agent_graph = build_agent_graph()


async def run_agent(
    query: str,
    top_k: int = 5,
    document_ids: Optional[List[str]] = None,
) -> AnswerResponse:
    """Execute the full agentic RAG pipeline.

    Args:
        query: User's natural-language question.
        top_k: Number of chunks to retrieve per attempt.
        document_ids: Optional list of document UUIDs to scope retrieval.

    Returns:
        AnswerResponse with grounded answer, verified claims, and sources.
    """
    initial_state = {
        "query": query,
        "top_k": top_k,
        "document_ids": document_ids,
        "retrieval_results": [],
        "generated_answer": None,
        "claims": [],
        "verification_passed": False,
        "retry_count": 0,
        "max_retries": 2,
        "refined_query": None,
        "query_id": str(uuid.uuid4()),
        "error": None,
    }

    logger.info("Running agent for query: %s", query)
    final_state = await agent_graph.ainvoke(initial_state)

    return final_state.get("answer_response", AnswerResponse(
        answer="An error occurred during processing.",
        claims=[],
        sources=[],
        query_id=initial_state["query_id"],
    ))
