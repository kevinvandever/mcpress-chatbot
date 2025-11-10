"""
Database migration for Story-011: Conversation History
Creates tables for conversations, messages, and conversation analytics
"""

import os
import asyncio
import asyncpg
import logging

logger = logging.getLogger(__name__)

async def run_conversation_migration():
    """
    Create tables for conversation history feature:
    - conversations: Main conversation metadata
    - messages: Individual chat messages
    - conversation_analytics: AI-generated conversation insights
    """

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    print("🔄 Starting Story-011 conversation history migration...")

    conn = await asyncpg.connect(database_url)

    try:
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
        print("✅ Conversations table created")

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
        print("✅ Messages table created")

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
        print("✅ Conversation analytics table created")

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

        print("✅ All indexes created")

        # Verify tables exist
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('conversations', 'messages', 'conversation_analytics')
        """)

        print(f"\n✅ Migration complete! Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table['table_name']}")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()


async def verify_migration():
    """Verify that migration was successful"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    conn = await asyncpg.connect(database_url)

    try:
        # Check tables exist
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('conversations', 'messages', 'conversation_analytics')
        """)

        print(f"\n📊 Found {len(tables)} conversation tables:")
        for table in tables:
            table_name = table['table_name']
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"   - {table_name}: {count} rows")

        return len(tables) == 3

    finally:
        await conn.close()


if __name__ == "__main__":
    # Run migration
    asyncio.run(run_conversation_migration())

    # Verify
    print("\n🔍 Verifying migration...")
    success = asyncio.run(verify_migration())

    if success:
        print("\n✅ Story-011 migration verified successfully!")
    else:
        print("\n⚠️  Migration verification failed - some tables may be missing")
