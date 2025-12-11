"""
Document-Author Relationship API Routes
Feature: multi-author-metadata-enhancement

Provides REST API endpoints for managing document-author relationships:
- Add authors to documents
- Remove authors from documents
- Reorder authors
- Get document with authors
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

document_author_router = APIRouter(prefix="/api/documents", tags=["document-authors"])

# Initialize services (will be set by main.py)
_author_service: Optional[AuthorService] = None
_doc_author_service: Optional[DocumentAuthorService] = None
_vector_store = None


def set_document_author_services(
    author_service: AuthorService,
    doc_author_service: DocumentAuthorService,
    vector_store
):
    """Set the service instances (called from main.py)"""
    global _author_service, _doc_author_service, _vector_store
    _author_service = author_service
    _doc_author_service = doc_author_service
    _vector_store = vector_store


# =====================================================
# Request/Response Models
# =====================================================

class AuthorInfo(BaseModel):
    """Author information in document response"""
    id: int
    name: str
    site_url: Optional[str] = None
    order: int


class AddAuthorRequest(BaseModel):
    """Request to add an author to a document"""
    author_name: str
    author_site_url: Optional[str] = None
    order: Optional[int] = None
    
    @validator('author_site_url')
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


class ReorderAuthorsRequest(BaseModel):
    """Request to reorder authors for a document"""
    author_ids: List[int]


class DocumentWithAuthorsResponse(BaseModel):
    """Document information with authors"""
    id: int
    filename: str
    title: str
    authors: List[AuthorInfo]
    document_type: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    article_url: Optional[str] = None
    mc_press_url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    year: Optional[int] = None
    total_pages: Optional[int] = None
    processed_at: Optional[str] = None


# =====================================================
# API Endpoints
# =====================================================

@document_author_router.post("/{document_id}/authors")
async def add_author_to_document(document_id: int, request: AddAuthorRequest):
    """
    Add an author to a document
    
    Creates a new author if the name doesn't exist, or reuses existing author.
    Prevents duplicate author associations.
    
    **Validates:** Requirements 1.1, 1.4, 5.3, 5.4
    """
    if not _author_service or not _doc_author_service:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Get or create the author
        author_id = await _author_service.get_or_create_author(
            name=request.author_name,
            site_url=request.author_site_url
        )
        
        # Add author to document
        await _doc_author_service.add_author_to_document(
            book_id=document_id,
            author_id=author_id,
            order=request.order
        )
        
        return {
            "message": "Author added successfully",
            "document_id": document_id,
            "author_id": author_id
        }
    except ValueError as e:
        # Handle validation errors (duplicate, not found, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add author: {str(e)}")


@document_author_router.delete("/{document_id}/authors/{author_id}")
async def remove_author_from_document(document_id: int, author_id: int):
    """
    Remove an author from a document
    
    Prevents removing the last author (documents must have at least one author).
    
    **Validates:** Requirements 1.5, 5.7
    """
    if not _doc_author_service:
        raise HTTPException(status_code=503, detail="Document author service not initialized")
    
    try:
        await _doc_author_service.remove_author_from_document(
            book_id=document_id,
            author_id=author_id
        )
        
        return {
            "message": "Author removed successfully",
            "document_id": document_id,
            "author_id": author_id
        }
    except ValueError as e:
        # Handle validation errors (last author, not found, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove author: {str(e)}")


@document_author_router.put("/{document_id}/authors/order")
async def reorder_document_authors(document_id: int, request: ReorderAuthorsRequest):
    """
    Reorder authors for a document
    
    Updates the display order of authors. The order of author_ids in the request
    determines the new order (first = 0).
    
    **Validates:** Requirements 1.3
    """
    if not _doc_author_service:
        raise HTTPException(status_code=503, detail="Document author service not initialized")
    
    try:
        await _doc_author_service.reorder_authors(
            book_id=document_id,
            author_ids=request.author_ids
        )
        
        return {
            "message": "Authors reordered successfully",
            "document_id": document_id,
            "author_ids": request.author_ids
        }
    except ValueError as e:
        # Handle validation errors (mismatched IDs, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reorder authors: {str(e)}")


@document_author_router.get("/{document_id}", response_model=DocumentWithAuthorsResponse)
async def get_document_with_authors(document_id: int):
    """
    Get document details including all authors
    
    Returns complete document information with authors in order.
    Includes document_type field.
    
    **Validates:** Requirements 1.3, 2.4, 5.1
    """
    if not _author_service or not _vector_store:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Get document from vector store
        conn = await _vector_store._get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, filename, title, category, subcategory,
                           document_type, article_url, mc_press_url,
                           description, tags, year, total_pages, processed_at
                    FROM books
                    WHERE id = %s
                """, (document_id,))
                
                row = await cursor.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
                
                # Get authors for this document
                authors = await _author_service.get_authors_for_document(document_id)
                
                return DocumentWithAuthorsResponse(
                    id=row[0],
                    filename=row[1],
                    title=row[2] or row[1].replace('.pdf', ''),
                    authors=[
                        AuthorInfo(
                            id=author['id'],
                            name=author['name'],
                            site_url=author['site_url'],
                            order=author['order']
                        )
                        for author in authors
                    ],
                    document_type=row[5] or 'book',
                    category=row[3],
                    subcategory=row[4],
                    article_url=row[6],
                    mc_press_url=row[7],
                    description=row[8],
                    tags=row[9] or [],
                    year=row[10],
                    total_pages=row[11],
                    processed_at=row[12].isoformat() if row[12] else None
                )
        finally:
            await conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")
