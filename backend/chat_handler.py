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
    def __init__(self, vector_store, conversation_service=None):
        self.vector_store = vector_store
        self.conversation_service = conversation_service  # Optional - for persistence
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables!")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.conversations = {}  # In-memory cache for performance
        self.db_conversation_ids = {}  # Map in-memory IDs to DB conversation IDs
        # Initialize tiktoken encoder for token counting
        self.model = OPENAI_CONFIG["model"]
        self.encoding = tiktoken.encoding_for_model(self.model)
        self.max_context_tokens = 6000  # Increased from 3000 to provide richer context
        
    async def _ensure_conversation_exists(self, conversation_id: str, first_message: str, user_id: str = "guest") -> str:
        """
        Ensure conversation exists in database. Creates if needed.
        Returns the database conversation ID.
        """
        if not self.conversation_service:
            return conversation_id  # No persistence - return as-is

        # Check if we already have a DB conversation for this in-memory ID
        if conversation_id in self.db_conversation_ids:
            return self.db_conversation_ids[conversation_id]

        try:
            # Try to get existing conversation from DB
            conv, messages = await self.conversation_service.get_conversation_with_messages(
                conversation_id, user_id
            )
            # Found existing - map it
            self.db_conversation_ids[conversation_id] = conv.id
            logger.info(f"✅ Found existing conversation in DB: {conv.id}")
            return conv.id
        except ValueError:
            # Conversation doesn't exist - create it
            try:
                conv = await self.conversation_service.create_conversation(
                    user_id=user_id,
                    initial_message=first_message
                )
                self.db_conversation_ids[conversation_id] = conv.id
                logger.info(f"✅ Created new conversation in DB: {conv.id} - '{conv.title}'")
                return conv.id
            except Exception as e:
                logger.error(f"⚠️ Failed to create conversation in DB: {e}")
                return conversation_id  # Fallback to in-memory only

    async def _save_message_to_db(self, conversation_id: str, role: str, content: str, metadata: dict = None):
        """Save message to database"""
        if not self.conversation_service:
            return  # No persistence available

        # Get the DB conversation ID
        db_conv_id = self.db_conversation_ids.get(conversation_id, conversation_id)

        try:
            await self.conversation_service.add_message(
                conversation_id=db_conv_id,
                role=role,
                content=content,
                metadata=metadata or {}
            )
            logger.info(f"✅ Saved {role} message to DB conversation {db_conv_id}")
        except Exception as e:
            logger.error(f"⚠️ Failed to save message to DB: {e}")

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
        """
        Calculate confidence score based on document relevance
        Uses the pre-calculated similarity scores from vector store
        """
        if not relevant_docs:
            return 0.0

        # Use pre-calculated similarity scores (0-1 scale)
        total_similarity = 0
        for doc in relevant_docs:
            # Use pre-calculated similarity if available, otherwise convert from distance
            similarity = doc.get("similarity", 0.0)
            total_similarity += similarity

        avg_confidence = total_similarity / len(relevant_docs)
        return round(avg_confidence, 3)
        
    async def stream_response(self, message: str, conversation_id: str, user_id: str = "guest") -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"=== CHAT REQUEST DEBUG ===")
        logger.info(f"Query: '{message}'")
        logger.info(f"Conversation ID: {conversation_id}")
        logger.info(f"User ID: {user_id}")

        # Ensure conversation exists in database (non-blocking - chat works even if this fails)
        try:
            await self._ensure_conversation_exists(conversation_id, message, user_id)
        except Exception as e:
            logger.error(f"⚠️ Failed to create/load conversation (continuing without persistence): {e}")
            import traceback
            logger.error(traceback.format_exc())
        
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
                "content": f"""You are an expert technical documentation assistant specialized in MC Press technical books and documentation. You provide precise, accurate, AND COMPREHENSIVE answers based on the uploaded PDF content.

                Current date: {current_date}
                Current year: {current_year}

                IMPORTANT: You have direct access to the content from uploaded PDF documents through the context provided in each message. Use this context to answer questions accurately, specifically, and WITH APPROPRIATE DEPTH.

                Core Instructions:
                - Base your responses STRICTLY on the provided document context
                - Provide COMPREHENSIVE answers - explain concepts thoroughly, not just the minimum
                - When explaining technical concepts, include:
                  * Core explanation from the documents
                  * Practical examples and use cases from the source material
                  * Related concepts and context mentioned in the documents
                  * Common pitfalls or best practices if mentioned in the sources
                - Quote specific passages when relevant, using exact text from the documents
                - Do NOT include inline citations or source references in your response - sources are displayed separately below your answer
                - Format code blocks with appropriate syntax highlighting (```language)
                - Use markdown tables for comparisons or structured data
                - Be precise and technical in your responses

                Response Depth Guidelines:
                - For "What is X?" questions: Provide definition, purpose, key characteristics, and examples from the documents
                - For "How do I X?" questions: Provide step-by-step guidance with explanations of WHY each step matters
                - For conceptual questions: Build a complete mental model using the available context
                - Synthesize information from multiple sources when relevant to provide a fuller picture
                - When multiple related topics appear in context, connect them to enrich the answer
                - Go beyond surface-level answers - provide the depth that helps users truly understand

                Response Guidelines:
                - If the context doesn't contain enough information, explicitly state: "The provided documents don't contain information about [topic]"
                - For ambiguous queries, ask for clarification and suggest related topics found in the documents
                - When multiple interpretations exist, present all relevant options with explanations
                - Include code examples from the documents when applicable
                - For technical terms, provide the definition as found in the documents

                Quality Standards:
                - Prioritize accuracy AND completeness - use all relevant context provided
                - Maintain technical precision - use exact terminology from the source material
                - If referencing multiple sources, clearly distinguish between them and synthesize insights
                - When calculating time periods or ages, use the current date/year provided above
                - For code-related questions, always check for the most recent/updated version in the documents
                - Never guess or infer beyond what the documents provide, but DO use all available context"""
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
            
            # Save to in-memory conversation
            self.conversations[conversation_id].append({"role": "user", "content": message})
            self.conversations[conversation_id].append({"role": "assistant", "content": full_response})

            # Save messages to database (non-blocking - chat works even if this fails)
            try:
                await self._save_message_to_db(
                    conversation_id,
                    "user",
                    message,
                    metadata={"sources": relevant_docs[:3] if relevant_docs else []}  # Store top 3 sources
                )
                await self._save_message_to_db(
                    conversation_id,
                    "assistant",
                    full_response,
                    metadata={
                        "model": OPENAI_CONFIG["model"],
                        "confidence": self.calculate_confidence(relevant_docs),
                        "source_count": len(relevant_docs),
                        "context_tokens": self.count_tokens(context) if context else 0
                    }
                )
            except Exception as e:
                logger.error(f"⚠️ Failed to save messages to DB (continuing): {e}")
            
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
        """
        Determine relevance threshold based on query characteristics
        NOTE: This returns a DISTANCE threshold (lower = more permissive for pgvector)
        pgvector cosine distance: 0=identical, 2=opposite
        """
        query_lower = query.lower()

        # RPG/IBM i specific technical terms - need comprehensive context
        rpg_keywords = ['subprocedure', 'subfile', 'rpg', 'ile', 'cl', 'db2', 'sql', 'as/400', 'ibm i', 'iseries']
        if any(keyword in query_lower for keyword in rpg_keywords):
            return 0.70  # Very permissive (was 0.85 for ChromaDB)

        # Code/technical queries - broader matching for better coverage
        code_keywords = ['function', 'class', 'method', 'error', 'code', 'syntax', 'api', 'import', 'return', 'how do i', 'what is']
        if any(keyword in query_lower for keyword in code_keywords):
            return 0.65  # Permissive (was 0.8 for ChromaDB)

        # Specific technical terms - still need good coverage
        tech_keywords = ['configure', 'install', 'setup', 'parameter', 'variable', 'property']
        if any(keyword in query_lower for keyword in tech_keywords):
            return 0.60  # Moderate (was 0.75 for ChromaDB)

        # Exact searches (with quotes) need higher precision
        if '"' in query:
            return 0.40  # Stricter for exact matches (was 0.65 for ChromaDB)

        # General questions - broader matching allowed
        return SEARCH_CONFIG["relevance_threshold"]  # 0.55 default

    def _filter_relevant_documents(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Filter documents by relevance threshold and log the decision process
        Handles both pgvector distance and fallback similarity metrics
        """
        RELEVANCE_THRESHOLD = self._get_dynamic_threshold(query)
        MAX_SOURCES = SEARCH_CONFIG["max_sources"]

        # Check if we're using pgvector or fallback
        using_pgvector = documents[0].get("using_pgvector", True) if documents else True
        logger.info(f"🔍 Vector Store Mode: {'pgvector' if using_pgvector else 'fallback (no pgvector)'}")
        logger.info(f"Query: '{query}'")
        logger.info(f"Initial search returned {len(documents)} documents")
        logger.info(f"Distance threshold: {RELEVANCE_THRESHOLD} (lower distance = better match)")

        filtered_docs = []
        for i, doc in enumerate(documents):
            distance = doc.get("distance", 2.0)  # pgvector distance or fallback distance
            similarity = doc.get("similarity", 0.0)  # Pre-calculated similarity (0-1)

            metadata = doc.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page", "N/A")

            # Log with appropriate precision
            logger.info(f"  Result {i+1}: {filename} (Page {page})")
            logger.info(f"    Distance: {distance:.4f}, Similarity: {similarity:.4f} ({similarity*100:.1f}%)")

            # Filter by distance threshold (works for both pgvector and fallback)
            if distance <= RELEVANCE_THRESHOLD:
                filtered_docs.append(doc)
                logger.info(f"    ✅ INCLUDED - Distance {distance:.4f} <= threshold {RELEVANCE_THRESHOLD}")
            else:
                logger.info(f"    ❌ EXCLUDED - Distance {distance:.4f} > threshold {RELEVANCE_THRESHOLD}")

        # Limit to MAX_SOURCES and sort by relevance (lowest distance first)
        filtered_docs = sorted(filtered_docs, key=lambda x: x.get("distance", 2.0))[:MAX_SOURCES]

        logger.info(f"✅ Final result: {len(filtered_docs)} relevant documents included (max {MAX_SOURCES})")

        if len(filtered_docs) == 0:
            logger.warning("⚠️ No documents met the relevance threshold - user query may not match available content")
            logger.warning(f"   Consider lowering threshold (current: {RELEVANCE_THRESHOLD})")

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