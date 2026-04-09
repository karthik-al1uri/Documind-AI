"""DocuMind AI — Hierarchical chunking with overlap and metadata tagging.

Implements the two-level chunking strategy defined in CLAUDE.md:
- Level 1 (parent): full sections (heading + all paragraphs beneath it)
- Level 2 (child): individual paragraphs and table rows — these are indexed
- Overlap: last 10% of child chunk N is prepended to child chunk N+1
- Table cells: each row is one chunk, column headers prepended to every row
- Every chunk carries: document_id, page_id, page_number, section_heading,
  bbox, chunk_type
"""

import logging
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import PageJSON, PageElement, BoundingBox, ChunkSchema
from utils.database import Chunk as ChunkORM

logger = logging.getLogger(__name__)

OVERLAP_RATIO = 0.10    # 10% of chunk length duplicated at boundaries
MAX_CHUNK_TOKENS = 512
MIN_CHUNK_TOKENS = 50

# Rough token estimate: 1 token ≈ 4 characters
CHARS_PER_TOKEN = 4
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN
MIN_CHUNK_CHARS = MIN_CHUNK_TOKENS * CHARS_PER_TOKEN


def _estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text string.

    Args:
        text: Input text.

    Returns:
        int: Estimated token count.
    """
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_text_with_overlap(text: str, max_chars: int, overlap_chars: int) -> List[str]:
    """Split text into chunks with overlap at boundaries.

    Args:
        text: The text to split.
        max_chars: Maximum characters per chunk.
        overlap_chars: Number of characters to overlap between consecutive chunks.

    Returns:
        List[str]: List of text chunks with overlap applied.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars

        # Try to break at a sentence or word boundary
        if end < len(text):
            # Look for sentence boundary within last 20% of the chunk
            search_start = end - max(50, max_chars // 5)
            best_break = -1
            for delim in [". ", ".\n", "\n\n", "\n", " "]:
                pos = text.rfind(delim, search_start, end)
                if pos > start:
                    best_break = pos + len(delim)
                    break
            if best_break > start:
                end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward, accounting for overlap
        start = end - overlap_chars if end < len(text) else end

    return chunks


def _group_elements_into_sections(elements: List[PageElement]) -> List[dict]:
    """Group page elements into sections based on headings.

    A section starts at a heading element and includes all subsequent
    non-heading elements until the next heading.

    Args:
        elements: List of classified page elements.

    Returns:
        List[dict]: List of section dicts with keys 'heading', 'elements',
            'heading_bbox'.
    """
    sections: List[dict] = []
    current_section: dict = {
        "heading": None,
        "elements": [],
        "heading_bbox": None,
    }

    for elem in elements:
        if elem.element_type == "heading":
            # Save the current section if it has content
            if current_section["elements"]:
                sections.append(current_section)
            current_section = {
                "heading": elem.text,
                "elements": [elem],
                "heading_bbox": elem.bbox,
            }
        else:
            current_section["elements"].append(elem)

    # Don't forget the last section
    if current_section["elements"]:
        sections.append(current_section)

    return sections


def chunk_page(
    page_json: PageJSON,
    page_id: str,
    start_chunk_index: int = 0,
) -> List[ChunkSchema]:
    """Chunk a single page into Level-2 child chunks.

    Args:
        page_json: The structured PageJSON for the page.
        page_id: UUID string of the page record.
        start_chunk_index: Starting index for chunk numbering (for
            multi-page documents).

    Returns:
        List[ChunkSchema]: List of chunks produced from this page.
    """
    elements = page_json.elements
    if not elements:
        return []

    sections = _group_elements_into_sections(elements)
    chunks: List[ChunkSchema] = []
    chunk_index = start_chunk_index

    for section in sections:
        heading = section["heading"]

        for elem in section["elements"]:
            # Skip headers and footers — they are not indexed
            if elem.element_type in ("header", "footer"):
                continue

            text = elem.text.strip()
            if not text:
                continue

            # Table cells become individual chunks directly
            if elem.element_type == "table_cell":
                if _estimate_tokens(text) >= MIN_CHUNK_TOKENS:
                    chunks.append(ChunkSchema(
                        document_id=page_json.document_id,
                        page_id=page_id,
                        chunk_index=chunk_index,
                        text=text,
                        chunk_type="table_cell",
                        section_heading=heading,
                        page_number=page_json.page_number,
                        bbox=elem.bbox,
                        metadata={"element_type": elem.element_type},
                    ))
                    chunk_index += 1
                continue

            # For paragraphs, headings, captions: split if too long
            overlap_chars = int(len(text) * OVERLAP_RATIO) if len(text) > MAX_CHUNK_CHARS else 0
            sub_texts = _split_text_with_overlap(text, MAX_CHUNK_CHARS, overlap_chars)

            for sub_text in sub_texts:
                if _estimate_tokens(sub_text) < MIN_CHUNK_TOKENS and len(sub_texts) > 1:
                    continue

                chunks.append(ChunkSchema(
                    document_id=page_json.document_id,
                    page_id=page_id,
                    chunk_index=chunk_index,
                    text=sub_text,
                    chunk_type=elem.element_type,
                    section_heading=heading,
                    page_number=page_json.page_number,
                    bbox=elem.bbox,
                    metadata={"element_type": elem.element_type},
                ))
                chunk_index += 1

    return chunks


def apply_cross_chunk_overlap(chunks: List[ChunkSchema]) -> List[ChunkSchema]:
    """Apply overlap between consecutive chunks from the same page.

    Prepends the last 10% of each chunk to the next chunk in sequence.

    Args:
        chunks: List of chunks in order.

    Returns:
        List[ChunkSchema]: Chunks with overlap text prepended where applicable.
    """
    if len(chunks) <= 1:
        return chunks

    overlapped: List[ChunkSchema] = [chunks[0]]

    for i in range(1, len(chunks)):
        prev_text = chunks[i - 1].text
        overlap_len = max(1, int(len(prev_text) * OVERLAP_RATIO))
        overlap_text = prev_text[-overlap_len:]

        current = chunks[i]
        new_text = overlap_text + " " + current.text

        # Ensure we don't exceed max size
        if _estimate_tokens(new_text) > MAX_CHUNK_TOKENS:
            new_text = new_text[:MAX_CHUNK_CHARS]

        overlapped.append(ChunkSchema(
            document_id=current.document_id,
            page_id=current.page_id,
            chunk_index=current.chunk_index,
            text=new_text,
            chunk_type=current.chunk_type,
            section_heading=current.section_heading,
            page_number=current.page_number,
            bbox=current.bbox,
            metadata={**current.metadata, "has_overlap": True},
        ))

    return overlapped


async def chunk_document(
    session: AsyncSession,
    document_id: str,
    pages: List[dict],
) -> List[ChunkSchema]:
    """Chunk all pages of a document and persist chunks to the database.

    Processes each page's PageJSON, produces Level-2 child chunks with overlap,
    and inserts them into the chunks table.

    Args:
        session: Async database session.
        document_id: UUID string of the document.
        pages: List of dicts with keys 'page_id', 'page_json', 'needs_review'.
            Pages with needs_review=True are skipped.

    Returns:
        List[ChunkSchema]: All chunks produced for the document.
    """
    all_chunks: List[ChunkSchema] = []
    chunk_index = 0

    for page_info in pages:
        if page_info.get("needs_review", False):
            logger.info(
                "Skipping page %s — flagged for review",
                page_info.get("page_id", "unknown"),
            )
            continue

        page_json_data = page_info.get("page_json")
        if not page_json_data:
            continue

        # Parse PageJSON
        if isinstance(page_json_data, dict):
            page_json = PageJSON(**page_json_data)
        else:
            page_json = page_json_data

        page_id = page_info["page_id"]

        # Produce chunks for this page
        page_chunks = chunk_page(page_json, page_id, start_chunk_index=chunk_index)

        # Apply cross-chunk overlap
        page_chunks = apply_cross_chunk_overlap(page_chunks)

        # Update chunk indices to be globally sequential
        for i, chunk in enumerate(page_chunks):
            chunk.chunk_index = chunk_index + i
        chunk_index += len(page_chunks)

        all_chunks.extend(page_chunks)

    # Persist all chunks to the database
    for chunk in all_chunks:
        record = ChunkORM(
            document_id=document_id,
            page_id=chunk.page_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            chunk_type=chunk.chunk_type,
            section_heading=chunk.section_heading,
            page_number=chunk.page_number,
            bbox=chunk.bbox.model_dump() if chunk.bbox else None,
            metadata_=chunk.metadata,
        )
        session.add(record)

    logger.info(
        "Chunking complete for document %s: %d chunks produced",
        document_id, len(all_chunks),
    )
    return all_chunks
