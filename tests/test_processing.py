"""Tests for Phase 3 processing components."""

import pytest
from processing.pii_redactor import redact_pii
from processing.language_detector import detect_language
from processing.field_extractor import classify_document_type, extract_fields
from processing.chunker import chunk_page


class TestPIIRedactor:
    """Test PII detection and redaction."""
    
    def test_redact_email_and_ssn(self):
        """Test redaction of email and SSN."""
        text = "Contact John Smith at john.smith@example.com or call 555-123-4567. SSN: 123-45-6789"
        redacted, redactions = redact_pii(text)
        
        # Check that PII is redacted
        assert "john.smith@example.com" not in redacted
        assert "123-45-6789" not in redacted
        
        # Check that placeholders exist
        assert "[EMAIL_ADDRESS]" in redacted or "[PERSON]" in redacted
        assert len(redactions) > 0
        
        # Verify redactions structure
        for redaction in redactions:
            assert "type" in redaction
            "start" in redaction
            "end" in redaction
            "value" in redaction
    
    def test_no_pii_text(self):
        """Test text without PII."""
        text = "This is a simple business document with no personal information."
        redacted, redactions = redact_pii(text)
        
        # Text should remain unchanged
        assert text == redacted
        assert len(redactions) == 0


class TestLanguageDetector:
    """Test language detection."""
    
    def test_detect_english(self):
        """Test English detection."""
        text = "This is an English document about contracts and legal agreements."
        lang = detect_language(text)
        assert lang == "en"
    
    def test_detect_short_text_defaults_to_english(self):
        """Test that short text defaults to English."""
        text = "Short"
        lang = detect_language(text)
        assert lang == "en"
    
    def test_detect_empty_text(self):
        """Test empty text handling."""
        lang = detect_language("")
        assert lang == "en"


class TestFieldExtractor:
    """Test document type classification and field extraction."""
    
    def test_classify_invoice(self):
        """Test invoice classification."""
        text = """
        Invoice #INV-2024-001
        Bill to: Acme Corporation
        Total Amount Due: $5,000.00
        Payment Terms: Net 30
        Due Date: March 15, 2025
        """
        doc_type = classify_document_type(text)
        assert doc_type == "invoice"
    
    def test_classify_contract(self):
        """Test contract classification."""
        text = """
        This Agreement is entered into between Party A and Party B.
        The effective date of this contract is January 1, 2025.
        This agreement is governed by the laws of Delaware.
        Either party may terminate with 30 days written notice.
        """
        doc_type = classify_document_type(text)
        assert doc_type == "contract"
    
    def test_extract_invoice_fields(self):
        """Test invoice field extraction."""
        text = """
        Invoice Number: INV-2024-001
        Invoice Date: 01/15/2025
        Total Due: $5,000.00
        Subtotal: $4,500.00
        Tax: $500.00
        """
        fields = extract_fields(text, "invoice")
        
        # Should extract invoice number
        invoice_numbers = [f for f in fields if f["field_name"] == "invoice_number"]
        assert len(invoice_numbers) > 0
        assert "INV-2024-001" in invoice_numbers[0]["field_value"]
        
        # Should extract total amount
        totals = [f for f in fields if "total" in f["field_name"].lower()]
        assert len(totals) > 0
    
    def test_extract_contract_fields(self):
        """Test contract field extraction."""
        text = """
        This Agreement dated 03/01/2025 between Alpha Corp and Beta LLC.
        Governing Law: State of New York.
        """
        fields = extract_fields(text, "contract")
        
        # Should extract contract date
        dates = [f for f in fields if "date" in f["field_name"].lower()]
        assert len(dates) > 0


class TestChunker:
    """Test document chunking."""
    
    def test_chunk_page_with_headings(self, sample_page_json):
        """Test chunking a page with headings and paragraphs."""
        chunks = chunk_page(sample_page_json, page_id="test-page-123")
        
        assert len(chunks) > 0
        
        # Verify chunk structure
        for chunk in chunks:
            assert chunk.document_id == "test-doc-123"
            assert chunk.page_id == "test-page-123"
            assert chunk.page_number == 1
            assert chunk.text.strip()
            assert chunk.chunk_type in ["heading", "paragraph", "table_cell", "caption"]
            assert chunk.chunk_index >= 0
        
        # Check that section headings are preserved
        chunks_with_headings = [c for c in chunks if c.section_heading]
        assert len(chunks_with_headings) > 0
    
    def test_chunk_minimum_length_filter(self, sample_page_json):
        """Test that very short chunks are filtered out."""
        # Create a page with very short elements
        from models.schemas import PageJSON, PageElement, BoundingBox
        
        short_elements = [
            PageElement(
                element_type="paragraph",
                text="Hi.",  # Very short
                bbox=BoundingBox(x0=72, y0=100, x1=100, y1=120),
                page_number=1
            )
        ]
        
        short_page = PageJSON(
            document_id="test-doc",
            page_number=1,
            width=612,
            height=792,
            elements=short_elements
        )
        
        chunks = chunk_page(short_page, page_id="test-page")
        # Very short chunks should be filtered out
        assert len(chunks) == 0
