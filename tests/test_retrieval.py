"""Tests for Phase 4 retrieval components."""

import pytest
import numpy as np
from retrieval.embedder import embed_query, embed_chunks
from retrieval.indexer import add_vectors, search, get_index_size, reset_index
from retrieval.rrf_fusion import rrf_score, fuse_results
from retrieval.reranker import rerank
from retrieval.hyde_expander import expand_query


@pytest.fixture(autouse=True)
def cleanup_faiss_index():
    """Reset FAISS index before each test."""
    reset_index()
    yield
    # Clean up after test if needed


class TestEmbedder:
    """Test BGE embedding generation."""
    
    def test_embed_query(self):
        """Test single query embedding."""
        query = "What are the payment terms in this contract?"
        embedding = embed_query(query)
        
        # Verify embedding properties
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1024,)  # BGE-Large dimension
        assert embedding.dtype in [np.float32, np.float64]
        
        # Check that embedding is normalized (BGE normalizes by default)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-6, f"Embedding not normalized: norm={norm}"
    
    def test_embed_chunks(self):
        """Test multiple chunk embeddings."""
        chunks = [
            "This is the first chunk about payment terms.",
            "This is the second chunk about termination clauses.",
            "This is the third chunk about governing law."
        ]
        
        embeddings = embed_chunks(chunks)
        
        # Verify shape and type
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 1024)
        assert embeddings.dtype in [np.float32, np.float64]
        
        # Each embedding should be normalized
        for i in range(3):
            norm = np.linalg.norm(embeddings[i])
            assert abs(norm - 1.0) < 1e-6
    
    def test_embed_empty_list(self):
        """Test embedding empty list."""
        embeddings = embed_chunks([])
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (0, 1024)


class TestFAISSIndexer:
    """Test FAISS vector indexing."""
    
    def test_add_and_search_vectors(self):
        """Test adding vectors and searching."""
        # Create test vectors (normalized)
        rng = np.random.default_rng(42)
        vectors = rng.standard_normal((5, 1024)).astype(np.float32)
        # Normalize
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        # Add to index
        ids = add_vectors(vectors)
        assert len(ids) == 5
        assert ids == list(range(5))  # Should start from 0
        
        # Search with first vector
        results = search(vectors[0], top_k=3)
        assert len(results) == 3
        
        # Results should be (id, score) tuples
        for vec_id, score in results:
            assert isinstance(vec_id, int)
            assert isinstance(score, float)
            assert 0 <= vec_id < 5
        
        # First result should be the same vector (highest similarity)
        assert results[0][0] == 0
        assert results[0][1] > 0.99  # Very high similarity for same vector
    
    def test_search_empty_index(self):
        """Test searching when index is empty."""
        query = np.random.randn(1024).astype(np.float32)
        results = search(query, top_k=5)
        assert results == []
    
    def test_index_size_tracking(self):
        """Test index size tracking."""
        initial_size = get_index_size()
        assert initial_size == 0
        
        # Add vectors
        vectors = np.random.randn(3, 1024).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        add_vectors(vectors)
        
        assert get_index_size() == 3


class TestRRFFusion:
    """Test Reciprocal Rank Fusion."""
    
    def test_rrf_score_calculation(self):
        """Test RRF score calculation."""
        dense_ranking = ["chunk_a", "chunk_b", "chunk_c", "chunk_d"]
        sparse_ranking = ["chunk_c", "chunk_a", "chunk_e", "chunk_b"]
        
        fused_scores = rrf_score([dense_ranking, sparse_ranking], k=60)
        
        # Check all unique items are present
        expected_items = {"chunk_a", "chunk_b", "chunk_c", "chunk_d", "chunk_e"}
        assert set(fused_scores.keys()) == expected_items
        
        # Items appearing in both lists should have higher scores
        assert fused_scores["chunk_a"] > fused_scores["chunk_d"]
        assert fused_scores["chunk_c"] > fused_scores["chunk_e"]
        
        # Scores should be sorted in descending order
        scores = list(fused_scores.values())
        assert scores == sorted(scores, reverse=True)
    
    def test_fuse_results_with_scores(self):
        """Test fusing scored results."""
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


class TestReranker:
    """Test cross-encoder reranking."""
    
    def test_rerank_candidates(self):
        """Test reranking candidate passages."""
        query = "What are the payment terms?"
        candidates = [
            ("c1", "The payment terms are net 30 days from invoice date.", 0.8),
            ("c2", "The weather is sunny today with clear skies.", 0.7),
            ("c3", "Payment must be received within 30 days of invoicing.", 0.6),
        ]
        
        results = rerank(query, candidates, top_k=3)
        
        # Should return fewer or equal candidates
        assert len(results) <= len(candidates)
        assert len(results) > 0
        
        # Results should be (chunk_id, reranker_score)
        for chunk_id, score in results:
            assert isinstance(chunk_id, str)
            assert isinstance(score, float)
        
        # Should be sorted by score (descending)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)
        
        # Relevant passages should score higher
        relevant_ids = {"c1", "c3"}
        top_id = results[0][0]
        assert top_id in relevant_ids
    
    def test_rerank_empty_candidates(self):
        """Test reranking with no candidates."""
        results = rerank("test query", [], top_k=5)
        assert results == []


class TestHyDEExpansion:
    """Test HyDE query expansion."""
    
    def test_expand_query(self):
        """Test query expansion."""
        query = "What are the payment terms in this contract?"
        
        # This test might fail if OpenAI API key is not set
        # In that case, it should fall back to returning the original query
        expanded = expand_query(query)
        
        assert isinstance(expanded, str)
        assert len(expanded) > 0
        
        # If API is not available, should return original query
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_key_here":
            assert expanded == query
        else:
            # With API, should be longer and different
            assert len(expanded) >= len(query)
            # Should contain relevant terms
            assert any(term in expanded.lower() for term in ["payment", "terms", "contract", "invoice"])
