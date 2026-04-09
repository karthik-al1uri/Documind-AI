# DocuMind.ai — Project Intelligence File

## Project Overview

DocuMind.ai is an end-to-end enterprise document intelligence platform. It allows users to upload unstructured documents (PDFs, scanned files, contracts, reports) and query them conversationally, receiving grounded answers with exact source citations.

The system is split into two groups:
- **Group 1 (You — Karthik)**: Data Processing and Retrieval — Phases 1 through 4
- **Group 2 (Glen)**: Agent, Frontend, and Evaluation — Phases 5 through 8

This file is the single source of truth for the entire project. When asked to implement a phase, follow the schemas, conventions, and tech stack defined here exactly.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API Framework | FastAPI (async) |
| Database | PostgreSQL 15 (SQLAlchemy 2.0) |
| Vector Store | FAISS flat index |
| ORM Schemas | Pydantic v2 |
| PDF Parsing | PyMuPDF (fitz), pdfplumber |
| OCR | PaddleOCR |
| PII Redaction | Microsoft Presidio |
| Embeddings | HuggingFace BGE-Large-EN (d=1024) |
| Retrieval | FAISS (dense) + PostgreSQL tsvector (BM25) |
| Reranking | MS-MARCO MiniLM cross-encoder |
| Query Expansion | HyDE via Llama 3 8B |
| LLM | GPT-4o (OpenAI API) or Llama 3 70B (local) |
| NLI Verification | DeBERTa-v3-large |
| Agent Framework | LangGraph |
| Frontend | Next.js 14, Tailwind CSS |
| Backend API | FastAPI |
| Containerization | Docker + Docker Compose |
| Evaluation | RAGAS framework |
| Tracing | LangSmith |
| Storage | Local filesystem or AWS S3 |

---

## Project Folder Structure
documind/
├── backend/
│   ├── api/
│   │   └── main.py                  # FastAPI app and all routes
│   ├── ingestion/
│   │   ├── upload_service.py        # file upload, storage, type detection
│   │   ├── pdf_parser.py            # PyMuPDF + pdfplumber native PDF parsing
│   │   ├── ocr_processor.py         # PaddleOCR for scanned documents
│   │   ├── layout_service.py        # heuristic layout classification
│   │   └── ingestion_pipeline.py    # orchestrates full ingestion flow
│   ├── processing/
│   │   ├── pii_redactor.py          # Presidio PII detection and replacement
│   │   ├── language_detector.py     # language detection and model routing
│   │   ├── field_extractor.py       # type-specific structured field extraction
│   │   └── chunker.py               # hierarchical chunking with overlap
│   ├── retrieval/
│   │   ├── embedder.py              # BGE-Large-EN embedding generation
│   │   ├── indexer.py               # FAISS index write and read
│   │   ├── bm25_search.py           # PostgreSQL tsvector BM25 retrieval
│   │   ├── hyde_expander.py         # HyDE query expansion via Llama 3 8B
│   │   ├── rrf_fusion.py            # Reciprocal Rank Fusion implementation
│   │   ├── reranker.py              # cross-encoder reranking
│   │   └── retrieval_pipeline.py    # orchestrates full retrieval flow
│   ├── agent/
│   │   ├── graph.py                 # LangGraph agent graph definition
│   │   ├── llm_generator.py         # LLM answer generation with citations
│   │   ├── nli_verifier.py          # DeBERTa-v3 NLI entailment check
│   │   └── critic_agent.py          # Critic Agent retry logic
│   ├── models/
│   │   └── schemas.py               # all Pydantic v2 schemas
│   └── utils/
│       ├── database.py              # SQLAlchemy engine and session
│       └── init_db.py               # creates all tables on startup
├── frontend/                        # Next.js app (Glen)
├── evaluation/
│   ├── benchmark/                   # 120-document QA benchmark
│   └── ragas_eval.py                # RAGAS evaluation runner
├── storage/                         # uploaded files stored here
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── CLAUDE.md                        # this file

---

## Environment Variables
DATABASE_URL=postgresql://documind:documind@localhost:5432/documind
STORAGE_PATH=./storage
OCR_CONFIDENCE_THRESHOLD=0.75
OPENAI_API_KEY=your_key_here
LANGSMITH_API_KEY=your_key_here
FAISS_INDEX_PATH=./storage/faiss.index
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
NLI_MODEL=cross-encoder/nli-deberta-v3-large
HF_CACHE_DIR=./models
DEBUG=true

---

## Database Schema

