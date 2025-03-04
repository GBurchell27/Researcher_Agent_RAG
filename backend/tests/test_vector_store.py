"""
Tests for vector store operations.

This module tests:
1. Embedding dimension verification
2. Similarity search with various query types
3. Retrieval latency measurements
4. Metadata retrieval validation
"""

import os
import time
import uuid
import pytest
from typing import List, Dict, Any

import sys
import os
# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_processing import TextChunk
from embeddings import get_embedding, EmbeddingGenerator
from vector_store import VectorStore, initialize_vector_store, EMBEDDING_DIMENSIONS

# Sample text chunks for testing
@pytest.fixture
def sample_chunks() -> List[TextChunk]:
    """Create sample text chunks for testing."""
    document_id = str(uuid.uuid4())
    document_name = "test_document.pdf"
    
    return [
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            text="This is a sample chunk about artificial intelligence and machine learning.",
            page_number=0,
            document_id=document_id,
            document_name=document_name,
            start_char_idx=0,
            end_char_idx=100
        ),
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            text="Vector databases are used to store and query high-dimensional vectors efficiently.",
            page_number=0,
            document_id=document_id,
            document_name=document_name,
            start_char_idx=101,
            end_char_idx=200
        ),
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            text="Semantic search uses embeddings to find relevant information based on meaning, not just keywords.",
            page_number=1,
            document_id=document_id,
            document_name=document_name,
            start_char_idx=0,
            end_char_idx=100
        ),
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            text="PDF processing involves extracting text from PDF files and chunking it into manageable pieces.",
            page_number=1,
            document_id=document_id,
            document_name=document_name,
            start_char_idx=101,
            end_char_idx=200
        ),
        TextChunk(
            chunk_id=str(uuid.uuid4()),
            text="RAG (Retrieval Augmented Generation) combines retrieval systems with language models for more accurate responses.",
            page_number=2,
            document_id=document_id,
            document_name=document_name,
            start_char_idx=0,
            end_char_idx=120
        ),
    ]

@pytest.fixture
def vector_store() -> VectorStore:
    """Create a vector store instance for testing."""
    return initialize_vector_store()

def test_embedding_dimensions():
    """Test that embedding dimensions match Pinecone index configuration."""
    # Generate a test embedding
    embedding_gen = EmbeddingGenerator()
    test_text = "This is a test text for embedding dimension verification."
    embedding = embedding_gen.get_embedding(test_text)
    
    # Check the embedding dimensions
    assert len(embedding) == EMBEDDING_DIMENSIONS, \
        f"Embedding dimensions {len(embedding)} do not match expected {EMBEDDING_DIMENSIONS}"
    
    # Additional validation that all elements are floats
    assert all(isinstance(x, float) for x in embedding), "Embedding contains non-float values"

def test_upsert_and_query(vector_store, sample_chunks):
    """Test upserting chunks and querying them."""
    # Create a test namespace
    test_namespace = f"test_{str(uuid.uuid4())}"
    
    try:
        # Upsert the chunks
        count = vector_store.upsert_chunks(sample_chunks, namespace=test_namespace)
        assert count == len(sample_chunks), f"Upserted {count} chunks, expected {len(sample_chunks)}"
        
        # Wait for indexing
        time.sleep(1)
        
        # Perform a simple query
        results = vector_store.query("artificial intelligence", namespace=test_namespace, top_k=2)
        
        # Check that we got results
        assert len(results) > 0, "No results returned from query"
        
        # Validate result structure
        assert "id" in results[0], "Result missing 'id' field"
        assert "score" in results[0], "Result missing 'score' field"
        assert "metadata" in results[0], "Result missing 'metadata' field"
        
        # Check that the most relevant result contains our query terms or similar concepts
        assert "artificial" in results[0]["metadata"]["text"].lower() or \
               "intelligence" in results[0]["metadata"]["text"].lower() or \
               "ai" in results[0]["metadata"]["text"].lower(), \
               "Query results don't seem relevant to the query"
    
    finally:
        # Clean up - delete the test namespace
        vector_store.delete_vectors(delete_all=True, namespace=test_namespace)

