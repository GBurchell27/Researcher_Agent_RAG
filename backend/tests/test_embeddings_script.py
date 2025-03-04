"""
Simple script to test the embeddings functionality in a real environment.

Usage:
    python -m backend.tests.test_embeddings_script

Make sure you have your OpenAI API key set in the environment variable OPENAI_API_KEY.
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

from backend.embeddings import (
    EmbeddingGenerator, 
    get_embedding, 
    get_embeddings_batch, 
    get_embeddings_for_chunks
)
from backend.pdf_processing import TextChunk


def test_single_embedding():
    """Test generating a single embedding."""
    print("\n=== Testing Single Embedding Generation ===")
    text = "This is a test of the OpenAI embedding API."
    
    print(f"Generating embedding for: '{text}'")
    start_time = time.time()
    embedding = get_embedding(text)
    duration = time.time() - start_time
    
    print(f"Embedding generated in {duration:.2f} seconds")
    print(f"Embedding dimensions: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    
    # Test caching
    print("\nTesting cache (should be faster)...")
    start_time = time.time()
    embedding2 = get_embedding(text)
    duration = time.time() - start_time
    
    print(f"Cached embedding retrieved in {duration:.2f} seconds")
    print(f"Embeddings are identical: {embedding == embedding2}")


def test_batch_embedding():
    """Test generating multiple embeddings in batch."""
    print("\n=== Testing Batch Embedding Generation ===")
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence.",
        "Python is a high-level, interpreted programming language."
    ]
    
    print(f"Generating embeddings for {len(texts)} texts")
    start_time = time.time()
    embeddings = get_embeddings_batch(texts)
    duration = time.time() - start_time
    
    print(f"Embeddings generated in {duration:.2f} seconds")
    print(f"Number of embeddings: {len(embeddings)}")
    for i, emb in enumerate(embeddings):
        print(f"Embedding {i+1} dimensions: {len(emb)}")


def test_chunk_embeddings():
    """Test generating embeddings for TextChunk objects."""
    print("\n=== Testing Text Chunk Embedding Generation ===")
    chunks = [
        TextChunk(
            chunk_id="chunk1",
            text="This is the content of the first chunk.",
            page_number=1,
            document_id="doc123",
            document_name="Test Document"
        ),
        TextChunk(
            chunk_id="chunk2",
            text="This is the content of the second chunk.",
            page_number=1,
            document_id="doc123",
            document_name="Test Document"
        )
    ]
    
    print(f"Generating embeddings for {len(chunks)} text chunks")
    start_time = time.time()
    chunk_embeddings = get_embeddings_for_chunks(chunks)
    duration = time.time() - start_time
    
    print(f"Chunk embeddings generated in {duration:.2f} seconds")
    print(f"Number of chunk embeddings: {len(chunk_embeddings)}")
    print(f"Chunk IDs with embeddings: {list(chunk_embeddings.keys())}")


def test_custom_embedding_generator():
    """Test creating a custom EmbeddingGenerator with specific settings."""
    print("\n=== Testing Custom Embedding Generator ===")
    generator = EmbeddingGenerator(
        model="text-embedding-3-small",
        batch_size=10,
        use_cache=True
    )
    
    print(f"Created custom generator with model: {generator.model}")
    text = "Testing custom embedding generator settings."
    
    print(f"Generating embedding with custom generator")
    embedding = generator.get_embedding(text)
    
    print(f"Embedding dimensions: {len(embedding)}")
    print(f"Using cache: {generator.use_cache}")


def check_environment():
    """Check if the environment is properly set up."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key with:")
        print("    export OPENAI_API_KEY='your-api-key'")
        print("Or check your .env file in the project root directory.")
        return False
    
    print(f"Using API key: {os.environ.get('OPENAI_API_KEY')[:10]}...")
    return True


def main():
    """Run all tests."""
    if not check_environment():
        return
    
    print("=== OpenAI Embeddings Test Script ===")
    print("This script will test various functionalities of the embeddings module.")
    
    try:
        test_single_embedding()
        test_batch_embedding()
        test_chunk_embeddings()
        test_custom_embedding_generator()
        
        print("\n=== All Tests Completed Successfully ===")
    except Exception as e:
        print(f"\nERROR: An exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 