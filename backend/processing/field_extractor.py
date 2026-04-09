"""DocuMind AI — Document type classification and structured field extraction.

Classifies documents into types (invoice, contract, report, paper) using
keyword heuristics, then extracts type-specific structured fields using
regex-based templates.
"""

import re
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from utils.database import ExtractedField as ExtractedFieldORM

logger = logging.getLogger(__name__)

# Keywords used to classify document types
DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "invoice": [
        "invoice", "bill to", "ship to", "amount due", "total due",
        "payment terms", "invoice number", "inv #", "subtotal", "tax",
        "due date", "remit to", "purchase order",
    ],
    "contract": [
        "agreement", "contract", "hereby agree", "parties", "effective date",
        "termination", "governing law", "jurisdiction", "indemnification",
        "confidential", "obligations", "witness", "signatory", "clause",
    ],
    "report": [
        "executive summary", "findings", "recommendations", "conclusion",
        "methodology", "analysis", "quarterly", "annual report",
        "key metrics", "performance", "summary of results",
    ],
    "paper": [
        "abstract", "introduction", "related work", "methodology",
        "experiments", "results", "discussion", "references",
        "acknowledgments", "keywords", "doi", "arxiv",
    ],
}

# Regex templates for field extraction per document type
FIELD_TEMPLATES: dict[str, list[dict]] = {
    "invoice": [
        {"field_name": "invoice_number", "pattern": r"(?:invoice\s*(?:#|no\.?|number)\s*[:.]?\s*)(\S+)", "flags": re.IGNORECASE},
        {"field_name": "invoice_date", "pattern": r"(?:invoice\s*date|date\s*of\s*invoice)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", "flags": re.IGNORECASE},
        {"field_name": "due_date", "pattern": r"(?:due\s*date|payment\s*due)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", "flags": re.IGNORECASE},
        {"field_name": "invoice_total", "pattern": r"(?:total\s*(?:due|amount)?|amount\s*due|grand\s*total)\s*[:.]?\s*\$?([\d,]+\.?\d*)", "flags": re.IGNORECASE},
        {"field_name": "subtotal", "pattern": r"(?:subtotal|sub\s*total)\s*[:.]?\s*\$?([\d,]+\.?\d*)", "flags": re.IGNORECASE},
        {"field_name": "tax_amount", "pattern": r"(?:tax|sales\s*tax|vat)\s*[:.]?\s*\$?([\d,]+\.?\d*)", "flags": re.IGNORECASE},
    ],
    "contract": [
        {"field_name": "contract_date", "pattern": r"(?:effective\s*date|dated?)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", "flags": re.IGNORECASE},
        {"field_name": "party_name_1", "pattern": r"(?:between|party\s*(?:a|1|of the first part))\s*[:.]?\s*([A-Z][A-Za-z\s,\.]+?)(?:\s*\(|,\s*a\s)", "flags": 0},
        {"field_name": "party_name_2", "pattern": r"(?:and|party\s*(?:b|2|of the second part))\s*[:.]?\s*([A-Z][A-Za-z\s,\.]+?)(?:\s*\(|,\s*a\s)", "flags": 0},
        {"field_name": "governing_law", "pattern": r"(?:governing\s*law|governed\s*by)\s*[:.]?\s*(?:the\s*)?(?:laws?\s*of\s*)?(?:the\s*)?(?:state\s*of\s*)?([\w\s]+?)(?:\.|,|\n)", "flags": re.IGNORECASE},
        {"field_name": "termination_clause", "pattern": r"(?:terminat(?:ion|e))\s*[:.]?\s*(.{20,100}?)(?:\.\s|\n)", "flags": re.IGNORECASE},
    ],
    "report": [
        {"field_name": "report_title", "pattern": r"^(.{10,150})$", "flags": re.MULTILINE},
        {"field_name": "report_date", "pattern": r"(?:date|published|issued)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", "flags": re.IGNORECASE},
        {"field_name": "author", "pattern": r"(?:author|prepared\s*by|written\s*by)\s*[:.]?\s*([A-Z][A-Za-z\s,\.]+?)(?:\n|,\s*\d)", "flags": 0},
    ],
    "paper": [
        {"field_name": "paper_title", "pattern": r"^(.{10,200})$", "flags": re.MULTILINE},
        {"field_name": "authors", "pattern": r"(?:^|\n)([A-Z][a-z]+(?:\s[A-Z][a-z]+)+(?:\s*,\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)*)", "flags": 0},
        {"field_name": "doi", "pattern": r"(?:doi\s*[:.]?\s*)(10\.\d{4,}/\S+)", "flags": re.IGNORECASE},
        {"field_name": "arxiv_id", "pattern": r"(?:arxiv\s*[:.]?\s*)(\d{4}\.\d{4,5})", "flags": re.IGNORECASE},
    ],
}


