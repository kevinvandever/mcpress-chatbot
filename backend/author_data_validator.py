"""
Author Data Validator for Author Display Investigation
Feature: author-display-investigation

Diagnostic tool to identify data quality issues in author associations:
- Books without authors
- Placeholder author names
- Orphaned authors (no document associations)
- Invalid foreign key references
"""

import os
from typing import List, Dict, Any, Optional, Tuple
import asyncpg


class AuthorDataValidator:
    """Validator for identifying author data quality issues"""

    # Placeholder patterns to detect suspicious author names
    PLACEHOLDER_PATTERNS = [
        "admin",
        "unknown",
        "annegrubb",
        "test",
        "default",
        "none",
        "n/a",
        "tbd",
        "pending",
    ]

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize author data validator

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

    async def find_books_without_authors(self) -> List[Dict[str, Any]]:
        """
        Find all books with no author associations.
        
        Returns books that have zero entries in the document_authors table.
        
        Returns:
            List of book dictionaries with id, filename, title
            
        Validates: Requirements 1.1, 4.1
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    b.id,
                    b.filename,
                    b.title,
                    b.document_type,
                    b.category
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                WHERE da.book_id IS NULL
                ORDER BY b.title NULLS LAST, b.filename
            """)
            
            return [
                {
                    'id': row['id'],
                    'filename': row['filename'],
                    'title': row['title'],
                    'document_type': row['document_type'],
                    'category': row['category']
                }
                for row in rows
            ]

    async def find_placeholder_authors(self) -> List[Tuple[int, str, int]]:
        """
        Find authors with placeholder names like 'Admin', 'Unknown', etc.
        
        Uses pattern matching to identify suspicious author names that are
        likely placeholders rather than real author names.
        
        Returns:
            List of tuples (author_id, author_name, document_count)
            
        Validates: Requirements 1.2, 4.2
        """
        await self._ensure_pool()
        
        # Build ILIKE conditions for all placeholder patterns
        conditions = " OR ".join([
            f"LOWER(a.name) LIKE '%{pattern}%'"
            for pattern in self.PLACEHOLDER_PATTERNS
        ])
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    a.id,
                    a.name,
                    COUNT(da.book_id) as document_count
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                WHERE {conditions}
                GROUP BY a.id, a.name
                ORDER BY document_count DESC, a.name
            """)
            
            return [
                (row['id'], row['name'], row['document_count'])
                for row in rows
            ]

    async def find_orphaned_authors(self) -> List[Dict[str, Any]]:
        """
        Find authors with zero document associations.
        
        These are author records that exist in the authors table but have
        no entries in the document_authors junction table.
        
        Returns:
            List of author dictionaries with id, name, site_url, created_at
            
        Validates: Requirements 4.3
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    a.id,
                    a.name,
                    a.site_url,
                    a.created_at,
                    a.updated_at
                FROM authors a
                LEFT JOIN document_authors da ON a.id = da.author_id
                WHERE da.author_id IS NULL
                ORDER BY a.created_at DESC
            """)
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'site_url': row['site_url'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                for row in rows
            ]

    async def validate_author_references(self) -> List[str]:
        """
        Check that all author_id foreign keys in document_authors are valid.
        
        Identifies any document_authors records that reference non-existent
        author IDs (orphaned foreign keys).
        
        Returns:
            List of error messages for invalid references
            
        Validates: Requirements 4.1
        """
        await self._ensure_pool()
        
        errors = []
        
        async with self.pool.acquire() as conn:
            # Check for invalid author_id references
            invalid_authors = await conn.fetch("""
                SELECT 
                    da.id as association_id,
                    da.book_id,
                    da.author_id
                FROM document_authors da
                WHERE NOT EXISTS (
                    SELECT 1 FROM authors a WHERE a.id = da.author_id
                )
            """)
            
            for row in invalid_authors:
                errors.append(
                    f"document_authors.id={row['association_id']}: "
                    f"References non-existent author_id={row['author_id']} "
                    f"for book_id={row['book_id']}"
                )
            
            # Check for invalid book_id references
            invalid_books = await conn.fetch("""
                SELECT 
                    da.id as association_id,
                    da.book_id,
                    da.author_id
                FROM document_authors da
                WHERE NOT EXISTS (
                    SELECT 1 FROM books b WHERE b.id = da.book_id
                )
            """)
            
            for row in invalid_books:
                errors.append(
                    f"document_authors.id={row['association_id']}: "
                    f"References non-existent book_id={row['book_id']} "
                    f"for author_id={row['author_id']}"
                )
        
        return errors

    async def check_author_order_gaps(self) -> List[Dict[str, Any]]:
        """
        Find books with gaps in author_order sequences.
        
        Author order should be sequential (0, 1, 2...) with no gaps.
        This identifies books where the ordering is broken.
        
        Returns:
            List of dictionaries with book_id, title, and order issues
        """
        await self._ensure_pool()
        
        issues = []
        
        async with self.pool.acquire() as conn:
            # Get all books with multiple authors
            books_with_authors = await conn.fetch("""
                SELECT DISTINCT book_id
                FROM document_authors
                GROUP BY book_id
                HAVING COUNT(*) > 1
            """)
            
            for book_row in books_with_authors:
                book_id = book_row['book_id']
                
                # Get author orders for this book
                orders = await conn.fetch("""
                    SELECT 
                        da.author_order,
                        a.name as author_name
                    FROM document_authors da
                    JOIN authors a ON da.author_id = a.id
                    WHERE da.book_id = $1
                    ORDER BY da.author_order
                """, book_id)
                
                # Check for gaps or duplicates
                order_values = [row['author_order'] for row in orders]
                expected_orders = list(range(len(order_values)))
                
                if order_values != expected_orders:
                    # Get book title
                    book_info = await conn.fetchrow("""
                        SELECT title, filename FROM books WHERE id = $1
                    """, book_id)
                    
                    issues.append({
                        'book_id': book_id,
                        'title': book_info['title'],
                        'filename': book_info['filename'],
                        'actual_orders': order_values,
                        'expected_orders': expected_orders,
                        'authors': [row['author_name'] for row in orders]
                    })
        
        return issues

    async def find_duplicate_associations(self) -> List[Dict[str, Any]]:
        """
        Find books with duplicate author associations.
        
        The same author should not be associated with a book multiple times.
        
        Returns:
            List of dictionaries with book_id, author_id, and count
        """
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    da.book_id,
                    da.author_id,
                    b.title,
                    b.filename,
                    a.name as author_name,
                    COUNT(*) as association_count
                FROM document_authors da
                JOIN books b ON da.book_id = b.id
                JOIN authors a ON da.author_id = a.id
                GROUP BY da.book_id, da.author_id, b.title, b.filename, a.name
                HAVING COUNT(*) > 1
                ORDER BY association_count DESC, b.title
            """)
            
            return [
                {
                    'book_id': row['book_id'],
                    'author_id': row['author_id'],
                    'title': row['title'],
                    'filename': row['filename'],
                    'author_name': row['author_name'],
                    'association_count': row['association_count']
                }
                for row in rows
            ]

    async def generate_data_quality_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive report of all data quality issues.
        
        Runs all validation checks and returns structured data about
        all identified issues.
        
        Returns:
            Dictionary with counts and examples of each issue type:
            - books_without_authors: List of books with no authors
            - placeholder_authors: List of suspicious author names
            - orphaned_authors: List of authors with no documents
            - invalid_references: List of broken foreign keys
            - author_order_gaps: List of books with ordering issues
            - duplicate_associations: List of duplicate author-book links
            - total_issues: Total count of all issues
            
        Validates: Requirements 1.1, 1.2, 4.1, 4.2, 4.3
        """
        await self._ensure_pool()
        
        # Run all validation checks
        books_without_authors = await self.find_books_without_authors()
        placeholder_authors = await self.find_placeholder_authors()
        orphaned_authors = await self.find_orphaned_authors()
        invalid_references = await self.validate_author_references()
        author_order_gaps = await self.check_author_order_gaps()
        duplicate_associations = await self.find_duplicate_associations()
        
        # Calculate total issues
        total_issues = (
            len(books_without_authors) +
            len(placeholder_authors) +
            len(orphaned_authors) +
            len(invalid_references) +
            len(author_order_gaps) +
            len(duplicate_associations)
        )
        
        # Get summary statistics
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(*) FROM books) as total_books,
                    (SELECT COUNT(*) FROM authors) as total_authors,
                    (SELECT COUNT(*) FROM document_authors) as total_associations,
                    (SELECT COUNT(DISTINCT book_id) FROM document_authors) as books_with_authors
            """)
        
        return {
            'summary': {
                'total_books': stats['total_books'],
                'total_authors': stats['total_authors'],
                'total_associations': stats['total_associations'],
                'books_with_authors': stats['books_with_authors'],
                'books_without_authors_count': len(books_without_authors),
                'total_issues': total_issues
            },
            'books_without_authors': books_without_authors,
            'placeholder_authors': [
                {
                    'author_id': author_id,
                    'author_name': name,
                    'document_count': count
                }
                for author_id, name, count in placeholder_authors
            ],
            'orphaned_authors': orphaned_authors,
            'invalid_references': invalid_references,
            'author_order_gaps': author_order_gaps,
            'duplicate_associations': duplicate_associations
        }
