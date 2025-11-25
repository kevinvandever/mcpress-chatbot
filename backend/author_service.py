"""
Author Service for Multi-Author Metadata Enhancement
Feature: multi-author-metadata-enhancement

Manages author-related operations including:
- Author creation and deduplication
- Author retrieval and search
- Author updates
- Document-author associations
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg
import re


class AuthorService:
    """Service for managing author operations"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize author service

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

    async def get_or_create_author(
        self,
        name: str,
        site_url: Optional[str] = None
    ) -> int:
        """
        Get existing author ID or create new author with name deduplication.
        
        This method implements author deduplication by using INSERT ... ON CONFLICT
        to ensure only one author record exists per unique name.
        
        Args:
            name: Author name (will be deduplicated)
            site_url: Optional author website URL
            
        Returns:
            Author ID (existing or newly created)
            
        Validates: Requirements 1.2, 5.3, 5.4
        """
        await self._ensure_pool()
        
        if not name or not name.strip():
            raise ValueError("Author name cannot be empty")
        
        name = name.strip()
        
        # Validate URL if provided
        if site_url:
            site_url = self._validate_url(site_url)
        
        async with self.pool.acquire() as conn:
            # Use INSERT ... ON CONFLICT to handle deduplication
            # If author exists, update site_url and return existing ID
            # If author doesn't exist, create new record
            author_id = await conn.fetchval("""
                INSERT INTO authors (name, site_url)
                VALUES ($1, $2)
                ON CONFLICT (name) DO UPDATE
                SET site_url = COALESCE(EXCLUDED.site_url, authors.site_url),
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, name, site_url)
            
            return author_id

    async def update_author(
        self,
        author_id: int,
        name: Optional[str] = None,
        site_url: Optional[str] = None
    ) -> None:
        """
        Update author information.
        
        Updates propagate to all documents associated with this author.
        
        Args:
            author_id: ID of author to update
            name: New author name (optional)
            site_url: New author website URL (optional, use empty string to clear)
            
        Raises:
            ValueError: If author not found or invalid data provided
            
        Validates: Requirements 3.1, 3.2, 5.6
        """
        await self._ensure_pool()
        
        if not author_id:
            raise ValueError("Author ID is required")
        
        # Build update query dynamically based on provided fields
        updates = []
        params = []
        param_index = 1
        
        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Author name cannot be empty")
            updates.append(f"name = ${param_index}")
            params.append(name)
            param_index += 1
        
        if site_url is not None:
            # Empty string clears the URL
            if site_url:
                site_url = self._validate_url(site_url)
            else:
                site_url = None
            updates.append(f"site_url = ${param_index}")
            params.append(site_url)
            param_index += 1
        
        if not updates:
            return  # Nothing to update
        
        # Always update the updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        # Add author_id as last parameter
        params.append(author_id)
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(f"""
                UPDATE authors
                SET {', '.join(updates)}
                WHERE id = ${param_index}
            """, *params)
            
            # Check if author was found
            if result == "UPDATE 0":
                raise ValueError(f"Author with ID {author_id} not found")

    async def get_author_by_id(self, author_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve author details by ID.
        
        Args:
            author_id: ID of author to retrieve
            
        Returns:
            Author dictionary with id, name, site_url, created_at, updated_at, document_count
            or None if not found
            
        Validates: Requirements 3.1, 3.3, 8.3
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    a.id,
                    a.name,
                    a.site_url,
                    a.created_at,
                    a.updated_at,
                    COUNT(da.book_id) as document_count
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                WHERE a.id = $1
                GROUP BY a.id, a.name, a.site_url, a.created_at, a.updated_at
            """, author_id)
            
            if not row:
                return None
            
            return {
                'id': row['id'],
                'name': row['name'],
                'site_url': row['site_url'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'document_count': row['document_count']
            }

    async def search_authors(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search authors by name for autocomplete.
        
        Performs case-insensitive partial matching on author names.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of author dictionaries with id, name, site_url, document_count
            
        Validates: Requirements 5.2, 8.1
        """
        await self._ensure_pool()
        
        if not query or not query.strip():
            return []
        
        query = query.strip()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    a.id,
                    a.name,
                    a.site_url,
                    COUNT(da.book_id) as document_count
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                WHERE a.name ILIKE $1
                GROUP BY a.id, a.name, a.site_url
                ORDER BY a.name
                LIMIT $2
            """, f"%{query}%", limit)
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'site_url': row['site_url'],
                    'document_count': row['document_count']
                }
                for row in rows
            ]

    async def get_authors_for_document(
        self,
        book_id: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch all authors for a document in order.
        
        Returns authors sorted by author_order field.
        
        Args:
            book_id: ID of document (book)
            
        Returns:
            List of author dictionaries with id, name, site_url, order
            
        Validates: Requirements 1.3, 3.4
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    a.id,
                    a.name,
                    a.site_url,
                    da.author_order as order
                FROM authors a
                INNER JOIN document_authors da ON a.id = da.author_id
                WHERE da.book_id = $1
                ORDER BY da.author_order
            """, book_id)
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'site_url': row['site_url'],
                    'order': row['order']
                }
                for row in rows
            ]

    def _validate_url(self, url: str) -> str:
        """
        Validate URL format.
        
        Args:
            url: URL string to validate
            
        Returns:
            Validated URL string
            
        Raises:
            ValueError: If URL format is invalid
            
        Validates: Requirements 3.2
        """
        if not url or not url.strip():
            return None
        
        url = url.strip()
        
        # Basic URL validation - must start with http:// or https://
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            raise ValueError(f"Invalid URL format: {url}")
        
        return url
