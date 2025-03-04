"""
A minimal script to quickly test if the OpenAI embeddings functionality is working.
This is useful for a quick sanity check without running the full test suite.

Usage:
    python -m backend.tests.simple_embedding_test
"""
import os
import time
import sys
from pprint import pprint
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file
project_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path)

from backend.embeddings import get_embedding


def main():
    """Run a simple embedding test."""
    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key with:")
        print("    export OPENAI_API_KEY='your-api-key'")
        print("Or check your .env file in the project root directory.")
        return
    
    print(f"Using API key: {os.environ.get('OPENAI_API_KEY')[:10]}...")
    
    # Simple test text
    text = "Testing OpenAI embeddings API connection."
    
    print(f"Generating embedding for: '{text}'")
    start_time = time.time()
    
    try:
        # Get embedding
        embedding = get_embedding(text)
        duration = time.time() - start_time
        
        # Output results
        print(f"✅ Success! Embedding generated in {duration:.2f} seconds")
        print(f"Embedding dimensions: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        
        # Test a second call to see caching in action
        print("\nTesting cache (second call should be faster)...")
        start_time = time.time()
        _ = get_embedding(text)
        cache_duration = time.time() - start_time
        print(f"Cached result retrieved in {cache_duration:.2f} seconds")
        print(f"Speed improvement: {duration/cache_duration:.1f}x faster")
        
    except Exception as e:
        print(f"❌ Error generating embedding: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 