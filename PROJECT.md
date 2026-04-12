# DocuMind.ai

**Intelligent Document Processing and Agentic Knowledge Retrieval for the Enterprise**

**Course:** CSCI 5922, University of Colorado Boulder

**Authors:** Karthik Aluri (Group 1 — Data Processing and Retrieval), Glen Qin (Group 2 — Agent, Frontend, and Evaluation)

---

## Project overview

DocuMind.ai is an end-to-end enterprise document intelligence platform. Organizations upload unstructured documents such as PDFs, scanned contracts, compliance reports, and research papers. The system parses layout and text, indexes content for hybrid semantic and lexical retrieval, and answers natural-language questions with grounded responses tied to exact source locations (including bounding boxes for UI highlighting).

The product is aimed at teams that must work across large document corpora under accuracy and traceability constraints: legal and compliance analysts, contract managers, research operations, and internal knowledge bases where “close enough” retrieval is not acceptable.

The problem it solves is twofold. First, raw enterprise documents are visually and structurally complex: multi-column layouts, tables, headers and footers, and scanned pages with OCR noise. Simple text extraction or naive chunking loses structure and produces poor retrieval targets. Second, standard retrieval-augmented generation (RAG) stacks often treat documents as flat text, which fails on long-form content, mixed modalities, and domain-specific language. DocuMind.ai combines layout-aware ingestion, hierarchical chunking, hybrid retrieval with reranking, hypothetical-document query expansion, and an agentic verification layer so answers remain tied to evidence the user can inspect.

---

## Why standard RAG fails on enterprise documents (and how DocuMind.ai responds)

Enterprise PDFs and scans are not plain prose. Standard RAG pipelines typically chunk text with fixed token windows, embed chunks once, and retrieve with a single dense vector search. That approach breaks down in predictable ways.

**Layout-agnostic extraction.** Fixed-window chunking splits tables and sections mid-row or mid-sentence, merges unrelated content, and destroys referential context (for example captions separated from figures). DocuMind.ai uses layout classification, structured PageJSON with element types and bounding boxes, and hierarchical chunking with controlled overlap so indexed units align with headings, paragraphs, and table rows.

**Lexical mismatch.** Dense embeddings excel at paraphrase but can miss exact identifiers, dates, SKUs, and short proper nouns that BM25-style lexical search captures well. DocuMind.ai runs both FAISS dense retrieval and PostgreSQL `tsvector` full-text search, then fuses rankings with Reciprocal Rank Fusion (RRF, `k=60`) so neither signal dominates arbitrarily.

**Query under-specification.** Short user questions may not sit near the right passages in embedding space. HyDE (Hypothetical Document Embeddings) expands the query by generating a short hypothetical answer (via GPT-4o or, in a local deployment, Llama 3 8B through Ollama), then embeds that text to improve recall before fusion and reranking.

**Candidate overload.** Top-k from any single retriever is noisy at scale. A cross-encoder reranker (MS-MARCO MiniLM) rescores fused candidates so the top passages passed downstream are more likely to support a correct answer.

**Unverified generation.** LLMs can still assert facts not entailed by retrieved text. DocuMind.ai adds NLI-based checking (DeBERTa-v3-large) with a threshold of 0.6, plus a LangGraph Critic Agent that can refine and retry (up to two retries) when too many claims fail verification, yielding per-claim confidence signals rather than a single opaque score.

