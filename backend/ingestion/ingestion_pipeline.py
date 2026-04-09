"""DocuMind AI — Ingestion pipeline orchestrator.

Coordinates the full document ingestion flow:
Phase 2: file upload, type detection, PDF parsing or OCR, layout
         classification, PageJSON generation, and database persistence.
Phase 3: PII redaction, language detection, field extraction, chunking.
Phase 4: Embedding generation and FAISS indexing.

Returns an UploadResponse when complete.
"""

import logging
from typing import Optional, List

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import UploadResponse, PageJSON
from utils.database import Document, Page, Chunk as ChunkORM
from ingestion.upload_service import save_upload, create_document_record
from ingestion.pdf_parser import parse_pdf, is_scanned_pdf
from ingestion.ocr_processor import ocr_pdf, ocr_image
from ingestion.layout_service import build_page_json
from processing.pii_redactor import redact_pii
from processing.language_detector import detect_document_language
from processing.field_extractor import run_field_extraction
from processing.chunker import chunk_document
from retrieval.embedder import embed_chunks
from retrieval.indexer import add_vectors

logger = logging.getLogger(__name__)


async def run_ingestion_pipeline(
    file: UploadFile,
    session: AsyncSession,
) -> UploadResponse:
    """Execute the full document ingestion pipeline (Phases 2–4).

    Steps:
        1.  Save the uploaded file to local storage
        2.  Create a document record in the database
        3.  Detect whether the file is a native PDF, scanned PDF, or image
        4.  Extract text + layout (PyMuPDF/pdfplumber) or run OCR (PaddleOCR)
        5.  Classify elements via layout_service
        6.  Build PageJSON for each page
        7.  Persist pages to the database
        8.  PII redaction on raw text
        9.  Language detection
        10. Document type classification and field extraction
        11. Hierarchical chunking with overlap
        12. Embed chunks via BGE-Large-EN
        13. Add vectors to FAISS index
        14. Update document status

    Args:
        file: The uploaded file from the FastAPI endpoint.
        session: Async database session.

    Returns:
        UploadResponse: Confirmation with document_id and final status.
    """
    # Step 1 — Save file
    storage_path, file_type = await save_upload(file)
    logger.info("File saved: type=%s, path=%s", file_type, storage_path)

    # Step 2 — Create document record
    doc = await create_document_record(
        session=session,
        filename=file.filename or "unknown",
        file_type=file_type,
        storage_path=storage_path,
    )
    document_id = str(doc.id)

    try:
        # Step 3 & 4 — Parse or OCR
        pages_data = await _extract_pages(storage_path, file_type, document_id)

        # Step 5, 6, 7 — Build PageJSON and persist pages
        any_needs_review = False
        page_records: List[dict] = []
        all_raw_texts: dict[int, str] = {}

        for page_number in sorted(pages_data.keys()):
            page_info = pages_data[page_number]
            elements = page_info["elements"]
            width = page_info["width"]
            height = page_info["height"]
            confidence_score = page_info.get("confidence_score")
            needs_review = page_info.get("needs_review", False)

            if needs_review:
                any_needs_review = True

            # Build classified PageJSON
            page_json = build_page_json(
                document_id=document_id,
                page_number=page_number,
                elements=elements,
                width=width,
                height=height,
            )

            # Concatenate raw text from all elements
            raw_text = "\n".join(elem.text for elem in page_json.elements if elem.text.strip())

            # Step 8 — PII redaction
            redacted_text, redactions = redact_pii(raw_text)
            if redactions:
                logger.info(
                    "Page %d: redacted %d PII entities", page_number, len(redactions)
                )

            # Also redact element texts in the PageJSON
            redacted_elements = []
            for elem in page_json.elements:
                elem_redacted, _ = redact_pii(elem.text)
                redacted_elements.append(elem.model_copy(update={"text": elem_redacted}))
            page_json = page_json.model_copy(update={"elements": redacted_elements})

            all_raw_texts[page_number] = redacted_text

            # Create page record
            page_record = Page(
                document_id=doc.id,
                page_number=page_number,
                raw_text=redacted_text,
                confidence_score=confidence_score,
                needs_review=needs_review,
                page_json=page_json.model_dump(),
            )
            session.add(page_record)
            await session.flush()

            page_records.append({
                "page_id": str(page_record.id),
                "page_json": page_json.model_dump(),
                "needs_review": needs_review,
                "page_number": page_number,
            })

        # Step 9 — Language detection
        language = detect_document_language(all_raw_texts)
        doc.language = language
        logger.info("Document language: %s", language)

        # Step 10 — Document type classification and field extraction
        full_text = "\n".join(
            all_raw_texts[pn] for pn in sorted(all_raw_texts.keys())
        )
        doc_type, fields = await run_field_extraction(session, document_id, full_text)
        if doc_type:
            doc.doc_type = doc_type
            logger.info("Document type: %s, extracted %d fields", doc_type, len(fields))

        # Step 11 — Hierarchical chunking
        all_chunks = await chunk_document(session, document_id, page_records)
        logger.info("Chunking produced %d chunks", len(all_chunks))

        # Step 12 & 13 — Embed chunks and index in FAISS
        if all_chunks:
            chunk_texts = [c.text for c in all_chunks]
            embeddings = embed_chunks(chunk_texts)
            embedding_ids = add_vectors(embeddings)

            # Update chunk records with embedding_id
            # Re-query chunks from DB to set embedding_id
            from sqlalchemy import select, update
            chunk_records = await session.execute(
                select(ChunkORM).where(
                    ChunkORM.document_id == document_id
                ).order_by(ChunkORM.chunk_index)
            )
            db_chunks = chunk_records.scalars().all()
            for i, db_chunk in enumerate(db_chunks):
                if i < len(embedding_ids):
                    db_chunk.embedding_id = embedding_ids[i]

            logger.info(
                "Embedded and indexed %d chunks (FAISS IDs: %d–%d)",
                len(all_chunks),
                embedding_ids[0] if embedding_ids else -1,
                embedding_ids[-1] if embedding_ids else -1,
            )

        # Step 14 — Update document status
        if any_needs_review:
            doc.status = "needs_review"
        else:
            doc.status = "completed"

        await session.commit()
        logger.info(
            "Ingestion complete: doc_id=%s, status=%s, pages=%d, chunks=%d",
            document_id, doc.status, len(pages_data), len(all_chunks),
        )

        return UploadResponse(
            document_id=document_id,
            filename=file.filename or "unknown",
            file_type=file_type,
            status=doc.status,
            message=(
                f"Document processed successfully. "
                f"{len(pages_data)} pages extracted, "
                f"{len(all_chunks)} chunks indexed."
            ),
        )

    except Exception as e:
        logger.error("Ingestion pipeline failed for doc_id=%s: %s", document_id, str(e))
        doc.status = "pending"
        await session.commit()
        raise


async def _extract_pages(
    storage_path: str,
    file_type: str,
    document_id: str,
) -> dict[int, dict]:
    """Extract page data using the appropriate method based on file type.

    Args:
        storage_path: Path to the stored file.
        file_type: 'pdf' or 'image'.
        document_id: UUID string for the document.

    Returns:
        dict[int, dict]: Page data keyed by page number.
    """
    if file_type == "image":
        logger.info("Processing as standalone image via OCR")
        return ocr_image(storage_path)

    # For PDFs: check if scanned or native
    scanned = is_scanned_pdf(storage_path)

    if scanned:
        logger.info("PDF detected as scanned — running OCR pipeline")
        return ocr_pdf(storage_path)
    else:
        logger.info("PDF detected as native — running PyMuPDF + pdfplumber pipeline")
        return parse_pdf(storage_path)
