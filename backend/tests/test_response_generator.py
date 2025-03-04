"""
Standalone test script for the response generator.
This file can be run directly without pytest.

Usage:
    python test_response_generator.py
"""

import sys
import os
import json
from datetime import datetime

# Add the parent directory to the Python path to allow importing project modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import project modules
from response_generator import ResponseGenerator, QueryType, SourceReference, GeneratedResponse, generate_response
from embeddings import get_embedding
from vector_store import VectorStore, initialize_vector_store
from query_handler import QueryProcessor, process_query

# Test mock data
MOCK_RESULTS = [
    {
        "id": "chunk1",
        "score": 0.85,
        "metadata": {
            "text": "Artificial intelligence (AI) is intelligence demonstrated by machines. Modern AI systems can perform tasks that typically require human intelligence.",
            "page_number": 1,
            "chunk_index": 0
        }
    },
    {
        "id": "chunk2",
        "score": 0.78,
        "metadata": {
            "text": "Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.",
            "page_number": 1,
            "chunk_index": 1
        }
    },
    {
        "id": "chunk3",
        "score": 0.72,
        "metadata": {
            "text": "Deep learning is a type of machine learning that uses neural networks with many layers. It has revolutionized fields like computer vision and natural language processing.",
            "page_number": 2,
            "chunk_index": 0
        }
    }
]

MOCK_CONTEXT = """
--- Page 1 ---

Artificial intelligence (AI) is intelligence demonstrated by machines. Modern AI systems can perform tasks that typically require human intelligence.

Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.

--- Page 2 ---

Deep learning is a type of machine learning that uses neural networks with many layers. It has revolutionized fields like computer vision and natural language processing.
"""

def test_query_classification():
    """Test query type classification functionality"""
    print("\n===== Testing Query Classification =====")
    
    # Initialize response generator
    response_gen = ResponseGenerator()
    
    # Test different query types
    test_queries = [
        "What is artificial intelligence?",
        "Explain how machine learning works",
        "Summarize the main concepts of deep learning",
        "Analyze the impact of AI on society",
        "Is AI consciousness possible?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        query_type = response_gen._classify_query_type(query)
        print(f"Classified as: {query_type.type}")
        print(f"Confidence: {query_type.confidence}")
        print(f"Reasoning: {query_type.reasoning}")


def test_source_extraction():
    """Test source reference extraction from context"""
    print("\n===== Testing Source Extraction =====")
    
    # Initialize response generator
    response_gen = ResponseGenerator()
    
    # Test source extraction
    query = "What is AI and machine learning?"
    print(f"\nQuery: {query}")
    
    sources = response_gen._extract_source_references(MOCK_CONTEXT, query, MOCK_RESULTS)
    
    print(f"Found {len(sources)} sources:")
    for i, source in enumerate(sources, 1):
        print(f"Source {i}:")
        print(f"  Page: {source.page_number}")
        print(f"  Text: {source.text_snippet}")
        print(f"  Relevance: {source.relevance}")


def test_response_generation():
    """Test full response generation"""
    print("\n===== Testing Full Response Generation =====")
    
    # Initialize response generator
    response_gen = ResponseGenerator()
    
    # Test queries
    test_queries = [
        "What is artificial intelligence?",
        "Explain the difference between machine learning and deep learning"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        
        # Generate response
        response = response_gen.generate_response(
            query=query,
            context=MOCK_CONTEXT,
            results=MOCK_RESULTS,
            document_id="test_doc"
        )
        
        # Print response details
        print(f"Answer: {response.answer}")
        print(f"Query type: {response.query_type.type}")
        print(f"Confidence: {response.confidence}")
        print(f"Sources: {len(response.sources)} references")
        
        # Test formatting with citations
        formatted = response.format_with_citations()
        print("\nFormatted response with citations:")
        print(formatted)


def test_fallback_handling():
    """Test fallback response generation"""
    print("\n===== Testing Fallback Handling =====")
    
    # Initialize response generator
    response_gen = ResponseGenerator()
    
    # Test with a query that likely won't match our limited context
    query = "What is the theory of quantum computing?"
    print(f"\nQuery: {query}")
    
    # Generate fallback response
    response = response_gen.generate_fallback_response(query)
    
    # Print response details
    print(f"Answer: {response.answer}")
    print(f"Query type: {response.query_type.type}")
    print(f"Confidence: {response.confidence}")
    print(f"Has sufficient context: {response.has_sufficient_context}")


def test_integrated_query_process():
    """
    Test integrated query processing with an actual vector store
    Note: This requires a properly configured vector store with data
    """
    print("\n===== Testing Integrated Query Processing =====")
    print("Note: This test will be skipped if no vector store is available or properly configured")
    
    try:
        # Initialize vector store
        vector_store = initialize_vector_store()
        
        # Check if vector store has any documents
        has_documents = True  # This would actually check the vector store
        
        if not has_documents:
            print("No documents found in vector store. Skipping integrated test.")
            return
            
        # Initialize query processor
        processor = QueryProcessor(vector_store)
        
        # Process a test query
        query = "What is artificial intelligence?"
        document_id = "test_document"  # This should be a real document ID in your store
        
        print(f"\nQuery: {query}")
        print(f"Document ID: {document_id}")
        
        # Process the query
        result = processor.process_query(query, document_id)
        
        # Print results
        print(f"Found {result['result_count']} relevant chunks")
        print(f"Processing time: {result['processing_time_ms']}ms")
        
        if "response" in result:
            print("\nGenerated response:")
            if isinstance(result["response"], dict) and "formatted_answer" in result["response"]:
                print(result["response"]["formatted_answer"])
            else:
                print(result["response"])
    
    except Exception as e:
        print(f"Error in integrated test: {str(e)}")
        print("Skipping integrated test.")


if __name__ == "__main__":
    print("===================================")
    print("RESPONSE GENERATOR STANDALONE TESTS")
    print("===================================")
    
    # Run all tests
    test_query_classification()
    test_source_extraction()
    test_response_generation()
    test_fallback_handling()
    
    # This test requires a configured vector store with data
    # Uncomment to run the integrated test
    # test_integrated_query_process()
    
    print("\n===================================")
    print("All tests completed!")
    print("===================================") 