def test_query_types(vector_store, sample_chunks):
    """Test similarity search with various query types."""
    # Create a test namespace
    test_namespace = f"test_{str(uuid.uuid4())}"
    
    try:
        # Upsert the chunks
        vector_store.upsert_chunks(sample_chunks, namespace=test_namespace)
        
        # Wait for indexing
        time.sleep(1)
        
        # Test direct concept query
        concept_results = vector_store.query(
            "machine learning", 
            namespace=test_namespace, 
            top_k=2
        )
        
        # Test question query
        question_results = vector_store.query(
            "What is semantic search?", 
            namespace=test_namespace, 
            top_k=2
        )
        
        # Test technical query
        technical_results = vector_store.query(
            "vector database implementation", 
            namespace=test_namespace, 
            top_k=2
        )
        
        # Check that we got results for each query type
        assert len(concept_results) > 0, "No results for concept query"
        assert len(question_results) > 0, "No results for question query"
        assert len(technical_results) > 0, "No results for technical query"
        
        # Verify that different query types return different top results
        top_result_ids = {
            concept_results[0]["id"],
            question_results[0]["id"],
            technical_results[0]["id"]
        }
        
        # We should ideally get at least 2 different results from our 3 very different queries
        assert len(top_result_ids) >= 2, "Different query types are not returning diverse results"
    
    finally:
        # Clean up
        vector_store.delete_vectors(delete_all=True, namespace=test_namespace)

def test_retrieval_latency(vector_store, sample_chunks):
    """Measure retrieval latency for optimization."""
    # Create a test namespace
    test_namespace = f"test_{str(uuid.uuid4())}"
    
    try:
        # Upsert the chunks
        vector_store.upsert_chunks(sample_chunks, namespace=test_namespace)
        
        # Wait for indexing
        time.sleep(1)
        
        # Measure query latency
        query_text = "vector databases semantic search"
        
        # Warm-up query to eliminate cold-start effects
        vector_store.query(query_text, namespace=test_namespace, top_k=3)
        
        # Timed query
        start_time = time.time()
        results = vector_store.query(query_text, namespace=test_namespace, top_k=3)
        query_time = time.time() - start_time
        
        # Log the latency
        print(f"Query latency: {query_time*1000:.2f}ms for {len(results)} results")
        
        # Typical latency should be under 500ms for this small dataset
        # Adjust this threshold based on your requirements and environment
        assert query_time < 0.5, f"Query latency ({query_time*1000:.2f}ms) exceeds threshold (500ms)"
        
        # Also verify we got the expected number of results
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    
    finally:
        # Clean up
        vector_store.delete_vectors(delete_all=True, namespace=test_namespace)

def test_metadata_retrieval(vector_store, sample_chunks):
    """Validate metadata retrieval works correctly."""
    # Create a test namespace
    test_namespace = f"test_{str(uuid.uuid4())}"
    
    try:
        # Upsert the chunks
        vector_store.upsert_chunks(sample_chunks, namespace=test_namespace)
        
        # Wait for indexing
        time.sleep(1)
        
        # Query to retrieve results with metadata
        results = vector_store.query("RAG retrieval", namespace=test_namespace, top_k=3)
        
        # Check that we got results
        assert len(results) > 0, "No results returned from query"
        
        # Validate metadata fields
        for result in results:
            metadata = result["metadata"]
            
            # Check required metadata fields
            assert "text" in metadata, "Metadata missing 'text' field"
            assert "chunk_id" in metadata, "Metadata missing 'chunk_id' field"
            assert "page_number" in metadata, "Metadata missing 'page_number' field"
            assert "document_id" in metadata, "Metadata missing 'document_id' field"
            assert "document_name" in metadata, "Metadata missing 'document_name' field"
            
            # Validate metadata values
            assert isinstance(metadata["text"], str), "Metadata 'text' is not a string"
            assert len(metadata["text"]) > 0, "Metadata 'text' is empty"
            assert isinstance(metadata["page_number"], int), "Metadata 'page_number' is not an integer"
            assert metadata["document_name"] == "test_document.pdf", "Incorrect document name in metadata"
            
            # Check that the chunk_id in metadata matches one of our sample chunks
            sample_chunk_ids = [chunk.chunk_id for chunk in sample_chunks]
            assert metadata["chunk_id"] in sample_chunk_ids, "Retrieved chunk_id not found in sample chunks"
    
    finally:
        # Clean up
        vector_store.delete_vectors(delete_all=True, namespace=test_namespace)

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