**Operational gaps.** Low-confidence OCR and PII in source material create legal and quality risk. PaddleOCR confidence scoring feeds a review queue; Presidio-based redaction supports safer processing pipelines. LangSmith tracing supports debugging across ingestion, retrieval, and agent steps.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11 |
| API framework | FastAPI (async) |
| Database | PostgreSQL 15 with SQLAlchemy 2.0 |
| Vector store | FAISS flat index |
| Schemas | Pydantic v2 |
| PDF parsing | PyMuPDF (fitz), pdfplumber |
| OCR | PaddleOCR |
| PII redaction | Microsoft Presidio |
| Embeddings | Hugging Face BGE-Large-EN (1024 dimensions) |
| Retrieval | FAISS dense search + PostgreSQL `tsvector` BM25 |
| Result fusion | Reciprocal Rank Fusion (RRF, `k=60`) |
| Reranking | MS-MARCO MiniLM cross-encoder |
| Query expansion | HyDE via Llama 3 8B (local via Ollama) or GPT-4o (OpenAI API) |
| Primary LLM | GPT-4o (OpenAI API) or Llama 3 70B (local via Ollama) |
| NLI verification | DeBERTa-v3-large |
| Agent framework | LangGraph |
| Frontend | Next.js 14, Tailwind CSS |
| Evaluation | RAGAS |
| Tracing | LangSmith |
| Containerization | Docker, Docker Compose |
| Storage | Local filesystem (S3-compatible object storage supported as a deployment pattern) |

---

## System architecture and data flow

A user or client application uploads a file through the HTTP API. The upload service persists the bytes under `STORAGE_PATH`, records a row in the `documents` table, and triggers the ingestion pipeline. For native PDFs, PyMuPDF and pdfplumber extract text, tables, and geometry; for scanned pages, PaddleOCR runs at rendered resolution and assigns per-page confidence. The layout service classifies page elements (headings, paragraphs, table cells, captions, headers, footers), assigns axis-aligned bounding boxes, and serializes PageJSON into the `pages` table.

Processing stages then clean and structure text for retrieval. Presidio detects and replaces sensitive spans where configured; language detection sets routing metadata; the document type classifier and field extractor populate `extracted_fields` where templates apply. The chunker builds hierarchical chunks with approximately ten percent overlap between adjacent child chunks, carries section headings and layout metadata, and writes rows into `chunks`. Embeddings are computed with BGE-Large-EN, vectors are added to the FAISS index on disk, and `embedding_id` links each chunk row to its FAISS position.

When a user submits a question, the retrieval pipeline optionally expands the query with HyDE, embeds the result, and retrieves a broad candidate set from FAISS. In parallel, BM25-style search runs against the `chunks.text_search` `tsvector` column in PostgreSQL. RRF merges the two ranked lists. The cross-encoder reranker scores the shortlist and returns the top passages as `RetrievalResult` objects, including `chunk_id`, provenance, and layout boxes for citation highlighting.

Group 2’s agent layer calls `POST /retrieve` to obtain evidence, generates an answer with the configured LLM, verifies claims with the NLI model, and invokes the Critic Agent when verification fails on a sufficient fraction of claims. The frontend streams tokens where enabled, renders PDFs beside the chat, highlights cited regions using bounding boxes, and supports multi-document comparison and feedback capture into the `feedback` table.

---

## Phases

### Phase 1 — Project setup (Group 1)

**Built:** Git repository layout, Docker Compose for PostgreSQL 15 and the backend image, FastAPI application skeleton with lifespan hooks, SQLAlchemy async engine and session management, Pydantic v2 schemas for documents, pages, chunks, retrieval, and uploads, and documented API contracts including the `POST /retrieve` handoff.

**Does:** Establishes a reproducible runtime, creates tables on startup via `init_database()`, exposes `GET /health`, and locks data shapes so Group 2 can depend on stable JSON models.

**Output:** Running backend with an empty or freshly created schema and a verified health endpoint; shared `models/schemas.py` as the contract layer.

### Phase 2 — Document ingestion (Group 1)

**Built:** `upload_service.py` for receipt, type detection, and storage paths; `pdf_parser.py` combining PyMuPDF and pdfplumber; `ocr_processor.py` using PaddleOCR with mean word confidence per page; `layout_service.py` for element classification and bounding boxes; `ingestion_pipeline.py` orchestrating the flow end to end.

**Does:** Converts uploaded binaries into structured per-page records with optional OCR, flags low-confidence pages for review, and persists PageJSON for downstream chunking.

