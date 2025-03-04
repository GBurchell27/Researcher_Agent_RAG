"""
Manual testing script for the query processor.
This script demonstrates how to use the query processor on an actual document.

Usage:
1. Upload a document using the web interface or API
2. Get the document_id
3. Run this script with the document_id and your test query
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Import our modules
from query_handler import process_query
from vector_store import VectorStore, initialize_vector_store
from document_processor import document_processor

def main():
    """Run a test query against a document."""
    parser = argparse.ArgumentParser(description='Test query processor on a document')
    parser.add_argument('--document_id', required=True, help='The document ID to query')
    parser.add_argument('--query', required=True, help='The query to process')
    parser.add_argument('--top_k', type=int, default=3, help='Number of results to return')
    parser.add_argument('--verbose', action='store_true', help='Print detailed results')
    
    args = parser.parse_args()
    
    # Verify document exists
    try:
        doc_info = document_processor.get_document_info(args.document_id)
        print(f"\nDocument found: {doc_info['filename']}")
        print(f"Document has {doc_info['total_pages']} pages and {doc_info['total_chunks']} chunks\n")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Make sure you've uploaded the document first and have the correct document_id")
        sys.exit(1)
    
    # Process the query
    print(f"Processing query: \"{args.query}\"")
    try:
        results = process_query(args.query, args.document_id, args.top_k)
        
        # Print results summary
        print(f"\nFound {results['result_count']} relevant chunks in {results['processing_time_ms']}ms")
        
        # Print detailed results if verbose
        if args.verbose:
            print("\nTop Results:")
            for i, result in enumerate(results['results']):
                print(f"\n--- Result {i+1} (Score: {result['score']:.2f}) ---")
                print(f"Text: {result['metadata']['text'][:100]}...")
                print(f"Page: {result['metadata']['page_number']}")
                
            print("\nAssembled Context:")
            print(results['context'])
        else:
            # Print just a summary of results
            print("\nTop Results (Scores):")
            for i, result in enumerate(results['results']):
                print(f"  {i+1}. Page {result['metadata']['page_number']} - Score: {result['score']:.2f}")
        
        print("\nTo see the full context, use the --verbose flag")
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        raise

if __name__ == "__main__":
    main() 