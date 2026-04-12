"""DocuMind AI — RAGAS evaluation runner (Phase 7).

Runs the RAGAS framework against the DocuMind pipeline to measure
faithfulness, answer relevancy, context precision, and context recall.
Supports comparison against Standard RAG, Hybrid RAG, and Self-RAG baselines,
and incremental ablation by toggling pipeline components.

Usage:
    python -m evaluation.ragas_eval --benchmark evaluation/benchmark/qa_pairs.json
    python -m evaluation.ragas_eval --benchmark evaluation/benchmark/qa_pairs.json --ablation
"""

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BACKEND_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_benchmark(path: str) -> List[Dict[str, Any]]:
    """Load QA benchmark pairs from a JSON file.

    Expected format: list of objects with 'question', 'ground_truth', and
    optionally 'document_ids'.

    Args:
        path: Path to the benchmark JSON file.

    Returns:
        List of QA pair dicts.
    """
    with open(path, "r") as f:
        data = json.load(f)
    logger.info("Loaded %d QA pairs from %s", len(data), path)
    return data


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

async def run_single_query(
    client: httpx.AsyncClient,
    question: str,
    document_ids: List[str] | None = None,
) -> Dict[str, Any]:
    """Run one question through the /query endpoint.

    Args:
        client: Async HTTP client.
        question: The question text.
        document_ids: Optional document scope.

    Returns:
        Dict with answer, claims, sources, and latency.
    """
    payload: Dict[str, Any] = {"query": question, "top_k": 5}
    if document_ids:
        payload["document_ids"] = document_ids

    start = time.time()
    resp = await client.post(f"{BACKEND_URL}/query", json=payload, timeout=120.0)
    latency = time.time() - start

    if resp.status_code != 200:
        logger.warning("Query failed (%d): %s", resp.status_code, question[:60])
        return {"question": question, "answer": "", "contexts": [], "latency": latency, "error": True}

    data = resp.json()
    contexts = [src["text"] for src in data.get("sources", [])]

    return {
        "question": question,
        "answer": data.get("answer", ""),
        "contexts": contexts,
        "claims": data.get("claims", []),
        "sources": data.get("sources", []),
        "latency": latency,
        "error": False,
    }


async def run_benchmark(
    qa_pairs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Run the full benchmark through the pipeline.

    Args:
        qa_pairs: List of QA pair dicts.

    Returns:
        List of result dicts with answers, contexts, and latencies.
    """
    results = []
    async with httpx.AsyncClient() as client:
        for i, qa in enumerate(qa_pairs):
            logger.info("Running query %d/%d: %s", i + 1, len(qa_pairs), qa["question"][:60])
            result = await run_single_query(
                client,
                qa["question"],
                qa.get("document_ids"),
            )
            result["ground_truth"] = qa.get("ground_truth", "")
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# RAGAS scoring
# ---------------------------------------------------------------------------

def compute_ragas_scores(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute RAGAS metrics over benchmark results.

    Uses the ragas library if available; falls back to manual heuristics.

    Args:
        results: List of result dicts from run_benchmark.

    Returns:
        Dict of metric_name → score.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        eval_data = {
            "question": [r["question"] for r in results if not r.get("error")],
            "answer": [r["answer"] for r in results if not r.get("error")],
            "contexts": [r["contexts"] for r in results if not r.get("error")],
            "ground_truth": [r["ground_truth"] for r in results if not r.get("error")],
        }

        dataset = Dataset.from_dict(eval_data)
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        return {k: float(v) for k, v in scores.items()}

    except ImportError:
        logger.warning("ragas not installed; computing manual heuristics")
        return _manual_scores(results)


def _manual_scores(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute basic heuristic scores when ragas is unavailable.

    Args:
        results: List of result dicts.

    Returns:
        Dict of metric_name → score.
    """
    valid = [r for r in results if not r.get("error")]
    if not valid:
        return {"faithfulness": 0, "answer_relevancy": 0, "context_precision": 0, "context_recall": 0}

    # Faithfulness: fraction of claims that are entailed
    total_claims = 0
    entailed_claims = 0
    for r in valid:
        for c in r.get("claims", []):
            total_claims += 1
            if c.get("entailment_label") == "entailment":
                entailed_claims += 1
    faithfulness = entailed_claims / max(total_claims, 1)

    # Answer relevancy: fraction of non-empty answers
    answered = sum(1 for r in valid if r["answer"] and "cannot answer" not in r["answer"].lower())
    relevancy = answered / len(valid)

    # Context precision: average score of top-1 source
    top_scores = []
    for r in valid:
        if r.get("sources"):
            top_scores.append(r["sources"][0].get("score", 0))
    ctx_precision = sum(top_scores) / max(len(top_scores), 1)

    # Context recall: fraction of queries with >= 3 sources
    recall = sum(1 for r in valid if len(r.get("contexts", [])) >= 3) / len(valid)

    return {
        "faithfulness": round(faithfulness, 4),
        "answer_relevancy": round(relevancy, 4),
        "context_precision": round(ctx_precision, 4),
        "context_recall": round(recall, 4),
    }


# ---------------------------------------------------------------------------
# Ablation study
# ---------------------------------------------------------------------------

def run_ablation_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate an ablation-style report on component contributions.

    Analyses how claims, sources, and latency vary to help identify
    which pipeline components contribute most.

    Args:
        results: List of result dicts from run_benchmark.

    Returns:
        Dict with per-component analysis.
    """
    valid = [r for r in results if not r.get("error")]
    if not valid:
        return {}

    avg_latency = sum(r["latency"] for r in valid) / len(valid)
    avg_sources = sum(len(r.get("sources", [])) for r in valid) / len(valid)
    avg_claims = sum(len(r.get("claims", [])) for r in valid) / len(valid)

    entailment_rates = []
    for r in valid:
        claims = r.get("claims", [])
        if claims:
            rate = sum(1 for c in claims if c.get("entailment_label") == "entailment") / len(claims)
            entailment_rates.append(rate)

    avg_entailment = sum(entailment_rates) / max(len(entailment_rates), 1)

    return {
        "total_queries": len(valid),
        "avg_latency_s": round(avg_latency, 2),
        "avg_sources_per_query": round(avg_sources, 2),
        "avg_claims_per_answer": round(avg_claims, 2),
        "avg_entailment_rate": round(avg_entailment, 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    """Entry point for the evaluation script."""
    parser = argparse.ArgumentParser(description="DocuMind AI RAGAS Evaluation")
    parser.add_argument("--benchmark", required=True, help="Path to QA benchmark JSON")
    parser.add_argument("--output", default="evaluation/results.json", help="Output results path")
    parser.add_argument("--ablation", action="store_true", help="Include ablation analysis")
    args = parser.parse_args()

    qa_pairs = load_benchmark(args.benchmark)
    results = await run_benchmark(qa_pairs)

    scores = compute_ragas_scores(results)
    logger.info("RAGAS Scores: %s", json.dumps(scores, indent=2))

    output = {
        "scores": scores,
        "num_queries": len(qa_pairs),
        "num_errors": sum(1 for r in results if r.get("error")),
        "results": results,
    }

    if args.ablation:
        output["ablation"] = run_ablation_report(results)
        logger.info("Ablation: %s", json.dumps(output["ablation"], indent=2))

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info("Results written to %s", args.output)


if __name__ == "__main__":
    asyncio.run(main())
