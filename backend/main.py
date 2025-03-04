import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any
import json
import tempfile

# Import our PDF processing module
from pdf_processing import process_pdf_bytes, PDFProcessor

# Load environment variables
load_dotenv()

# Get configuration from environment variables
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Create a PDF processor with the configured values
pdf_processor = PDFProcessor(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

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

@app.get("/")
async def root():
    return {"message": "Welcome to the Researcher Agent Chat App API"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API is running normally"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint for uploading a PDF file
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read the uploaded file content
        pdf_content = await file.read()
        
        # Process the PDF
        chunks = pdf_processor.process_pdf_bytes(pdf_content, file.filename)
        
        # Get document statistics
        stats = pdf_processor.get_document_statistics(chunks)
        
        # In a real implementation, we would store the chunks in a database
        # and/or send them to the vector store for embedding
        
        # For now, just return statistics and a sample of the extracted text
        return {
            "filename": file.filename,
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/query")
async def process_query(query_data: Dict[str, Any] = Body(...)):
    """
    Endpoint for processing a query and returning a response
    This is a test endpoint that echoes back the query
    """
    # Extract the query
    if "query" not in query_data:
        raise HTTPException(status_code=400, detail="Query field is required")
    
    query = query_data["query"]
    
    # In a real implementation, this would process the query and return a response
    # For now, just echo back the query for testing
    response = {
        "response": f"Received query: '{query}'. This is a test response from the backend API.",
        "status": "success",
        "message": "Query processing test successful!"
    }
    
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True) 