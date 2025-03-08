# Simple RAG Improvements: Phased Implementation

A prioritized plan starting with the easiest implementations for improving retrieval quality.

✅ = implemented

## ✅ Phase 1: Quick Wins (Minimal Code Changes)

### ✅1. Lower the Similarity Threshold

```python
# In backend/query_handler.py
# Change this line
MIN_SIMILARITY_THRESHOLD = 0.7  # Current threshold

# To this lower value
MIN_SIMILARITY_THRESHOLD = 0.5  # More permissive threshold
```

This allows more chunks to be considered relevant, which is helpful when exact matches aren't found.

### ✅2. Increase Retrieved Results Before Filtering

```python
# In backend/query_handler.py, modify the process_query method:

# Change this line:
top_k_retrieval = max(top_k * 2, 10)  # Retrieve more results than needed for filtering

# To retrieve even more candidates:
top_k_retrieval = max(top_k * 3, 15)  # Retrieve more candidates before filtering
```

This gives your filtering system more candidates to work with.

### ✅3. Adjust Chunk Size and Overlap

```python
# In .env file or where you set these variables:

# Current settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Adjusted settings (smaller chunks with higher overlap)
CHUNK_SIZE=500
CHUNK_OVERLAP=150
```

Smaller chunks with higher relative overlap can help capture more context while still being specific enough for retrieval.

## Phase 2: Moderate Changes

### 4. Basic Query Expansion

Add this simple method to `query_handler.py`:

```python
def _expand_query(self, query_text: str) -> List[str]:
    """Simple query expansion to improve retrieval."""
    expanded_queries = [query_text]  # Start with original query
    
    # Remove question words and punctuation for a more direct query
    clean_query = query_text.strip()
    if clean_query.endswith("?"):
        clean_query = clean_query[:-1]
    
    for prefix in ["what is", "who is", "how does", "where is", "when did", "why does"]:
        if clean_query.lower().startswith(prefix):
            # Remove the question prefix to create a more direct statement
            statement_query = clean_query[len(prefix):].strip()
            expanded_queries.append(statement_query)
            break
    
    return expanded_queries
```

And then update the `process_query` method to use it:

```python
def process_query(self, query_text: str, document_id: str, top_k: int = 5) -> Dict[str, Any]:
    # ... existing code ...
    
    # Use query expansion
    queries = self._expand_query(query_text)
    all_results = []
    
    # Query for each expanded query
    for query in queries:
        results = self.vector_store.query(
            query_text=query,
            namespace=namespace,
            top_k=top_k_retrieval,
            include_metadata=True
        )
        all_results.extend(results)
    
    # Deduplicate results
    unique_results = []
    seen_ids = set()
    for result in all_results:
        if result["id"] not in seen_ids:
            unique_results.append(result)
            seen_ids.add(result["id"])
    
    # Continue with existing code, but use unique_results instead of results
    filtered_results = self._filter_results_by_relevance(unique_results)
    # ... rest of the method
```

### 5. Enhanced Text Cleaning

Improve the existing `clean_text` method in `pdf_processing.py`:

```python
def clean_text(self, text: str) -> str:
    """Enhanced text cleaning for better semantic understanding."""
    # Replace multiple newlines with a single one
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple spaces with a single one
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove form feed characters
    text = text.replace('\f', '')
    
    # Fix hyphenated words that may have been split across lines
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    
    # Normalize whitespace around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Trim whitespace
    text = text.strip()
    
    return text
```

## Phase 3: More Advanced Improvements (After Phase 1-2 Validation)

### 6. Basic Keywords + Vector Hybrid Search

Add a simple hybrid search method to boost exact term matches:

```python
def _keyword_boost(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Boost scores for results containing exact keywords from the query."""
    # Extract important keywords (non-stop words)
    stop_words = {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'with', 'on', 'at'}
    keywords = [word.lower() for word in re.findall(r'\b[a-zA-Z]{3,}\b', query)
                if word.lower() not in stop_words]
    
    # If no meaningful keywords, return original results
    if not keywords:
        return results
    
    # Boost scores for results containing keywords
    for result in results:
        text = result.get("metadata", {}).get("text", "").lower()
        
        # Count matches
        matches = sum(1 for keyword in keywords if keyword in text)
        
        # Apply boost based on match ratio
        keyword_boost = 0.1 * (matches / len(keywords))
        
        # Apply boost to score
        result["score"] = min(1.0, result.get("score", 0) + keyword_boost)
    
    # Re-sort based on adjusted scores
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results
```

And add a call to this function in your processing pipeline:

```python
# In process_query method in query_handler.py:
filtered_results = self._filter_results_by_relevance(unique_results)
boosted_results = self._keyword_boost(query_text, filtered_results)
context = self._assemble_context(boosted_results[:top_k])
```

### 7. Improved Semantic Chunking

This would require modifying the chunking algorithm to divide text based on semantic units rather than just character counts:

```python
def chunk_text(self, text: str, page_number: int, 
               document_id: str, document_name: str) -> List[TextChunk]:
    """Split text into chunks based on semantic boundaries."""
    cleaned_text = self.clean_text(text)
    
    # First, try to split by semantic units (paragraphs)
    paragraphs = re.split(r'\n\s*\n', cleaned_text)
    
    chunks = []
    current_chunk = ""
    current_start = 0
    
    for para in paragraphs:
        # If adding this paragraph exceeds chunk size and we already have content
        if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
            # Save current chunk
            chunks.append(TextChunk(
                chunk_id=str(uuid.uuid4()),
                text=current_chunk.strip(),
                page_number=page_number,
                document_id=document_id,
                document_name=document_name,
                start_char_idx=current_start,
                end_char_idx=current_start + len(current_chunk)
            ))
            
            # Start new chunk with some overlap
            if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                # Take the last part of previous chunk for context
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + "\n\n" + para
                current_start += overlap_start
            else:
                current_chunk = para
                current_start += len(current_chunk) + 2  # +2 for paragraph break
        else:
            # Add to the current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Add the final chunk if not empty
    if current_chunk.strip():
        chunks.append(TextChunk(
            chunk_id=str(uuid.uuid4()),
            text=current_chunk.strip(),
            page_number=page_number,
            document_id=document_id,
            document_name=document_name,
            start_char_idx=current_start,
            end_char_idx=current_start + len(current_chunk)
        ))
    
    return chunks
```

