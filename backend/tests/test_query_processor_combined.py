"""
Combined test script for the query processor.
This script allows testing with both mock data and real documents.

Usage:
1. Run with '--mock' to test with mock data: python -m tests.test_query_processor_combined --mock
2. Run with '--document_id' to test with a real document: python -m tests.test_query_processor_combined --document_id YOUR_DOC_ID --query "Your query"
"""

import os
import sys
import json
import argparse
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Import our modules
from query_handler import QueryProcessor, process_query
from vector_store import VectorStore, initialize_vector_store
from document_processor import document_processor

# Import the mock test functions
from tests.test_query_processor import create_mock_vector_store, test_filter_results_by_relevance, test_assemble_context, test_process_query

def test_with_mock_data():
    """Run all tests with mock data."""
    print("\n=======================================")
    print("RUNNING TESTS WITH MOCK DATA")
    print("=======================================")
    
    # Run the tests from test_query_processor.py
    test_results = [
        test_filter_results_by_relevance(),
        test_assemble_context(),
        test_process_query()
    ]
    
    # Summary
    print("\n=======================================")
    print("MOCK TEST SUMMARY")
    print("=======================================")
    print(f"Tests passed: {sum(test_results)} / {len(test_results)}")
    
    if all(test_results):
        print("\nAll mock tests PASSED! ✓")
    else:
        print("\nSome mock tests FAILED! ✗")
    
    return all(test_results)

def test_with_real_document(document_id, query_text, top_k=3, verbose=True):
    """Run tests with a real document."""
    print("\n=======================================")
    print("RUNNING TEST WITH REAL DOCUMENT")
    print("=======================================")
    
    # Verify document exists
    try:
        doc_info = document_processor.get_document_info(document_id)
        print(f"\nDocument found: {doc_info['filename']}")
        print(f"Document has {doc_info['total_pages']} pages and {doc_info['total_chunks']} chunks\n")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Make sure you've uploaded the document first and have the correct document_id")
        sys.exit(1)
    
    # Process the query
    print(f"Processing query: \"{query_text}\"")
    try:
        start_time = time.time()
        results = process_query(query_text, document_id, top_k)
        duration = (time.time() - start_time) * 1000
        
        # Print results summary
        print(f"\nFound {results['result_count']} relevant chunks")
        print(f"Query processing time: {results['processing_time_ms']}ms")
        print(f"Total processing time (includes function call overhead): {duration:.2f}ms")
        
        # Print detailed results if verbose
        if verbose:
            print("\nTop Results:")
            for i, result in enumerate(results['results']):
                print(f"\n--- Result {i+1} (Score: {result['score']:.2f}) ---")
                text = result['metadata']['text']
                print(f"Text: {text[:100]}..." if len(text) > 100 else f"Text: {text}")
                print(f"Page: {result['metadata']['page_number']}")
                
            print("\nAssembled Context:")
            print("-" * 80)
            print(results['context'])
            print("-" * 80)
        else:
            # Print just a summary of results
            print("\nTop Results (Scores):")
            for i, result in enumerate(results['results']):
                print(f"  {i+1}. Page {result['metadata']['page_number']} - Score: {result['score']:.2f}")
        
        if not verbose:
            print("\nFor detailed results, add the --verbose flag")
        
        return True
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Parse arguments and run the appropriate test."""
    parser = argparse.ArgumentParser(description='Test query processor with mock or real data')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mock', action='store_true', help='Run tests with mock data')
    group.add_argument('--document_id', help='The document ID to query')
    
    parser.add_argument('--query', default="What are the main topics discussed in this document?", 
                         help='The query to process (for real document testing)')
    parser.add_argument('--top_k', type=int, default=3, help='Number of results to return')
    parser.add_argument('--verbose', action='store_true', help='Print detailed results')
    
    args = parser.parse_args()
    
    # Run the appropriate test
    if args.mock:
        success = test_with_mock_data()
    else:
        # For real document tests, we need a query
        if args.document_id:
            success = test_with_real_document(
                document_id=args.document_id,
                query_text=args.query,
                top_k=args.top_k,
                verbose=args.verbose
            )
    
    # Return exit code based on test results
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    import time  # Import here to avoid circular imports
    main() 