def classify_document_type(full_text: str) -> Optional[str]:
    """Classify a document into a type based on keyword frequency.

    Scans the full document text for type-specific keywords and returns
    the type with the highest weighted match count.

    Args:
        full_text: The concatenated text of all pages.

    Returns:
        Optional[str]: Detected document type ('invoice', 'contract',
            'report', 'paper') or None if no type matches confidently.
    """
    if not full_text or len(full_text.strip()) < 50:
        logger.info("Text too short for document type classification")
        return None

    text_lower = full_text.lower()
    scores: dict[str, int] = {}

    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[doc_type] = score

    if not scores or max(scores.values()) == 0:
        logger.info("No document type keywords matched")
        return None

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Require at least 2 keyword matches to be confident
    if best_score < 2:
        logger.info("Low confidence for doc type '%s' (score=%d)", best_type, best_score)
        return None

    logger.info(
        "Classified document as '%s' (score=%d, all_scores=%s)",
        best_type, best_score, scores,
    )
    return best_type


def extract_fields(full_text: str, doc_type: str) -> list[dict]:
    """Extract structured fields from document text using regex templates.

    Args:
        full_text: The full document text.
        doc_type: The classified document type.

    Returns:
        list[dict]: List of dicts with keys 'field_name', 'field_value',
            and 'confidence'.
    """
    templates = FIELD_TEMPLATES.get(doc_type, [])
    if not templates:
        logger.info("No extraction templates for doc_type='%s'", doc_type)
        return []

    extracted: list[dict] = []

    for template in templates:
        field_name = template["field_name"]
        pattern = template["pattern"]
        flags = template.get("flags", 0)

        match = re.search(pattern, full_text, flags=flags)
        if match:
            value = match.group(1).strip()
            extracted.append({
                "field_name": field_name,
                "field_value": value,
                "confidence": 0.8,
            })
            logger.info("Extracted field '%s' = '%s'", field_name, value[:50])

    logger.info(
        "Field extraction for doc_type='%s': %d fields extracted",
        doc_type, len(extracted),
    )
    return extracted


async def run_field_extraction(
    session: AsyncSession,
    document_id: str,
    full_text: str,
) -> tuple[Optional[str], list[dict]]:
    """Classify a document and extract structured fields, persisting to DB.

    Args:
        session: Async database session.
        document_id: UUID string of the document.
        full_text: The full concatenated document text.

    Returns:
        tuple[Optional[str], list[dict]]: The detected doc_type and a list
            of extracted field dicts.
    """
    doc_type = classify_document_type(full_text)

    if not doc_type:
        logger.info("No doc_type detected for document %s — skipping field extraction", document_id)
        return None, []

    fields = extract_fields(full_text, doc_type)

    for field in fields:
        record = ExtractedFieldORM(
            document_id=document_id,
            field_name=field["field_name"],
            field_value=field["field_value"],
            confidence=field["confidence"],
        )
        session.add(record)

    logger.info(
        "Persisted %d extracted fields for document %s (type=%s)",
        len(fields), document_id, doc_type,
    )
    return doc_type, fields
