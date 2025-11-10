"""
Pydantic models for Story-011 Conversation History
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class Conversation(BaseModel):
    """Main conversation model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    summary: Optional[str] = None  # AI-generated summary
    tags: List[str] = []
    is_favorite: bool = False
    is_archived: bool = False
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Message(BaseModel):
    """Individual chat message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    metadata: Dict[str, Any] = {}  # Code snippets, book references, etc.
    tokens_used: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationAnalytics(BaseModel):
    """AI-extracted metadata about conversation"""
    id: Optional[int] = None
    conversation_id: str
    topics: List[str] = []  # AI-detected topics
    mentioned_books: List[str] = []  # Referenced books
    code_languages: List[str] = []  # Languages discussed
    difficulty_level: Optional[str] = None  # 'beginner', 'intermediate', 'advanced'
    primary_category: Optional[str] = None  # RPG, SQL, CL, etc.
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Request/Response models for API

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    initial_message: str
    user_id: str


class AddMessageRequest(BaseModel):
    """Request to add a message to conversation"""
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    metadata: Dict[str, Any] = {}
    tokens_used: Optional[int] = None


class UpdateConversationRequest(BaseModel):
    """Request to update conversation metadata"""
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None
    summary: Optional[str] = None


class ConversationListFilters(BaseModel):
    """Filters for listing conversations"""
    is_archived: Optional[bool] = None
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    """Response for listing conversations"""
    conversations: List[Conversation]
    total: int
    page: int
    per_page: int
    total_pages: int


class ConversationWithMessages(BaseModel):
    """Conversation with full message history"""
    conversation: Conversation
    messages: List[Message]


class ConversationSearchRequest(BaseModel):
    """Request to search conversations"""
    query: str
    page: int = 1
    per_page: int = 20


class BulkOperationRequest(BaseModel):
    """Request for bulk operations on conversations"""
    conversation_ids: List[str]
    operation: str  # 'archive', 'delete', 'tag'
    tags: Optional[List[str]] = None  # For tag operation


class ConversationStatsResponse(BaseModel):
    """User conversation statistics"""
    total_conversations: int
    total_messages: int
    favorite_count: int
    archived_count: int
    most_used_tags: List[Dict[str, Any]]
    conversations_this_week: int
    conversations_this_month: int
