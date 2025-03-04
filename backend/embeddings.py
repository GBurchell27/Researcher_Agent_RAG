# Functions to call OpenAI API for generating embeddings
import os
import time
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import asdict
import numpy as np
from diskcache import Cache
from tqdm import tqdm
import backoff
import openai
from openai import OpenAI
from dotenv import load_dotenv

from pdf_processing import TextChunk

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("embeddings")

# Initialize cache
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
embedding_cache = Cache(os.path.join(CACHE_DIR, "embeddings_cache"))

# Default model for embeddings
DEFAULT_EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-3-small")

class EmbeddingGenerator:
    """Class to handle generation of embeddings using OpenAI API with caching and retry logic."""
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 model: str = DEFAULT_EMBEDDING_MODEL,
                 batch_size: int = 100,
                 max_retries: int = 5,
                 use_cache: bool = True):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: OpenAI API key. If None, it will try to use the OPENAI_API_KEY environment variable
            model: The OpenAI model to use for embeddings
            batch_size: Maximum number of texts to embed in a single API call
            max_retries: Maximum number of retries for failed API calls
            use_cache: Whether to use caching to avoid regenerating embeddings
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please provide it as an argument or set the OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.use_cache = use_cache
        logger.info(f"Initialized EmbeddingGenerator with model {model} and batch size {batch_size}")
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate a cache key for a text and model."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{model}_{text_hash}"
    
    @backoff.on_exception(
        backoff.expo,
        (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError),
        max_tries=5,
        factor=2
    )
    def _get_embedding_single(self, text: str, model: str) -> List[float]:
        """
        Get embedding for a single text with backoff retry logic.
        
        Args:
            text: The text to embed
            model: The model to use
            
        Returns:
            The embedding as a list of floats
        """
        if not text.strip():
            logger.warning("Received empty text for embedding, returning zero vector")
            # Return a zero vector of appropriate dimension
            # Dimensions depend on the model: text-embedding-3-small = 1536, text-embedding-3-large = 3072
            dim = 1536 if "small" in model else 3072
            return [0.0] * dim
        
        response = self.client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Get embedding for a single text with caching.
        
        Args:
            text: The text to embed
            model: The model to use (defaults to self.model)
            
        Returns:
            The embedding as a list of floats
        """
        model = model or self.model
        
        # Check cache if enabled
        if self.use_cache:
            cache_key = self._get_cache_key(text, model)
            cached_embedding = embedding_cache.get(cache_key)
            if cached_embedding is not None:
                return cached_embedding
        
        # Generate embedding
        embedding = self._get_embedding_single(text, model)
        
        # Cache the result if caching is enabled
        if self.use_cache:
            cache_key = self._get_cache_key(text, model)
            embedding_cache[cache_key] = embedding
            
        return embedding
    
    def get_embeddings_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """
        Get embeddings for a list of texts, processing them in batches.
        
        Args:
            texts: List of texts to embed
            model: The model to use (defaults to self.model)
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        model = model or self.model
        embeddings = []
        
        # Process in batches
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i+self.batch_size]
            batch_embeddings = []
            
            # Check cache for each text in the batch
            for text in batch_texts:
                if self.use_cache:
                    cache_key = self._get_cache_key(text, model)
                    cached_embedding = embedding_cache.get(cache_key)
                    if cached_embedding is not None:
                        batch_embeddings.append(cached_embedding)
                        continue
                
                # Generate embedding for texts not in cache
                embedding = self._get_embedding_single(text, model)
                batch_embeddings.append(embedding)
                
                # Cache the result
                if self.use_cache:
                    cache_key = self._get_cache_key(text, model)
                    embedding_cache[cache_key] = embedding
            
            embeddings.extend(batch_embeddings)
            
            # Add a small delay to avoid hitting rate limits
            if i + self.batch_size < len(texts):
                time.sleep(0.1)
                
        return embeddings
    
    def get_embeddings_for_chunks(self, chunks: List[TextChunk], model: Optional[str] = None) -> Dict[str, List[float]]:
        """
        Generate embeddings for a list of TextChunk objects.
        
        Args:
            chunks: List of TextChunk objects
            model: The model to use (defaults to self.model)
            
        Returns:
            Dictionary mapping chunk_id to embedding
        """
        model = model or self.model
        texts = [chunk.text for chunk in chunks]
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        
        embeddings = self.get_embeddings_batch(texts, model)
        
        return dict(zip(chunk_ids, embeddings))

# Utility functions for easy access
def get_embedding(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    """
    Utility function to get embedding for a single text.
    
    Args:
        text: The text to embed
        model: The model to use
        
    Returns:
        The embedding as a list of floats
    """
    generator = EmbeddingGenerator(model=model)
    return generator.get_embedding(text, model)

def get_embeddings_batch(texts: List[str], model: str = DEFAULT_EMBEDDING_MODEL) -> List[List[float]]:
    """
    Utility function to get embeddings for a batch of texts.
    
    Args:
        texts: List of texts to embed
        model: The model to use
        
    Returns:
        List of embeddings
    """
    generator = EmbeddingGenerator(model=model)
    return generator.get_embeddings_batch(texts, model)

def get_embeddings_for_chunks(chunks: List[TextChunk], model: str = DEFAULT_EMBEDDING_MODEL) -> Dict[str, List[float]]:
    """
    Utility function to get embeddings for TextChunk objects.
    
    Args:
        chunks: List of TextChunk objects
        model: The model to use
        
    Returns:
        Dictionary mapping chunk_id to embedding
    """
    generator = EmbeddingGenerator(model=model)
    return generator.get_embeddings_for_chunks(chunks, model)
