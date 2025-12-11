"""
Document Author Service for Multi-Author Metadata Enhancement
Feature: multi-author-metadata-enhancement

Manages document-author relationship operations including:
- Adding authors to documents
- Removing authors from documents
- Reordering authors
- Finding documents by author
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg


class DocumentAuthorService:
    """Service for managing document-author relationships"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize document-author service

        Args:
            database_url: PostgreSQL database URL (defaults to DATABASE_URL env var)
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.pool = None

    async def init_database(self):
        """Initialize database connection pool"""
        if self.pool:
            return
        
        self.pool = await asyncpg.create_pool(
            self.database_url,
            statement_cache_size=0,  # Fix for pgbouncer compatibility
            min_size=1,
            max_size=10,
            command_timeout=60
        )
    
    async def _ensure_pool(self):
        """Ensure connection pool is initialized (lazy initialization)"""
        if not self.pool:
            await self.init_database()

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def add_author_to_document(
        self,
        book_id: int,
        author_id: int,
        order: Optional[int] = None
    ) -> None:
        """
        Associate an author with a document with duplicate prevention.
        
        Prevents adding the same author to a document multiple times.
        If order is not specified, adds author at the end.
        
        Args:
            book_id: ID of document (book)
            author_id: ID of author
            order: Optional position in author list (0 = first)
            
        Raises:
            ValueError: If document or author not found, or duplicate association
            
        Validates: Requirements 1.1, 1.4
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            # Verify document exists
            doc_exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM books WHERE id = $1)
            """, book_id)
            
            if not doc_exists:
                raise ValueError(f"Document with ID {book_id} not found")
            
            # Verify author exists
            author_exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM authors WHERE id = $1)
            """, author_id)
            
            if not author_exists:
                raise ValueError(f"Author with ID {author_id} not found")
            
            # Check for duplicate association
            duplicate_exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM document_authors 
                    WHERE book_id = $1 AND author_id = $2
                )
            """, book_id, author_id)
            
            if duplicate_exists:
                raise ValueError(
                    f"Author {author_id} is already associated with document {book_id}"
                )
            
            # Determine order if not specified
            if order is None:
                # Add at the end
                max_order = await conn.fetchval("""
                    SELECT COALESCE(MAX(author_order), -1) 
                    FROM document_authors 
                    WHERE book_id = $1
                """, book_id)
                order = max_order + 1
            
            # Insert the association
            await conn.execute("""
                INSERT INTO document_authors (book_id, author_id, author_order)
                VALUES ($1, $2, $3)
            """, book_id, author_id, order)

    async def remove_author_from_document(
        self,
        book_id: int,
        author_id: int
    ) -> None:
        """
        Remove author association from document with last-author validation.
        
        Prevents removing the last author from a document (documents must have
        at least one author).
        
        Args:
            book_id: ID of document (book)
            author_id: ID of author to remove
            
        Raises:
            ValueError: If trying to remove last author or association not found
            
        Validates: Requirements 1.5, 5.7
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            # Check if association exists
            association_exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM document_authors 
                    WHERE book_id = $1 AND author_id = $2
                )
            """, book_id, author_id)
            
            if not association_exists:
                raise ValueError(
                    f"Author {author_id} is not associated with document {book_id}"
                )
            
            # Count total authors for this document
            author_count = await conn.fetchval("""
                SELECT COUNT(*) FROM document_authors WHERE book_id = $1
            """, book_id)
            
            # Prevent removing last author
            if author_count <= 1:
                raise ValueError(
                    f"Cannot remove last author from document {book_id}. "
                    "Documents must have at least one author."
                )
            
            # Remove the association
            await conn.execute("""
                DELETE FROM document_authors 
                WHERE book_id = $1 AND author_id = $2
            """, book_id, author_id)

    async def reorder_authors(
        self,
        book_id: int,
        author_ids: List[int]
    ) -> None:
        """
        Update author order for a document.
        
        Reorders authors by updating the author_order field. The order of
        author_ids in the list determines the new order (first = 0).
        
        Args:
            book_id: ID of document (book)
            author_ids: List of author IDs in desired order
            
        Raises:
            ValueError: If document not found or author IDs don't match existing authors
            
        Validates: Requirements 1.3
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            # Verify document exists
            doc_exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM books WHERE id = $1)
            """, book_id)
            
            if not doc_exists:
                raise ValueError(f"Document with ID {book_id} not found")
            
            # Get current authors for this document
            current_authors = await conn.fetch("""
                SELECT author_id FROM document_authors WHERE book_id = $1
            """, book_id)
            
            current_author_ids = set(row['author_id'] for row in current_authors)
            provided_author_ids = set(author_ids)
            
            # Verify the provided list matches current authors
            if current_author_ids != provided_author_ids:
                missing = current_author_ids - provided_author_ids
                extra = provided_author_ids - current_author_ids
                error_msg = f"Author ID mismatch for document {book_id}."
                if missing:
                    error_msg += f" Missing: {missing}."
                if extra:
                    error_msg += f" Extra: {extra}."
                raise ValueError(error_msg)
            
            # Update the order for each author
            for new_order, author_id in enumerate(author_ids):
                await conn.execute("""
                    UPDATE document_authors 
                    SET author_order = $1 
                    WHERE book_id = $2 AND author_id = $3
                """, new_order, book_id, author_id)

    async def get_documents_by_author(
        self,
        author_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all documents by an author.
        
        Returns documents with basic metadata. Supports pagination.
        
        Args:
            author_id: ID of author
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            
        Returns:
            List of document dictionaries with id, filename, title, etc.
            
        Validates: Requirements 8.1
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            # Build query with optional pagination
            query = """
                SELECT 
                    b.id,
                    b.filename,
                    b.title,
                    b.category,
                    b.subcategory,
                    b.document_type,
                    b.total_pages,
                    b.processed_at,
                    da.author_order
                FROM books b
                INNER JOIN document_authors da ON b.id = da.book_id
                WHERE da.author_id = $1
                ORDER BY b.title
            """
            
            params = [author_id]
            param_index = 2
            
            if limit is not None:
                query += f" LIMIT ${param_index}"
                params.append(limit)
                param_index += 1
            
            if offset is not None:
                query += f" OFFSET ${param_index}"
                params.append(offset)
            
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    'id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'],
                    'category': row['category'],
                    'subcategory': row['subcategory'],
                    'document_type': row['document_type'],
                    'total_pages': row['total_pages'],
                    'processed_at': row['processed_at'],
                    'author_order': row['author_order']
                }
                for row in rows
            ]

    async def get_author_count_for_document(self, book_id: int) -> int:
        """
        Get the number of authors for a document.
        
        Args:
            book_id: ID of document (book)
            
        Returns:
            Number of authors associated with the document
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM document_authors WHERE book_id = $1
            """, book_id)
            return count

    async def clear_document_authors(self, book_id: int) -> None:
        """
        Remove all author associations for a document.
        
        Used during CSV import to replace existing authors with new ones.
        
        Args:
            book_id: ID of document (book)
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM document_authors WHERE book_id = $1
            """, book_id)

    async def verify_cascade_deletion(
        self,
        author_id: int,
        deleted_book_id: int
    ) -> Dict[str, Any]:
        """
        Verify that cascade deletion works correctly.
        
        After deleting a document, verifies that:
        1. The document_authors association is removed
        2. The author record still exists if used by other documents
        
        Args:
            author_id: ID of author to check
            deleted_book_id: ID of document that was deleted
            
        Returns:
            Dictionary with verification results
            
        Validates: Requirements 1.5
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            # Check if association still exists (should not)
            association_exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM document_authors 
                    WHERE book_id = $1 AND author_id = $2
                )
            """, deleted_book_id, author_id)
            
            # Check if author still exists
            author_exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM authors WHERE id = $1)
            """, author_id)
            
            # Count remaining documents for this author
            remaining_docs = await conn.fetchval("""
                SELECT COUNT(*) FROM document_authors WHERE author_id = $1
            """, author_id)
            
            return {
                'association_removed': not association_exists,
                'author_still_exists': author_exists,
                'remaining_document_count': remaining_docs
            }
