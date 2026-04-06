import openai
from typing import AsyncGenerator, Dict, Any, List
import os
import json
import logging
from datetime import datetime
import tiktoken
import asyncpg
from .config import OPENAI_CONFIG, SEARCH_CONFIG, RESPONSE_CONFIG, TEMPORAL_CONFIG

# Set up logging for source relevance debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentDetector:
    """Classifies user queries by RPG era intent using keyword matching."""

    MODERN_SIGNALS: set = {
        "free-form", "fully free", "fully-free", "dcl-s", "dcl-proc",
        "dcl-ds", "dcl-pi", "dcl-pr", "/free", "**free", "vs code",
        "rdi", "sql embedded", "ibm i 7.3", "ibm i 7.4", "ibm i 7.5",
        "modern rpg", "free format rpg",
    }

    LEGACY_SIGNALS: set = {
        "c-spec", "h-spec", "d-spec", "f-spec", "o-spec",
        "fixed-format", "fixed format", "rpg iii", "rpg/400", "rpg-400",
        "s/36", "s/38", "rpgle fixed", "column-based", "column based",
        "specifications", "c spec", "h spec", "d spec", "f spec", "o spec",
    }

    def detect_era(self, query: str) -> str:
        """
        Returns 'modern', 'legacy', or 'neutral'.
        Must complete in <5ms for queries up to 500 chars.
        Uses case-insensitive keyword matching against MODERN_SIGNALS and LEGACY_SIGNALS.
        If both modern and legacy signals are found, returns 'neutral' (ambiguous).
        """
        if not query:
            return "neutral"

        query_lower = query.lower()

        has_modern = any(signal in query_lower for signal in self.MODERN_SIGNALS)
        has_legacy = any(signal in query_lower for signal in self.LEGACY_SIGNALS)

        if has_modern and has_legacy:
            return "neutral"
        if has_modern:
            return "modern"
        if has_legacy:
            return "legacy"
        return "neutral"


# Era sets for temporal boost matching
_MODERN_ERAS = {"free-form", "fully-free"}
_LEGACY_ERAS = {"fixed-format", "rpg-iv"}


