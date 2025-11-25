"""
Author Management API Routes
Feature: multi-author-metadata-enhancement

Provides REST API endpoints for managing authors:
- Search authors (autocomplete)
- Get author details
- Update author information
- Get documents by author
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, validator
from typing import List, Optional
import re

# Import services
try:
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
except ImportError:
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService

author_router = APIRouter(prefix="/api/authors", tags=["authors"])

# Initialize services (will be set by main.py)
_author_service: Optional[AuthorService] = None
_doc_author_service: Optional[DocumentAuthorService] = None


def set_author_services(author_service: AuthorService, doc_author_service: DocumentAuthorService):
    """Set the service instances (called from main.py)"""
    global _author_service, _doc_author_service
    _author_service = author_service
    _doc_author_service = doc_author_service


# =====================================================
# Request/Response Models
# =====================================================

class AuthorResponse(BaseModel):
    """Author information response"""
    id: int
    name: str
    site_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    document_count: Optional[int] = None


class AuthorUpdateRequest(BaseModel):
    """Request to update author information"""
    name: Optional[str] = None
    site_url: Optional[str] = None
    
    @validator('site_url')
    def validate_url(cls, v):
        """Validate URL format"""
        if v is None or v == '':
            return None
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format. Must start with http:// or https://')
        
        return v


class DocumentResponse(BaseModel):
    """Document information response"""
    id: int
    filename: str
    title: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    document_type: str
    total_pages: Optional[int] = None
    processed_at: Optional[str] = None
    author_order: int


# =====================================================
# API Endpoints
# =====================================================

@author_router.get("/search", response_model=List[AuthorResponse])
async def search_authors(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results")
):
    """
    Search authors by name for autocomplete
    
    Returns authors matching the search query with their document counts.
    
    **Validates:** Requirements 5.2, 8.1
    """
    if not _author_service:
        raise HTTPException(status_code=503, detail="Author service not initialized")
    
    try:
        authors = await _author_service.search_authors(q, limit)
        
        return [
            AuthorResponse(
                id=author['id'],
                name=author['name'],
                site_url=author['site_url'],
                document_count=author['document_count']
            )
            for author in authors
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@author_router.get("/{author_id}", response_model=AuthorResponse)
async def get_author(author_id: int):
    """
    Get author details by ID
    
    Returns complete author information including document count.
    
    **Validates:** Requirements 3.1, 3.3, 8.3
    """
    if not _author_service:
        raise HTTPException(status_code=503, detail="Author service not initialized")
    
    try:
        author = await _author_service.get_author_by_id(author_id)
        
        if not author:
            raise HTTPException(status_code=404, detail=f"Author {author_id} not found")
        
        return AuthorResponse(
            id=author['id'],
            name=author['name'],
            site_url=author['site_url'],
            created_at=author['created_at'].isoformat() if author.get('created_at') else None,
            updated_at=author['updated_at'].isoformat() if author.get('updated_at') else None,
            document_count=author.get('document_count', 0)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get author: {str(e)}")


@author_router.patch("/{author_id}", response_model=AuthorResponse)
async def update_author(author_id: int, update: AuthorUpdateRequest):
    """
    Update author information
    
    Updates propagate to all documents associated with this author.
    
    **Validates:** Requirements 3.2, 5.6
    """
    if not _author_service:
        raise HTTPException(status_code=503, detail="Author service not initialized")
    
    # Validate at least one field is provided
    if update.name is None and update.site_url is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field (name or site_url) must be provided"
        )
    
    try:
        # Update the author
        await _author_service.update_author(
            author_id=author_id,
            name=update.name,
            site_url=update.site_url
        )
        
        # Fetch and return updated author
        author = await _author_service.get_author_by_id(author_id)
        
        if not author:
            raise HTTPException(status_code=404, detail=f"Author {author_id} not found")
        
        return AuthorResponse(
            id=author['id'],
            name=author['name'],
            site_url=author['site_url'],
            created_at=author['created_at'].isoformat() if author.get('created_at') else None,
            updated_at=author['updated_at'].isoformat() if author.get('updated_at') else None,
            document_count=author.get('document_count', 0)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update author: {str(e)}")


@author_router.get("/{author_id}/documents", response_model=List[DocumentResponse])
async def get_author_documents(
    author_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset for pagination")
):
    """
    Get all documents by an author
    
    Returns documents with pagination support.
    
    **Validates:** Requirements 8.1
    """
    if not _doc_author_service:
        raise HTTPException(status_code=503, detail="Document author service not initialized")
    
    try:
        documents = await _doc_author_service.get_documents_by_author(
            author_id=author_id,
            limit=limit,
            offset=offset
        )
        
        return [
            DocumentResponse(
                id=doc['id'],
                filename=doc['filename'],
                title=doc['title'],
                category=doc.get('category'),
                subcategory=doc.get('subcategory'),
                document_type=doc['document_type'],
                total_pages=doc.get('total_pages'),
                processed_at=doc['processed_at'].isoformat() if doc.get('processed_at') else None,
                author_order=doc['author_order']
            )
            for doc in documents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")


@author_router.get("/", response_model=List[AuthorResponse])
async def list_authors(
    limit: int = Query(50, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset for pagination")
):
    """
    List all authors with pagination
    
    Returns authors ordered by name.
    """
    if not _author_service:
        raise HTTPException(status_code=503, detail="Author service not initialized")
    
    try:
        # Use search with empty query to get all authors
        # This is a simple implementation - could be optimized with a dedicated method
        authors = await _author_service.search_authors("", limit=limit)
        
        return [
            AuthorResponse(
                id=author['id'],
                name=author['name'],
                site_url=author['site_url'],
                document_count=author['document_count']
            )
            for author in authors
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list authors: {str(e)}")
