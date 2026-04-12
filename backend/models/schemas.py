"""DocuMind AI — Pydantic v2 schemas for the entire platform.

Defines all request/response models, database transfer objects, and internal
data structures used across ingestion, retrieval, agent, and evaluation
pipelines. This is the single source of truth for data shapes.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    """Coordinate rectangle for locating elements on a page."""
    x0: float
    y0: float
    x1: float
    y1: float


# ---------------------------------------------------------------------------
# Page-level models
# ---------------------------------------------------------------------------

class PageElement(BaseModel):
    """Single classified element extracted from a document page."""
    element_type: str
    text: str
    bbox: BoundingBox
    page_number: int
    confidence: Optional[float] = None


class PageJSON(BaseModel):
    """Full structured representation of one document page."""
    document_id: str
    page_number: int
    width: float
    height: float
    elements: List[PageElement]


# ---------------------------------------------------------------------------
# Document and page schemas (API responses)
# ---------------------------------------------------------------------------

class DocumentSchema(BaseModel):
    """Document metadata returned by the API."""
    id: Optional[str] = None
    filename: str
    file_type: str
    doc_type: Optional[str] = None
    language: str = "en"
    status: str = "pending"
    upload_date: Optional[datetime] = None
    storage_path: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PageSchema(BaseModel):
    """Page metadata returned by the API."""
    id: Optional[str] = None
    document_id: str
    page_number: int
    raw_text: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_review: bool = False
    page_json: Optional[PageJSON] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------

class ChunkSchema(BaseModel):
    """A text chunk with full provenance metadata."""
    id: Optional[str] = None
    document_id: str
    page_id: str
    chunk_index: int
    text: str
    chunk_type: Optional[str] = None
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    bbox: Optional[Any] = None
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """Response from POST /upload."""
    document_id: str
    filename: str
    file_type: str
    status: str
    message: str = "Ingestion complete"


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Incoming query from the user or agent pipeline."""
    query: str
    top_k: int = Field(default=5, ge=1, le=100)
    document_ids: Optional[List[str]] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("query must not be empty")
        return s


# ---------------------------------------------------------------------------
# Compare (multi-document)
# ---------------------------------------------------------------------------


class CompareRequest(BaseModel):
    """Request body for POST /compare."""
    document_ids: List[str] = Field(..., min_length=2, max_length=2)
    focus: Optional[str] = None


class CompareDifference(BaseModel):
    """One row of a structured document comparison."""
    topic: str
    document_1: str
    document_2: str
    similarity_score: float


class CompareResponse(BaseModel):
    """Response from POST /compare."""
    comparison_id: str
    documents: List[str]
    differences: List[CompareDifference]
    summary: str


class RetrievalResult(BaseModel):
    """Single retrieval hit returned by the retrieval pipeline."""
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_number: int
    section_heading: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    source_filename: str


# ---------------------------------------------------------------------------
# Agent (Group 2 — Phase 5)
# ---------------------------------------------------------------------------

class Claim(BaseModel):
    """A single factual claim extracted from the generated answer."""
    text: str
    confidence: float
    citation: Optional[RetrievalResult] = None
    entailment_label: Optional[str] = None   # 'entailment' | 'contradiction' | 'neutral'
    entailment_score: Optional[float] = None


class AnswerResponse(BaseModel):
    """Final grounded answer with per-claim verification and sources."""
    answer: str
    claims: List[Dict[str, Any]]
    sources: List[RetrievalResult]
    query_id: str


class FeedbackRequest(BaseModel):
    """User feedback on an answer (thumbs up/down)."""
    query: str
    answer: str
    rating: int              # 1 (thumbs up) | -1 (thumbs down)
    correction: Optional[str] = None
    document_ids: Optional[List[str]] = None


class AgentState(BaseModel):
    """Internal state carried through the LangGraph agent graph."""
    query: str
    top_k: int = 5
    document_ids: Optional[List[str]] = None
    retrieval_results: List[RetrievalResult] = []
    generated_answer: Optional[str] = None
    claims: List[Claim] = []
    verification_passed: bool = False
    retry_count: int = 0
    max_retries: int = 2
    refined_query: Optional[str] = None
    query_id: Optional[str] = None
    error: Optional[str] = None
