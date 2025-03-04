import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Researcher Agent Chat App",
    description="A FastAPI application for research agent chat",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Researcher Agent Chat App API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True) 