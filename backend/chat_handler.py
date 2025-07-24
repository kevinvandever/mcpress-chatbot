import openai
from typing import AsyncGenerator, Dict, Any, List
import os
import json
from datetime import datetime

class ChatHandler:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversations = {}
        
    async def stream_response(self, message: str, conversation_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        relevant_docs = await self.vector_store.search(message, n_results=5)
        
        context = self._build_context(relevant_docs)
        
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
        
        messages.append({
            "role": "user",
            "content": f"""Here is the relevant content from the uploaded PDF documents:

{context}

Based on this content, please answer the following question: {message}"""
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
    
    def _format_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sources = []
        seen = set()
        
        for doc in documents:
            metadata = doc.get("metadata", {})
            key = f"{metadata.get('filename', 'Unknown')}-{metadata.get('page', 'N/A')}"
            
            if key not in seen:
                seen.add(key)
                sources.append({
                    "filename": metadata.get("filename", "Unknown"),
                    "page": metadata.get("page", "N/A"),
                    "type": metadata.get("type", "text"),
                    "relevance": 1 - doc.get("distance", 0)
                })
        
        return sources