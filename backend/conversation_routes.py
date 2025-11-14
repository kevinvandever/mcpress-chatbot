"""
API Routes for Story-011 Conversation History
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime

# Handle Railway vs local imports
try:
    from conversation_models import (
        Conversation,
        Message,
        CreateConversationRequest,
        AddMessageRequest,
        UpdateConversationRequest,
        ConversationListFilters,
        ConversationListResponse,
        ConversationWithMessages,
        ConversationSearchRequest,
        BulkOperationRequest,
        ConversationStatsResponse
    )
except ImportError:
    from backend.conversation_models import (
        Conversation,
        Message,
        CreateConversationRequest,
        AddMessageRequest,
        UpdateConversationRequest,
        ConversationListFilters,
        ConversationListResponse,
        ConversationWithMessages,
        ConversationSearchRequest,
        BulkOperationRequest,
        ConversationStatsResponse
    )

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Will be set by main.py
_conversation_service = None


def set_conversation_service(service):
    global _conversation_service
    _conversation_service = service


def get_conversation_service():
    if _conversation_service is None:
        raise HTTPException(status_code=500, detail="Conversation service not initialized")
    return _conversation_service


# Conversation Management Endpoints

@router.post("", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest,
    service = Depends(get_conversation_service)
):
    """Create a new conversation"""
    try:
        conversation = await service.create_conversation(
            user_id=request.user_id,
            initial_message=request.initial_message
        )
        return conversation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=ConversationListResponse)
async def search_conversations(
    user_id: str = Query(..., description="User ID"),
    query: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service = Depends(get_conversation_service)
):
    """Search conversations by title, content, or tags"""
    print(f"🔍 [ROUTE] Search endpoint called: user_id={user_id}, query={query}, page={page}, per_page={per_page}")
    try:
        conversations, total = await service.search_conversations(
            user_id=user_id,
            query=query,
            page=page,
            per_page=per_page
        )

        total_pages = (total + per_page - 1) // per_page

        print(f"🔍 [ROUTE] Search completed: found {len(conversations)} conversations, total={total}")

        # Return empty results if no conversations found (not an error)
        return ConversationListResponse(
            conversations=conversations,
            total=total or 0,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except ValueError as e:
        # Conversation not found or access denied
        print(f"🔍 [ROUTE] Search ValueError: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log the actual error for debugging
        print(f"🔍 [ROUTE] Search error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_archived: Optional[bool] = Query(None),
    is_favorite: Optional[bool] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    service = Depends(get_conversation_service)
):
    """List user's conversations with filtering and pagination"""
    try:
        # Parse tags if provided
        tag_list = tags.split(",") if tags else None

        # Build filters
        filters = ConversationListFilters(
            is_archived=is_archived,
            is_favorite=is_favorite,
            tags=tag_list,
            date_from=date_from,
            date_to=date_to
        )

        conversations, total = await service.list_conversations(
            user_id=user_id,
            filters=filters,
            page=page,
            per_page=per_page
        )

        total_pages = (total + per_page - 1) // per_page

        return ConversationListResponse(
            conversations=conversations,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Get conversation with all messages"""
    try:
        conversation, messages = await service.get_conversation_with_messages(
            conversation_id=conversation_id,
            user_id=user_id
        )

        return ConversationWithMessages(
            conversation=conversation,
            messages=messages
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Update conversation metadata"""
    try:
        # Build updates dict from request (only include non-None values)
        updates = {}
        if request.title is not None:
            updates['title'] = request.title
        if request.tags is not None:
            updates['tags'] = request.tags
        if request.is_favorite is not None:
            updates['is_favorite'] = request.is_favorite
        if request.is_archived is not None:
            updates['is_archived'] = request.is_archived
        if request.summary is not None:
            updates['summary'] = request.summary

        conversation = await service.update_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            updates=updates
        )

        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Delete conversation and all messages"""
    try:
        await service.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id
        )
        return {"status": "success", "message": f"Conversation {conversation_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Message Endpoints

@router.post("/{conversation_id}/messages", response_model=Message)
async def add_message(
    conversation_id: str,
    request: AddMessageRequest,
    service = Depends(get_conversation_service)
):
    """Add a message to conversation"""
    try:
        message = await service.add_message(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
            tokens_used=request.tokens_used
        )
        return message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Quick Action Endpoints

@router.post("/{conversation_id}/favorite")
async def toggle_favorite(
    conversation_id: str,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Toggle conversation favorite status (flip current value)"""
    try:
        # Get current conversation to read current favorite status
        conv, _ = await service.get_conversation_with_messages(conversation_id, user_id)

        # Flip the favorite status
        new_value = not conv.is_favorite

        # Update with new value
        conversation = await service.update_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            updates={'is_favorite': new_value}
        )
        return {"status": "success", "is_favorite": conversation.is_favorite}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/archive")
async def toggle_archive(
    conversation_id: str,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Toggle conversation archive status (flip current value)"""
    try:
        # Get current conversation to read current archive status
        conv, _ = await service.get_conversation_with_messages(conversation_id, user_id)

        # Flip the archive status
        new_value = not conv.is_archived

        # Update with new value
        conversation = await service.update_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            updates={'is_archived': new_value}
        )
        return {"status": "success", "is_archived": conversation.is_archived}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Bulk Operations

@router.post("/bulk/archive")
async def bulk_archive(
    request: BulkOperationRequest,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Archive multiple conversations"""
    try:
        results = []
        for conv_id in request.conversation_ids:
            try:
                await service.update_conversation(
                    conversation_id=conv_id,
                    user_id=user_id,
                    updates={'is_archived': True}
                )
                results.append({"conversation_id": conv_id, "status": "success"})
            except Exception as e:
                results.append({"conversation_id": conv_id, "status": "error", "error": str(e)})

        return {"status": "completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/delete")
async def bulk_delete(
    request: BulkOperationRequest,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Delete multiple conversations"""
    try:
        results = []
        for conv_id in request.conversation_ids:
            try:
                await service.delete_conversation(
                    conversation_id=conv_id,
                    user_id=user_id
                )
                results.append({"conversation_id": conv_id, "status": "success"})
            except Exception as e:
                results.append({"conversation_id": conv_id, "status": "error", "error": str(e)})

        return {"status": "completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/tag")
async def bulk_tag(
    request: BulkOperationRequest,
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Add tags to multiple conversations"""
    try:
        if not request.tags:
            raise HTTPException(status_code=400, detail="Tags are required for tag operation")

        results = []
        for conv_id in request.conversation_ids:
            try:
                # Get current conversation to merge tags
                conversation, _ = await service.get_conversation_with_messages(conv_id, user_id)
                existing_tags = set(conversation.tags)
                new_tags = existing_tags.union(set(request.tags))

                await service.update_conversation(
                    conversation_id=conv_id,
                    user_id=user_id,
                    updates={'tags': list(new_tags)}
                )
                results.append({"conversation_id": conv_id, "status": "success"})
            except Exception as e:
                results.append({"conversation_id": conv_id, "status": "error", "error": str(e)})

        return {"status": "completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Statistics Endpoint

@router.get("/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(
    user_id: str = Query(..., description="User ID"),
    service = Depends(get_conversation_service)
):
    """Get user conversation statistics"""
    try:
        stats = await service.get_conversation_stats(user_id=user_id)
        return ConversationStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
