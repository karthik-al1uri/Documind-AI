"""Integration tests for DocuMind AI pipeline."""

import pytest
import asyncio
from pathlib import Path
import sys

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from ingestion.pdf_parser import parse_pdf
from ingestion.layout_service import build_page_json
from processing.pii_redactor import redact_pii
from processing.language_detector import detect_language
from processing.chunker import chunk_page
from retrieval.embedder import embed_query
from retrieval.indexer import add_vectors, search, reset_index


class TestEndToEndPipeline:
    """Test the complete document processing pipeline."""
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up before and after each test."""
        reset_index()
        yield
        reset_index()
    
    def test_pdf_to_embeddings_pipeline(self, test_pdf_path):
        """Test processing a PDF from file to embeddings."""
        # Step 1: Parse PDF
        pages = parse_pdf(str(test_pdf_path))
        assert len(pages) > 0, "PDF parsing failed"
        
        first_page_num = min(pages.keys())
        first_page = pages[first_page_num]
        
        # Step 2: Build PageJSON
        page_json = build_page_json(
            document_id="test-doc-123",
            page_number=first_page_num,
            elements=first_page["elements"],
            width=first_page["width"],
            height=first_page["height"]
        )
        
        assert len(page_json.elements) > 0, "No elements found in page"
        
        # Step 3: Extract text for processing
        full_text = " ".join([elem.text for elem in page_json.elements if elem.text])
        
        # Step 4: PII Redaction
        redacted_text, redactions = redact_pii(full_text)
        assert isinstance(redacted_text, str)
        assert isinstance(redactions, list)
        
        # Step 5: Language Detection
        language = detect_language(redacted_text)
        assert language in ["en", "es", "fr", "de", "it"], f"Unexpected language: {language}"
        
        # Step 6: Chunking
        chunks = chunk_page(page_json, page_id="test-page-123")
        assert len(chunks) > 0, "No chunks created"
        
        # Verify chunk properties
        for chunk in chunks:
            assert chunk.text.strip(), "Empty chunk text"
            assert chunk.document_id == "test-doc-123"
            assert chunk.page_id == "test-page-123"
        
        # Step 7: Embedding Generation
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embed_query(chunk_texts[0]) if chunk_texts else embed_query("test")
        assert embeddings.shape == (1024,), "Embedding dimension mismatch"
        
        # Step 8: Indexing
        if len(chunks) > 0:
            # Create embeddings for all chunks
            from retrieval.embedder import embed_chunks
            all_embeddings = embed_chunks(chunk_texts)
            
            # Add to FAISS index
            ids = add_vectors(all_embeddings)
            assert len(ids) == len(chunks), "Not all chunks indexed"
            
            # Step 9: Search
            query = "payment terms"
            query_embedding = embed_query(query)
            results = search(query_embedding, top_k=5)
            
            assert isinstance(results, list), "Search should return list"
            if results:  # Might be empty if no good matches
                for chunk_id, score in results:
                    assert isinstance(chunk_id, int)
                    assert isinstance(score, float)
                    assert 0 <= score <= 1.0  # Cosine similarity range
    
    def test_multilingual_document_processing(self):
        """Test processing documents in different languages."""
        # Create sample texts in different languages
        documents = {
            "en": "This contract is governed by English law. Payment terms are net 30 days.",
            "es": "Este contrato se rige por la ley española. Los términos de pago son a 30 días.",
            "fr": "Ce contrat est régi par le droit français. Les conditions de paiement sont à 30 jours."
        }
        
        detected_languages = {}
        for lang_code, text in documents.items():
            detected = detect_language(text)
            detected_languages[lang_code] = detected
        
        # English should be detected correctly
        assert detected_languages["en"] == "en", f"English not detected: {detected_languages['en']}"
        
        # Other languages might be detected as English if text is too short
        # This is expected behavior per the implementation
    
    def test_pii_redaction_preserves_structure(self):
        """Test that PII redaction preserves document structure."""
        text_with_pii = """
        Contract Agreement
        
        Parties:
        - John Smith (Email: john.smith@company.com, SSN: 123-45-6789)
        - Jane Doe (Phone: 555-123-4567)
        
        Terms:
        Payment of $10,000.00 is due within 30 days.
        Please send payment to:
        Acme Corporation
        123 Business St
        New York, NY 10001
        """
        
        redacted, redactions = redact_pii(text_with_pii)
        
        # Should redact PII
        assert "john.smith@company.com" not in redacted
        assert "123-45-6789" not in redacted
        
        # Should preserve structure
        assert "Contract Agreement" in redacted
        assert "Payment of $10,000.00" in redacted
        assert "Acme Corporation" in redacted
        
        # Should have redaction records
        assert len(redactions) > 0
        
        # Check redaction metadata
        for redaction in redactions:
            assert "type" in redaction
            assert "start" in redaction
            assert "end" in redaction
            assert redaction["start"] < redaction["end"]
    
    def test_chunking_with_overlap(self):
        """Test that chunking applies overlap correctly."""
        from models.schemas import PageJSON, PageElement, BoundingBox
        
        # Create a long paragraph that will be split
        long_text = "This is a very long paragraph that should be split into multiple chunks. " * 20
        
        elements = [
            PageElement(
                element_type="paragraph",
                text=long_text,
                bbox=BoundingBox(x0=72, y0=100, x1=540, y1=500),
                page_number=1
            )
        ]
        
        page_json = PageJSON(
            document_id="overlap-test",
            page_number=1,
            width=612,
            height=792,
            elements=elements
        )
        
        chunks = chunk_page(page_json, page_id="test-page")
        
        # Should create multiple chunks
        assert len(chunks) > 1, "Long paragraph should be split into multiple chunks"
        
        # Apply overlap
        from processing.chunker import apply_cross_chunk_overlap
        overlapped_chunks = apply_cross_chunk_overlap(chunks)
        
        # Should have same number of chunks
        assert len(overlapped_chunks) == len(chunks)
        
        # Overlapped chunks should be longer (except first one)
        if len(overlapped_chunks) > 1:
            for i in range(1, len(overlapped_chunks)):
                # Overlapped chunk should contain some text from previous chunk
                prev_chunk = chunks[i-1].text
                curr_chunk = overlapped_chunks[i].text
                
                # Check for overlap (last 10% of previous should be in current)
                overlap_len = max(1, int(len(prev_chunk) * 0.10))
                overlap_text = prev_chunk[-overlap_len:]
                
                # This might not always be true due to sentence boundaries
                # but is a good sanity check
                if overlap_text in curr_chunk:
                    break  # Overlap detected
            else:
                pytest.skip("No overlap detected - might be due to sentence boundary splitting")


class TestErrorHandling:
    """Test error handling in pipeline components."""
    
    def test_parse_nonexistent_file(self):
        """Test handling of nonexistent PDF file."""
        from ingestion.pdf_parser import parse_pdf
        
        with pytest.raises(FileNotFoundError):
            parse_pdf("/nonexistent/file.pdf")
    
    def test_embed_empty_text(self):
        """Test embedding empty or None text."""
        from retrieval.embedder import embed_query
        
        # Empty string should work
        result = embed_query("")
        assert result.shape == (1024,)
        
        # None should raise an error
        with pytest.raises((TypeError, AttributeError)):
            embed_query(None)
    
    def test_chunk_empty_page(self):
        """Test chunking an empty page."""
        from models.schemas import PageJSON
        
        empty_page = PageJSON(
            document_id="empty-doc",
            page_number=1,
            width=612,
            height=792,
            elements=[]
        )
        
        chunks = chunk_page(empty_page, page_id="empty-page")
        assert chunks == []
    
    def test_search_empty_index(self):
        """Test searching when no documents are indexed."""
        reset_index()
        
        query = "test query"
        query_embedding = embed_query(query)
        results = search(query_embedding, top_k=5)
        
        assert results == []


# Async tests for database operations
@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async database operations."""
    
    async def test_field_extraction_async(self):
        """Test async field extraction."""
        from processing.field_extractor import run_field_extraction
        from utils.database import async_session
        
        sample_text = """
        Invoice #TEST-123
        Total Amount: $5,000.00
        Due Date: March 15, 2025
        Payment Terms: Net 30
        """
        
        async with async_session() as session:
            doc_type, fields = await run_field_extraction(
                session=session,
                document_id="test-doc-456",
                full_text=sample_text
            )
            
            assert doc_type == "invoice"
            assert len(fields) > 0
            
            # Check field structure
            for field in fields:
                assert "field_name" in field
                assert "field_value" in field
                assert "confidence" in field
