"""
Response generation module using Pydantic AI.

This module handles:
1. Structured response generation using Pydantic AI
2. Prompt templates for different query types
3. Source citation mechanisms
4. Fallback handling when context is insufficient
"""

import logging
import json
from typing import List, Dict, Any, Optional, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("response_generator")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define query types
class QueryType(BaseModel):
    """Classification of query types"""
    type: Literal["factual", "explanation", "summary", "analysis", "other"] = Field(
        ..., 
        description="The type of query being asked"
    )
    confidence: float = Field(
        ..., 
        description="Confidence score (0-1) for the classification",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        ..., 
        description="Brief explanation for why this classification was chosen"
    )

# Define source reference structure
class SourceReference(BaseModel):
    """Reference to a source in the document"""
    page_number: int = Field(..., description="Page number where the information was found")
    text_snippet: str = Field(..., description="Short snippet of relevant text from the source")
    relevance: float = Field(
        ..., 
        description="Relevance score (0-1) indicating how relevant this source is to the answer",
        ge=0.0,
        le=1.0
    )

# Define the response structure
class GeneratedResponse(BaseModel):
    """Structured response to a user query"""
    answer: str = Field(
        ..., 
        description="Comprehensive answer to the user's question based on document context"
    )
    query_type: QueryType = Field(
        ..., 
        description="Classification of the query type"
    )
    sources: List[SourceReference] = Field(
        ..., 
        description="References to source material supporting the answer"
    )
    confidence: float = Field(
        ..., 
        description="Overall confidence (0-1) in the accuracy of the answer",
        ge=0.0,
        le=1.0
    )
    has_sufficient_context: bool = Field(
        ..., 
        description="Whether the retrieved context was sufficient to answer the query"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the response was generated"
    )
    
    def format_with_citations(self) -> str:
        """Format the answer with inline citations"""
        answer_with_citations = self.answer
        
        # Add footnotes for sources
        footnotes = []
        for i, source in enumerate(self.sources, 1):
            footnote = f"[{i}] Page {source.page_number}: \"{source.text_snippet}\""
            footnotes.append(footnote)
            
            # Add citation number in the answer if not already present
            if f"[{i}]" not in answer_with_citations:
                # Attempt to find a relevant point to insert the citation
                for snippet_part in source.text_snippet.split():
                    if len(snippet_part) > 4 and snippet_part in answer_with_citations:
                        # Insert after this part of text
                        position = answer_with_citations.find(snippet_part) + len(snippet_part)
                        answer_with_citations = (
                            answer_with_citations[:position] + 
                            f" [{i}]" + 
                            answer_with_citations[position:]
                        )
                        break
        
        # Append footnotes
        if footnotes:
            answer_with_citations += "\n\n**Sources:**\n" + "\n".join(footnotes)
            
        # Add confidence information
        answer_with_citations += f"\n\nConfidence: {self.confidence:.2f}"
        
        return answer_with_citations


