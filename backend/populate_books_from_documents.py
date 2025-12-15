"""
Populate books table from documents table
Create metadata records for existing documents so multi-author migration can work
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
from datetime import datetime

populate_books_router = APIRouter(prefix="/populate-books", tags=["populate-books"])

@populate_books_router.get("/run")
async def populate_books_from_documents():
    """
    Create books table records from existing documents table data
    This prepares the data for the multi-author migration
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        results = []
        
        # Step 1: Get unique documents from documents table
        unique_docs = await conn.fetch("""
            SELECT DISTINCT 
                filename,
                MIN(created_at) as first_seen,
                COUNT(*) as chunk_count
            FROM documents 
            WHERE filename IS NOT NULL 
            GROUP BY filename
            ORDER BY filename
        """)
        
        results.append(f"✅ Found {len(unique_docs)} unique documents")
        
        if len(unique_docs) == 0:
            await conn.close()
            return {
                "status": "success",
                "message": "No documents found to populate",
                "results": results
            }
        
        # Step 2: Check if books table exists and has the right structure
        books_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'books'
            )
        """)
        
        if not books_exists:
            results.append("❌ books table does not exist - run migration 003 first")
            await conn.close()
            raise HTTPException(status_code=400, detail="books table does not exist")
        
        results.append("✅ books table exists")
        
        # Step 3: Create books records for each unique document
        books_created = 0
        books_skipped = 0
        
        for doc in unique_docs:
            filename = doc['filename']
            
            # Check if book already exists
            existing = await conn.fetchval("""
                SELECT id FROM books WHERE filename = $1
            """, filename)
            
            if existing:
                books_skipped += 1
                continue
            
            # Extract title from filename (remove .pdf extension)
            title = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            
            # Try to extract author from metadata if available
            author_info = await conn.fetchval("""
                SELECT metadata->>'author' as author
                FROM documents 
                WHERE filename = $1 
                AND metadata->>'author' IS NOT NULL
                LIMIT 1
            """, filename)
            
            # Default author if none found
            author = author_info if author_info else "Unknown"
            
            # Calculate total pages (approximate from chunks)
            total_pages = max(1, doc['chunk_count'] // 10)  # Rough estimate
            
            # Insert book record
            try:
                book_id = await conn.fetchval("""
                    INSERT INTO books (
                        filename, title, author, document_type, 
                        total_pages, processed_at, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """, 
                    filename, title, author, 'book',
                    total_pages, doc['first_seen'], datetime.now()
                )
                
                books_created += 1
                results.append(f"  ✅ Created book {book_id}: {title}")
                
            except Exception as e:
                results.append(f"  ⚠️ Error creating book for {filename}: {str(e)}")
                books_skipped += 1
        
        results.append(f"✅ Created {books_created} book records")
        if books_skipped > 0:
            results.append(f"⚠️ Skipped {books_skipped} books (already exist or errors)")
        
        # Step 4: Verify results
        total_books = await conn.fetchval("SELECT COUNT(*) FROM books")
        results.append(f"✅ Total books in database: {total_books}")
        
        await conn.close()
        
        return {
            "status": "success",
            "message": f"Successfully populated {books_created} book records",
            "results": results,
            "statistics": {
                "documents_processed": len(unique_docs),
                "books_created": books_created,
                "books_skipped": books_skipped,
                "total_books": total_books
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Population failed: {str(e)}")


@populate_books_router.get("/status")
async def check_population_status():
    """Check if books have been populated from documents"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)
        
        # Count documents and books
        doc_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT filename) FROM documents WHERE filename IS NOT NULL
        """)
        
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        
        # Sample books
        sample_books = await conn.fetch("""
            SELECT id, filename, title, author, document_type, total_pages
            FROM books 
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        await conn.close()
        
        return {
            "unique_documents": doc_count,
            "books_records": book_count,
            "population_needed": doc_count > book_count,
            "sample_books": [dict(book) for book in sample_books],
            "message": "Population complete" if doc_count == book_count else "Population needed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")