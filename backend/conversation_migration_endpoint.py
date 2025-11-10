"""
Story-011 Conversation History Migration Endpoint
Creates tables for conversations, messages, and conversation analytics
Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS)
"""

from fastapi import APIRouter, HTTPException
import os

router = APIRouter()

# Will be set by main.py
_vector_store = None

def set_vector_store(store):
    global _vector_store
    _vector_store = store


@router.post("/run-story11-conversation-migration")
async def run_story11_migration():
    """
    Create tables for Story-011 Conversation History:
    - conversations: Main conversation metadata
    - messages: Individual chat messages
    - conversation_analytics: AI-generated conversation insights

    Safe to call multiple times - uses IF NOT EXISTS
    """

    if not _vector_store or not hasattr(_vector_store, 'pool'):
        return {
            "error": "Database not initialized",
            "message": "Vector store or connection pool not available"
        }

    try:
        results = []

        async with _vector_store.pool.acquire() as conn:
            # Create conversations table
            print("📊 Creating conversations table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    tags TEXT[] DEFAULT '{}',
                    is_favorite BOOLEAN DEFAULT FALSE,
                    is_archived BOOLEAN DEFAULT FALSE,
                    message_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results.append("✅ Conversations table created")

            # Create messages table
            print("📊 Creating messages table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    tokens_used INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)
            results.append("✅ Messages table created")

            # Create conversation_analytics table
            print("📊 Creating conversation_analytics table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_analytics (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    topics TEXT[],
                    mentioned_books TEXT[],
                    code_languages TEXT[],
                    difficulty_level TEXT,
                    primary_category TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    UNIQUE(conversation_id)
                )
            """)
            results.append("✅ Conversation analytics table created")

            # Create indexes for performance
            print("📊 Creating indexes...")

            # Conversations indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id, last_message_at DESC)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_tags
                ON conversations USING GIN(tags)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_search
                ON conversations USING GIN(to_tsvector('english', title || ' ' || COALESCE(summary, '')))
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_favorite
                ON conversations(user_id, is_favorite) WHERE is_favorite = true
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_archived
                ON conversations(user_id, is_archived)
            """)

            # Messages indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, created_at)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_search
                ON messages USING GIN(to_tsvector('english', content))
            """)

            results.append("✅ All indexes created")

            # Verify tables exist
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('conversations', 'messages', 'conversation_analytics')
            """)

            # Get row counts
            conversations_count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
            messages_count = await conn.fetchval("SELECT COUNT(*) FROM messages")
            analytics_count = await conn.fetchval("SELECT COUNT(*) FROM conversation_analytics")

            return {
                "success": True,
                "message": "Story-011 Conversation History migration completed",
                "results": results,
                "tables_created": len(tables),
                "table_names": [t['table_name'] for t in tables],
                "row_counts": {
                    "conversations": conversations_count,
                    "messages": messages_count,
                    "conversation_analytics": analytics_count
                }
            }

    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
