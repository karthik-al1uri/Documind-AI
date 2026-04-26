"""Pytest configuration and shared fixtures for DocuMind AI tests."""

import os
import tempfile
from pathlib import Path
import pytest
import sys

# Add backend to path for imports
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env.example")


@pytest.fixture(scope="session")
def temp_storage():
    """Create a temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "storage"
        storage_path.mkdir(exist_ok=True)
        # Override storage path for tests
        original_storage = os.getenv("STORAGE_PATH")
        os.environ["STORAGE_PATH"] = str(storage_path)
        yield storage_path
        # Restore original
        if original_storage:
            os.environ["STORAGE_PATH"] = original_storage
        elif "STORAGE_PATH" in os.environ:
            del os.environ["STORAGE_PATH"]


@pytest.fixture(scope="session")
def test_pdf_path():
    """Path to a test PDF file."""
    pdf_path = Path(__file__).resolve().parent.parent / "test_contract.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {pdf_path}")
    return pdf_path


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    This is a sample contract document for testing purposes.
    
    Payment Terms: Net 30 days from invoice date.
    Invoice Number: TEST-2024-001
    Total Amount: $5,000.00
    Due Date: March 15, 2025
    
    The parties agree to the following terms and conditions.
    This agreement is governed by the laws of the State of Delaware.
    Either party may terminate with 30 days written notice.
    
    Contact: John Smith, john.smith@example.com, SSN: 123-45-6789
    """


@pytest.fixture
def sample_page_json():
    """Sample PageJSON for testing."""
    from models.schemas import PageJSON, PageElement, BoundingBox
    
    elements = [
        PageElement(
            element_type="heading",
            text="Payment Terms",
            bbox=BoundingBox(x0=72, y0=100, x1=300, y1=120),
            page_number=1
        ),
        PageElement(
            element_type="paragraph",
            text="Net 30 days from invoice date. Late fee of 1.5% per month.",
            bbox=BoundingBox(x0=72, y0=130, x1=540, y1=160),
            page_number=1
        ),
        PageElement(
            element_type="paragraph",
            text="Invoice Number: TEST-2024-001, Total: $5,000.00",
            bbox=BoundingBox(x0=72, y0=170, x1=540, y1=200),
            page_number=1
        )
    ]
    
    return PageJSON(
        document_id="test-doc-123",
        page_number=1,
        width=612,
        height=792,
        elements=elements
    )
