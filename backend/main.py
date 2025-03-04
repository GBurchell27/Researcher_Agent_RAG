import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any
import json

# Load environment variables
load_dotenv()

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
    This is a test endpoint that just returns file information
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # In a real implementation, this would process the file and store it
    # For now, just return file information for testing
    file_info = {
        "filename": file.filename,
        "content_type": file.content_type,
        "status": "received",
        "message": "File upload test successful! In a real implementation, the file would be processed and stored."
    }
    
    return file_info

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