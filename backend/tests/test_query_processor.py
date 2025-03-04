"""
Direct test script for the query processor module.
This script tests the QueryProcessor functionality with mock data without requiring unittest.
"""

import sys
import os
import json
from unittest.mock import MagicMock

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from query_handler import QueryProcessor, process_query

def create_mock_vector_store():
    """Create a mock vector store for testing."""
    # Create a mock VectorStore instance
    mock_vector_store = MagicMock()
    
    # Create mock query results
    mock_results = [
        {
            "id": "chunk_1",
            "score": 0.92,
            "metadata": {
                "text": "This is the first chunk of text. It contains important information about the topic at hand and should be highly relevant to queries about main concepts.",
                "page_number": 1,
                "chunk_index": 0,
                "document_id": "doc123"
            }
        },
        {
            "id": "chunk_2",
            "score": 0.85,
            "metadata": {
                "text": "This is the second chunk of text. It elaborates on the previous information and provides additional context for the reader to understand the subject matter.",
                "page_number": 1,
                "chunk_index": 1,
                "document_id": "doc123"
            }
        },
        {
            "id": "chunk_3",
            "score": 0.75,
            "metadata": {
                "text": "This is text from page 2. It introduces new concepts that build upon the foundation established in the previous page.",
                "page_number": 2,
                "chunk_index": 0,
                "document_id": "doc123"
            }
        },
        {
            "id": "chunk_4",
            "score": 0.65,
            "metadata": {
                "text": "This is less relevant text from page 3. It contains tangentially related information that might not be directly applicable to the main topic.",
                "page_number": 3,
                "chunk_index": 0,
                "document_id": "doc123"
            }
        }
    ]
    
    # Configure the mock to return our test results
    mock_vector_store.query.return_value = mock_results
    
    return mock_vector_store, mock_results

def test_filter_results_by_relevance():
    """Test the relevance filtering logic."""
    print("\n===== TESTING RELEVANCE FILTERING =====")
    
    # Create query processor with mock data
    mock_vector_store, mock_results = create_mock_vector_store()
    query_processor = QueryProcessor(vector_store=mock_vector_store)
    
    # Filter results with our test threshold (0.7)
    filtered_results = query_processor._filter_results_by_relevance(mock_results)
    
    # Display results
    print(f"Original result count: {len(mock_results)}")
    print(f"Filtered result count: {len(filtered_results)}")
    print("\nScores in original results:")
    for result in mock_results:
        score = result.get("score", 0)
        print(f" - {score:.2f}" + (" (filtered out)" if score < 0.7 else ""))
    
    # Test with empty results
    empty_filtered = query_processor._filter_results_by_relevance([])
    print(f"\nEmpty results test: {len(empty_filtered)} (expected 0)")
    
    # Test when all results are below threshold
    low_results = [{"id": "low", "score": 0.5}]
    low_filtered = query_processor._filter_results_by_relevance(low_results)
    print(f"Below threshold test: {len(low_filtered)} (expected 1 - best result still kept)")
    
    # Test success
    success = len(filtered_results) == 3  # We expect 3 results above threshold (0.7)
    print(f"\nTest {'PASSED' if success else 'FAILED'}: Expected 3 results above threshold")
    
    return success

def test_assemble_context():
    """Test the context assembly logic."""
    print("\n===== TESTING CONTEXT ASSEMBLY =====")
    
    # Create query processor with mock data
    mock_vector_store, mock_results = create_mock_vector_store()
    query_processor = QueryProcessor(vector_store=mock_vector_store)
    
    # Assemble context from our mock results (using first 3 results)
    context = query_processor._assemble_context(mock_results[:3])
    
    # Display context
    print("Assembled context:")
    print("-" * 50)
    print(context)
    print("-" * 50)
    
    # Check that the context contains expected text and page markers
    checks = [
        ("Page 1", "Page 1 marker"),
        ("Page 2", "Page 2 marker"),
        ("first chunk of text", "First chunk content"),
        ("second chunk of text", "Second chunk content")
    ]
    
    print("\nChecking content:")
    success = True
    for text, label in checks:
        found = text in context
        print(f" - {label}: {'✓' if found else '✗'}")
        if not found:
            success = False
    
    # Test with empty results
    empty_context = query_processor._assemble_context([])
    print(f"\nEmpty context test: {'✓' if empty_context == '' else '✗'} (expected empty string)")
    
    # Test success
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    
    return success

def test_process_query():
    """Test the main process_query method."""
    print("\n===== TESTING QUERY PROCESSING =====")
    
    # Create query processor with mock data
    mock_vector_store, mock_results = create_mock_vector_store()
    query_processor = QueryProcessor(vector_store=mock_vector_store)
    
    # Process a test query
    query_text = "test query about main concepts"
    document_id = "doc123"
    top_k = 2
    
    print(f"Query: '{query_text}'")
    print(f"Document ID: {document_id}")
    print(f"Top K: {top_k}")
    
    # Run the query
    results = query_processor.process_query(query_text, document_id, top_k)
    
    # Display results
    print("\nQuery Results:")
    print(f" - Found {results['result_count']} results")
    print(f" - Processing time: {results['processing_time_ms']}ms")
    
    print("\nTop results:")
    for i, result in enumerate(results['results']):
        print(f"\n--- Result {i+1} (Score: {result['score']:.2f}) ---")
        print(f"Text: {result['metadata']['text'][:50]}...")
        print(f"Page: {result['metadata']['page_number']}")
    
    # Verify the structure of results
    print("\nChecking result structure:")
    checks = [
        ("query" in results, "Query field"),
        ("document_id" in results, "Document ID field"),
        ("results" in results, "Results array"),
        ("context" in results, "Context field"),
        (len(results["results"]) == top_k, f"Results count matches top_k ({top_k})")
    ]
    
    success = True
    for check, label in checks:
        print(f" - {label}: {'✓' if check else '✗'}")
        if not check:
            success = False
    
    # Test success
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    
    return success

def main():
    """Run all query processor tests."""
    print("=======================================")
    print("QUERY PROCESSOR DIRECT TESTS")
    print("=======================================")
    
    test_results = [
        test_filter_results_by_relevance(),
        test_assemble_context(),
        test_process_query()
    ]
    
    # Summary
    print("\n=======================================")
    print("TEST SUMMARY")
    print("=======================================")
    print(f"Tests passed: {sum(test_results)} / {len(test_results)}")
    
    if all(test_results):
        print("\nAll tests PASSED! ✓")
    else:
        print("\nSome tests FAILED! ✗")
    
    return all(test_results)

if __name__ == "__main__":
    success = main()
    # Return exit code based on test results (for automation)
    sys.exit(0 if success else 1) 