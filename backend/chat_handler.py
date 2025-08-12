import openai
from typing import AsyncGenerator, Dict, Any, List
import os
import json
import logging
from datetime import datetime
import tiktoken
from .config import OPENAI_CONFIG, SEARCH_CONFIG, RESPONSE_CONFIG

# Set up logging for source relevance debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables!")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.conversations = {}
        # Initialize tiktoken encoder for token counting
        self.model = OPENAI_CONFIG["model"]
        self.encoding = tiktoken.encoding_for_model(self.model)
        self.max_context_tokens = 3000  # Leave room for response
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.encoding.encode(text))
    
    def truncate_context_by_tokens(self, context: str) -> str:
        """Truncate context to fit within token limits"""
        token_count = self.count_tokens(context)
        
        if token_count <= self.max_context_tokens:
            return context
            
        logger.info(f"Context too long ({token_count} tokens), truncating to {self.max_context_tokens}")
        
        # Simple truncation - take first portion that fits
        words = context.split()
        truncated = ""
        
        for word in words:
            test_context = truncated + " " + word if truncated else word
            if self.count_tokens(test_context) > self.max_context_tokens:
                break
            truncated = test_context
            
        return truncated
    
    def calculate_confidence(self, relevant_docs: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on document relevance"""
        if not relevant_docs:
            return 0.0
            
        # Average similarity score (convert from distance)
        total_similarity = 0
        for doc in relevant_docs:
            distance = doc.get("distance", 2.0)
            similarity = max(0, (2 - distance) / 2)  # Convert to 0-1 scale
            total_similarity += similarity
            
        avg_confidence = total_similarity / len(relevant_docs)
        return round(avg_confidence, 3)
        
    async def stream_response(self, message: str, conversation_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"=== CHAT REQUEST DEBUG ===")
        logger.info(f"Query: '{message}'")
        logger.info(f"Conversation ID: {conversation_id}")
        
        # Get more results initially to have options for filtering
        logger.info("Step 1: Calling vector store search...")
        search_results = await self.vector_store.search(message, n_results=SEARCH_CONFIG["initial_search_results"])
        logger.info(f"Step 1 Result: Found {len(search_results)} initial search results")
        
        # Log raw search results
        for i, result in enumerate(search_results[:3]):
            logger.info(f"  Raw Result {i+1}: distance={result.get('distance', 'N/A')}, filename={result.get('metadata', {}).get('filename', 'Unknown')}")
        
        # Filter results by relevance threshold
        logger.info("Step 2: Filtering results by relevance...")
        relevant_docs = self._filter_relevant_documents(search_results, message)
        logger.info(f"Step 2 Result: {len(relevant_docs)} documents passed filtering")
        
        # Build context
        logger.info("Step 3: Building context from relevant documents...")
        context = self._build_context(relevant_docs)
        
        # Apply token-based truncation
        context = self.truncate_context_by_tokens(context)
        context_tokens = self.count_tokens(context)
        
        logger.info(f"Step 3 Result: Context length = {len(context)} characters, {context_tokens} tokens")
        logger.info(f"Context preview: {context[:200]}..." if context else "Context is EMPTY")
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_year = datetime.now().year
        
        messages = [
            {
                "role": "system",
                "content": f"""You are an expert technical documentation assistant specialized in MC Press technical books and documentation. You provide precise, accurate answers based on the uploaded PDF content.
                
                Current date: {current_date}
                Current year: {current_year}
                
                IMPORTANT: You have direct access to the content from uploaded PDF documents through the context provided in each message. Use this context to answer questions accurately and specifically.
                
                Core Instructions:
                - Base your responses STRICTLY on the provided document context
                - Quote specific passages when relevant, using exact text from the documents
                - Always cite sources in format: [Book/Document Title, p.XX]
                - Format code blocks with appropriate syntax highlighting (```language)
                - Use markdown tables for comparisons or structured data
                - Be precise and technical in your responses
                
                Response Guidelines:
                - If the context doesn't contain enough information, explicitly state: "The provided documents don't contain information about [topic]"
                - For ambiguous queries, ask for clarification and suggest related topics found in the documents
                - When multiple interpretations exist, briefly present all relevant options
                - Include code examples from the documents when applicable
                - For technical terms, provide the definition as found in the documents
                
                Quality Standards:
                - Prioritize accuracy over completeness - never guess or infer beyond the documents
                - Maintain technical precision - use exact terminology from the source material
                - If referencing multiple sources, clearly distinguish between them
                - When calculating time periods or ages, use the current date/year provided above
                - For code-related questions, always check for the most recent/updated version in the documents"""
            }
        ]
        
        messages.extend(self.conversations[conversation_id][-RESPONSE_CONFIG["max_conversation_history"]:])
        
        if context.strip():
            user_content = f"""Here is the relevant content from the uploaded PDF documents:

{context}

Based on this content, please answer the following question: {message}"""
            logger.info("Step 4: Context found - sending document-based request to OpenAI")
        else:
            user_content = f"""No relevant content was found in the uploaded PDF documents for this query.

Please answer the following question based on your general knowledge, but clearly indicate that your response is not based on the provided documents: {message}"""
            logger.info("Step 4: NO CONTEXT - sending general knowledge request to OpenAI")
        
        logger.info(f"Final prompt length: {len(user_content)} characters")
        
        messages.append({
            "role": "user", 
            "content": user_content
        })
        
        try:
            stream = await self.client.chat.completions.create(
                model=OPENAI_CONFIG["model"],
                messages=messages,
                stream=OPENAI_CONFIG["stream"],
                temperature=OPENAI_CONFIG["temperature"],
                max_tokens=OPENAI_CONFIG["max_tokens"]
            )
            
            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield {
                        "type": "content",
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    }
            
            self.conversations[conversation_id].append({"role": "user", "content": message})
            self.conversations[conversation_id].append({"role": "assistant", "content": full_response})
            
            # Calculate response metadata
            confidence_score = self.calculate_confidence(relevant_docs)
            threshold_used = self._get_dynamic_threshold(message)
            
            yield {
                "type": "metadata",
                "confidence": confidence_score,
                "source_count": len(relevant_docs),
                "model_used": OPENAI_CONFIG["model"],
                "temperature": OPENAI_CONFIG["temperature"],
                "threshold_used": threshold_used,
                "context_tokens": self.count_tokens(context) if context else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            yield {
                "type": "done",
                "sources": self._format_sources(relevant_docs),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        context_parts = []
        
        for doc in documents:
            metadata = doc.get("metadata", {})
            source_info = f"[Source: {metadata.get('filename', 'Unknown')}"
            
            if metadata.get("page"):
                source_info += f", Page {metadata['page']}"
            
            if metadata.get("type"):
                source_info += f", Type: {metadata['type']}"
            
            source_info += "]"
            
            context_parts.append(f"{source_info}\n{doc['content']}\n")
        
        return "\n---\n".join(context_parts)
    
    def _get_dynamic_threshold(self, query: str) -> float:
        """Determine relevance threshold based on query characteristics"""
        query_lower = query.lower()
        
        # Exact searches (with quotes) need higher precision
        if '"' in query:
            return 0.5
        
        # Code/technical queries - more specific matching
        code_keywords = ['function', 'class', 'method', 'error', 'code', 'syntax', 'api', 'import', 'return']
        if any(keyword in query_lower for keyword in code_keywords):
            return 0.6
            
        # Specific technical terms - precise matching
        tech_keywords = ['configure', 'install', 'setup', 'parameter', 'variable', 'property']
        if any(keyword in query_lower for keyword in tech_keywords):
            return 0.65
        
        # General questions - broader matching allowed
        return SEARCH_CONFIG["relevance_threshold"]

    def _filter_relevant_documents(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Filter documents by relevance threshold and log the decision process"""
        # ChromaDB uses cosine distance: 0 = identical, 2 = completely different
        RELEVANCE_THRESHOLD = self._get_dynamic_threshold(query)
        MAX_SOURCES = SEARCH_CONFIG["max_sources"]
        
        logger.info(f"Query: '{query}'")
        logger.info(f"Initial search returned {len(documents)} documents")
        
        filtered_docs = []
        for i, doc in enumerate(documents):
            distance = doc.get("distance", 2.0)  # Default to max distance if missing
            similarity_score = max(0, (2 - distance) / 2)  # Convert to 0-1 scale
            similarity_percent = similarity_score * 100
            
            metadata = doc.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page", "N/A")
            
            logger.info(f"  Result {i+1}: {filename} (Page {page}) - Distance: {distance:.3f}, Similarity: {similarity_percent:.1f}%")
            
            if distance <= RELEVANCE_THRESHOLD:
                filtered_docs.append(doc)
                logger.info(f"    ✓ INCLUDED - Above threshold ({RELEVANCE_THRESHOLD})")
            else:
                logger.info(f"    ✗ EXCLUDED - Below threshold ({RELEVANCE_THRESHOLD})")
        
        # Limit to MAX_SOURCES and sort by relevance (lowest distance first)
        filtered_docs = sorted(filtered_docs, key=lambda x: x.get("distance", 2.0))[:MAX_SOURCES]
        
        logger.info(f"Final result: {len(filtered_docs)} relevant documents included")
        
        if len(filtered_docs) == 0:
            logger.warning("No documents met the relevance threshold - user query may not match available content")
        
        return filtered_docs
    
    def _format_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sources = []
        seen = set()
        
        for doc in documents:
            metadata = doc.get("metadata", {})
            
            # Extract page from multiple possible locations
            page = (metadata.get("page") or 
                   metadata.get("page_number") or 
                   doc.get("page_number") or 
                   "N/A")
            
            filename = metadata.get("filename", "Unknown")
            key = f"{filename}-{page}"
            
            if key not in seen:
                seen.add(key)
                
                # Extract content type from metadata
                content_type = (metadata.get("type") or 
                               metadata.get("content_type") or 
                               "text")
                
                sources.append({
                    "filename": filename,
                    "page": page,
                    "type": content_type,
                    "distance": doc.get("distance", 0),
                    "author": metadata.get("author", "Unknown"),
                    "mc_press_url": metadata.get("mc_press_url", "")
                })
        
        return sources