# Researcher Agent RAG

A research assistant chat application that helps users upload and interact with PDF documents.

## Features

- Upload and process PDF documents
- Extract and chunk text from PDFs
- Generate embeddings for document chunks
- Store document vectors in Pinecone
- Query documents with natural language
- Retrieve relevant context for user queries
- Format responses with citations and source references
- Classify query types for optimized responses

## Project Structure

- `backend/`: FastAPI backend service
  - `pdf_processing.py`: PDF text extraction and chunking
  - `embeddings.py`: Embedding generation with OpenAI
  - `vector_store.py`: Pinecone vector database operations
  - `document_processor.py`: Document management and tracking
  - `query_handler.py`: Query processing and context retrieval
  - `response_generator.py`: AI response generation with citations
  - `main.py`: FastAPI application and API endpoints
  - `tests/`: Unit and integration tests
- `frontend/`: Streamlit web interface
  - `app.py`: Main Streamlit application
  - `components/`: UI components
    - `pdf_upload.py`: Document upload interface
    - `chat_interface.py`: Chat UI for querying documents
    - `document_details.py`: Document metadata display
    - `document_preview.py`: Document preview functionality

## Setup Instructions

1. Clone the repository
2. Create a `.env` file based on the `.env.template` with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
   PINECONE_INDEX_NAME=your_pinecone_index_name
   CHUNK_SIZE=1000
   CHUNK_OVERLAP=200
   EMBEDDING_MODEL_NAME=text-embedding-3-small
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

### Backend

Start the FastAPI backend:

```bash
cd backend
uvicorn main:app --reload
```

The API server will run at http://localhost:8000

### Frontend

Start the Streamlit frontend:

```bash
cd frontend
streamlit run app.py
```

The web interface will be available at http://localhost:8501

## Testing Query Processing

You can test the query processing functionality using the provided test scripts:

### Option 1: Testing with mock data

Test the query processor with mock data to verify functionality without needing a real document:

```bash
cd backend
python -m tests.test_query_processor
```

### Option 2: Testing with a real document

Test the query processor with a real document that you've uploaded:

```bash
cd backend
python -m tests.test_query_processor_manual --document_id YOUR_DOC_ID --query "Your test query" --verbose
```

### Option 3: Combined testing (recommended)

Use the combined test script that supports both mock and real document testing:

```bash
# For mock data testing:
cd backend
python -m tests.test_query_processor_combined --mock

# For real document testing:
cd backend
python -m tests.test_query_processor_combined --document_id YOUR_DOC_ID --query "Your test query" --verbose
```

These test scripts will:
- Verify the core query processing functionality
- Test relevance filtering and context assembly
- When using real documents, retrieve and display the most relevant chunks
- Show the assembled context from the document

## Running Unit Tests

```bash
cd backend
python -m unittest discover tests
```

## Implementation Status

- ✅ Phase 1: Project Setup
- ✅ Phase 2: PDF Upload & Text Extraction
- ✅ Phase 3: Embeddings & Pinecone Integration
- ✅ Phase 4: Query Handling & AI Response
- ✅ Phase 5: Frontend UI Implementation
- ⚙️ Phase 6: End-to-End Testing & Refinement (in progress)
- ⬜ Phase 7: Deployment & Documentation

## Key Components

### Backend
- **Document Processing**: Handles PDF upload, text extraction, chunking, and metadata extraction
- **Embedding Generation**: Creates vector representations of document chunks using OpenAI embeddings
- **Vector Storage**: Manages storage and retrieval of document vectors in Pinecone
- **Query Handling**: Processes user queries, retrieves relevant context, and assembles information
- **Response Generation**: Creates structured AI responses with proper citations and source references

### Frontend
- **Document Upload**: Interface for uploading and processing PDF documents
- **Chat Interface**: Conversational UI for querying documents and viewing responses
- **Document Management**: Displays document details and allows document selection