### Table: documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,           -- 'pdf' | 'image'
    doc_type TEXT,                     -- 'invoice' | 'contract' | 'report' | 'paper'
    language TEXT DEFAULT 'en',
    upload_date TIMESTAMP DEFAULT NOW(),
    storage_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending',     -- 'pending' | 'processing' | 'completed' | 'needs_review'
    metadata JSONB DEFAULT '{}'
);
```

### Table: pages
```sql
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    raw_text TEXT,
    confidence_score FLOAT,            -- 0.0 to 1.0, null for native PDFs
    needs_review BOOLEAN DEFAULT FALSE,
    page_json JSONB,                   -- full PageJSON object
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table: chunks
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    text_search tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    chunk_type TEXT,                   -- 'paragraph' | 'table_cell' | 'heading' | 'caption'
    section_heading TEXT,
    page_number INTEGER,
    bbox JSONB,                        -- {x0, y0, x1, y1}
    metadata JSONB DEFAULT '{}',
    embedding_id INTEGER,              -- FAISS index position
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chunks_text_search ON chunks USING GIN(text_search);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
```

### Table: extracted_fields
```sql
CREATE TABLE extracted_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,          -- 'invoice_total' | 'contract_date' | 'party_name' etc
    field_value TEXT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table: feedback
```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating INTEGER,                    -- 1 (thumbs up) | -1 (thumbs down)
    correction TEXT,
    document_ids JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Pydantic Schemas (models/schemas.py)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class PageElement(BaseModel):
    element_type: str        # 'heading' | 'paragraph' | 'table_cell' | 'caption' | 'header' | 'footer'
    text: str
    bbox: BoundingBox
    page_number: int
    confidence: Optional[float] = None

class PageJSON(BaseModel):
    document_id: str
    page_number: int
    width: float
    height: float
    elements: List[PageElement]

class ChunkSchema(BaseModel):
    id: Optional[str] = None
    document_id: str
    page_id: str
    chunk_index: int
    text: str
    chunk_type: str
    section_heading: Optional[str] = None
    page_number: int
    bbox: Optional[BoundingBox] = None
    metadata: Dict[str, Any] = {}

class DocumentSchema(BaseModel):
    id: Optional[str] = None
    filename: str
    file_type: str
    doc_type: Optional[str] = None
    language: str = 'en'
    status: str = 'pending'
    upload_date: Optional[datetime] = None

class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_number: int
    section_heading: Optional[str]
    bbox: Optional[BoundingBox]
    source_filename: str

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    document_ids: Optional[List[str]] = None

class AnswerResponse(BaseModel):
    answer: str
    claims: List[Dict[str, Any]]      # each claim has text, confidence, citation
    sources: List[RetrievalResult]
    query_id: str
```

---

## API Contracts

### Group 1 Exposes (Karthik builds these)
POST   /upload                         Upload a document, returns document_id
GET    /documents                      List all documents with status
GET    /documents/{id}                 Get document details and page count
GET    /documents/{id}/pages           Get all pages with PageJSON
GET    /documents/{id}/chunks          Get all chunks for a document
POST   /retrieve                       Body: QueryRequest → Returns List[RetrievalResult]
GET    /health                         Health check

### Group 2 Consumes (Glen's pipeline calls these)
POST /retrieve
Request:  { "query": str, "top_k": 5, "document_ids": [optional list] }
Response: List[RetrievalResult] — each with text, score, page_number, bbox, source_filename

This is the handoff point. The retrieval endpoint must be stable before Glen can build Phase 5.

---

## Data Flow Summary
User uploads file
→ upload_service.py         detects file type, saves to /storage, inserts into documents table
→ pdf_parser.py             (if native PDF) extracts text + tables per page
→ ocr_processor.py          (if scanned) renders at 300 DPI, runs PaddleOCR, scores confidence
→ layout_service.py         classifies elements, assigns bboxes, produces PageJSON
→ pii_redactor.py           replaces PII with typed placeholders
→ language_detector.py      detects language, sets embedding model
→ field_extractor.py        extracts structured fields into extracted_fields table
→ chunker.py                hierarchical chunking with 10% overlap, attaches metadata
→ embedder.py               BGE-Large-EN encodes chunks → FAISS index
→ indexer.py                stores vectors in FAISS, stores embedding_id in chunks table
User submits query
→ hyde_expander.py          generates hypothetical answer, embeds it
→ embedder.py               embeds hypothetical answer
→ indexer.py                ANN search top-50
→ bm25_search.py            PostgreSQL tsvector search top-50
→ rrf_fusion.py             merges ranked lists with k=60
→ reranker.py               cross-encoder scores top-20, returns top-5
→ retrieval_pipeline.py     returns List[RetrievalResult] via /retrieve endpoint
Glen's agent receives List[RetrievalResult]
→ llm_generator.py          generates grounded answer with source annotations
→ nli_verifier.py           checks each claim against cited chunk (threshold 0.6)
→ critic_agent.py           if >20% claims fail, refines query and retries (max 2)
→ returns AnswerResponse    with per-claim confidence badges and citations

---

## OCR Confidence Rules

```python
CONFIDENCE_THRESHOLD = 0.75

# Per page:
# - confidence_score = mean of all word-level confidence scores from PaddleOCR
# - if confidence_score < 0.75: needs_review = True, page is flagged
# - flagged pages are saved to DB but NOT passed to chunker
# - document status set to 'needs_review' if any page is flagged
```

