"""DocuMind AI — NLI entailment verification using DeBERTa-v3-large.

Checks each claim in a generated answer against its cited source chunk.
Claims that are not entailed (score below threshold) are flagged, enabling
the Critic Agent to decide whether to retry the generation.
"""

import logging
import os
from typing import List

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from models.schemas import Claim

logger = logging.getLogger(__name__)

NLI_MODEL = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-large")
ENTAILMENT_THRESHOLD = 0.2

_tokenizer = None
_model = None


def _load_model():
    """Lazily load the NLI model and tokenizer.

    Returns:
        Tuple of (tokenizer, model).
    """
    global _tokenizer, _model
    if _tokenizer is None:
        cache_dir = os.getenv("HF_CACHE_DIR", "./models")
        logger.info("Loading NLI model: %s", NLI_MODEL)
        _tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL, cache_dir=cache_dir)
        _model = AutoModelForSequenceClassification.from_pretrained(
            NLI_MODEL, cache_dir=cache_dir
        )
        _model.eval()
        logger.info("NLI model loaded successfully")
    return _tokenizer, _model


def _predict_entailment(premise: str, hypothesis: str) -> dict:
    """Run a single NLI prediction.

    Args:
        premise: The source text (retrieved chunk).
        hypothesis: The claim to verify.

    Returns:
        Dict with scores for each NLI class.
    """
    tokenizer, model = _load_model()

    inputs = tokenizer(
        premise,
        hypothesis,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)[0]

    # Label order is model-specific (cross-encoder NLI is often contradiction, entailment, neutral).
    id2label = getattr(model.config, "id2label", None) or {}
    scores = {}
    for i in range(len(probs)):
        key = id2label.get(str(i), id2label.get(i, f"label_{i}"))
        name = str(key).lower()
        if "contradiction" in name or name == "contradict":
            scores["contradiction"] = probs[i].item()
        elif "entail" in name:
            scores["entailment"] = probs[i].item()
        elif "neutral" in name:
            scores["neutral"] = probs[i].item()
        else:
            scores[str(key)] = probs[i].item()

    # Ensure canonical keys exist
    scores.setdefault("contradiction", 0.0)
    scores.setdefault("neutral", 0.0)
    scores.setdefault("entailment", 0.0)
    return scores


class NLIVerifier:
    """Thin wrapper for standalone entailment checks (premise = source, hypothesis = claim)."""

    model_name = NLI_MODEL

    async def verify(self, claim: str, context: str) -> float:
        """Return probability mass on the entailment class."""
        scores = _predict_entailment(context, claim)
        return float(scores.get("entailment", 0.0))


def verify_claims(claims: List[Claim]) -> List[Claim]:
    """Verify each claim against its cited source using NLI.

    Args:
        claims: List of claims, each with a citation containing source text.

    Returns:
        Updated claims with entailment_label and entailment_score populated.
    """
    logger.info("Verifying %d claims via NLI", len(claims))
    verified = []

    for claim in claims:
        if claim.citation is None or not claim.citation.text:
            claim.entailment_label = "neutral"
            claim.entailment_score = 0.0
            verified.append(claim)
            continue

        scores = _predict_entailment(
            premise=claim.citation.text,
            hypothesis=claim.text,
        )

        entailment_score = scores.get("entailment", 0.0)
        if entailment_score >= ENTAILMENT_THRESHOLD:
            label = "entailment"
        elif scores.get("contradiction", 0.0) > scores.get("neutral", 0.0):
            label = "contradiction"
        else:
            label = "neutral"

        claim.entailment_label = label
        claim.entailment_score = entailment_score
        logger.debug("Claim '%.60s…' → %s (%.3f)", claim.text, label, entailment_score)
        verified.append(claim)

    passed = sum(1 for c in verified if c.entailment_label == "entailment")
    logger.info("NLI verification: %d/%d claims entailed", passed, len(verified))
    return verified


def check_verification_threshold(claims: List[Claim], threshold: float = 0.8) -> bool:
    """Check whether enough claims pass entailment.

    Args:
        claims: Verified claims with entailment labels.
        threshold: Minimum fraction of entailed claims to pass.

    Returns:
        True if verification passes (>= threshold entailed).
    """
    if not claims:
        return True
    entailed = sum(1 for c in claims if c.entailment_label == "entailment")
    ratio = entailed / len(claims)
    logger.info("Verification ratio: %.2f (threshold=%.2f)", ratio, threshold)
    return ratio >= threshold
