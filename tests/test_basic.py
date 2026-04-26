"""Basic tests for DocuMind AI core functionality."""

import pytest
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


class TestBasicFunctionality:
    """Test basic functionality without heavy dependencies."""
    
    def test_language_detection(self):
        """Test language detection."""
        from processing.language_detector import detect_language
        
        # Test English
        assert detect_language("This is an English document.") == "en"
        
        # Test short text defaults to English
        assert detect_language("Short") == "en"
        
        # Test empty text
        assert detect_language("") == "en"
        
        print("✓ Language detection tests passed")
    
    def test_field_extraction_classification(self):
        """Test document type classification."""
        from processing.field_extractor import classify_document_type
        
        # Test invoice classification
        invoice_text = """
        Invoice #INV-2024-001
        Bill to: Acme Corporation
        Total Amount Due: $5,000.00
        Payment Terms: Net 30
        Due Date: March 15, 2025
        """
        assert classify_document_type(invoice_text) == "invoice"
        
        # Test contract classification
        contract_text = """
        This Agreement is entered into between Party A and Party B.
        The effective date of this contract is January 1, 2025.
        This agreement is governed by the laws of Delaware.
        Either party may terminate with 30 days written notice.
        """
        assert classify_document_type(contract_text) == "contract"
        
        print("✓ Document classification tests passed")
    
    def test_field_extraction_extraction(self):
        """Test field extraction from documents."""
        from processing.field_extractor import extract_fields
        
        # Test invoice field extraction
        invoice_text = """
        Invoice Number: INV-2024-001
        Invoice Date: 01/15/2025
        Total Due: $5,000.00
        """
        fields = extract_fields(invoice_text, "invoice")
        
        # Should extract some fields
        assert len(fields) > 0
        
        # Check field structure
        for field in fields:
            assert "field_name" in field
            assert "field_value" in field
            assert "confidence" in field
            assert field["confidence"] > 0
        
        print("✓ Field extraction tests passed")
    
    def test_chunking_basic(self):
        """Test basic chunking functionality."""
        from models.schemas import PageJSON, PageElement, BoundingBox
        from processing.chunker import chunk_page
        
        # Create a simple page
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
            )
        ]
        
        page_json = PageJSON(
            document_id="test-doc-123",
            page_number=1,
            width=612,
            height=792,
            elements=elements
        )
        
        chunks = chunk_page(page_json, page_id="test-page-123")
        
        # Should create chunks
        assert len(chunks) > 0
        
        # Verify chunk structure
        for chunk in chunks:
            assert chunk.document_id == "test-doc-123"
            assert chunk.page_id == "test-page-123"
            assert chunk.page_number == 1
            assert chunk.text.strip()
            assert chunk.chunk_type in ["heading", "paragraph", "table_cell", "caption"]
        
        print("✓ Chunking tests passed")
    
    def test_rrf_fusion(self):
        """Test RRF fusion algorithm."""
        from retrieval.rrf_fusion import rrf_score, fuse_results
        
        # Test RRF scoring
        dense_ranking = ["chunk_a", "chunk_b", "chunk_c", "chunk_d"]
        sparse_ranking = ["chunk_c", "chunk_a", "chunk_e", "chunk_b"]
        
        fused_scores = rrf_score([dense_ranking, sparse_ranking], k=60)
        
        # Check all unique items are present
        expected_items = {"chunk_a", "chunk_b", "chunk_c", "chunk_d", "chunk_e"}
        assert set(fused_scores.keys()) == expected_items
        
        # Items appearing in both lists should have higher scores
        assert fused_scores["chunk_a"] > fused_scores["chunk_d"]
        assert fused_scores["chunk_c"] > fused_scores["chunk_e"]
        
        # Test fuse_results with scores
        dense_results = [("chunk_a", 0.9), ("chunk_b", 0.8), ("chunk_c", 0.7)]
        sparse_results = [("chunk_c", 0.95), ("chunk_a", 0.6), ("chunk_d", 0.5)]
        
        fused = fuse_results(dense_results, sparse_results)
        
        # Should return (chunk_id, rrf_score) tuples
        for chunk_id, score in fused:
            assert isinstance(chunk_id, str)
            assert isinstance(score, float)
        
        # Should be sorted by RRF score
        scores = [s for _, s in fused]
        assert scores == sorted(scores, reverse=True)
        
        print("✓ RRF fusion tests passed")
    
    def test_hyde_expansion(self):
        """Test HyDE query expansion."""
        from retrieval.hyde_expander import expand_query
        
        query = "What are the payment terms in this contract?"
        
        # This should work even without OpenAI API (falls back to original query)
        expanded = expand_query(query)
        
        assert isinstance(expanded, str)
        assert len(expanded) > 0
        
        # If API is not available, should return original query
        import os
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_key_here":
            assert expanded == query
            print("✓ HyDE expansion tests passed (fallback mode)")
        else:
            # With API, should be longer or different
            assert len(expanded) >= len(query)
            print("✓ HyDE expansion tests passed (API mode)")


def run_basic_tests():
    """Run basic tests without pytest."""
    print("\n" + "="*60)
    print("Running DocuMind AI Basic Tests")
    print("="*60 + "\n")
    
    test_instance = TestBasicFunctionality()
    
    tests = [
        test_instance.test_language_detection,
        test_instance.test_field_extraction_classification,
        test_instance.test_field_extraction_extraction,
        test_instance.test_chunking_basic,
        test_instance.test_rrf_fusion,
        test_instance.test_hyde_expansion,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)
