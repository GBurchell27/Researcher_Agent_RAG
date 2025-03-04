
# ✅TEST EMBEDDINGS - SUCCESS

## Quick sanity check:
python -m backend.tests.simple_embedding_test

## Full functional test:
python -m backend.tests.test_embeddings_script

## Unit tests:
python backend/tests/test_embeddings.py

# ✅TEST Vector Store
python -m backend.tests.test_vector_store

# ✅TEST 4.1 Query Processing
## For quick testing with mock data
cd backend
python -m tests.test_query_processor_combined --mock

## For real document testing after uploading a document
cd backend
python -m tests.test_query_processor_combined --document_id YOUR_DOC_ID --query "Your test query" --verbose


# TEST 4.2 Response Generation with Pydantic AI