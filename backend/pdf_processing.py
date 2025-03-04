"""
Functions for text extraction and processing from PDFs using PyMuPDF (fitz).
This module handles:
1. Extracting raw text from PDF files
2. Chunking text with configurable size and overlap
3. Maintaining metadata about the chunks (page numbers, positions)
4. Basic validation and error handling
"""

import os
import fitz  # PyMuPDF
import uuid
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class TextChunk:
    """Data class to store text chunks and their metadata."""
    chunk_id: str
    text: str
    page_number: int
    document_id: str
    document_name: str
    start_char_idx: Optional[int] = None
    end_char_idx: Optional[int] = None


class PDFProcessor:
    """Class to handle PDF processing operations."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the PDF processor with configuration.
        
        Args:
            chunk_size: Maximum number of characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[int, str]:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping page numbers (0-indexed) to text content
        
        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            ValueError: If the file is not a valid PDF
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not pdf_path.lower().endswith('.pdf'):
            raise ValueError(f"File is not a PDF: {pdf_path}")
        
        try:
            # Open the PDF
            pdf_document = fitz.open(pdf_path)
            
            # Extract text from each page
            page_text = {}
            for page_num, page in enumerate(pdf_document):
                text = page.get_text()
                # Only add pages that have actual text content
                if text.strip():
                    page_text[page_num] = text
            
            # Close the document
            pdf_document.close()
            
            return page_text
            
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    def extract_text_from_bytes(self, pdf_bytes: bytes, filename: str) -> Dict[int, str]:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_bytes: PDF content as bytes
            filename: Original filename for reference
            
        Returns:
            Dictionary mapping page numbers (0-indexed) to text content
        
        Raises:
            ValueError: If the bytes cannot be parsed as a PDF
        """
        try:
            # Open the PDF from memory
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Extract text from each page
            page_text = {}
            for page_num, page in enumerate(pdf_document):
                text = page.get_text()
                # Only add pages that have actual text content
                if text.strip():
                    page_text[page_num] = text
            
            # Close the document
            pdf_document.close()
            
            return page_text
            
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF bytes: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing excessive whitespace and handling common issues.
        
        Args:
            text: Raw text extracted from PDF
            
        Returns:
            Cleaned text
        """
        # Replace multiple newlines with a single one
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace multiple spaces with a single one
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove form feed characters
        text = text.replace('\f', '')
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def chunk_text(self, text: str, page_number: int, 
                   document_id: str, document_name: str) -> List[TextChunk]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to be chunked
            page_number: Page number where the text is from
            document_id: Unique identifier for the document
            document_name: Name of the document
            
        Returns:
            List of TextChunk objects
        """
        cleaned_text = self.clean_text(text)
        
        # If text is shorter than chunk size, return it as a single chunk
        if len(cleaned_text) <= self.chunk_size:
            return [TextChunk(
                chunk_id=str(uuid.uuid4()),
                text=cleaned_text,
                page_number=page_number,
                document_id=document_id,
                document_name=document_name,
                start_char_idx=0,
                end_char_idx=len(cleaned_text)
            )]
        
        chunks = []
        start = 0
        
        while start < len(cleaned_text):
            # Calculate end position with respect to chunk size
            end = start + self.chunk_size
            
            # If we're not at the end of the text, try to find a good break point
            if end < len(cleaned_text):
                # Try to break at paragraph, then sentence, then word boundary
                paragraph_break = cleaned_text.rfind('\n\n', start, end)
                if paragraph_break != -1 and paragraph_break > start + self.chunk_size // 2:
                    end = paragraph_break + 2  # Include the newlines
                else:
                    # Look for sentence boundary (., !, ?)
                    sentence_break = max(
                        cleaned_text.rfind('. ', start, end),
                        cleaned_text.rfind('! ', start, end),
                        cleaned_text.rfind('? ', start, end)
                    )
                    if sentence_break != -1 and sentence_break > start + self.chunk_size // 2:
                        end = sentence_break + 2  # Include the period and space
                    else:
                        # Fall back to word boundary
                        space_pos = cleaned_text.rfind(' ', start, end)
                        if space_pos != -1 and space_pos > start + self.chunk_size // 4:
                            end = space_pos + 1  # Include the space
            
            # Create a chunk
            chunk_text = cleaned_text[start:end].strip()
            if chunk_text:  # Only add non-empty chunks
                chunks.append(TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    page_number=page_number,
                    document_id=document_id,
                    document_name=document_name,
                    start_char_idx=start,
                    end_char_idx=end
                ))
            
            # Move start position for next chunk, considering overlap
            start = end - self.chunk_overlap
            
            # Ensure we're making progress
            if start <= 0 or start >= len(cleaned_text):
                break
        
        return chunks
    
    def process_pdf(self, pdf_path: str, document_id: str = None) -> List[TextChunk]:
        """
        Process a PDF file: extract text and create chunks.
        
        Args:
            pdf_path: Path to the PDF file
            document_id: Optional unique identifier for the document
                        (will be generated if not provided)
                        
        Returns:
            List of TextChunk objects containing the processed text
        """
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        document_name = os.path.basename(pdf_path)
        
        # Extract text from PDF
        page_text = self.extract_text_from_pdf(pdf_path)
        
        # Process each page and create chunks
        all_chunks = []
        for page_num, text in page_text.items():
            page_chunks = self.chunk_text(
                text, 
                page_number=page_num,
                document_id=document_id,
                document_name=document_name
            )
            all_chunks.extend(page_chunks)
        
        return all_chunks
    
    def process_pdf_bytes(self, pdf_bytes: bytes, filename: str, 
                          document_id: str = None) -> List[TextChunk]:
        """
        Process PDF bytes: extract text and create chunks.
        
        Args:
            pdf_bytes: PDF content as bytes
            filename: Original filename for reference
            document_id: Optional unique identifier for the document
                        (will be generated if not provided)
                        
        Returns:
            List of TextChunk objects containing the processed text
        """
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Extract text from PDF bytes
        page_text = self.extract_text_from_bytes(pdf_bytes, filename)
        
        # Process each page and create chunks
        all_chunks = []
        for page_num, text in page_text.items():
            page_chunks = self.chunk_text(
                text, 
                page_number=page_num,
                document_id=document_id,
                document_name=filename
            )
            all_chunks.extend(page_chunks)
        
        return all_chunks
    
    def get_document_statistics(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """
        Calculate statistics about the processed document.
        
        Args:
            chunks: List of TextChunk objects from a document
            
        Returns:
            Dictionary with statistics (total pages, chunks, tokens, etc.)
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_pages": 0,
                "total_characters": 0,
                "estimated_tokens": 0
            }
        
        # Count unique pages
        unique_pages = len(set(chunk.page_number for chunk in chunks))
        
        # Count total characters
        total_chars = sum(len(chunk.text) for chunk in chunks)
        
        # Rough estimate of tokens (assuming ~4 chars per token on average)
        estimated_tokens = total_chars // 4
        
        return {
            "total_chunks": len(chunks),
            "total_pages": unique_pages,
            "total_characters": total_chars,
            "estimated_tokens": estimated_tokens,
            "document_name": chunks[0].document_name if chunks else None,
            "document_id": chunks[0].document_id if chunks else None
        }


# Default instance with standard configuration
default_processor = PDFProcessor()


def extract_text_from_pdf(pdf_path: str) -> Dict[int, str]:
    """
    Convenience function to extract text from a PDF file using the default processor.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary mapping page numbers to text content
    """
    return default_processor.extract_text_from_pdf(pdf_path)


def process_pdf(pdf_path: str, document_id: str = None) -> List[TextChunk]:
    """
    Convenience function to process a PDF file using the default processor.
    
    Args:
        pdf_path: Path to the PDF file
        document_id: Optional unique identifier for the document
        
    Returns:
        List of TextChunk objects
    """
    return default_processor.process_pdf(pdf_path, document_id)


def process_pdf_bytes(pdf_bytes: bytes, filename: str, document_id: str = None) -> List[TextChunk]:
    """
    Convenience function to process PDF bytes using the default processor.
    
    Args:
        pdf_bytes: PDF content as bytes
        filename: Original filename for reference
        document_id: Optional unique identifier for the document
        
    Returns:
        List of TextChunk objects
    """
    return default_processor.process_pdf_bytes(pdf_bytes, filename, document_id)