class ResponseGenerator:
    """Handles generation of structured responses using Pydantic AI"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the response generator.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model_name = model_name
        
    def _classify_query_type(self, query: str) -> QueryType:
        """
        Classify the type of query being asked.
        
        Args:
            query: The user's query
            
        Returns:
            QueryType classification
        """
        try:
            system_prompt = """
            You are a query classifier that categorizes questions into different types:
            - factual: Questions seeking factual information or data
            - explanation: Questions seeking explanations of concepts or processes
            - summary: Questions asking for summaries of content
            - analysis: Questions requiring analysis or interpretation
            - other: Questions that don't fit into the above categories
            
            Your response should be in JSON format with these fields:
            {
                "type": "one of [factual, explanation, summary, analysis, other]",
                "confidence": "a float between 0 and 1",
                "reasoning": "brief explanation for the classification"
            }
            """
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify the following query: \"{query}\""}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}  # Request JSON response
            )
            
            # Parse the response text into JSON
            response_text = response.choices[0].message.content
            response_json = json.loads(response_text)
            
            # Create and return a QueryType model
            return QueryType(
                type=response_json.get("type", "other"),
                confidence=response_json.get("confidence", 0.5),
                reasoning=response_json.get("reasoning", "No reasoning provided")
            )
            
        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            # Default to "other" with low confidence if classification fails
            return QueryType(
                type="other",
                confidence=0.5,
                reasoning="Failed to classify due to an error"
            )
    
    def _extract_source_references(self, context: str, query: str, results: List[Dict[str, Any]]) -> List[SourceReference]:
        """
        Extract source references from the context and search results.
        
        Args:
            context: The compiled context from retrieved chunks
            query: The user's query
            results: The raw results from vector search
            
        Returns:
            List of SourceReference objects
        """
        sources = []
        
        # Extract sources from results
        for result in results:
            metadata = result.get("metadata", {})
            text = metadata.get("text", "")
            page_number = metadata.get("page_number", 0)
            relevance = result.get("score", 0.5)
            
            # If the text is too long, extract a shorter snippet
            if len(text) > 150:
                text = text[:147] + "..."
                
            sources.append(
                SourceReference(
                    page_number=page_number,
                    text_snippet=text,
                    relevance=relevance
                )
            )
        
        # Sort sources by relevance (highest first)
        sources.sort(key=lambda x: x.relevance, reverse=True)
        
        # Return top 3 most relevant sources
        return sources[:3]
    
    def generate_response(
        self, 
        query: str, 
        context: str, 
        results: List[Dict[str, Any]],
        document_id: str
    ) -> GeneratedResponse:
        """
        Generate a structured response to the user's query.
        
        Args:
            query: The user's query
            context: The compiled context from retrieved chunks
            results: The raw results from vector search
            document_id: ID of the document being queried
            
        Returns:
            GeneratedResponse object
        """
        # Classify the query type
        query_type = self._classify_query_type(query)
        
        # Extract source references
        sources = self._extract_source_references(context, query, results)
        
        # Determine if we have sufficient context
        has_sufficient_context = len(results) > 0 and results[0].get("score", 0) > 0.7
        
        # Create different system prompts based on query type
        system_prompts = {
            "factual": """You are a research assistant that provides factual information from documents.
                      Answer the question based ONLY on the provided context. Cite specific facts with numbers.
                      If the context doesn't contain the information needed, acknowledge the limitations.""",
            
            "explanation": """You are a research assistant that explains concepts found in documents.
                         Give clear, structured explanations based ONLY on the provided context.
                         Use analogies when helpful for complex concepts.""",
            
            "summary": """You are a research assistant that summarizes information from documents.
                      Provide concise summaries based ONLY on the provided context.
                      Structure your summary with bullet points for key points.""",
            
            "analysis": """You are a research assistant that analyzes information from documents.
                       Provide thoughtful analysis based ONLY on the provided context.
                       Consider different perspectives and implications in your analysis.""",
            
            "other": """You are a research assistant that answers questions about documents.
                    Answer based ONLY on the provided context. 
                    Be helpful and informative in your response."""
        }
        
        # Select the appropriate system prompt
        system_prompt = system_prompts.get(query_type.type, system_prompts["other"])
        
        # Prepare the user prompt with context
        user_prompt = f"""
        Question: {query}
        
        Context from document:
        {context}
        
        Please answer the question based solely on the provided context.
        """
        
        try:
            # Generate answer using OpenAI
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Lower temperature for more factual responses
                max_tokens=800
            )
            
            answer = completion.choices[0].message.content
            
            # Calculate confidence based on result scores and answer
            if not has_sufficient_context:
                confidence = 0.3  # Low confidence if context is insufficient
            elif query_type.confidence < 0.7:
                confidence = 0.5  # Medium confidence if query type is uncertain
            else:
                # Calculate from source relevances
                relevances = [source.relevance for source in sources]
                confidence = sum(relevances) / len(relevances) if relevances else 0.5
                
            # Create structured response
            response = GeneratedResponse(
                answer=answer,
                query_type=query_type,
                sources=sources,
                confidence=confidence,
                has_sufficient_context=has_sufficient_context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            
            # Fallback response when generation fails
            sources = sources if sources else [
                SourceReference(
                    page_number=0, 
                    text_snippet="Error retrieving sources", 
                    relevance=0.0
                )
            ]
            
            return GeneratedResponse(
                answer=f"I apologize, but I encountered an error while generating a response: {str(e)}. Please try again with a different question.",
                query_type=query_type,
                sources=sources,
                confidence=0.0,
                has_sufficient_context=False
            )
            
    def generate_fallback_response(self, query: str) -> GeneratedResponse:
        """
        Generate a fallback response when no relevant context is found.
        
        Args:
            query: The user's query
            
        Returns:
            GeneratedResponse object with fallback answer
        """
        query_type = self._classify_query_type(query)
        
        return GeneratedResponse(
            answer=f"I don't have enough information in the document to answer the question: '{query}'. Please try a different question related to the content of the document, or upload a document that contains this information.",
            query_type=query_type,
            sources=[
                SourceReference(
                    page_number=0,
                    text_snippet="No relevant information found in the document",
                    relevance=0.0
                )
            ],
            confidence=0.0,
            has_sufficient_context=False
        )

# Create a singleton instance
response_generator = ResponseGenerator()


def generate_response(
    query: str, 
    context: str, 
    results: List[Dict[str, Any]],
    document_id: str
) -> Dict[str, Any]:
    """
    Convenience function to generate a response.
    
    Args:
        query: The user's query
        context: The compiled context from retrieved chunks
        results: The raw results from vector search
        document_id: ID of the document being queried
        
    Returns:
        Dict containing the structured response as a dictionary
    """
    response = response_generator.generate_response(query, context, results, document_id)
    
    # Convert to dictionary for easier JSON serialization
    response_dict = response.model_dump()
    
    # Format datetime to string
    response_dict["generated_at"] = response_dict["generated_at"].isoformat()
    
    # Add formatted answer with citations
    response_dict["formatted_answer"] = response.format_with_citations()
    
    return response_dict 