"""
Document Processing Pipeline.

This module integrates:
1. PDF text extraction and chunking
2. Embedding generation for chunks
3. Vector storage in Pinecone
4. Document and session management

It serves as the integration layer between components.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import asdict
import json
import time

from pdf_processing import PDFProcessor, TextChunk
from embeddings import EmbeddingGenerator, get_embedding, get_embeddings_for_chunks
from vector_store import VectorStore, initialize_vector_store, store_document_chunks

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("document_processor")

# Get configuration from environment variables
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

class DocumentProcessor:
    """
    Integration layer that connects PDF processing, embedding generation, and vector storage.
    Manages document tracking and session handling.
    """
    
    def __init__(self):
        """Initialize the document processor with component instances."""
        self.pdf_processor = PDFProcessor(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = initialize_vector_store()
        
        # Track documents and sessions
        self.documents = {}  # Maps document_id to document metadata
        self.sessions = {}   # Maps session_id to list of document_ids
    
    def process_document(self, pdf_bytes: bytes, filename: str, 
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document from PDF bytes: extract, chunk, embed, and store.
        
        Args:
            pdf_bytes: The PDF file as bytes
            filename: The name of the file
            session_id: Optional session identifier for tracking
            
        Returns:
            Dictionary with document details including document_id, statistics, etc.
        """
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 1. Process PDF and extract chunks
        logger.info(f"Processing PDF: {filename}")
        start_time = time.time()
        chunks = self.pdf_processor.process_pdf_bytes(
            pdf_bytes, 
            filename, 
            document_id=document_id
        )
        logger.info(f"Extracted {len(chunks)} chunks in {time.time() - start_time:.2f}s")
        
        # 2. Generate embeddings for chunks
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        start_time = time.time()
        chunk_embeddings = get_embeddings_for_chunks(chunks)
        logger.info(f"Generated embeddings in {time.time() - start_time:.2f}s")
        
        # 3. Store in vector database
        logger.info(f"Storing vectors in Pinecone")
        start_time = time.time()
        namespace = f"doc_{document_id}"
        count = self.vector_store.upsert_chunks(chunks, namespace=namespace)
        logger.info(f"Stored {count} vectors in {time.time() - start_time:.2f}s")
        
        # 4. Track the document
        stats = self.pdf_processor.get_document_statistics(chunks)
        
        document_info = {
            "document_id": document_id,
            "filename": filename,
            "namespace": namespace,
            "chunk_count": len(chunks),
            "statistics": stats,
            "created_at": time.time()
        }
        
        # Store document info
        self.documents[document_id] = document_info
        
        # Add to session tracking
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(document_id)
        
        # Return document details
        result = {
            "document_id": document_id,
            "session_id": session_id,
            "filename": filename,
            "status": "processed",
            "statistics": stats,
            "sample_chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "page": chunk.page_number + 1,  # Convert to 1-indexed for display
                    "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text
                }
                for chunk in chunks[:3]  # Show first 3 chunks as samples
            ]
        }
        
        return result
    
    def query_document(self, query: str, document_id: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Query a document by ID and return relevant chunks.
        
        Args:
            query: The query string
            document_id: The document ID to query
            top_k: Number of results to return
            
        Returns:
            Dictionary with query results
        """
        # Check if document exists
        if document_id not in self.documents:
            raise ValueError(f"Document not found: {document_id}")
            
        document_info = self.documents[document_id]
        namespace = document_info.get("namespace") or f"doc_{document_id}"
        
        # Generate embedding for query
        query_embedding = get_embedding(query)
        
        # Search vector store
        start_time = time.time()
        results = self.vector_store.query(query, namespace=namespace, top_k=top_k)
        query_time = time.time() - start_time
        
        return {
            "document_id": document_id,
            "filename": document_info.get("filename"),
            "query": query,
            "results": results,
            "result_count": len(results),
            "query_time_ms": round(query_time * 1000),
        }
    
    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """
        Get information about a document.
        
        Args:
            document_id: The document ID
            
        Returns:
            Dictionary with document metadata
        """
        if document_id not in self.documents:
            raise ValueError(f"Document not found: {document_id}")
            
        return self.documents[document_id]
    
    def get_session_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents associated with a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of document metadata dictionaries
        """
        if session_id not in self.sessions:
            return []
            
        return [
            self.documents[doc_id] 
            for doc_id in self.sessions[session_id]
            if doc_id in self.documents
        ]
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            document_id: The document ID to delete
            
        Returns:
            True if successful
        """
        if document_id not in self.documents:
            raise ValueError(f"Document not found: {document_id}")
            
        document_info = self.documents[document_id]
        namespace = document_info.get("namespace") or f"doc_{document_id}"
        
        # Delete vectors from store
        self.vector_store.delete_vectors(delete_all=True, namespace=namespace)
        
        # Remove from document tracking
        del self.documents[document_id]
        
        # Remove from all sessions
        for session_id, doc_ids in self.sessions.items():
            if document_id in doc_ids:
                self.sessions[session_id].remove(document_id)
        
        return True
    
    def clear_session(self, session_id: str) -> int:
        """
        Clear all documents associated with a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Number of documents deleted
        """
        if session_id not in self.sessions:
            return 0
            
        document_ids = list(self.sessions[session_id])
        count = 0
        
        for document_id in document_ids:
            try:
                self.delete_document(document_id)
                count += 1
            except Exception as e:
                logger.error(f"Error deleting document {document_id}: {str(e)}")
        
        # Clear session tracking
        self.sessions[session_id] = []
        
        return count

# Create a singleton instance
document_processor = DocumentProcessor()

# Utility functions for easier access
def process_document(pdf_bytes: bytes, filename: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a document using the singleton document processor.
    
    Args:
        pdf_bytes: PDF content as bytes
        filename: Original filename
        session_id: Optional session identifier
        
    Returns:
        Document processing results
    """
    return document_processor.process_document(pdf_bytes, filename, session_id)

def query_document(query: str, document_id: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Query a document using the singleton document processor.
    
    Args:
        query: The query text
        document_id: Document identifier
        top_k: Number of results to return
        
    Returns:
        Query results
    """
    return document_processor.query_document(query, document_id, top_k) 