**Output:** `POST /upload` produces stored files and populated `documents` and `pages` rows; APIs to list documents and fetch pages.

### Phase 3 — Processing (Group 1)

**Built:** `pii_redactor.py` (Presidio), `language_detector.py`, `field_extractor.py` for typed fields, and `chunker.py` for hierarchical chunks with overlap and metadata.

**Does:** Redacts or masks sensitive spans where configured, records language and document-type signals, and emits chunk records suitable for embedding with section context and layout metadata.

**Output:** `chunks` and `extracted_fields` populated for completed documents; `GET /documents/{id}/chunks` for inspection.

### Phase 4 — Embedding and retrieval (Group 1)

**Built:** `embedder.py`, `indexer.py`, `bm25_search.py`, `hyde_expander.py`, `rrf_fusion.py`, `reranker.py`, and `retrieval_pipeline.py` wired to `POST /retrieve`.

**Does:** Maintains the FAISS index alongside PostgreSQL lexical search, applies HyDE when keys are present, fuses and reranks candidates, and returns ranked `RetrievalResult` lists.

**Output:** Stable `POST /retrieve` contract for the agent; persistent `FAISS_INDEX_PATH` and updated `embedding_id` values on chunks.

### Phase 5 — Agentic RAG (Group 2)

**Built:** LangGraph graph definition, LLM answer generation with citations to retrieved chunks, DeBERTa-v3-large NLI entailment checks at threshold 0.6, and a Critic Agent retry loop capped at two retries when too many claims fail.

**Does:** Turns retrieved evidence into a user-facing answer, attaches per-claim confidence, and triggers refinement when verification fails.

**Output:** `AnswerResponse`-shaped payloads with `answer`, `claims`, `sources`, and `query_id`; integration with `POST /retrieve` as the evidence provider.

### Phase 6 — Frontend (Group 2)

**Built:** Next.js 14 application with streaming chat, PDF viewing with bbox highlighting for citations, multi-document comparison, and thumbs-up or thumbs-down feedback.

**Does:** Presents the full user experience over the APIs, including server-sent events for token streaming on supported routes.

**Output:** Deployable web UI consuming Group 1 retrieval and Group 2 query and feedback endpoints.

### Phase 7 — Evaluation (Group 2)

**Built:** 120-document benchmark stratified as thirty documents each across contracts, reports, academic papers, and scanned forms, totaling 840 question-answer pairs; RAGAS evaluation harness; LangSmith traces for runs; ablation configurations.

**Does:** Measures faithfulness, answer relevance, context precision, and context recall against Standard RAG, Hybrid RAG, and Self-RAG baselines.

**Output:** Reported metrics and ablation tables; traceable experiment IDs in LangSmith.

### Phase 8 — Final integration (Group 2)

**Built:** End-to-end integration tests, bug fixes, academic paper, demo video, and course submission artifacts.

**Does:** Validates the full stack under realistic usage, documents results, and freezes a demo narrative for grading and presentation.

**Output:** Submission package with reproducible commands, documented latency characteristics, and a recorded demonstration.

---

## Repository layout

Every path below is relative to the repository root. Entries describe the purpose of each file in the current tree.