---

## Chunking Rules

```python
OVERLAP_RATIO = 0.10   # 10% of chunk length duplicated at boundaries
MAX_CHUNK_TOKENS = 512
MIN_CHUNK_TOKENS = 50

# Hierarchy:
# Level 1 (parent): full section (heading + all paragraphs beneath it)
# Level 2 (child):  individual paragraphs and table rows — these are indexed
# Overlap: last 10% of child chunk N is prepended to child chunk N+1
# Table cells: each row is one chunk, column headers prepended to every row chunk
# Every chunk carries: document_id, page_id, page_number, section_heading, bbox, chunk_type
```

---

## RRF Fusion Formula

```python
def rrf_score(rankings: list[dict], k: int = 60) -> dict:
    scores = {}
    for ranked_list in rankings:
        for rank, doc_id in enumerate(ranked_list):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
```

---

## Coding Conventions

- All files must have module-level docstrings explaining purpose
- All functions must have docstrings with Args and Returns
- Use async/await throughout FastAPI routes and DB calls
- Use SQLAlchemy 2.0 style (not legacy 1.x)
- All DB IDs are UUIDs not integers
- All bounding boxes stored as JSONB with keys x0, y0, x1, y1
- Confidence scores are always floats between 0.0 and 1.0
- Log every major pipeline step using Python logging module
- Never use print() in production code — use logger.info() / logger.error()
- All environment variables loaded from .env via python-dotenv
- No hardcoded credentials anywhere

---

## Group 1 Phases — Karthik

### Phase 1 — Project Setup and Contracts
Goal: stable backend foundation with agreed schemas
- Set up repo, Docker Compose, PostgreSQL, FastAPI skeleton
- Run init_db.py to create all tables
- Define and lock all Pydantic schemas
- Document API contracts
- Output: running backend with empty DB and /health endpoint responding

### Phase 2 — Document Ingestion Pipeline
Goal: raw documents converted into structured PageJSON
- upload_service.py — file receipt, type detection, DB insert
- pdf_parser.py — native PDF text + table extraction
- ocr_processor.py — scanned doc rendering, PaddleOCR, confidence scoring
- layout_service.py — element classification, bbox assignment, PageJSON output
- ingestion_pipeline.py — orchestrates all of the above
- Output: POST /upload processes a file and stores PageJSON in pages table

### Phase 3 — Chunking, Metadata, and Processing
Goal: clean structured chunks ready for embedding
- pii_redactor.py — Presidio integration, placeholder replacement
- language_detector.py — language detection, model routing flag
- field_extractor.py — document type classifier + field extraction templates
- chunker.py — hierarchical chunking with overlap, metadata tagging
- Output: chunks table populated with clean metadata-rich records

### Phase 4 — Embedding and Retrieval
Goal: retrieval system returning top-5 relevant chunks for any query
- embedder.py — BGE-Large-EN encoding
- indexer.py — FAISS write and ANN search
- bm25_search.py — PostgreSQL tsvector search
- hyde_expander.py — HyDE query expansion
- rrf_fusion.py — RRF score fusion
- reranker.py — cross-encoder reranking
- retrieval_pipeline.py — full retrieval orchestration
- Output: POST /retrieve returns List[RetrievalResult] reliably

---

## Group 2 Phases — Glen

### Phase 5 — Agentic RAG Pipeline
Goal: grounded, verified, cited answers from retrieved chunks
- Consumes: POST /retrieve → List[RetrievalResult]
- Builds: LangGraph graph, LLM generation, NLI check, Critic Agent
- Output: AnswerResponse with per-claim confidence and citations

### Phase 6 — Frontend Application
Goal: fully functional user interface
- Next.js chat interface with streaming SSE
- Side-by-side PDF viewer with bbox citation highlighting
- Multi-document comparison engine
- Thumbs-up/down feedback form

### Phase 7 — Evaluation and Benchmarking
Goal: RAGAS scores and ablation results
- 120-document benchmark, 840 QA pairs
- Compare DocuMind.ai vs Standard RAG, Hybrid RAG, Self-RAG
- Run ablation: add components incrementally
- Output: faithfulness, relevance, precision, recall scores

### Phase 8 — System Testing and Final Submission
Goal: stable integrated system ready for demo
- End-to-end integration testing
- Bug fixes and latency optimization
- Final paper, slides, demo video

---

## How to Use This File

When you want to implement a phase, say:

"Implement Phase 1 from CLAUDE.md"
"Implement Phase 2 from CLAUDE.md"
"Implement Phase 3 from CLAUDE.md"
"Implement Phase 4 from CLAUDE.md"

Claude will read this file, follow the schemas and conventions exactly, and generate all files for that phase completely with no placeholders or TODOs.

When Glen wants to implement his phases he says:

"Implement Phase 5 from CLAUDE.md"
"Implement Phase 6 from CLAUDE.md"

Claude will use the same schemas and API contracts defined here to ensure both groups integrate cleanly.