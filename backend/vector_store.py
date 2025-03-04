"""
Vector store management using Pinecone.
This module handles:
1. Initializing and connecting to Pinecone
2. Storing embeddings with their metadata
3. Querying vectors by similarity
4. Managing document namespaces and vector operations
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid

from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

from pdf_processing import TextChunk
from embeddings import get_embedding, get_embeddings_for_chunks

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("vector_store")

# Pinecone configuration
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "researcheragentrag")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", "gcp-starter")
EMBEDDING_DIMENSIONS = 1536  # Dimensions for text-embedding-3-small

class VectorStore:
    """Class to handle Pinecone vector database operations."""
    
    def __init__(self, api_key: Optional[str] = None, index_name: Optional[str] = None):
        """
        Initialize the vector store.
        
        Args:
            api_key: Pinecone API key (defaults to environment variable)
            index_name: Name of the Pinecone index to use (defaults to environment variable)
        """
        self.api_key = api_key or PINECONE_API_KEY
        if not self.api_key:
            raise ValueError("Pinecone API key is required. Please provide it as an argument or set the PINECONE_API_KEY environment variable.")
        
        self.index_name = index_name or PINECONE_INDEX_NAME
        if not self.index_name:
            raise ValueError("Pinecone index name is required. Please provide it as an argument or set the PINECONE_INDEX_NAME environment variable.")
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.api_key)
        
        # Check if index exists, create if it doesn't
        try:
            existing_indexes = self.pc.list_indexes().names()
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                
                # For GCP starter tier, we need different parameters
                if PINECONE_ENVIRONMENT == "gcp-starter":
                    # For GCP starter, the ServerlessSpec is not needed
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=EMBEDDING_DIMENSIONS,
                        metric="cosine"
                    )
                else:
                    # For normal serverless, specify cloud and region
                    # Parse environment into cloud and region if needed
                    parts = PINECONE_ENVIRONMENT.split('-')
                    if len(parts) >= 2:
                        cloud = parts[0]
                        region = '-'.join(parts[1:])
                    else:
                        cloud = "aws"  # Default cloud
                        region = "us-west-2"  # Default region
                        
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=EMBEDDING_DIMENSIONS,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud=cloud,
                            region=region
                        )
                    )
                    
                # Short wait for index to initialize
                logger.info(f"Waiting for index to initialize...")
                time.sleep(5)
            else:
                logger.info(f"Index {self.index_name} already exists")
                
            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
            # Get index stats to verify connection
            stats = self.index.describe_index_stats()
            logger.info(f"Index stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error connecting to Pinecone index: {str(e)}")
            raise
    
    def upsert_chunks(self, chunks: List[TextChunk], namespace: Optional[str] = None) -> int:
        """
        Generate embeddings for chunks and upsert them to Pinecone.
        
        Args:
            chunks: List of TextChunk objects to embed and store
            namespace: Optional namespace for organizing vectors
            
        Returns:
            Number of vectors upserted
        """
        if not chunks:
            logger.warning("No chunks provided for upserting.")
            return 0
        
        try:
            # Generate embeddings for all chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            chunk_embeddings = get_embeddings_for_chunks(chunks)
            
            # Prepare vectors for upserting
            vectors = []
            for chunk in chunks:
                # Skip if embedding generation failed
                if chunk.chunk_id not in chunk_embeddings:
                    logger.warning(f"No embedding found for chunk {chunk.chunk_id}")
                    continue
                
                # Prepare metadata
                metadata = {
                    "text": chunk.text,
                    "page": chunk.page_number,
                    "document_id": chunk.document_id,
                    "document_name": chunk.document_name,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add vector to batch
                vectors.append({
                    "id": chunk.chunk_id,
                    "values": chunk_embeddings[chunk.chunk_id],
                    "metadata": metadata
                })
            
            # Upsert vectors in batches of 100
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                
                # Upsert the batch
                upsert_response = self.index.upsert(
                    vectors=batch,
                    namespace=namespace
                )
                
                # Update count and add delay to avoid rate limits
                total_upserted += upsert_response.get('upserted_count', 0)
                if i + batch_size < len(vectors):
                    time.sleep(0.5)  # Small delay between batches
            
            logger.info(f"Successfully upserted {total_upserted} vectors to namespace '{namespace}'")
            return total_upserted
            
        except Exception as e:
            logger.error(f"Error upserting vectors: {str(e)}")
            raise
    
    def query(self, 
              query_text: str, 
              namespace: Optional[str] = None,
              top_k: int = 5,
              include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar chunks.
        
        Args:
            query_text: The query text to find similar chunks for
            namespace: Optional namespace to search in
            top_k: Number of results to return
            include_metadata: Whether to include metadata in the results
            
        Returns:
            List of matching vectors with similarity scores and metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = get_embedding(query_text)
            
            # Perform the query
            query_response = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=include_metadata
            )
            
            # Format and return results
            results = []
            for match in query_response.get('matches', []):
                result = {
                    "id": match.get('id'),
                    "score": match.get('score'),
                    "metadata": match.get('metadata', {})
                }
                results.append(result)
            
            logger.info(f"Query returned {len(results)} results from namespace '{namespace}'")
            return results
            
        except Exception as e:
            logger.error(f"Error querying vectors: {str(e)}")
            raise
    
    def delete_vectors(self, 
                       vector_ids: Optional[List[str]] = None,
                       namespace: Optional[str] = None,
                       delete_all: bool = False,
                       filter: Optional[Dict[str, Any]] = None) -> int:
        """
        Delete vectors from the index.
        
        Args:
            vector_ids: List of vector IDs to delete
            namespace: Optional namespace to delete from
            delete_all: If True, delete all vectors in the namespace
            filter: Optional metadata filter for deletion
            
        Returns:
            Number of vectors deleted
        """
        try:
            if delete_all:
                # Delete all vectors in the namespace
                self.index.delete(delete_all=True, namespace=namespace)
                logger.info(f"Deleted all vectors from namespace '{namespace}'")
                return -1  # Can't determine exact count for delete_all
            
            if vector_ids:
                # Delete specific vectors
                self.index.delete(ids=vector_ids, namespace=namespace)
                logger.info(f"Deleted {len(vector_ids)} vectors from namespace '{namespace}'")
                return len(vector_ids)
            
            if filter:
                # Delete vectors matching a filter
                # Note: This depends on Pinecone version/tier support for metadata filtering
                raise NotImplementedError("Metadata filtering for deletion not supported in this implementation.")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            raise
    
    def get_namespaces(self) -> List[str]:
        """
        Get list of available namespaces.
        
        Returns:
            List of namespace names
        """
        try:
            # Get index stats which contains namespace information
            stats = self.index.describe_index_stats()
            
            # Extract namespace names
            namespaces = list(stats.get('namespaces', {}).keys())
            return namespaces
            
        except Exception as e:
            logger.error(f"Error getting namespaces: {str(e)}")
            raise
    
    def get_namespace_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a namespace.
        
        Args:
            namespace: Optional namespace name (if None, returns stats for all namespaces)
            
        Returns:
            Dictionary with namespace statistics
        """
        try:
            # Get index stats
            stats = self.index.describe_index_stats()
            
            if namespace:
                # Return stats for specific namespace
                return stats.get('namespaces', {}).get(namespace, {})
            else:
                # Return all namespaces stats
                return stats.get('namespaces', {})
            
        except Exception as e:
            logger.error(f"Error getting namespace stats: {str(e)}")
            raise
    
    def create_document_namespace(self, document_id: str) -> str:
        """
        Create a namespace for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Namespace name
        """
        # In Pinecone, namespaces are created implicitly when vectors are added,
        # but we'll define a consistent naming scheme
        namespace = f"doc_{document_id}"
        logger.info(f"Created namespace: {namespace}")
        return namespace


