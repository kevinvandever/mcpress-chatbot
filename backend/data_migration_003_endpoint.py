"""
Data Migration 003 HTTP Endpoint
Run data migration in production via HTTP request
Access at: https://your-backend-url/data-migration-003/*
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
from typing import Dict, List

# Import services
try:
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
except ImportError:
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService

data_migration_003_router = APIRouter(
    prefix="/data-migration-003",
    tags=["data-migration-003"]
)


@data_migration_003_router.get("/run")
async def run_data_migration():
    """
    Run Data Migration 003: Populate authors from existing books
    
    This migration:
    1. Extracts unique authors from books.author column
    2. Creates author records with deduplication
    3. Creates document_authors associations for all books
    4. Assigns 'Unknown' author to books without authors
    5. Verifies all documents have at least one author
    
    Access this at: https://your-backend-url/data-migration-003/run
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        # Initialize services
        author_service = AuthorService(database_url)
        doc_author_service = DocumentAuthorService(database_url)
        await author_service.init_database()
        await doc_author_service.init_database()
        
        conn = await asyncpg.connect(database_url)
        results = []
        
        try:
            # Step 1: Check if books table has author column
            author_column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'books' AND column_name = 'author'
                )
            """)
            
            if not author_column_exists:
                results.append("⚠️ books.author column does not exist (might be already migrated)")
            else:
                results.append("✅ books.author column found")
            
            # Step 2: Get all books
            books = await conn.fetch("""
                SELECT id, filename, title, author
                FROM books
                ORDER BY id
            """)
            
            total_books = len(books)
            results.append(f"✅ Found {total_books} books")
            
            if total_books == 0:
                await conn.close()
                await author_service.close()
                await doc_author_service.close()
                
                return {
                    "status": "success",
                    "message": "No books to migrate",
                    "results": results
                }
            
            # Step 3: Create author records
            author_map: Dict[str, int] = {}
            books_without_author = []
            
            for book in books:
                author_name = book['author']
                
                if not author_name or author_name.strip() == '':
                    books_without_author.append(book['id'])
                    continue
                
                author_name = author_name.strip()
                
                if author_name not in author_map:
                    try:
                        author_id = await author_service.get_or_create_author(author_name)
                        author_map[author_name] = author_id
                    except Exception as e:
                        results.append(f"⚠️ Error creating author '{author_name}': {str(e)}")
            
            results.append(f"✅ Created {len(author_map)} unique author records")
            
            # Handle books without authors - assign to 'Unknown'
            unknown_author_id = None
            if books_without_author:
                results.append(f"⚠️ Found {len(books_without_author)} books without authors")
                unknown_author_id = await author_service.get_or_create_author("Unknown")
                results.append(f"✅ Created 'Unknown' author (ID: {unknown_author_id})")
            
            # Step 4: Create associations
            associations_created = 0
            associations_skipped = 0
            
            for book in books:
                author_name = book['author']
                
                # Determine author_id
                if not author_name or author_name.strip() == '':
                    if unknown_author_id:
                        author_id = unknown_author_id
                    else:
                        associations_skipped += 1
                        continue
                else:
                    author_name = author_name.strip()
                    if author_name not in author_map:
                        associations_skipped += 1
                        continue
                    author_id = author_map[author_name]
                
                # Create association
                try:
                    await doc_author_service.add_author_to_document(
                        book_id=book['id'],
                        author_id=author_id,
                        order=0
                    )
                    associations_created += 1
                except Exception as e:
                    if "already associated" in str(e):
                        # Already exists, that's fine
                        pass
                    else:
                        associations_skipped += 1
            
            results.append(f"✅ Created {associations_created} document-author associations")
            if associations_skipped > 0:
                results.append(f"⚠️ Skipped {associations_skipped} associations")
            
            # Step 5: Verify
            books_without_authors = await conn.fetch("""
                SELECT b.id, b.filename
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                WHERE da.book_id IS NULL
            """)
            
            if books_without_authors:
                results.append(f"⚠️ Warning: {len(books_without_authors)} books still have no authors")
            else:
                results.append("✅ All books have at least one author")
            
            # Statistics
            total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
            total_associations = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
            total_books_with_authors = await conn.fetchval("""
                SELECT COUNT(DISTINCT book_id) FROM document_authors
            """)
            
            stats = {
                "total_books": total_books,
                "total_authors": total_authors,
                "total_associations": total_associations,
                "books_with_authors": total_books_with_authors,
                "books_without_authors": total_books - total_books_with_authors
            }
            
            await conn.close()
            await author_service.close()
            await doc_author_service.close()
            
            return {
                "status": "success",
                "message": "Data migration completed successfully",
                "results": results,
                "statistics": stats
            }
            
        except Exception as e:
            await conn.close()
            await author_service.close()
            await doc_author_service.close()
            raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@data_migration_003_router.get("/status")
async def check_migration_status():
    """
    Check the status of the data migration
    
    Returns statistics about authors and associations
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            # Check if author column still exists
            author_column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'books' AND column_name = 'author'
                )
            """)
            
            # Get statistics
            total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
            total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
            total_associations = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
            
            books_with_authors = await conn.fetchval("""
                SELECT COUNT(DISTINCT book_id) FROM document_authors
            """)
            
            books_without_authors = await conn.fetch("""
                SELECT b.id, b.filename, b.title
                FROM books b
                LEFT JOIN document_authors da ON b.id = da.book_id
                WHERE da.book_id IS NULL
                LIMIT 10
            """)
            
            migration_complete = (total_books > 0 and books_with_authors == total_books)
            
            await conn.close()
            
            return {
                "migration_complete": migration_complete,
                "author_column_exists": author_column_exists,
                "statistics": {
                    "total_books": total_books,
                    "total_authors": total_authors,
                    "total_associations": total_associations,
                    "books_with_authors": books_with_authors,
                    "books_without_authors": total_books - books_with_authors
                },
                "books_needing_authors": [
                    {
                        "id": book['id'],
                        "filename": book['filename'],
                        "title": book['title']
                    }
                    for book in books_without_authors
                ],
                "message": "Migration complete" if migration_complete else "Migration needed or incomplete"
            }
            
        except Exception as e:
            await conn.close()
            raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