def apply_temporal_boost(documents: list, era_intent: str, boost_amount: float = 0.10) -> list:
    """
    Adjusts document distance scores based on era match.

    - For 'modern' intent: reduces distance for docs with rpg_era in {'free-form', 'fully-free'}
    - For 'legacy' intent: reduces distance for docs with rpg_era in {'fixed-format', 'rpg-iv'}
    - For 'neutral' intent: no adjustment
    - Documents with rpg_era=None or 'general': no adjustment

    Returns a new list of documents with 'adjusted_distance' field added.
    Logs original distance, boost, and adjusted distance per document.
    """
    result = []
    for doc in documents:
        original_distance = doc.get("distance", 0.0)
        rpg_era = doc.get("rpg_era")
        boost = 0.0

        if era_intent != "neutral" and rpg_era not in (None, "general"):
            if era_intent == "modern" and rpg_era in _MODERN_ERAS:
                boost = boost_amount
            elif era_intent == "legacy" and rpg_era in _LEGACY_ERAS:
                boost = boost_amount

        adjusted_distance = max(0, original_distance - boost)

        logger.info(
            "Temporal boost: file=%s era=%s intent=%s original=%.4f boost=%.4f adjusted=%.4f",
            doc.get("metadata", {}).get("filename", "unknown"),
            rpg_era,
            era_intent,
            original_distance,
            boost,
            adjusted_distance,
        )

        new_doc = {**doc, "adjusted_distance": adjusted_distance}
        result.append(new_doc)

    return result


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
        relevant_docs = await self._filter_relevant_documents(search_results, message)
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
                "content": f"""You are an expert technical documentation assistant specialized in MC Press technical books and documentation about IBM i, RPG, ILE, CL, DB2, and related IBM midrange technologies. You provide precise, accurate, and comprehensive answers based on the uploaded PDF content.

                Current date: {current_date}
                Current year: {current_year}

                SCOPE RESTRICTIONS - IMPORTANT:
                - You specialize in IBM i, RPG, ILE, CL, DB2, AS/400, iSeries, and related IBM midrange technologies
                - PLATFORM NAME SYNONYMS: "IBM i", "AS/400", "iSeries", "System i", "i5/OS", and "OS/400" all refer to the same IBM midrange platform. Treat questions using any of these names as equivalent.
                - If a question is CLEARLY outside this technical domain (e.g., tennis tournaments, cooking, sports, entertainment, politics), you MUST refuse to answer
                - For off-topic questions, respond: "I'm specialized in IBM i, RPG, ILE, CL, DB2, and related IBM midrange technologies based on MC Press documentation. I cannot help with questions about [topic]. Please ask questions related to IBM i development, system administration, or related technologies."

                WHEN YOU HAVE RELEVANT DOCUMENTATION (context provided):
                - Base your responses on the provided document context
                - Provide COMPREHENSIVE answers - explain concepts thoroughly
                - Include practical examples and code from the source material
                - Quote specific passages when relevant
                - NEVER mention source names, book titles, author names, or filenames in your answer. Do NOT say things like "According to [book title]..." or "As described in [source]..." or "In the book [title]...". Sources are displayed separately below your answer in a dedicated UI section — the user will see them there.
                - Format code blocks with appropriate syntax highlighting (```rpg, ```cl, ```sql, etc.)

                WHEN NO RELEVANT DOCUMENTATION IS FOUND (empty context):
                - For IBM i/RPG related questions: You may provide a brief, helpful response based on general IBM i knowledge, but clearly state: "Note: I don't have specific MC Press documentation on this topic, but here's what I can share about [topic]..."
                - For clearly off-topic questions: Refuse and explain your specialization

                Response Depth Guidelines:
                - For "What is X?" questions: Provide definition, purpose, key characteristics, and examples
                - For "How do I X?" questions: Provide step-by-step guidance with explanations
                - For conceptual questions: Build a complete mental model
                - Synthesize information from multiple sources when relevant

                Quality Standards:
                - Prioritize accuracy AND completeness
                - Maintain technical precision - use exact terminology from source material
                - When calculating time periods or ages, use the current date/year provided above
                - For code-related questions, always check for the most recent/updated version in the documents

                COMMUNICATION STYLE:
                - Write in a conversational, approachable tone — like a knowledgeable friend explaining things, not a textbook
                - Use casual transitions ("so basically", "here's the deal", "the cool thing is")
                - Keep sentences punchy and scannable — avoid walls of text
                - It's fine to show enthusiasm about clever solutions or elegant code
                - Use analogies to make complex concepts click
                - Still be precise with technical terms and code — don't sacrifice accuracy for vibes
                - Avoid corporate/stiff language ("it should be noted that", "one must consider")

                RPG ERA AWARENESS:
                RPG has evolved dramatically over 30+ years. You MUST distinguish between these two major eras:

                Fixed-Format RPG (Legacy):
                - Uses columnar specification types: H-specs (control), F-specs (file), D-specs (definition), C-specs (calculation), O-specs (output)
                - Code position matters — operations, factors, and results occupy fixed columns
                - Associated with RPG III, RPG/400, and early RPG IV (pre-2013)

                Modern Free-Form RPG:
                - Uses declarative keywords: dcl-s (scalar), dcl-ds (data structure), dcl-proc (procedure), dcl-pi (procedure interface), dcl-pr (prototype)
                - Free-form calculation blocks (/free … /end-free) or fully-free source (**free)
                - Associated with RPG IV free-form (2013+) and fully-free RPG (2019+)

                Few-Shot Examples — Same Operation in Both Eras:

                Example 1 — Declaring a standalone variable:
                Fixed-format (D-spec):
                ```rpg
                D myName          S             50A
                ```
                Modern free-form:
                ```rpg
                dcl-s myName char(50);
                ```

                Example 2 — Calling a procedure and capturing the return value:
                Fixed-format (C-spec):
                ```rpg
                C                   EVAL      result = getTotal(custId)
                ```
                Modern free-form:
                ```rpg
                result = getTotal(custId);
                ```

                Default Behavior:
                - When the user does NOT specify an RPG era, ALWAYS default to modern free-form RPG syntax and conventions.
                - Only use fixed-format examples when the user explicitly asks about legacy/fixed-format RPG, C-specs, or older RPG versions.

                Era Mismatch Flagging:
                - If the retrieved source material uses a DIFFERENT RPG era than what the user is asking about, flag it with a brief note before your answer.
                - Example: "Note: the source material uses RPG IV fixed-format syntax. Here's the modern free-form equivalent..."
                - This helps the user understand the era context without confusion."""
            }
        ]
        
        messages.extend(self.conversations[conversation_id][-RESPONSE_CONFIG["max_conversation_history"]:])
        
        if context.strip():
            user_content = f"""Here is the relevant content from the uploaded PDF documents:

{context}

Based on this content, please answer the following question: {message}"""
            logger.info("Step 4: Context found - sending document-based request to OpenAI")
        else:
            user_content = f"""No specific documentation was found in the MC Press library for this query.

User question: {message}

If this question is about IBM i, RPG, ILE, CL, DB2, AS/400, or related technologies, you may provide a helpful response based on your general knowledge of these systems, but note that you don't have specific MC Press documentation on this topic.

If this question is clearly off-topic (not related to IBM i/midrange technologies), politely refuse and explain your specialization."""
            logger.info("Step 4: NO CONTEXT - sending general IBM i knowledge request to OpenAI")
        
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
                "sources": await self._format_sources(relevant_docs),
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
            
            # Era annotation: include only when rpg_era is set and not "general"
            rpg_era = doc.get("rpg_era")
            if rpg_era is not None and rpg_era != "general":
                source_info += f", Era: {rpg_era}"
            
            # Year annotation: include only when publication_year is set
            publication_year = doc.get("publication_year")
            if publication_year is not None:
                source_info += f", Year: {publication_year}"
            
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

    async def _filter_relevant_documents(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Filter documents by relevance threshold and log the decision process
        Handles both pgvector distance and fallback similarity metrics.
        Applies temporal re-ranking when era intent is detected.
        """
        RELEVANCE_THRESHOLD = self._get_dynamic_threshold(query)
        MAX_SOURCES = SEARCH_CONFIG["max_sources"]

        # Check if we're using pgvector or fallback
        using_pgvector = documents[0].get("using_pgvector", True) if documents else True
        logger.info(f"🔍 Vector Store Mode: {'pgvector' if using_pgvector else 'fallback (no pgvector)'}")
        logger.info(f"Query: '{query}'")
        logger.info(f"Initial search returned {len(documents)} documents")
        logger.info(f"Distance threshold: {RELEVANCE_THRESHOLD} (lower distance = better match)")

        # --- Temporal re-ranking ---
        # 1. Detect era intent from the query
        intent_detector = IntentDetector()
        era_intent = intent_detector.detect_era(query)
        logger.info(f"🕰️ Era intent detected: '{era_intent}'")

        # 2. Extract filenames and look up rpg_era metadata
        filenames = [
            doc.get("metadata", {}).get("filename", "")
            for doc in documents
        ]
        era_lookup = await self._lookup_rpg_eras(filenames)

        # 3. Attach rpg_era to each document
        for doc in documents:
            filename = doc.get("metadata", {}).get("filename", "")
            era_info = era_lookup.get(filename, {"rpg_era": "general", "publication_year": None})
            doc["rpg_era"] = era_info["rpg_era"]
            doc["publication_year"] = era_info["publication_year"]

        # 4. Apply temporal boost
        boost_amount = TEMPORAL_CONFIG["era_boost_amount"]
        documents = apply_temporal_boost(documents, era_intent, boost_amount)

        # 5. Re-sort by adjusted_distance and filter by threshold
        documents = sorted(documents, key=lambda x: x.get("adjusted_distance", x.get("distance", 2.0)))

        filtered_docs = []
        for i, doc in enumerate(documents):
            adjusted_distance = doc.get("adjusted_distance", doc.get("distance", 2.0))
            distance = doc.get("distance", 2.0)
            similarity = doc.get("similarity", 0.0)

            metadata = doc.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page", "N/A")

            # Log with appropriate precision
            logger.info(f"  Result {i+1}: {filename} (Page {page})")
            logger.info(f"    Distance: {distance:.4f}, Adjusted: {adjusted_distance:.4f}, Similarity: {similarity:.4f} ({similarity*100:.1f}%)")

            # Filter by adjusted distance threshold
            if adjusted_distance <= RELEVANCE_THRESHOLD:
                filtered_docs.append(doc)
                logger.info(f"    ✅ INCLUDED - Adjusted distance {adjusted_distance:.4f} <= threshold {RELEVANCE_THRESHOLD}")
            else:
                logger.info(f"    ❌ EXCLUDED - Adjusted distance {adjusted_distance:.4f} > threshold {RELEVANCE_THRESHOLD}")

        # Limit to MAX_SOURCES (already sorted by adjusted_distance)
        filtered_docs = filtered_docs[:MAX_SOURCES]

        logger.info(f"✅ Final result: {len(filtered_docs)} relevant documents included (max {MAX_SOURCES})")

        if len(filtered_docs) == 0:
            logger.warning("⚠️ No documents met the relevance threshold - user query may not match available content")
            logger.warning(f"   Consider lowering threshold (current: {RELEVANCE_THRESHOLD})")

        return filtered_docs
    
    async def _format_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                
                # Enrich with database metadata
                logger.info(f"About to enrich metadata for: {filename}")
                enriched_metadata = await self._enrich_source_metadata(filename)
                logger.info(f"Enrichment result: {enriched_metadata}")
                
                sources.append({
                    "filename": filename,
                    "page": page,
                    "type": content_type,
                    "distance": doc.get("distance", 0),
                    "title": enriched_metadata.get("title", filename.replace('.pdf', '')),  # Add title field
                    "author": enriched_metadata.get("author", metadata.get("author", "Unknown")),
                    "mc_press_url": enriched_metadata.get("mc_press_url", metadata.get("mc_press_url", "")),
                    "article_url": enriched_metadata.get("article_url"),
                    "document_type": enriched_metadata.get("document_type", "book"),
                    "authors": enriched_metadata.get("authors", []),
                    "publication_year": enriched_metadata.get("publication_year"),
                    "rpg_era": enriched_metadata.get("rpg_era", "general"),
                })
        
        return sources
    
    async def _lookup_rpg_eras(self, filenames: List[str]) -> Dict[str, Dict[str, Any]]:
        """Look up rpg_era and publication_year for a batch of filenames.

        Returns a dict mapping filename -> {"rpg_era": str, "publication_year": int|None}.
        Filenames not found in the books table default to {"rpg_era": "general", "publication_year": None}.
        Uses a single query for the entire batch to avoid repeated DB round-trips.
        """
        default_entry: Dict[str, Any] = {"rpg_era": "general", "publication_year": None}

        if not filenames:
            return {}

        # De-duplicate while preserving the caller's list
        unique_filenames = list(set(filenames))

        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                logger.warning("DATABASE_URL not available for rpg_era lookup")
                return {fn: dict(default_entry) for fn in filenames}

            conn = await asyncpg.connect(database_url)
            try:
                # Check if temporal columns exist before querying them
                temporal_cols = await conn.fetch("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'books' AND column_name IN ('publication_year', 'rpg_era')
                """)
                temporal_col_names = {row['column_name'] for row in temporal_cols}
                
                if 'rpg_era' not in temporal_col_names:
                    logger.info("rpg_era column not yet available — returning defaults")
                    return {fn: dict(default_entry) for fn in filenames}
                
                select_parts = ["filename", "rpg_era"]
                if 'publication_year' in temporal_col_names:
                    select_parts.append("publication_year")
                
                rows = await conn.fetch(
                    f"""
                    SELECT {', '.join(select_parts)}
                    FROM books
                    WHERE filename = ANY($1)
                    """,
                    unique_filenames,
                )

                result: Dict[str, Dict[str, Any]] = {}
                for row in rows:
                    result[row["filename"]] = {
                        "rpg_era": row["rpg_era"] or "general",
                        "publication_year": row.get("publication_year"),
                    }

                # Fill in defaults for filenames not found
                for fn in filenames:
                    if fn not in result:
                        result[fn] = dict(default_entry)

                logger.info(
                    "rpg_era lookup: queried %d unique filenames, found %d in books table",
                    len(unique_filenames),
                    len(rows),
                )
                return result
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Error looking up rpg_eras: {e}")
            return {fn: dict(default_entry) for fn in filenames}

    async def _enrich_source_metadata(self, filename: str) -> Dict[str, Any]:
        """Enrich source with full book and author metadata from database"""
        try:
            # Create direct database connection
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.warning("DATABASE_URL not available for enrichment")
                return {}
            
            logger.info(f"Enriching metadata for filename: {filename}")
            conn = await asyncpg.connect(database_url)
            
            try:
                # Check which temporal columns exist (safe for pre-migration state)
                temporal_cols = await conn.fetch("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'books' AND column_name IN ('publication_year', 'rpg_era')
                """)
                temporal_col_names = {row['column_name'] for row in temporal_cols}
                
                # Build SELECT dynamically to avoid errors if temporal columns don't exist yet
                select_fields = [
                    "b.id", "b.filename", "b.title",
                    "b.author as legacy_author", "b.mc_press_url",
                    "b.article_url", "b.document_type",
                ]
                if 'publication_year' in temporal_col_names:
                    select_fields.append("b.publication_year")
                if 'rpg_era' in temporal_col_names:
                    select_fields.append("b.rpg_era")
                
                # Get book metadata
                book_data = await conn.fetchrow(f"""
                    SELECT {', '.join(select_fields)}
                    FROM books b
                    WHERE b.filename = $1
                    LIMIT 1
                """, filename)
                
                if not book_data:
                    logger.info(f"No book found for filename: {filename}")
                    return {}
                
                logger.info(f"Found book: {book_data['title']} by {book_data['legacy_author']}")
                
                # Get detailed author information from document_authors table
                authors = await conn.fetch("""
                    SELECT 
                        a.id,
                        a.name,
                        a.site_url,
                        da.author_order
                    FROM document_authors da
                    JOIN authors a ON da.author_id = a.id
                    WHERE da.book_id = $1
                    ORDER BY da.author_order
                """, book_data['id'])
                
                # Determine author information
                if authors:
                    # Use multi-author data if available
                    author_names = ", ".join([author['name'] for author in authors])
                    authors_list = [
                        {
                            "id": author['id'],
                            "name": author['name'],
                            "site_url": author['site_url'],
                            "order": author['author_order']
                        }
                        for author in authors
                    ]
                    logger.info(f"Using multi-author data: {author_names}")
                else:
                    # Fall back to legacy author field
                    author_names = book_data['legacy_author'] or "Unknown"
                    authors_list = []
                    logger.info(f"Using legacy author: {author_names}")
                
                return {
                    "title": book_data['title'] or filename.replace('.pdf', ''),
                    "author": author_names,
                    "mc_press_url": book_data['mc_press_url'] or "",
                    "article_url": book_data['article_url'],
                    "document_type": book_data['document_type'] or "book",
                    "authors": authors_list,
                    "publication_year": book_data.get('publication_year'),
                    "rpg_era": (book_data.get('rpg_era') or "general"),
                }
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error enriching source metadata for {filename}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}