# Utility functions for easy access
def initialize_vector_store() -> VectorStore:
    """
    Initialize the vector store connection.
    
    Returns:
        VectorStore instance
    """
    try:
        return VectorStore()
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        raise


def store_document_chunks(chunks: List[TextChunk], document_id: Optional[str] = None) -> Tuple[str, int]:
    """
    Store document chunks in the vector store.
    
    Args:
        chunks: List of TextChunk objects
        document_id: Optional document identifier (generated if not provided)
        
    Returns:
        Tuple of (document_id, number of chunks stored)
    """
    # Generate document ID if not provided
    if not document_id:
        document_id = str(uuid.uuid4())
    
    # Create vector store
    vector_store = initialize_vector_store()
    
    # Create namespace
    namespace = vector_store.create_document_namespace(document_id)
    
    # Store chunks
    count = vector_store.upsert_chunks(chunks, namespace)
    
    return (document_id, count)


def query_document(query_text: str, document_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Query a specific document.
    
    Args:
        query_text: Query text
        document_id: Document identifier
        top_k: Number of results to return
        
    Returns:
        List of matching chunks with similarity scores
    """
    # Create vector store
    vector_store = initialize_vector_store()
    
    # Construct namespace
    namespace = f"doc_{document_id}"
    
    # Perform query
    results = vector_store.query(query_text, namespace, top_k)
    
    return results


def delete_document(document_id: str) -> bool:
    """
    Delete a document from the vector store.
    
    Args:
        document_id: Document identifier
        
    Returns:
        True if successful
    """
    # Create vector store
    vector_store = initialize_vector_store()
    
    # Construct namespace
    namespace = f"doc_{document_id}"
    
    # Delete all vectors in the namespace
    vector_store.delete_vectors(delete_all=True, namespace=namespace)
    
    return True