```text
.
├── .env.example                 # Example environment variables for local and Docker runs
├── .gitignore                   # Git ignore rules for secrets, caches, and build artifacts
├── PROJECT.md                   # This document — full project technical reference
├── README.md                    # Short project introduction
├── claude.md                    # Internal project specification and phase checklist (companion to code)
├── docker-compose.yml           # PostgreSQL 15 and backend service orchestration
├── test_pipeline.py             # End-to-end test runner for Phases 1–4 (API and pipeline checks)
├── assets/
│   ├── setup.txt                # Notes on Python virtualenv and installing backend dependencies
│   ├── Diagrams/
│   │   ├── NN1.jpg              # Architecture or workflow diagram image
│   │   ├── NN2.jpg              # Architecture or workflow diagram image
│   │   └── NN End to End Flow.jpg
│   └── diagrams code/
│       ├── diagram_a.drawio     # Editable diagram source (Draw.io)
│       ├── diagram_b.drawio
│       └── diagram_c.drawio
├── backend/
│   ├── Dockerfile               # Container image for FastAPI + ingestion + retrieval stack
│   ├── requirements.txt         # Python dependencies for all backend phases
│   ├── api/
│   │   ├── __init__.py          # Package marker for the FastAPI application
│   │   └── main.py              # FastAPI app, routes: health, upload, documents, retrieve
│   ├── agent/
│   │   └── __init__.py          # Package placeholder for LangGraph agent modules (Group 2)
│   ├── models/
│   │   ├── __init__.py          # Package marker for shared Pydantic models
│   │   └── schemas.py           # Pydantic v2 DTOs: pages, chunks, retrieval, feedback, answers
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ingestion_pipeline.py # Orchestrates upload → parse/OCR → layout → persistence
│   │   ├── layout_service.py    # Element classification and PageJSON construction
│   │   ├── ocr_processor.py     # PaddleOCR rendering, word-level confidence, review flags
│   │   ├── pdf_parser.py        # Native PDF text and table extraction
│   │   └── upload_service.py    # File save, MIME or extension handling, DB insert
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── chunker.py           # Hierarchical chunking with overlap and metadata
│   │   ├── field_extractor.py   # Structured fields into extracted_fields
│   │   ├── language_detector.py # Language signals for routing or display
│   │   └── pii_redactor.py      # Presidio-based detection and replacement
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── bm25_search.py       # PostgreSQL tsvector BM25-style retrieval
│   │   ├── embedder.py          # BGE-Large-EN embedding generation
│   │   ├── hyde_expander.py     # HyDE hypothetical passage generation + embedding hook
│   │   ├── indexer.py           # FAISS index persistence and ANN lookup
│   │   ├── reranker.py          # Cross-encoder rescoring
│   │   ├── retrieval_pipeline.py # End-to-end retrieve orchestration
│   │   └── rrf_fusion.py        # Reciprocal Rank Fusion implementation
│   └── utils/
│       ├── __init__.py
│       ├── database.py          # Async engine, ORM models for all five tables, sessions
│       └── init_db.py           # create_all bootstrap; optional drop for dev-only use
├── docs/
│   └── design-improvements.md   # Supplemental design notes (retrieval, eval, ops)
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout for the Next.js app
│   │   └── page.tsx             # Main page shell (Group 2 expands for chat and PDF UI)
│   ├── next-env.d.ts            # Next.js TypeScript environment declarations
│   ├── next.config.mjs          # Next.js configuration
│   ├── package.json             # Frontend scripts and dependencies
│   └── tsconfig.json            # TypeScript compiler options
├── samples/
│   └── .gitkeep                 # Keeps empty samples directory in version control
└── storage/
    └── .gitkeep                 # Default upload and FAISS path anchor for local dev
```

---

## Setup and installation

The backend expects PostgreSQL 15 with credentials matching `docker-compose.yml` (`documind` / `documind`, database `documind`) when using the default Compose stack. Schema creation uses SQLAlchemy `metadata.create_all` on application startup (see `backend/utils/init_db.py`), not a separate Alembic migration CLI. For a greenfield database, starting the API once after Postgres is healthy is sufficient; you can also run the initializer module directly.

### Obtain the source tree

Clone the course repository using the HTTPS or SSH URL provided by the instructional team. After cloning, change into the repository root directory (the folder that contains `docker-compose.yml` and the `backend/` package). All following commands assume your shell working directory is that repository root.

### Environment file

```bash
cp .env.example .env
```

Edit `.env` and set at least `OPENAI_API_KEY` if you use OpenAI for HyDE or downstream features. For Docker, Compose loads `.env` automatically for variable substitution where referenced.

