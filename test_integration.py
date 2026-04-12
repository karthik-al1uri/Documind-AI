"""DocuMind AI — End-to-end integration tests (Phase 8).

Tests the full pipeline from upload through agent query to feedback,
exercising all Group 1 and Group 2 endpoints. Requires the backend
to be running at BACKEND_URL.

Usage:
    python -m pytest test_integration.py -v
    # or directly:
    python test_integration.py
"""

import json
import os
import time
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BACKEND_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
SAMPLE_DIR = Path(__file__).parent / "samples"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_backend(timeout: int = 30) -> bool:
    """Wait until the backend health endpoint responds.

    Args:
        timeout: Maximum seconds to wait.

    Returns:
        True if backend is reachable.
    """
    for _ in range(timeout):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(1)
    return False


def create_test_pdf(path: Path) -> Path:
    """Create a minimal test PDF with reportlab.

    Args:
        path: Directory to save the PDF.

    Returns:
        Path to the generated PDF.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = path / "test_document.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica", 12)

        content = [
            "DocuMind AI Test Document",
            "",
            "Section 1: Contract Overview",
            "This contract is between Acme Corp and Widget Industries.",
            "The total contract value is $1,200,000 (one million two hundred thousand dollars).",
            "The agreement was signed on January 15, 2024.",
            "",
            "Section 2: Payment Terms",
            "Payments are due quarterly, beginning 30 days after the signing date.",
            "Each quarterly payment shall be $300,000.",
            "",
            "Section 3: Termination",
            "Either party may terminate this agreement with 90 days written notice.",
            "Early termination fees apply at 10% of remaining contract value.",
        ]

        y = 750
        for line in content:
            c.drawString(72, y, line)
            y -= 20

        c.save()
        return pdf_path

    except ImportError:
        logger.warning("reportlab not installed; skipping PDF creation")
        return path / "nonexistent.pdf"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health(self):
        """Health endpoint returns ok status."""
        r = requests.get(f"{BACKEND_URL}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


class TestDocumentEndpoints:
    """Test document listing and detail endpoints."""

    def test_list_documents(self):
        """GET /documents returns a list."""
        r = requests.get(f"{BACKEND_URL}/documents")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestUploadAndIngestion:
    """Test the full upload → ingestion flow."""

    def test_upload_pdf(self):
        """Upload a PDF and verify it appears in the document list."""
        pdf_path = create_test_pdf(Path("/tmp"))
        if not pdf_path.exists():
            logger.warning("Skipping upload test — no test PDF")
            return

        with open(pdf_path, "rb") as f:
            r = requests.post(f"{BACKEND_URL}/upload", files={"file": ("test.pdf", f, "application/pdf")})

        assert r.status_code == 200
        data = r.json()
        assert "document_id" in data
        doc_id = data["document_id"]

        # Verify document appears in list
        r2 = requests.get(f"{BACKEND_URL}/documents")
        doc_ids = [d["id"] for d in r2.json()]
        assert doc_id in doc_ids


class TestRetrievalEndpoint:
    """Test the /retrieve endpoint (Group 1 handoff)."""

    def test_retrieve(self):
        """POST /retrieve returns a list of results."""
        r = requests.post(
            f"{BACKEND_URL}/retrieve",
            json={"query": "What is the contract value?", "top_k": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


class TestAgentQueryEndpoint:
    """Test the /query endpoint (Phase 5)."""

    def test_query(self):
        """POST /query returns an AnswerResponse."""
        r = requests.post(
            f"{BACKEND_URL}/query",
            json={"query": "What is the total contract value?", "top_k": 5},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "claims" in data
        assert "sources" in data
        assert "query_id" in data

    def test_query_with_document_filter(self):
        """POST /query with document_ids filter."""
        r = requests.post(
            f"{BACKEND_URL}/query",
            json={
                "query": "When was the agreement signed?",
                "top_k": 3,
                "document_ids": [],
            },
        )
        assert r.status_code == 200


class TestStreamingEndpoint:
    """Test the /query/stream SSE endpoint (Phase 6)."""

    def test_stream(self):
        """POST /query/stream returns SSE events."""
        r = requests.post(
            f"{BACKEND_URL}/query/stream",
            json={"query": "What are the payment terms?", "top_k": 5},
            stream=True,
        )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

        events = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
            if len(events) >= 3:
                break

        assert len(events) >= 1
        assert events[0]["type"] == "status"


class TestFeedbackEndpoint:
    """Test the /feedback endpoint (Phase 6)."""

    def test_submit_feedback(self):
        """POST /feedback records a rating."""
        r = requests.post(
            f"{BACKEND_URL}/feedback",
            json={
                "query": "What is the contract value?",
                "answer": "The total contract value is $1.2 million.",
                "rating": 1,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "recorded"
        assert "feedback_id" in data

    def test_submit_negative_feedback_with_correction(self):
        """POST /feedback with thumbs-down and correction."""
        r = requests.post(
            f"{BACKEND_URL}/feedback",
            json={
                "query": "Who signed the contract?",
                "answer": "The contract was signed by John Doe.",
                "rating": -1,
                "correction": "The contract was signed by Jane Smith.",
            },
        )
        assert r.status_code == 200

    def test_list_feedback(self):
        """GET /feedback returns recorded entries."""
        r = requests.get(f"{BACKEND_URL}/feedback")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Execute all integration tests and report results."""
    test_classes = [
        TestHealthEndpoint,
        TestDocumentEndpoints,
        TestUploadAndIngestion,
        TestRetrievalEndpoint,
        TestAgentQueryEndpoint,
        TestStreamingEndpoint,
        TestFeedbackEndpoint,
    ]

    if not wait_for_backend():
        logger.error("Backend not reachable at %s", BACKEND_URL)
        return False

    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if not method_name.startswith("test_"):
                continue
            test_name = f"{cls.__name__}.{method_name}"
            try:
                getattr(instance, method_name)()
                logger.info("PASS: %s", test_name)
                passed += 1
            except Exception as e:
                logger.error("FAIL: %s — %s", test_name, str(e))
                failed += 1

    logger.info("Results: %d passed, %d failed", passed, failed)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
