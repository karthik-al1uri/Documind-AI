# Design improvements (integrated into DocuMind AI)

These items extend the base phased plan: they improve retrieval quality, provenance, demos, and production readiness without replacing the core pipeline.

## Retrieval

- **Hybrid search**: Combine dense embeddings with lexical/BM25-style search (e.g. PostgreSQL full-text or a dedicated lexical index). Helps IDs, dates, SKUs, and table-like tokens that pure embeddings miss.
- **Re-ranking**: After top-k vector (and optional lexical) retrieval, apply a cross-encoder or lightweight reranker on candidates before the LLM. Often beats swapping embedding models alone.

## Provenance and citations

- **Stable chunk identity**: Keep explicit chunk IDs and, where possible, char offsets or layout bboxes so citations can move beyond “page + section title” toward highlight-capable references.

## Evaluation

- **Eval earlier than “Phase 9”**: Maintain a small fixed set of questions (10–20) on 2–3 sample documents from the first retrieval milestone. Expand formal benchmarking in the evaluation phase.

## Product and scope

- **Focused demo vertical**: Pick one document family first (e.g. invoices vs compliance reports) so chunking, eval, and UI tell one strong story.

## Operations

- **Failure modes**: Document behavior for partial OCR, mixed native/scan pages, password PDFs, very large files, and optional PII handling.
- **Cost and latency**: Cap context to retrieved chunks, batch embeddings, cache by content hash, and consider a small local model for dry runs.

## Grounding (stretch)

- **Citation verification**: Optional second pass that checks claims against retrieved spans to reduce hallucination and strengthen “grounded RAG” positioning.

## API and jobs

- **Versioned APIs**: Prefer `/v1/...` if the surface will evolve.
- **Async processing**: Treat upload processing as jobs with status and polling or WebSocket updates from the first UI milestone.
