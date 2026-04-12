"""DocuMind AI — PII detection and redaction using Microsoft Presidio.

Scans text for personally identifiable information (PII) and replaces
detected entities with typed placeholders (e.g. [PERSON], [EMAIL_ADDRESS]).
"""

import logging
import re
from typing import List, Tuple

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)

# Regex fallbacks — Presidio often misses formatted SSNs / phones in short strings.
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{3}\s\d{2}\s\d{4}\b")
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)
_PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\d{3}-\d{3}-\d{4}\b",
)


def _apply_regex_redactions(text: str) -> str:
    """Apply deterministic regex redactions after Presidio."""
    if not text:
        return text
    out = _SSN_RE.sub("[US_SSN]", text)
    out = _EMAIL_RE.sub("[EMAIL_ADDRESS]", out)
    out = _PHONE_RE.sub("[PHONE_NUMBER]", out)
    return out


# Lazy-loaded engines
_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None

# PII entity types to detect.
# DATE_TIME is intentionally excluded: Presidio often flags durations like
# "30 days" / "90 days", which are not PII and break grounded answers.
SUPPORTED_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "US_BANK_NUMBER",
    "IP_ADDRESS",
    "LOCATION",
]


def _get_analyzer() -> AnalyzerEngine:
    """Lazy-initialize the Presidio AnalyzerEngine.

    Returns:
        AnalyzerEngine: The initialized analyzer.
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
        logger.info("Presidio AnalyzerEngine initialized")
    return _analyzer


def _get_anonymizer() -> AnonymizerEngine:
    """Lazy-initialize the Presidio AnonymizerEngine.

    Returns:
        AnonymizerEngine: The initialized anonymizer.
    """
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
        logger.info("Presidio AnonymizerEngine initialized")
    return _anonymizer


def detect_pii(text: str, language: str = "en") -> List[RecognizerResult]:
    """Detect PII entities in a text string.

    Args:
        text: The input text to scan for PII.
        language: Language code for analysis (default 'en').

    Returns:
        List[RecognizerResult]: List of detected PII entities with positions
            and confidence scores.
    """
    analyzer = _get_analyzer()
    results = analyzer.analyze(
        text=text,
        entities=SUPPORTED_ENTITIES,
        language=language,
    )
    logger.info("Detected %d PII entities in text of length %d", len(results), len(text))
    return results


def redact_pii(text: str, language: str = "en") -> Tuple[str, List[dict]]:
    """Detect and replace PII in text with typed placeholders.

    Replaces each PII entity with a bracketed placeholder matching its type,
    e.g. ``John Smith`` → ``[PERSON]``, ``john@example.com`` → ``[EMAIL_ADDRESS]``.

    Args:
        text: The input text to redact.
        language: Language code for analysis (default 'en').

    Returns:
        Tuple[str, List[dict]]: A tuple of:
            - The redacted text string.
            - A list of dicts describing each redaction (entity_type, start,
              end, original_text, score).
    """
    if not text or not text.strip():
        return text, []

    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()

    analysis_results = analyzer.analyze(
        text=text,
        entities=SUPPORTED_ENTITIES,
        language=language,
    )

    if not analysis_results:
        final_text = _apply_regex_redactions(text)
        return final_text, []

    # Build operator config: replace each entity with [ENTITY_TYPE]
    operators = {}
    for entity_type in set(r.entity_type for r in analysis_results):
        operators[entity_type] = OperatorConfig(
            "replace",
            {"new_value": f"[{entity_type}]"},
        )

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=analysis_results,
        operators=operators,
    )

    redactions = [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "original_text": text[r.start : r.end],
            "score": r.score,
        }
        for r in analysis_results
    ]

    logger.info(
        "Redacted %d PII entities: %s",
        len(redactions),
        [r["entity_type"] for r in redactions],
    )
    final_text = _apply_regex_redactions(anonymized.text)
    return final_text, redactions


def redact_page_texts(
    pages_text: dict[int, str],
    language: str = "en",
) -> dict[int, Tuple[str, List[dict]]]:
    """Redact PII from a mapping of page numbers to raw text.

    Args:
        pages_text: Dict mapping page number → raw text string.
        language: Language code for analysis.

    Returns:
        dict[int, Tuple[str, List[dict]]]: Dict mapping page number →
            (redacted_text, redactions_list).
    """
    results: dict[int, Tuple[str, List[dict]]] = {}
    total_redactions = 0

    for page_num, text in pages_text.items():
        redacted, redactions = redact_pii(text, language)
        results[page_num] = (redacted, redactions)
        total_redactions += len(redactions)

    logger.info(
        "PII redaction complete across %d pages: %d total redactions",
        len(pages_text), total_redactions,
    )
    return results
