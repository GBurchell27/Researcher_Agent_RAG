"""
Tests for the embeddings.py module.

This file can be run directly:
    python backend/tests/test_embeddings.py
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables from .env file
project_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path)

import numpy as np
# Import modules but use different names to avoid import issues with patching
import backend.embeddings as embeddings_module
from backend.embeddings import (
    EmbeddingGenerator, 
    get_embedding, 
    get_embeddings_batch, 
    get_embeddings_for_chunks,
    DEFAULT_EMBEDDING_MODEL
)
from backend.pdf_processing import TextChunk


class TestEmbeddings(unittest.TestCase):
    """Test cases for the embeddings module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for the cache
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('backend.embeddings.CACHE_DIR', self.temp_dir)
        self.patcher.start()
        
        # Mock OpenAI API key for testing
        self.original_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.original_api_key:
            os.environ["OPENAI_API_KEY"] = "mock-api-key"
            self.using_mock_key = True
        else:
            self.using_mock_key = False
        
        # Sample text for testing
        self.sample_text = "This is a sample text for embedding generation."
        self.sample_texts = [
            "This is the first sample text.",
            "This is the second sample text.",
            "This is the third sample text."
        ]
        
        # Sample text chunks
        self.sample_chunks = [
            TextChunk(
                chunk_id="chunk1",
                text="This is chunk 1",
                page_number=1,
                document_id="doc1",
                document_name="Test Document"
            ),
            TextChunk(
                chunk_id="chunk2",
                text="This is chunk 2",
                page_number=1,
                document_id="doc1",
                document_name="Test Document"
            )
        ]
        
        # Mock embedding
        self.mock_embedding = [0.1] * 1536  # text-embedding-3-small has 1536 dimensions
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)
        
        # Restore original API key state
        if self.using_mock_key:
            del os.environ["OPENAI_API_KEY"]
    
    # Test initialization without making API calls
    def test_embedding_generator_init(self):
        """Test initialization of EmbeddingGenerator."""
        # Test with default parameters
        generator = EmbeddingGenerator()
        self.assertEqual(generator.model, DEFAULT_EMBEDDING_MODEL)
        self.assertEqual(generator.batch_size, 100)
        self.assertEqual(generator.max_retries, 5)
        self.assertTrue(generator.use_cache)
        
        # Test with custom parameters
        generator = EmbeddingGenerator(
            api_key="custom-key",
            model="text-embedding-3-large",
            batch_size=50,
            max_retries=3,
            use_cache=False
        )
        self.assertEqual(generator.api_key, "custom-key")
        self.assertEqual(generator.model, "text-embedding-3-large")
        self.assertEqual(generator.batch_size, 50)
        self.assertEqual(generator.max_retries, 3)
        self.assertFalse(generator.use_cache)
    
    def test_get_embedding_single(self):
        """Test getting a single embedding."""
        # Create a mock for the embeddings.create method
        mock_embedding_response = MagicMock()
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = self.mock_embedding
        mock_embedding_response.data = [mock_embedding_data]
        
        # Create a mock for the OpenAI client
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        # Use the patch to replace the actual OpenAI client with our mock
        with patch.object(EmbeddingGenerator, '__init__', return_value=None) as mock_init:
            with patch.object(EmbeddingGenerator, 'client', mock_client, create=True):
                # Create generator and manually set required attributes
                generator = EmbeddingGenerator()
                generator.model = DEFAULT_EMBEDDING_MODEL
                generator.use_cache = False
                generator.batch_size = 100
                
                # Test the method
                embedding = generator._get_embedding_single(self.sample_text, DEFAULT_EMBEDDING_MODEL)
                
                # Assertions
                self.assertEqual(len(embedding), 1536)
                self.assertEqual(embedding, self.mock_embedding)
                mock_client.embeddings.create.assert_called_once_with(
                    model=DEFAULT_EMBEDDING_MODEL,
                    input=self.sample_text
                )
    
    def test_get_embedding_with_caching(self):
        """Test that caching works for embeddings."""
        # Create a mock for the embeddings.create method
        mock_embedding_response = MagicMock()
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = self.mock_embedding
        mock_embedding_response.data = [mock_embedding_data]
        
        # Create a mock for the OpenAI client
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        # Create a test cache for this test
        test_cache = {}
        
        # Patch the necessary components
        with patch.object(EmbeddingGenerator, '__init__', return_value=None) as mock_init:
            with patch.object(EmbeddingGenerator, 'client', mock_client, create=True):
                with patch.dict(embeddings_module.embedding_cache, test_cache, clear=True):
                    with patch.object(EmbeddingGenerator, '_get_cache_key', return_value='test_key'):
                        # Create generator and manually set required attributes
                        generator = EmbeddingGenerator()
                        generator.model = DEFAULT_EMBEDDING_MODEL
                        generator.use_cache = True
                        
                        # First call should hit the API
                        embedding1 = generator.get_embedding(self.sample_text)
                        self.assertEqual(embedding1, self.mock_embedding)
                        mock_client.embeddings.create.assert_called_once()
                        
                        # Reset mock to verify no more calls
                        mock_client.embeddings.create.reset_mock()
                        
                        # Second call with same text should use cache
                        embedding2 = generator.get_embedding(self.sample_text)
                        self.assertEqual(embedding2, self.mock_embedding)
                        mock_client.embeddings.create.assert_not_called()
    
    def test_get_embeddings_batch(self):
        """Test batch processing of embeddings."""
        # Create a mock for the embeddings.create method
        mock_embedding_response = MagicMock()
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = self.mock_embedding
        mock_embedding_response.data = [mock_embedding_data]
        
        # Create a mock for the OpenAI client
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        # Patch the necessary components
        with patch.object(EmbeddingGenerator, '__init__', return_value=None) as mock_init:
            with patch.object(EmbeddingGenerator, 'client', mock_client, create=True):
                with patch('time.sleep', return_value=None):  # Skip sleeps
                    with patch('tqdm.tqdm', return_value=range(1)):  # Skip progress bar
                        # Create generator and manually set required attributes
                        generator = EmbeddingGenerator()
                        generator.model = DEFAULT_EMBEDDING_MODEL
                        generator.use_cache = False
                        generator.batch_size = 2
                        
                        # Test method
                        embeddings = generator.get_embeddings_batch(self.sample_texts)
                        
                        # Assertions
                        self.assertEqual(len(embeddings), 3)
                        for embedding in embeddings:
                            self.assertEqual(embedding, self.mock_embedding)
                        
                        # Should be called once for each text
                        self.assertEqual(mock_client.embeddings.create.call_count, 3)
    
    def test_get_embeddings_for_chunks(self):
        """Test getting embeddings for TextChunk objects."""
        # Patch the batch embedding method to return known values
        with patch.object(
            EmbeddingGenerator, 
            'get_embeddings_batch', 
            return_value=[self.mock_embedding, self.mock_embedding]
        ) as mock_batch:
            # Create generator and test
            generator = EmbeddingGenerator()
            chunk_embeddings = generator.get_embeddings_for_chunks(self.sample_chunks)
            
            # Assertions
            self.assertEqual(len(chunk_embeddings), 2)
            self.assertIn("chunk1", chunk_embeddings)
            self.assertIn("chunk2", chunk_embeddings)
            self.assertEqual(chunk_embeddings["chunk1"], self.mock_embedding)
            self.assertEqual(chunk_embeddings["chunk2"], self.mock_embedding)
            
            # Verify batch was called with correct texts
            mock_batch.assert_called_once_with(
                ["This is chunk 1", "This is chunk 2"], 
                DEFAULT_EMBEDDING_MODEL
            )
    
    def test_empty_text_handling(self):
        """Test handling of empty text."""
        # Create a mock for the OpenAI client
        mock_client = MagicMock()
        
        # Patch the client
        with patch.object(EmbeddingGenerator, '__init__', return_value=None) as mock_init:
            with patch.object(EmbeddingGenerator, 'client', mock_client, create=True):
                # Create generator and manually set required attributes
                generator = EmbeddingGenerator()
                generator.use_cache = False
                
                # Test the method
                embedding = generator._get_embedding_single("", DEFAULT_EMBEDDING_MODEL)
                
                # Assertions - should return zero vector
                self.assertEqual(len(embedding), 1536)
                self.assertEqual(embedding, [0.0] * 1536)
                
                # API should not be called for empty text
                mock_client.embeddings.create.assert_not_called()
    
    def test_utility_functions(self):
        """Test utility functions."""
        # Mock the EmbeddingGenerator class
        with patch('backend.embeddings.EmbeddingGenerator') as mock_generator_class:
            # Setup mock generator instance
            mock_generator = MagicMock()
            mock_generator.get_embedding.return_value = self.mock_embedding
            mock_generator.get_embeddings_batch.return_value = [self.mock_embedding] * 3
            mock_generator.get_embeddings_for_chunks.return_value = {
                "chunk1": self.mock_embedding,
                "chunk2": self.mock_embedding
            }
            mock_generator_class.return_value = mock_generator
            
            # Test utility functions
            embedding = get_embedding(self.sample_text)
            embeddings = get_embeddings_batch(self.sample_texts)
            chunk_embeddings = get_embeddings_for_chunks(self.sample_chunks)
            
            # Assertions
            self.assertEqual(embedding, self.mock_embedding)
            self.assertEqual(len(embeddings), 3)
            self.assertEqual(len(chunk_embeddings), 2)


def run_tests():
    """Run all the tests and print a summary."""
    print("\n=== Running Embeddings Unit Tests ===\n")
    
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add all the test methods
    test_loader = unittest.TestLoader()
    suite.addTest(test_loader.loadTestsFromTestCase(TestEmbeddings))
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(suite)
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. See details above.")


if __name__ == "__main__":
    run_tests()