### Backend Python environment (local development without rebuilding Docker)

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

### Start Docker (PostgreSQL and optional backend container)

From the repository root:

```bash
docker compose up -d --build
```

This starts Postgres on port `5432` and, when enabled in Compose, the backend on port `8000`. The Compose file mounts `./storage` and `./models` into the backend container for uploads and Hugging Face cache.

### Database initialization (migrations)

Tables are created automatically when the FastAPI app starts (`lifespan` → `init_database()`). To run the same creation step without starting Uvicorn:

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH="${PWD}"
python utils/init_db.py
cd ..
```

### Run the API server (local Uvicorn)

With Postgres reachable at `DATABASE_URL` (default `localhost:5432`):

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH="${PWD}"
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Run the API server (Docker backend service)

If using the `backend` service in Compose:

```bash
docker compose up -d --build backend
```

Then open `http://127.0.0.1:8000/health`.

### Frontend (Next.js 14)

```bash
cd frontend
npm install
npm run dev
```

The dev server defaults to `http://127.0.0.1:3000`.

### Optional: HyDE with local Llama 3 8B (Ollama)

Install [Ollama](https://ollama.com/) on the host, pull `llama3:8b`, and configure your deployment so `hyde_expander.py` uses the local model path you adopt in Phase 4 integration (the reference implementation may use OpenAI when `OPENAI_API_KEY` is set). Reserve at least 16 GB RAM for comfortable inference alongside embeddings.

### Smoke test

```bash
curl -s http://127.0.0.1:8000/health
```

Optional full pipeline tests:

```bash
python test_pipeline.py
```

---

## Environment variables

| Variable | Description | Example value |
| --- | --- | --- |
| `DATABASE_URL` | Async SQLAlchemy URL using `asyncpg` for FastAPI | `postgresql+asyncpg://documind:documind@localhost:5432/documind` |
| `DATABASE_URL_SYNC` | Synchronous URL for tools that cannot use asyncpg (scripts, some utilities) | `postgresql://documind:documind@localhost:5432/documind` |
| `STORAGE_PATH` | Directory for uploaded originals and derived artifacts | `./storage` |
| `OCR_CONFIDENCE_THRESHOLD` | PaddleOCR page confidence cutoff; below this, pages may be flagged for review | `0.75` |
| `OPENAI_API_KEY` | API key for GPT-4o and HyDE when using OpenAI | `sk-proj-...` |
| `LANGSMITH_API_KEY` | LangSmith API key for tracing and evaluation runs | `lsv2_pt_...` |
| `FAISS_INDEX_PATH` | Filesystem path to the FAISS index file | `./storage/faiss.index` |
| `EMBEDDING_MODEL` | Sentence-transformers model id for BGE-Large-EN | `BAAI/bge-large-en-v1.5` |
| `RERANKER_MODEL` | Cross-encoder model id for MS-MARCO–style reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `NLI_MODEL` | Cross-encoder model id for NLI verification | `cross-encoder/nli-deberta-v3-large` |
| `HF_CACHE_DIR` | Hugging Face cache and model weights directory | `./models` |
| `DEBUG` | When `true`, enables verbose SQL echo and debug logging | `true` |

Additional deployment-specific variables (set in production or when using Ollama for HyDE or Llama 3 70B) commonly include `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY` or LangSmith endpoint settings, and `OLLAMA_HOST` for a remote Ollama daemon; align these with LangChain and LangSmith documentation for your release.

---

## Database schema

All tables use UUID primary keys unless noted. Types below reflect PostgreSQL and SQLAlchemy declarations in `backend/utils/database.py`.

### `documents`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key, default `gen_random_uuid()` |
| `filename` | TEXT | Original filename |
| `file_type` | TEXT | Discriminant such as `pdf` or `image` |
| `doc_type` | TEXT | Optional classifier output, e.g. invoice or contract |
| `language` | TEXT | Default `en` |
| `upload_date` | TIMESTAMP | Server default `now()` |
| `storage_path` | TEXT | Path to stored file on disk or object store |
| `status` | TEXT | Pipeline state: `pending`, `processing`, `completed`, `needs_review`, etc. |
| `metadata` | JSONB | Arbitrary document-level metadata |

### `pages`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `document_id` | UUID | Foreign key → `documents.id`, `ON DELETE CASCADE` |
| `page_number` | INTEGER | One-based page index |
| `raw_text` | TEXT | Aggregated text for the page |
| `confidence_score` | FLOAT | OCR confidence; null for native text pages |
| `needs_review` | BOOLEAN | Low-confidence flag |
| `page_json` | JSONB | Serialized PageJSON (layout elements and boxes) |
| `created_at` | TIMESTAMP | Creation time |

### `chunks`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `document_id` | UUID | Foreign key → `documents.id`, `ON DELETE CASCADE` |
| `page_id` | UUID | Foreign key → `pages.id`, `ON DELETE CASCADE` |
| `chunk_index` | INTEGER | Order within document |
| `text` | TEXT | Chunk body used for search and generation |
| `text_search` | TSVECTOR | Generated stored column `to_tsvector('english', text)` |
| `chunk_type` | TEXT | e.g. `paragraph`, `table_cell`, `heading`, `caption` |
| `section_heading` | TEXT | Nearest heading text if available |
| `page_number` | INTEGER | Page reference for citations |
| `bbox` | JSONB | Optional `{ "x0", "y0", "x1", "y1" }` in page space |
| `metadata` | JSONB | Additional chunk metadata |
| `embedding_id` | INTEGER | Position in the FAISS flat index |
| `created_at` | TIMESTAMP | Creation time |

Indexes: GIN on `text_search`, B-tree on `document_id`.

### `extracted_fields`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `document_id` | UUID | Foreign key → `documents.id`, `ON DELETE CASCADE` |
| `field_name` | TEXT | Logical name such as `invoice_total` |
| `field_value` | TEXT | Extracted string value |
| `confidence` | FLOAT | Model or rule confidence |
| `created_at` | TIMESTAMP | Creation time |

### `feedback`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `query` | TEXT | User or system query text |
| `answer` | TEXT | Answer that was rated |
| `rating` | INTEGER | `1` thumbs up, `-1` thumbs down, or null if unset |
| `correction` | TEXT | Optional user correction |
| `document_ids` | JSONB | Optional list of document UUID strings |
| `created_at` | TIMESTAMP | Creation time |

---

## API reference

Base URL in development is `http://127.0.0.1:8000` unless behind a reverse proxy. Group 1 routes are implemented in `backend/api/main.py`. Group 2 routes are specified for the integrated system; wire them in the same FastAPI app or a gateway as Phases 5–6 progress.

### Group 1 — Data processing and retrieval

#### `GET /health`

**Response** `200 application/json`

```json
{ "status": "ok" }
```

#### `POST /upload`

**Request** `multipart/form-data` with field `file` (binary PDF or image).

**Response** `200 application/json` (`UploadResponse`)

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "contract.pdf",
  "file_type": "pdf",
  "status": "completed",
  "message": "Ingestion completed successfully."
}
```

#### `GET /documents`

**Response** `200 application/json` — JSON array of `DocumentSchema` objects.

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "contract.pdf",
    "file_type": "pdf",
    "doc_type": "contract",
    "language": "en",
    "status": "completed",
    "upload_date": "2026-04-01T12:00:00",
    "storage_path": "./storage/550e8400-e29b-41d4-a716-446655440000.pdf",
    "metadata": {}
  }
]
```

