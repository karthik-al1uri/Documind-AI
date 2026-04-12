"""DocuMind AI — Native PDF text and table extraction.

Uses PyMuPDF (fitz) for text extraction with bounding boxes and pdfplumber
for table detection and extraction. Produces structured element lists per page.
"""

import logging
from typing import List, Optional

import fitz  # PyMuPDF
import pdfplumber

from models.schemas import BoundingBox, PageElement

logger = logging.getLogger(__name__)


def extract_text_elements(pdf_path: str) -> dict[int, List[PageElement]]:
    """Extract text blocks with bounding boxes from a native PDF using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        dict[int, List[PageElement]]: Mapping of 1-indexed page numbers to
            lists of PageElement objects extracted from the text layer.
    """
    elements_by_page: dict[int, List[PageElement]] = {}

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error("Failed to open PDF with PyMuPDF: %s", e)
        return elements_by_page

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_number = page_idx + 1
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        page_elements: List[PageElement] = []

        for block in blocks:
            if block.get("type") != 0:
                continue

            block_text_parts = []
            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                block_text_parts.append(line_text)

            full_text = "\n".join(block_text_parts).strip()
            if not full_text:
                continue

            bbox_raw = block.get("bbox", (0, 0, 0, 0))
            bbox = BoundingBox(x0=bbox_raw[0], y0=bbox_raw[1], x1=bbox_raw[2], y1=bbox_raw[3])

            element_type = _classify_text_block(full_text, block, page)
            page_elements.append(
                PageElement(
                    element_type=element_type,
                    text=full_text,
                    bbox=bbox,
                    page_number=page_number,
                    confidence=None,
                )
            )

        elements_by_page[page_number] = page_elements

    doc.close()
    logger.info("Extracted text elements from %d pages via PyMuPDF", len(elements_by_page))
    return elements_by_page


def extract_tables(pdf_path: str) -> dict[int, List[PageElement]]:
    """Extract tables from a PDF using pdfplumber.

    Each table row becomes a separate PageElement with element_type 'table_cell'.
    Column headers are prepended to each row for context.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        dict[int, List[PageElement]]: Mapping of page numbers to table elements.
    """
    table_elements_by_page: dict[int, List[PageElement]] = {}

    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        logger.error("Failed to open PDF with pdfplumber: %s", e)
        return table_elements_by_page

    for page_idx, page in enumerate(pdf.pages):
        page_number = page_idx + 1
        tables = page.extract_tables()
        page_table_elements: List[PageElement] = []

        for table in tables:
            if not table or len(table) < 2:
                continue

            headers = [str(h).strip() if h else "" for h in table[0]]
            table_bbox = _get_table_bbox(page, table)

            for row_idx, row in enumerate(table[1:], start=1):
                cells = [str(c).strip() if c else "" for c in row]
                row_text = " | ".join(
                    f"{headers[i]}: {cells[i]}" if i < len(headers) else cells[i]
                    for i in range(len(cells))
                )
                if not row_text.strip() or row_text.strip() == "|":
                    continue

                page_table_elements.append(
                    PageElement(
                        element_type="table_cell",
                        text=row_text,
                        bbox=table_bbox,
                        page_number=page_number,
                        confidence=None,
                    )
                )

        if page_table_elements:
            table_elements_by_page[page_number] = page_table_elements

    pdf.close()
    logger.info("Extracted table elements from %d pages via pdfplumber", len(table_elements_by_page))
    return table_elements_by_page


def parse_pdf(pdf_path: str) -> dict[int, dict]:
    """Run full PDF parsing: text extraction + table extraction.

    Merges text and table elements per page and returns page dimensions.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        dict[int, dict]: Mapping of page numbers to dicts with keys:
            - 'elements': List[PageElement]
            - 'width': float
            - 'height': float
    """
    text_elements = extract_text_elements(pdf_path)
    table_elements = extract_tables(pdf_path)

    all_pages = set(text_elements.keys()) | set(table_elements.keys())
    result: dict[int, dict] = {}

    try:
        doc = fitz.open(pdf_path)
        page_dims = {
            i + 1: (doc[i].rect.width, doc[i].rect.height) for i in range(len(doc))
        }
        doc.close()
    except Exception:
        page_dims = {}

    for page_num in sorted(all_pages):
        elements = text_elements.get(page_num, []) + table_elements.get(page_num, [])
        width, height = page_dims.get(page_num, (612.0, 792.0))
        result[page_num] = {
            "elements": elements,
            "width": width,
            "height": height,
        }

    logger.info("Full PDF parse complete: %d pages", len(result))
    return result


def is_scanned_pdf(pdf_path: str) -> bool:
    """Determine whether a PDF is scanned (image-only) or has a native text layer.

    A PDF is considered scanned if fewer than 20% of its pages contain
    extractable text of meaningful length (>50 characters).

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        bool: True if the PDF appears to be scanned.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return True

    if len(doc) == 0:
        doc.close()
        return True

    pages_with_text = 0
    for page in doc:
        text = page.get_text().strip()
        if len(text) > 50:
            pages_with_text += 1

    ratio = pages_with_text / len(doc)
    doc.close()
    is_scanned = ratio < 0.2
    logger.info(
        "Scanned PDF check: %d/%d pages have text (ratio=%.2f, scanned=%s)",
        pages_with_text, len(doc) if not doc.is_closed else 0, ratio, is_scanned,
    )
    return is_scanned


def _classify_text_block(text: str, block: dict, page) -> str:
    """Heuristically classify a text block as heading, paragraph, caption, etc.

    Args:
        text: The extracted text content.
        block: The raw block dict from PyMuPDF.
        page: The PyMuPDF page object.

    Returns:
        str: Element type classification.
    """
    lines = block.get("lines", [])
    if not lines:
        return "paragraph"

    first_span = lines[0].get("spans", [{}])[0] if lines[0].get("spans") else {}
    font_size = first_span.get("size", 12)
    is_bold = "bold" in first_span.get("font", "").lower()

    if font_size >= 16 or (is_bold and len(text) < 100):
        return "heading"

    if len(text) < 50 and any(kw in text.lower() for kw in ["figure", "table", "fig.", "tab."]):
        return "caption"

    bbox = block.get("bbox", (0, 0, 0, 0))
    page_height = page.rect.height
    # Narrow bands — 8% was too aggressive: normal body text at y≈60 was labeled header.
    if bbox[1] < page_height * 0.03:
        return "header"
    if bbox[3] > page_height * 0.97:
        return "footer"

    return "paragraph"


def _get_table_bbox(page, table) -> BoundingBox:
    """Estimate a bounding box for a table.

    Args:
        page: pdfplumber page object.
        table: The raw table data.

    Returns:
        BoundingBox: Estimated bounding box.
    """
    try:
        if hasattr(page, "bbox"):
            return BoundingBox(
                x0=page.bbox[0],
                y0=page.bbox[1],
                x1=page.bbox[2],
                y1=page.bbox[3],
            )
    except Exception:
        pass
    return BoundingBox(x0=0, y0=0, x1=612, y1=792)
