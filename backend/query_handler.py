"""
Query processing and response generation module.
This handles:
1. Query embedding generation
2. Similarity search to retrieve relevant chunks
3. Context assembly to combine retrieved chunks
4. Relevance filtering to exclude low-similarity results
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import defaultdict

from embeddings import get_embedding
from vector_store import VectorStore
from pdf_processing import TextChunk

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("query_handler")

# Configuration
MIN_SIMILARITY_THRESHOLD = 0.7  # Minimum similarity score to consider a chunk relevant


class QueryProcessor:
    """Handles query processing and context retrieval."""
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        Initialize the query processor.
        
        Args:
            vector_store: VectorStore instance to use for queries
        """
        self.vector_store = vector_store
        if not self.vector_store:
            # Import here to avoid circular imports
            from vector_store import initialize_vector_store
            self.vector_store = initialize_vector_store()
    
    def process_query(self, query_text: str, document_id: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Process a query against a specific document.
        
        Args:
            query_text: The user's query
            document_id: ID of the document to query against
            top_k: Number of top results to retrieve
            
        Returns:
            Dict containing query results and processed context
        """
        # Start timing the processing
        start_time = time.time()
        
        # Generate query embedding
        logger.info(f"Generating embedding for query: {query_text}")
        query_embedding_time = time.time()
        
        # Create namespace from document_id
        namespace = f"doc_{document_id}"
        
        # Query the vector store
        logger.info(f"Querying document {document_id} with: {query_text}")
        top_k_retrieval = max(top_k * 2, 10)  # Retrieve more results than needed for filtering
        similarity_search_time = time.time()
        results = self.vector_store.query(
            query_text=query_text,
            namespace=namespace,
            top_k=top_k_retrieval,
            include_metadata=True
        )
        search_duration = time.time() - similarity_search_time
        
        # Apply relevance filtering
        filtered_results = self._filter_results_by_relevance(results)
        
        # Combine the retrieved chunks into a coherent context
        context = self._assemble_context(filtered_results[:top_k])
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare the response
        response = {
            "query": query_text,
            "document_id": document_id,
            "results": filtered_results[:top_k],
            "result_count": len(filtered_results[:top_k]),
            "context": context,
            "processing_time_ms": round(processing_time * 1000),
            "search_time_ms": round(search_duration * 1000),
        }
        
        return response
    
    def _filter_results_by_relevance(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter results by relevance score.
        
        Args:
            results: List of query results from vector store
            
        Returns:
            Filtered list of results above the threshold
        """
        if not results:
            return []
            
        # Filter results by similarity score
        filtered_results = [
            result for result in results 
            if result.get("score", 0) >= MIN_SIMILARITY_THRESHOLD
        ]
        
        # If no results meet the threshold but we have results, return the best one
        if not filtered_results and results:
            filtered_results = [max(results, key=lambda x: x.get("score", 0))]
            
        return filtered_results
    
    def _assemble_context(self, results: List[Dict[str, Any]]) -> str:
        """
        Assemble the retrieved chunks into a coherent context.
        
        Args:
            results: List of query results
            
        Returns:
            Assembled context string
        """
        if not results:
            return ""
            
        # Sort results by page number and position to maintain document order
        sorted_results = sorted(
            results,
            key=lambda x: (
                x.get("metadata", {}).get("page_number", 0),
                x.get("metadata", {}).get("chunk_index", 0)
            )
        )
        
        # Group by page for better context assembly
        page_chunks = defaultdict(list)
        for result in sorted_results:
            metadata = result.get("metadata", {})
            page_num = metadata.get("page_number", 0)
            page_chunks[page_num].append(result)
        
        # Assemble the context with page markers
        context_parts = []
        for page_num in sorted(page_chunks.keys()):
            page_results = page_chunks[page_num]
            
            # Sort chunks within the page by position
            page_results.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 0))
            
            # Add page header
            context_parts.append(f"\n--- Page {page_num} ---\n")
            
            # Add text from each chunk
            for result in page_results:
                text = result.get("metadata", {}).get("text", "")
                if text:
                    context_parts.append(text.strip())
        
        # Join all parts with newlines between different sections
        return "\n\n".join(context_parts)


# Create a singleton instance
query_processor = QueryProcessor()


def process_query(query_text: str, document_id: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Convenience function to process a query.
    
    Args:
        query_text: The user's query
        document_id: ID of the document to query against
        top_k: Number of top results to retrieve
        
    Returns:
        Dict containing query results and processed context
    """
    return query_processor.process_query(query_text, document_id, top_k)