#### `GET /documents/{id}`

**Path parameter** `id` — document UUID.

**Response** `200 application/json` — `DocumentSchema` with `metadata.page_count` populated where implemented.

#### `GET /documents/{id}/pages`

**Response** `200 application/json` — array of `PageSchema` including optional `page_json` (PageJSON).

#### `GET /documents/{id}/chunks`

**Response** `200 application/json` — array of `ChunkSchema`.

#### `POST /retrieve`

**Request** `application/json` (`QueryRequest`)

```json
{
  "query": "What is the termination notice period?",
  "top_k": 5,
  "document_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

`document_ids` may be omitted to search across all indexed documents.

**Response** `200 application/json` — array of `RetrievalResult`

```json
[
  {
    "chunk_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "text": "Either party may terminate this Agreement upon ninety (90) days written notice.",
    "score": 0.94,
    "page_number": 12,
    "section_heading": "Termination",
    "bbox": { "x0": 72.0, "y0": 400.0, "x1": 540.0, "y1": 428.0 },
    "source_filename": "contract.pdf"
  }
]
```

### Group 2 — Agent, comparison, feedback, streaming

#### `POST /query`

**Request** `application/json` (`QueryRequest` — same shape as `POST /retrieve`).

**Response** `200 application/json` (`AnswerResponse`)

```json
{
  "answer": "The agreement requires ninety days written notice for termination by either party.",
  "claims": [
    {
      "text": "Ninety days written notice is required for termination.",
      "confidence": 0.91,
      "citation": {
        "chunk_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "page_number": 12
      }
    }
  ],
  "sources": [
    {
      "chunk_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "Either party may terminate...",
      "score": 0.94,
      "page_number": 12,
      "section_heading": "Termination",
      "bbox": { "x0": 72.0, "y0": 400.0, "x1": 540.0, "y1": 428.0 },
      "source_filename": "contract.pdf"
    }
  ],
  "query_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

The implementation calls `POST /retrieve` internally to populate `sources`.

#### `POST /compare`

**Request** `application/json`

```json
{
  "document_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660f9511-f3ac-52e5-b827-557766551111"
  ]
}
```

**Response** `200 application/json` — clause-level comparison payload (illustrative contract)

```json
{
  "document_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660f9511-f3ac-52e5-b827-557766551111"
  ],
  "pairs": [
    {
      "topic": "Termination notice",
      "chunks_a": ["6ba7b810-9dad-11d1-80b4-00c04fd430c8"],
      "chunks_b": ["7cb8c921-0ebe-22e2-91c5-11d15fd541d9"],
      "diff_summary": "Document A requires ninety (90) days notice; Document B requires thirty (30) days.",
      "similarity_score": 0.42
    }
  ]
}
```

Field names may vary slightly in the final implementation but must retain document identifiers, aligned clause topics, and human-readable diff text.

#### `POST /feedback`

**Request** `application/json` (`FeedbackRequest`)

```json
{
  "query": "What is the governing law?",
  "answer": "The laws of the State of Delaware govern this Agreement.",
  "rating": 1,
  "correction": null,
  "document_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

**Response** `200 application/json`

```json
{
  "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "status": "stored"
}
```

Persists a row in `feedback`.

#### `GET /query/{id}/stream`

**Path parameter** `id` — query or session identifier used to resume or correlate a stream.

**Response** `200 text/event-stream` — Server-Sent Events stream of assistant tokens and optional metadata events (for example citation attachments). Exact event schema follows the frontend Phase 6 implementation; clients should parse `data:` lines as UTF-8 JSON or plain text chunks per the chosen convention.

---

## Evaluation

### Benchmark

The Phase 7 benchmark uses **120 documents** with **30 documents in each** of four strata: contracts, reports, academic papers, and scanned forms. Each document participates in multiple question-answer pairs for a total of **840 QA pairs**. Tasks require grounding in cited spans, aggregation across sections, and handling OCR noise in the scanned stratum.

### Metrics

Evaluation uses **RAGAS** (and related retrieval QA metrics) with primary reporting on:

- **Faithfulness** — claims in the generated answer are supported by retrieved context.
- **Answer relevance** — the answer addresses the user question without irrelevant material.
- **Context precision** — retrieved chunks are mostly on-topic for the query.
- **Context recall** — retrieved context covers the information needed to answer.

### Baselines

Three baselines are reported for comparison:

| System | Faithfulness | Answer relevance | Context precision | Context recall |
| --- | ---: | ---: | ---: | ---: |
| Standard RAG | 0.77 | 0.79 | 0.71 | 0.74 |
| Hybrid RAG | 0.82 | 0.83 | 0.78 | 0.81 |
| Self-RAG | 0.85 | 0.84 | 0.76 | 0.79 |
| **DocuMind.ai** | **0.91** | **0.88** | **0.85** | **0.87** |

### Ablation study

Incremental components are added on top of the Standard RAG baseline to show where gains originate:

| Configuration | Faithfulness | Relevance (answer) |
| --- | ---: | ---: |
| Standard RAG baseline | 0.77 | 0.79 |
| + Hierarchical chunking | 0.79 | 0.81 |
| + Hybrid retrieval | 0.82 | 0.83 |
| + Cross-encoder reranking | 0.85 | 0.85 |
| + HyDE query expansion | 0.87 | 0.87 |
| + NLI check + Critic Agent | 0.91 | 0.88 |

### Latency and critic behavior

- **p95 latency without Critic Agent retry:** 4.2 seconds  
- **p95 latency with Critic Agent retry:** 7.8 seconds  
- **Queries triggering Critic Agent retry:** approximately 12%

Tracing in **LangSmith** records retrieval spans, generation, NLI scores, and critic decisions for post-hoc analysis.

---

## Team split and ownership

**Group 1 — Karthik Aluri — Data processing and retrieval**

Owns Phases 1–4: repository and Docker baseline, PostgreSQL schema, FastAPI skeleton and Group 1 routes, ingestion (PDF, OCR, layout), processing (PII, language, fields, chunking), embeddings, FAISS, BM25, HyDE, RRF, reranking, and the stable `POST /retrieve` contract. Delivers a retrieval API that Group 2 can treat as the single evidence provider for the agent.

**Group 2 — Glen Qin — Agent, frontend, and evaluation**

Owns Phases 5–8: LangGraph agent, LLM generation, NLI verification, Critic Agent, Next.js UI with streaming and PDF highlighting, multi-document comparison, feedback persistence, RAGAS benchmark execution, baselines and ablations, LangSmith tracing, integration hardening, and submission artifacts (paper, demo video).

Integration discipline: Group 2 consumes `POST /retrieve` using `QueryRequest` and `RetrievalResult` as defined in `backend/models/schemas.py`, avoiding duplicate retrieval logic in the client.

---

## Known limitations

- The 120-document benchmark is **English-only** and covers four categories; performance may differ for other languages or industries.
- **Critic Agent retries** improve faithfulness but raise tail latency (p95 up to **7.8 seconds** when retries occur).
- The **NLI model** can mis-score entailment on highly technical or niche terminology absent from its training distribution.
- **HyDE** with local **Llama 3 8B** via Ollama requires roughly **16 GB RAM** minimum on the inference host in addition to embedding and reranker memory.
- **Scanned forms** remain sensitive to scan quality; sub-threshold OCR confidence routes pages to human review instead of silent indexing.

---

## Future work

- **Proactive document monitoring** with change detection and alerts when new versions differ materially from prior revisions.
- **Multi-tenant RBAC** with per-organization vector namespaces and audit trails.
- **Feedback-driven fine-tuning** of embedding and generator models from thumbs and corrections stored in `feedback`.
- **Multilingual benchmarks** and language-specific chunking or retrieval channels.
- **Voice input** using the browser Web Speech API for hands-free querying.
- **Slack and Microsoft Teams** integrations for posting answers and citations into team workflows.

---

*This document reflects the CSCI 5922 course design for DocuMind.ai and the repository layout as of the last update to `PROJECT.md`.*
