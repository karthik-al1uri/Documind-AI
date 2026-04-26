#!/usr/bin/env python3
"""Run AI retrieval queries on 5 documents and save results."""

import json
import sys
import urllib.request
from pathlib import Path

API = "http://localhost:8000"
OUT = Path(__file__).resolve().parent / "ai_review_results.json"


def retrieve(query, doc_ids, top_k=3):
    body = json.dumps({"query": query, "top_k": top_k, "document_ids": doc_ids}).encode()
    req = urllib.request.Request(f"{API}/retrieve", data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=60)
    return json.loads(resp.read())


def get_docs():
    resp = urllib.request.urlopen(f"{API}/documents", timeout=10)
    return json.loads(resp.read())


def main():
    print("Fetching documents...")
    docs = get_docs()

    # Pick 5 diverse docs
    picks = {}
    for d in docs:
        fn = d["filename"]
        if fn.startswith("test_invoice") and "invoice" not in picks:
            picks["invoice"] = d
        elif fn.startswith("test_contract") and "contract" not in picks:
            picks["contract"] = d
        elif fn.startswith("test_financial") and "financial" not in picks:
            picks["financial"] = d
        elif fn.startswith("test_nda") and "nda" not in picks:
            picks["nda"] = d
        elif fn.startswith("test_employment") and "employment" not in picks:
            picks["employment"] = d
        if len(picks) == 5:
            break

    queries = {
        "invoice":    "What is the total amount due and payment terms?",
        "contract":   "What is the termination clause and governing law?",
        "financial":  "What was the total revenue and growth rate?",
        "nda":        "What are the confidentiality obligations and term?",
        "employment": "What is the salary and benefits package?",
    }

    results = []
    for key, doc in picks.items():
        q = queries[key]
        print(f"  [{key}] {doc['filename']} — {q}")
        try:
            chunks = retrieve(q, [doc["id"]])
            top = chunks[0]["text"][:400] if chunks else ""
            results.append({
                "filename": doc["filename"],
                "doc_type_label": key,
                "doc_type_detected": doc.get("doc_type", "unknown"),
                "query": q,
                "num_results": len(chunks),
                "top_score": round(chunks[0]["score"], 4) if chunks else 0,
                "ai_output": top,
            })
            print(f"    -> {len(chunks)} chunks, score={results[-1]['top_score']}")
        except Exception as e:
            print(f"    -> ERROR: {e}")
            results.append({
                "filename": doc["filename"],
                "doc_type_label": key,
                "doc_type_detected": doc.get("doc_type", "unknown"),
                "query": q,
                "error": str(e),
            })

    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {OUT}")
    return results


if __name__ == "__main__":
    main()
