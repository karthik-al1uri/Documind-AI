"""DocuMind AI — Language detection and embedding model routing.

Detects the dominant language of a document's text and sets a flag indicating
which embedding model variant to use during the retrieval phase.
"""

import logging
from typing import Optional

from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)

# Mapping of language codes to embedding model routing flags.
# 'en' uses the primary BGE-Large-EN model; others could use multilingual variants.
LANGUAGE_MODEL_MAP: dict[str, str] = {
    "en": "BAAI/bge-large-en-v1.5",
    "zh": "BAAI/bge-large-zh-v1.5",
    "default": "BAAI/bge-large-en-v1.5",
}


def detect_language(text: str) -> str:
    """Detect the dominant language of a text string.

    Uses the langdetect library which is based on Google's language-detection.
    Falls back to 'en' if detection fails or text is too short.

    Args:
        text: The input text to detect language from.

    Returns:
        str: ISO 639-1 language code (e.g. 'en', 'fr', 'zh').
    """
    if not text or len(text.strip()) < 20:
        logger.info("Text too short for language detection, defaulting to 'en'")
        return "en"

    try:
        lang = detect(text)
        logger.info("Detected language: %s", lang)
        return lang
    except LangDetectException as e:
        logger.warning("Language detection failed: %s — defaulting to 'en'", e)
        return "en"


def detect_language_with_confidence(text: str) -> list[dict]:
    """Detect language with per-language probability scores.

    Args:
        text: The input text to analyze.

    Returns:
        list[dict]: List of dicts with 'lang' and 'prob' keys, sorted by
            probability descending.
    """
    if not text or len(text.strip()) < 20:
        return [{"lang": "en", "prob": 1.0}]

    try:
        results = detect_langs(text)
        output = [{"lang": str(r.lang), "prob": round(float(r.prob), 4)} for r in results]
        logger.info("Language detection results: %s", output)
        return output
    except LangDetectException as e:
        logger.warning("Language detection failed: %s", e)
        return [{"lang": "en", "prob": 1.0}]


def get_embedding_model_for_language(language: str) -> str:
    """Get the appropriate embedding model name for a detected language.

    Args:
        language: ISO 639-1 language code.

    Returns:
        str: HuggingFace model identifier for the embedding model to use.
    """
    model = LANGUAGE_MODEL_MAP.get(language, LANGUAGE_MODEL_MAP["default"])
    logger.info("Routing language '%s' to embedding model: %s", language, model)
    return model


def detect_document_language(pages_text: dict[int, str]) -> str:
    """Detect the dominant language across all pages of a document.

    Concatenates a sample of text from each page (first 500 chars) and runs
    detection on the combined sample.

    Args:
        pages_text: Dict mapping page numbers to raw text strings.

    Returns:
        str: The detected ISO 639-1 language code.
    """
    sample_parts = []
    for page_num in sorted(pages_text.keys()):
        text = pages_text[page_num]
        if text and text.strip():
            sample_parts.append(text[:500])

    combined = " ".join(sample_parts)
    language = detect_language(combined)
    logger.info("Document language detected as '%s' from %d page samples", language, len(sample_parts))
    return language
