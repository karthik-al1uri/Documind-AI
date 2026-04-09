"""DocuMind AI — Heuristic layout classification service.

Classifies extracted page elements (from native PDF or OCR) into semantic
categories and produces structured PageJSON objects for storage.
"""

import logging
from typing import List

from models.schemas import BoundingBox, PageElement, PageJSON

logger = logging.getLogger(__name__)

# Vertical position thresholds (as fractions of page height)
HEADER_ZONE = 0.08
FOOTER_ZONE = 0.92

# Font-size-based heuristics (only applicable to native PDF elements)
HEADING_MIN_LENGTH = 3
HEADING_MAX_LENGTH = 200
CAPTION_MAX_LENGTH = 80
CAPTION_KEYWORDS = {"figure", "fig.", "table", "tab.", "chart", "graph", "exhibit"}


def classify_elements(
    elements: List[PageElement],
    page_width: float,
    page_height: float,
) -> List[PageElement]:
    """Reclassify page elements using heuristic layout rules.

    Applies zone-based header/footer detection, length-based heading detection,
    and keyword-based caption detection. Elements already classified as
    'table_cell' are left unchanged.

    Args:
        elements: Raw page elements from PDF parser or OCR.
        page_width: Width of the page in points.
        page_height: Height of the page in points.

    Returns:
        List[PageElement]: Elements with updated element_type classifications.
    """
    classified: List[PageElement] = []

    for elem in elements:
        if elem.element_type == "table_cell":
            classified.append(elem)
            continue

        new_type = _apply_layout_rules(elem, page_width, page_height)
        classified.append(
            PageElement(
                element_type=new_type,
                text=elem.text,
                bbox=elem.bbox,
                page_number=elem.page_number,
                confidence=elem.confidence,
            )
        )

    return classified


def build_page_json(
    document_id: str,
    page_number: int,
    elements: List[PageElement],
    width: float,
    height: float,
) -> PageJSON:
    """Build a PageJSON object for a single page.

    Args:
        document_id: UUID string of the parent document.
        page_number: 1-indexed page number.
        elements: Classified page elements.
        width: Page width in points.
        height: Page height in points.

    Returns:
        PageJSON: Structured page representation ready for DB storage.
    """
    classified = classify_elements(elements, width, height)
    page_json = PageJSON(
        document_id=document_id,
        page_number=page_number,
        width=width,
        height=height,
        elements=classified,
    )
    logger.info(
        "Built PageJSON for doc=%s page=%d with %d elements",
        document_id, page_number, len(classified),
    )
    return page_json


def _apply_layout_rules(
    elem: PageElement,
    page_width: float,
    page_height: float,
) -> str:
    """Apply heuristic rules to determine element type.

    Args:
        elem: The page element to classify.
        page_width: Page width in points.
        page_height: Page height in points.

    Returns:
        str: The determined element type.
    """
    text = elem.text.strip()
    bbox = elem.bbox

    if page_height > 0:
        if bbox.y0 < page_height * HEADER_ZONE:
            return "header"
        if bbox.y1 > page_height * FOOTER_ZONE:
            return "footer"

    text_lower = text.lower()
    if (
        len(text) <= CAPTION_MAX_LENGTH
        and any(kw in text_lower for kw in CAPTION_KEYWORDS)
    ):
        return "caption"

    if HEADING_MIN_LENGTH <= len(text) <= HEADING_MAX_LENGTH:
        if text.isupper() or (text[0].isupper() and "\n" not in text):
            if elem.element_type == "heading":
                return "heading"

    if elem.element_type in ("heading", "paragraph", "caption", "header", "footer"):
        return elem.element_type

    return "paragraph"
