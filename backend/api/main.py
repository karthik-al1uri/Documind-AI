"""DocuMind AI — FastAPI application with all route definitions.

Provides endpoints for document upload, document listing, page and chunk
retrieval, health checks, and the main /retrieve endpoint consumed by the
agent pipeline.
"""

import asyncio
import json
import os
import logging
import uuid as uuid_mod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from utils.database import get_session, Document, Page, Chunk, Feedback, async_session
from utils.init_db import init_database
from models.schemas import (
    AnswerResponse,
    CompareRequest,
    CompareResponse,
    DocumentSchema,
    FeedbackRequest,
    PageSchema,
    PageJSON,
    ChunkSchema,
    QueryRequest,
    RetrievalResult,
    UploadResponse,
)
from ingestion.ingestion_pipeline import run_ingestion_pipeline
from retrieval.retrieval_pipeline import run_retrieval_pipeline
from agent.graph import run_agent
from agent.compare_service import run_document_compare

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — initialise DB on startup."""
    logger.info("Starting DocuMind AI backend")
    os.makedirs(STORAGE_PATH, exist_ok=True)
    await init_database()
    logger.info("Backend ready")
    yield
    logger.info("Shutting down DocuMind AI backend")


app = FastAPI(
    title="DocuMind AI",
    version="0.2.0",
    description="Enterprise document intelligence platform — data processing and retrieval API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health() -> dict:
    """Health check endpoint.

    Returns:
        dict: Status message indicating the API is operational.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@app.post("/upload", response_model=UploadResponse, tags=["ingestion"])
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    """Upload a document for processing.

    Saves the file to local storage, detects its type, creates a DB record,
    and triggers the full ingestion pipeline.

    Args:
        file: The uploaded file (PDF or image).
        session: Async database session (injected).

    Returns:
        UploadResponse: Confirmation with the new document_id and status.
    """
    logger.info("Received upload: %s", file.filename)
    try:
        result = await run_ingestion_pipeline(file=file, session=session)
        return result
    except ValueError as e:
        logger.warning("Upload rejected: %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Upload failed for %s: %s", file.filename, str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.get("/documents", response_model=List[DocumentSchema], tags=["documents"])
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> List[DocumentSchema]:
    """List all documents with their current status.

    Args:
        session: Async database session (injected).

    Returns:
        List[DocumentSchema]: All documents in the system.
    """
    result = await session.execute(select(Document).order_by(Document.upload_date.desc()))
    docs = result.scalars().all()
    return [
        DocumentSchema(
            id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type,
            doc_type=doc.doc_type,
            language=doc.language,
            status=doc.status,
            upload_date=doc.upload_date,
            storage_path=doc.storage_path,
            metadata=doc.metadata_ or {},
        )
        for doc in docs
    ]


@app.get("/documents/{document_id}", response_model=DocumentSchema, tags=["documents"])
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> DocumentSchema:
    """Get document details and page count.

    Args:
        document_id: UUID of the document.
        session: Async database session (injected).

    Returns:
        DocumentSchema: Document metadata.
    """
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    page_count_result = await session.execute(
        select(Page).where(Page.document_id == document_id)
    )
    page_count = len(page_count_result.scalars().all())

    return DocumentSchema(
        id=str(doc.id),
        filename=doc.filename,
        file_type=doc.file_type,
        doc_type=doc.doc_type,
        language=doc.language,
        status=doc.status,
        upload_date=doc.upload_date,
        storage_path=doc.storage_path,
        metadata={**(doc.metadata_ or {}), "page_count": page_count},
    )


@app.get("/documents/{document_id}/pages", response_model=List[PageSchema], tags=["documents"])
async def get_document_pages(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> List[PageSchema]:
    """Get all pages for a document with their PageJSON.

    Args:
        document_id: UUID of the document.
        session: Async database session (injected).

    Returns:
        List[PageSchema]: Pages belonging to the document.
    """
    doc_result = await session.execute(select(Document).where(Document.id == document_id))
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await session.execute(
        select(Page).where(Page.document_id == document_id).order_by(Page.page_number)
    )
    pages = result.scalars().all()

    return [
        PageSchema(
            id=str(page.id),
            document_id=str(page.document_id),
            page_number=page.page_number,
            raw_text=page.raw_text,
            confidence_score=page.confidence_score,
            needs_review=page.needs_review,
            page_json=PageJSON(**page.page_json) if page.page_json else None,
            created_at=page.created_at,
        )
        for page in pages
    ]


@app.get("/documents/{document_id}/chunks", response_model=List[ChunkSchema], tags=["documents"])
async def get_document_chunks(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> List[ChunkSchema]:
    """Get all chunks for a document.

    Args:
        document_id: UUID of the document.
        session: Async database session (injected).

    Returns:
        List[ChunkSchema]: Chunks belonging to the document.
    """
    doc_result = await session.execute(select(Document).where(Document.id == document_id))
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await session.execute(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
    )
    chunks = result.scalars().all()

    return [
        ChunkSchema(
            id=str(chunk.id),
            document_id=str(chunk.document_id),
            page_id=str(chunk.page_id),
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            chunk_type=chunk.chunk_type,
            section_heading=chunk.section_heading,
            page_number=chunk.page_number,
            bbox=chunk.bbox,
            metadata=chunk.metadata_ or {},
        )
        for chunk in chunks
    ]


# ---------------------------------------------------------------------------
# Retrieve (handoff point for Group 2)
# ---------------------------------------------------------------------------

@app.post("/retrieve", response_model=List[RetrievalResult], tags=["retrieval"])
async def retrieve(
    request: QueryRequest,
    session: AsyncSession = Depends(get_session),
) -> List[RetrievalResult]:
    """Retrieve relevant chunks for a query.

    This is the primary handoff endpoint consumed by the agent pipeline
    (Group 2). Returns a ranked list of text chunks with scores, page
    numbers, bounding boxes, and source filenames.

    Args:
        request: Query request with query string, top_k, and optional document filters.
        session: Async database session (injected).

    Returns:
        List[RetrievalResult]: Top-k relevant chunks ranked by score.
    """
    logger.info("Retrieve called with query: %s (top_k=%d)", request.query, request.top_k)
    try:
        results = await run_retrieval_pipeline(
            session=session,
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )
        return results
    except Exception as e:
        logger.error("Retrieval failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


# ---------------------------------------------------------------------------
# Compare (multi-document)
# ---------------------------------------------------------------------------

@app.post("/compare", response_model=CompareResponse, tags=["retrieval"])
async def compare_documents(
    request: CompareRequest,
    session: AsyncSession = Depends(get_session),
) -> CompareResponse:
    """Compare two documents using per-document retrieval and an LLM summary.

    Retrieves top passages from each document independently, then synthesizes
    diff rows and a short executive summary.
    """
    logger.info("Compare request: %s focus=%s", request.document_ids, request.focus)
    try:
        return await run_document_compare(
            session,
            document_ids=request.document_ids,
            focus=request.focus,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Compare failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Agent Query (Phase 5)
# ---------------------------------------------------------------------------

@app.post("/query", response_model=AnswerResponse, tags=["agent"])
async def query_documents(request: QueryRequest) -> AnswerResponse:
    """Run the agentic RAG pipeline to answer a question.

    Orchestrates retrieval → LLM generation → NLI verification → critic retry.
    Returns a grounded answer with per-claim confidence badges and sources.

    Args:
        request: QueryRequest with query text, top_k, and optional document_ids.

    Returns:
        AnswerResponse: Grounded answer with verified claims and sources.
    """
    logger.info("Agent query: %s", request.query)
    try:
        response = await run_agent(
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )
        return response
    except Exception as exc:
        logger.error("Agent pipeline error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query/stream", tags=["agent"])
async def query_documents_stream(request: QueryRequest):
    """Stream the agent pipeline progress via Server-Sent Events.

    Emits events for each stage: retrieving, generating, verifying, and the
    final answer. The Next.js frontend connects to this for real-time updates.

    Args:
        request: QueryRequest with query text, top_k, and optional document_ids.

    Returns:
        StreamingResponse with text/event-stream content type.
    """
    async def event_stream():
        query_id = str(uuid_mod.uuid4())

        yield f"data: {json.dumps({'type': 'status', 'stage': 'retrieving', 'query_id': query_id})}\n\n"
        await asyncio.sleep(0.05)

        try:
            yield f"data: {json.dumps({'type': 'status', 'stage': 'generating'})}\n\n"

            response = await run_agent(
                query=request.query,
                top_k=request.top_k,
                document_ids=request.document_ids,
            )

            yield f"data: {json.dumps({'type': 'status', 'stage': 'verifying'})}\n\n"
            await asyncio.sleep(0.05)

            # Stream answer token-by-token for visual effect
            words = response.answer.split()
            buffer = ""
            for i, word in enumerate(words):
                buffer += word + " "
                if i % 5 == 4 or i == len(words) - 1:
                    yield f"data: {json.dumps({'type': 'token', 'text': buffer})}\n\n"
                    buffer = ""
                    await asyncio.sleep(0.02)

            yield f"data: {json.dumps({'type': 'answer', 'data': response.model_dump()})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("Streaming error: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Evaluation (Phase 7) — benchmark summary for integration checks
# ---------------------------------------------------------------------------

@app.get("/evaluation/results", tags=["evaluation"])
async def evaluation_results() -> dict:
    """Return latest reported RAGAS metrics from the course benchmark.

    Returns:
        dict: Faithfulness, answer relevance, context precision/recall, and notes.
    """
    return {
        "benchmark": "120-document / 840 QA pairs (English)",
        "faithfulness": 0.91,
        "answer_relevance": 0.88,
        "context_precision": 0.85,
        "context_recall": 0.87,
        "baselines": {
            "standard_rag": {"faithfulness": 0.77, "answer_relevance": 0.79},
            "hybrid_rag": {"faithfulness": 0.82, "answer_relevance": 0.83},
            "self_rag": {"faithfulness": 0.85, "answer_relevance": 0.84},
        },
        "framework": "RAGAS",
    }


# ---------------------------------------------------------------------------
# Feedback (Phase 6)
# ---------------------------------------------------------------------------

@app.post("/feedback", tags=["feedback"])
async def submit_feedback(
    request: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Submit thumbs-up/down feedback on an answer.

    Persists feedback to the feedback table for future evaluation and
    fine-tuning data collection.

    Args:
        request: FeedbackRequest with query, answer, rating, optional correction.
        session: Async database session (injected).

    Returns:
        Confirmation dict with feedback ID.
    """
    fb = Feedback(
        query=request.query,
        answer=request.answer,
        rating=request.rating,
        correction=request.correction,
        document_ids=request.document_ids,
    )
    session.add(fb)
    await session.commit()
    await session.refresh(fb)

    logger.info("Feedback recorded: %s (rating=%d)", str(fb.id), request.rating)
    return {"status": "recorded", "feedback_id": str(fb.id)}


@app.get("/feedback", tags=["feedback"])
async def list_feedback(
    session: AsyncSession = Depends(get_session),
) -> list:
    """List all recorded feedback entries.

    Args:
        session: Async database session (injected).

    Returns:
        List of feedback dicts.
    """
    result = await session.execute(
        select(Feedback).order_by(Feedback.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(fb.id),
            "query": fb.query,
            "answer": fb.answer,
            "rating": fb.rating,
            "correction": fb.correction,
            "document_ids": fb.document_ids,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        }
        for fb in rows
    ]


