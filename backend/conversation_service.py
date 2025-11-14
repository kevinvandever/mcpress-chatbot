"""
Conversation Service for Story-011 Conversation History
Manages conversation CRUD operations, message persistence, and search
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Try to import anthropic (optional for AI title generation)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ anthropic package not available - AI title generation will be disabled")

# Handle Railway vs local imports
try:
    from conversation_models import (
        Conversation,
        Message,
        ConversationAnalytics,
        ConversationListFilters
    )
except ImportError:
    from backend.conversation_models import (
        Conversation,
        Message,
        ConversationAnalytics,
        ConversationListFilters
    )


class ConversationService:
    """Service for managing conversation history"""

    def __init__(self, vector_store):
        """
        Initialize conversation service

        Args:
            vector_store: PostgreSQL vector store with connection pool
        """
        self.vector_store = vector_store
        self.claude_api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')

        if not ANTHROPIC_AVAILABLE:
            print("⚠️ anthropic package not available - AI title generation disabled")
            self.claude_client = None
        elif not self.claude_api_key:
            print("⚠️ Warning: No Claude API key found. AI title generation will be disabled.")
            self.claude_client = None
        else:
            self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)

    async def create_conversation(
        self,
        user_id: str,
        initial_message: str
    ) -> Conversation:
        """Create new conversation with AI-generated title"""

        # Generate title from first message
        title = await self._generate_title(initial_message)

        conversation = Conversation(
            user_id=user_id,
            title=title,
            message_count=0  # Will increment when first message is added
        )

        await self._save_conversation(conversation)

        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = {},
        tokens_used: Optional[int] = None
    ) -> Message:
        """Add message to conversation"""

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata,
            tokens_used=tokens_used
        )

        await self._save_message(message)

        # Update conversation stats
        await self._update_conversation_stats(conversation_id)

        return message

    async def list_conversations(
        self,
        user_id: str,
        filters: Optional[ConversationListFilters] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Conversation], int]:
        """List user's conversations with filtering and pagination"""

        query_conditions = [f"user_id = $1"]
        params = [user_id]
        param_index = 2

        # Apply filters
        if filters:
            if filters.is_archived is not None:
                query_conditions.append(f"is_archived = ${param_index}")
                params.append(filters.is_archived)
                param_index += 1

            if filters.is_favorite:
                query_conditions.append(f"is_favorite = ${param_index}")
                params.append(True)
                param_index += 1

            if filters.tags:
                # Check if any of the filter tags match
                tag_conditions = " OR ".join([f"${param_index + i} = ANY(tags)" for i in range(len(filters.tags))])
                query_conditions.append(f"({tag_conditions})")
                params.extend(filters.tags)
                param_index += len(filters.tags)

            if filters.date_from:
                # Convert date string to start of day timestamp
                query_conditions.append(f"DATE(created_at) >= ${param_index}::date")
                params.append(filters.date_from)
                param_index += 1

            if filters.date_to:
                # Convert date string to end of day timestamp
                query_conditions.append(f"DATE(created_at) <= ${param_index}::date")
                params.append(filters.date_to)
                param_index += 1

        # Build query
        where_clause = " AND ".join(query_conditions)
        offset = (page - 1) * per_page

        # Get conversations
        query = f"""
            SELECT * FROM conversations
            WHERE {where_clause}
            ORDER BY last_message_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        params.extend([per_page, offset])

        async with self.vector_store.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            # Get total count
            count_query = f"SELECT COUNT(*) FROM conversations WHERE {where_clause}"
            total = await conn.fetchval(count_query, *params[:-2])  # Exclude limit/offset

        conversations = [self._row_to_conversation(row) for row in rows]

        return conversations, total

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Conversation], int]:
        """Full-text search across conversations and messages"""

        offset = (page - 1) * per_page

        search_query = """
            SELECT DISTINCT c.* FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = $1
            AND (
                c.title ILIKE $2
                OR c.summary ILIKE $2
                OR m.content ILIKE $2
                OR $3 = ANY(c.tags)
            )
            ORDER BY c.last_message_at DESC
            LIMIT $4 OFFSET $5
        """

        pattern = f"%{query}%"

        async with self.vector_store.pool.acquire() as conn:
            rows = await conn.fetch(search_query, user_id, pattern, query, per_page, offset)

            # Get total count
            count_query = """
                SELECT COUNT(DISTINCT c.id) FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = $1
                AND (
                    c.title ILIKE $2
                    OR c.summary ILIKE $2
                    OR m.content ILIKE $2
                    OR $3 = ANY(c.tags)
                )
            """
            total = await conn.fetchval(count_query, user_id, pattern, query)

        conversations = [self._row_to_conversation(row) for row in rows]

        return conversations, total

    async def get_conversation_with_messages(
        self,
        conversation_id: str,
        user_id: str
    ) -> Tuple[Conversation, List[Message]]:
        """Get conversation with all messages"""

        async with self.vector_store.pool.acquire() as conn:
            # Get conversation
            conv_row = await conn.fetchrow(
                "SELECT * FROM conversations WHERE id = $1 AND user_id = $2",
                conversation_id,
                user_id
            )

            if not conv_row:
                raise ValueError(f"Conversation {conversation_id} not found or access denied")

            conversation = self._row_to_conversation(conv_row)

            # Get messages
            msg_rows = await conn.fetch(
                "SELECT * FROM messages WHERE conversation_id = $1 ORDER BY created_at ASC",
                conversation_id
            )

            messages = [self._row_to_message(row) for row in msg_rows]

        return conversation, messages

    async def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Conversation:
        """Update conversation metadata"""

        async with self.vector_store.pool.acquire() as conn:
            # Verify ownership
            exists = await conn.fetchval(
                "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
                conversation_id,
                user_id
            )

            if not exists:
                raise ValueError(f"Conversation {conversation_id} not found or access denied")

            # Build update query
            set_clauses = []
            params = []
            param_index = 1

            for key, value in updates.items():
                if key in ['title', 'summary', 'tags', 'is_favorite', 'is_archived']:
                    set_clauses.append(f"{key} = ${param_index}")
                    params.append(value)
                    param_index += 1

            # Always update updated_at
            set_clauses.append(f"updated_at = ${param_index}")
            params.append(datetime.utcnow())
            param_index += 1

            params.extend([conversation_id, user_id])

            update_query = f"""
                UPDATE conversations
                SET {', '.join(set_clauses)}
                WHERE id = ${param_index} AND user_id = ${param_index + 1}
                RETURNING *
            """

            row = await conn.fetchrow(update_query, *params)

        return self._row_to_conversation(row)

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> None:
        """Delete conversation and all messages (CASCADE handles messages)"""

        async with self.vector_store.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM conversations WHERE id = $1 AND user_id = $2",
                conversation_id,
                user_id
            )

            if result == "DELETE 0":
                raise ValueError(f"Conversation {conversation_id} not found or access denied")

    async def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user conversation statistics"""

        async with self.vector_store.pool.acquire() as conn:
            # Total conversations and messages
            total_convs = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE user_id = $1",
                user_id
            )

            total_msgs = await conn.fetchval("""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = $1
            """, user_id)

            # Favorites and archived
            favorite_count = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE user_id = $1 AND is_favorite = true",
                user_id
            )

            archived_count = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE user_id = $1 AND is_archived = true",
                user_id
            )

            # Most used tags
            tag_rows = await conn.fetch("""
                SELECT unnest(tags) as tag, COUNT(*) as count
                FROM conversations
                WHERE user_id = $1 AND array_length(tags, 1) > 0
                GROUP BY tag
                ORDER BY count DESC
                LIMIT 10
            """, user_id)

            most_used_tags = [{"tag": row['tag'], "count": row['count']} for row in tag_rows]

            # Recent conversations
            convs_this_week = await conn.fetchval("""
                SELECT COUNT(*) FROM conversations
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '7 days'
            """, user_id)

            convs_this_month = await conn.fetchval("""
                SELECT COUNT(*) FROM conversations
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '30 days'
            """, user_id)

        return {
            "total_conversations": total_convs,
            "total_messages": total_msgs,
            "favorite_count": favorite_count,
            "archived_count": archived_count,
            "most_used_tags": most_used_tags,
            "conversations_this_week": convs_this_week,
            "conversations_this_month": convs_this_month
        }

    # Private helper methods

    async def _save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to database"""

        async with self.vector_store.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO conversations (
                    id, user_id, title, summary, tags, is_favorite, is_archived,
                    message_count, created_at, updated_at, last_message_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                conversation.id,
                conversation.user_id,
                conversation.title,
                conversation.summary,
                conversation.tags,
                conversation.is_favorite,
                conversation.is_archived,
                conversation.message_count,
                conversation.created_at,
                conversation.updated_at,
                conversation.last_message_at
            )

    async def _save_message(self, message: Message) -> None:
        """Save message to database"""

        async with self.vector_store.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO messages (
                    id, conversation_id, role, content, metadata, tokens_used, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                message.id,
                message.conversation_id,
                message.role,
                message.content,
                json.dumps(message.metadata),
                message.tokens_used,
                message.created_at
            )

    async def _update_conversation_stats(self, conversation_id: str) -> None:
        """Update conversation message count and last_message_at"""

        async with self.vector_store.pool.acquire() as conn:
            await conn.execute("""
                UPDATE conversations
                SET message_count = (
                    SELECT COUNT(*) FROM messages WHERE conversation_id = $1
                ),
                last_message_at = NOW(),
                updated_at = NOW()
                WHERE id = $1
            """, conversation_id)

    async def _generate_title(self, first_message: str) -> str:
        """Generate conversation title using Claude"""

        if not self.claude_client:
            # Fallback to truncated message
            return first_message[:57] + "..." if len(first_message) > 60 else first_message

        try:
            prompt = f"""Generate a concise title (max 60 characters) for a conversation that starts with:

"{first_message[:200]}"

Title should be descriptive but brief. Respond with ONLY the title, no explanation."""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            title = response.content[0].text.strip()

            # Remove quotes if Claude added them
            title = title.strip('"').strip("'")

            # Fallback if too long
            if len(title) > 60:
                title = first_message[:57] + "..."

            return title

        except Exception as e:
            print(f"⚠️ Error generating title: {e}")
            # Fallback to truncated message
            return first_message[:57] + "..." if len(first_message) > 60 else first_message

    def _row_to_conversation(self, row) -> Conversation:
        """Convert database row to Conversation model"""

        return Conversation(
            id=row['id'],
            user_id=row['user_id'],
            title=row['title'],
            summary=row['summary'],
            tags=row['tags'] or [],
            is_favorite=row['is_favorite'],
            is_archived=row['is_archived'],
            message_count=row['message_count'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_message_at=row['last_message_at']
        )

    def _row_to_message(self, row) -> Message:
        """Convert database row to Message model"""

        # Parse metadata JSON if it's a string
        metadata = row['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}

        return Message(
            id=row['id'],
            conversation_id=row['conversation_id'],
            role=row['role'],
            content=row['content'],
            metadata=metadata,
            tokens_used=row['tokens_used'],
            created_at=row['created_at']
        )
