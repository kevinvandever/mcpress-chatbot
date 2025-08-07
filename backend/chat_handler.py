import openai
from typing import AsyncGenerator, Dict, Any, List
import os
import json
import logging
from datetime import datetime

# Set up logging for source relevance debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversations = {}
        
    async def stream_response(self, message: str, conversation_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"=== CHAT REQUEST DEBUG ===")
        logger.info(f"Query: '{message}'")
        logger.info(f"Conversation ID: {conversation_id}")
        
        # Get more results initially to have options for filtering
        logger.info("Step 1: Calling vector store search...")
        search_results = await self.vector_store.search(message, n_results=10)
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
        logger.info(f"Step 3 Result: Context length = {len(context)} characters")
        logger.info(f"Context preview: {context[:200]}..." if context else "Context is EMPTY")
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_year = datetime.now().year
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful assistant that answers questions based on the provided document context. 
                
                Current date: {current_date}
                Current year: {current_year}
                
                IMPORTANT: You have direct access to the content from uploaded PDF documents through the context provided in each message. Use this context to answer questions accurately and specifically.
                
                When answering:
                - Base your responses on the provided context from the documents
                - Quote specific passages when relevant
                - Reference page numbers when available
                - Format code blocks properly with markdown
                - Be precise and technical in your responses
                - If the context doesn't contain enough information to answer a question, say so clearly
                - When calculating time periods or ages, use the current date/year provided above"""
            }
        ]
        
        messages.extend(self.conversations[conversation_id][-10:])
        
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
                model="gpt-4-turbo-preview",
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000
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
    
    def _filter_relevant_documents(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Filter documents by relevance threshold and log the decision process"""
        # ChromaDB uses cosine distance: 0 = identical, 2 = completely different
        # We want documents with distance <= 0.7 (roughly 65% similarity or higher)
        RELEVANCE_THRESHOLD = 0.7
        MAX_SOURCES = 8
        
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
                    "mc_press_url": metadata.get("mc_press_url")
                })
        
        return sources