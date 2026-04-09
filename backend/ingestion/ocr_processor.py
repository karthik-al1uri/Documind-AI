"""DocuMind AI — OCR processing for scanned documents.

Renders PDF pages at 300 DPI and runs PaddleOCR to extract text with
word-level confidence scores. Flags low-confidence pages for human review.
"""

import os
import logging
from typing import List, Optional

import fitz  # PyMuPDF
from PIL import Image

from dotenv import load_dotenv

from models.schemas import BoundingBox, PageElement

load_dotenv()

logger = logging.getLogger(__name__)

OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.75"))

# Lazy-loaded PaddleOCR instance
_ocr_engine = None


def _get_ocr_engine():
    """Lazy-initialize the PaddleOCR engine.

    Returns:
        PaddleOCR: The initialized OCR engine instance.
    """
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        logger.info("PaddleOCR engine initialized")
    return _ocr_engine


def render_page_to_image(pdf_path: str, page_number: int, dpi: int = 300) -> Image.Image:
    """Render a single PDF page to a PIL Image at the specified DPI.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-indexed page number to render.
        dpi: Resolution for rendering (default 300).

    Returns:
        Image.Image: Rendered page as a PIL Image.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    logger.info("Rendered page %d at %d DPI (%dx%d)", page_number, dpi, pix.width, pix.height)
    return img


def run_ocr_on_image(image: Image.Image, page_number: int) -> tuple[List[PageElement], float]:
    """Run PaddleOCR on a PIL Image and return structured elements with confidence.

    Args:
        image: PIL Image to OCR.
        page_number: Page number for element metadata.

    Returns:
        tuple[List[PageElement], float]: Extracted elements and the mean
            confidence score across all detected words.
    """
    import numpy as np

    ocr = _get_ocr_engine()
    img_array = np.array(image)
    results = ocr.ocr(img_array, cls=True)

    elements: List[PageElement] = []
    confidences: List[float] = []

    if not results or not results[0]:
        logger.warning("No OCR results for page %d", page_number)
        return elements, 0.0

    for line in results[0]:
        box = line[0]
        text_data = line[1]
        text = text_data[0]
        confidence = float(text_data[1])

        if not text.strip():
            continue

        confidences.append(confidence)

        x_coords = [pt[0] for pt in box]
        y_coords = [pt[1] for pt in box]
        bbox = BoundingBox(
            x0=min(x_coords),
            y0=min(y_coords),
            x1=max(x_coords),
            y1=max(y_coords),
        )

        elements.append(
            PageElement(
                element_type="paragraph",
                text=text,
                bbox=bbox,
                page_number=page_number,
                confidence=confidence,
            )
        )

    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    logger.info(
        "OCR page %d: %d elements, mean confidence=%.3f",
        page_number, len(elements), mean_confidence,
    )
    return elements, mean_confidence


def ocr_pdf(pdf_path: str) -> dict[int, dict]:
    """Run OCR on all pages of a scanned PDF.

    Renders each page at 300 DPI, runs PaddleOCR, and returns structured
    elements with confidence scores. Low-confidence pages are flagged.

    Args:
        pdf_path: Path to the scanned PDF file.

    Returns:
        dict[int, dict]: Mapping of page numbers to dicts with keys:
            - 'elements': List[PageElement]
            - 'confidence_score': float (mean word confidence)
            - 'needs_review': bool (True if below threshold)
            - 'width': float
            - 'height': float
    """
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    page_dims = {
        i + 1: (doc[i].rect.width, doc[i].rect.height) for i in range(num_pages)
    }
    doc.close()

    result: dict[int, dict] = {}

    for page_num in range(1, num_pages + 1):
        image = render_page_to_image(pdf_path, page_num)
        elements, confidence = run_ocr_on_image(image, page_num)
        needs_review = confidence < OCR_CONFIDENCE_THRESHOLD
        width, height = page_dims.get(page_num, (612.0, 792.0))

        if needs_review:
            logger.warning(
                "Page %d flagged for review (confidence=%.3f < %.3f)",
                page_num, confidence, OCR_CONFIDENCE_THRESHOLD,
            )

        result[page_num] = {
            "elements": elements,
            "confidence_score": confidence,
            "needs_review": needs_review,
            "width": width,
            "height": height,
        }

    logger.info("OCR complete for %d pages", num_pages)
    return result


def ocr_image(image_path: str) -> dict[int, dict]:
    """Run OCR on a standalone image file (not a PDF).

    Treats the image as a single page.

    Args:
        image_path: Path to the image file.

    Returns:
        dict[int, dict]: Single-page result with the same structure as ocr_pdf.
    """
    image = Image.open(image_path)
    width, height = image.size
    elements, confidence = run_ocr_on_image(image, page_number=1)
    needs_review = confidence < OCR_CONFIDENCE_THRESHOLD

    logger.info(
        "OCR image complete: %d elements, confidence=%.3f, needs_review=%s",
        len(elements), confidence, needs_review,
    )

    return {
        1: {
            "elements": elements,
            "confidence_score": confidence,
            "needs_review": needs_review,
            "width": float(width),
            "height": float(height),
        }
    }
