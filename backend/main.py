import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any, List, Optional
import json
import tempfile
import uuid
import logging
from pydantic import BaseModel

# Import our modules
from pdf_processing import process_pdf_bytes, PDFProcessor
from document_processor import document_processor, process_document
from query_handler import process_query
from response_generator import generate_response, response_generator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Create FastAPI app
app = FastAPI(
    title="Researcher Agent Chat App",
    description="A FastAPI application for research agent chat",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add this model definition before your endpoint
class QueryRequest(BaseModel):
    """Request model for document queries"""
    query: str
    document_id: str
    top_k: int = 5

@app.get("/")
async def root():
    return {"message": "Welcome to the Researcher Agent Chat App API"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API is running normally"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), session_id: Optional[str] = None):
    """
    Endpoint for uploading a PDF file
    
    Args:
        file: The PDF file to upload
        session_id: Optional session identifier for tracking related documents
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read the uploaded file content
        pdf_content = await file.read()
        
        # Process the document (extract, chunk, embed, store)
        result = process_document(pdf_content, file.filename, session_id)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/query")
async def query_document(query_request: QueryRequest):
    """
    Process a query against a document and return results.
    """
    try:
        # Process the query
        results = process_query(
            query_text=query_request.query,
            document_id=query_request.document_id,
            top_k=query_request.top_k
        )
        
        # Extract the formatted answer for the frontend
        if "response" in results and "formatted_answer" in results["response"]:
            formatted_answer = results["response"]["formatted_answer"]
        else:
            formatted_answer = "No response was generated. Please try a different query."
        
        # Return query results and the formatted answer
        return {
            "success": True,
            "query": query_request.query,
            "document_id": query_request.document_id,
            "result_count": results.get("result_count", 0),
            "processing_time_ms": results.get("processing_time_ms", 0),
            "response": formatted_answer,
            "detailed_response": results.get("response", {})
        }
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/documents/{session_id}")
async def get_session_documents(session_id: str):
    """
    Get all documents for a session
    
    Args:
        session_id: The session identifier
    """
    try:
        documents = document_processor.get_session_documents(session_id)
        return {
            "session_id": session_id,
            "document_count": len(documents),
            "documents": documents
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@app.get("/document/{document_id}")
async def get_document_info(document_id: str):
    """
    Get information about a specific document
    
    Args:
        document_id: The document identifier
    """
    try:
        document = document_processor.get_document_info(document_id)
        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

@app.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document from the system
    
    Args:
        document_id: The document identifier
    """
    try:
        success = document_processor.delete_document(document_id)
        return {"success": success, "document_id": document_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Delete all documents associated with a session
    
    Args:
        session_id: The session identifier
    """
    try:
        count = document_processor.clear_session(session_id)
        return {
            "success": True, 
            "session_id": session_id,
            "deleted_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True) 