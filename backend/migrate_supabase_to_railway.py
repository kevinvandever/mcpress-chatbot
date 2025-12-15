"""
Migrate books data from Supabase to Railway
Copy the 115 books from Supabase books table to Railway books table
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
from typing import Dict, List

migrate_supabase_router = APIRouter(prefix="/migrate-supabase", tags=["migrate-supabase"])

# You'll need to provide your Supabase DATABASE_URL
SUPABASE_URL = os.getenv('SUPABASE_DATABASE_URL')  # Set this in Railway environment
RAILWAY_URL = os.getenv('DATABASE_URL')  # This is already set

@migrate_supabase_router.get("/run")
async def migrate_books_from_supabase():
    """
    Migrate books from Supabase to Railway
    This will copy all books from Supabase books table to Railway books table
    """
    try:
        if not SUPABASE_URL:
            raise HTTPException(
                status_code=400, 
                detail="SUPABASE_DATABASE_URL not configured. Please set it in Railway environment variables."
            )
        
        if not RAILWAY_URL:
            raise HTTPException(status_code=500, detail="Railway DATABASE_URL not configured")

        results = []
        
        # Connect to both databases
        results.append("🔌 Connecting to databases...")
        supabase_conn = await asyncpg.connect(SUPABASE_URL)
        railway_conn = await asyncpg.connect(RAILWAY_URL)
        
        try:
            # Step 1: Get books from Supabase
            results.append("📚 Fetching books from Supabase...")
            
            supabase_books = await supabase_conn.fetch("""
                SELECT id, title, author, filename, category, mc_press_url, 
                       created_at, document_type, article_url
                FROM books 
                ORDER BY id
            """)
            
            results.append(f"✅ Found {len(supabase_books)} books in Supabase")
            
            if len(supabase_books) == 0:
                results.append("⚠️ No books found in Supabase")
                return {
                    "status": "success",
                    "message": "No books to migrate",
                    "results": results
                }
            
            # Step 2: Check Railway books table structure
            results.append("🔍 Checking Railway books table...")
            
            railway_books_exist = await railway_conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'books'
                )
            """)
            
            if not railway_books_exist:
                results.append("❌ Railway books table does not exist")
                raise HTTPException(status_code=400, detail="Railway books table not found")
            
            # Get current count
            current_railway_books = await railway_conn.fetchval("SELECT COUNT(*) FROM books")
            results.append(f"📊 Railway currently has {current_railway_books} books")
            
            # Step 3: Migrate books
            results.append("🚀 Starting migration...")
            
            migrated_count = 0
            skipped_count = 0
            error_count = 0
            
            for book in supabase_books:
                try:
                    # Check if book already exists in Railway (by filename)
                    existing = await railway_conn.fetchval("""
                        SELECT id FROM books WHERE filename = $1
                    """, book['filename'])
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Insert book into Railway
                    await railway_conn.execute("""
                        INSERT INTO books (
                            title, author, filename, category, mc_press_url,
                            created_at, document_type, article_url
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """, 
                        book['title'],
                        book['author'], 
                        book['filename'],
                        book['category'],
                        book['mc_press_url'],
                        book['created_at'],
                        book.get('document_type', 'book'),
                        book.get('article_url')
                    )
                    
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        results.append(f"  ✅ Migrated {migrated_count} books...")
                        
                except Exception as e:
                    error_count += 1
                    results.append(f"  ⚠️ Error migrating book {book.get('filename', 'unknown')}: {str(e)}")
            
            # Step 4: Verify migration
            final_railway_books = await railway_conn.fetchval("SELECT COUNT(*) FROM books")
            
            results.append(f"✅ Migration complete!")
            results.append(f"  📊 Migrated: {migrated_count}")
            results.append(f"  ⏭️ Skipped: {skipped_count}")
            results.append(f"  ❌ Errors: {error_count}")
            results.append(f"  📚 Railway total: {final_railway_books}")
            
            # Step 5: Sample migrated books
            sample_books = await railway_conn.fetch("""
                SELECT id, filename, title, author, document_type
                FROM books 
                ORDER BY id DESC
                LIMIT 5
            """)
            
            return {
                "status": "success",
                "message": f"Successfully migrated {migrated_count} books from Supabase to Railway",
                "results": results,
                "statistics": {
                    "supabase_books": len(supabase_books),
                    "migrated": migrated_count,
                    "skipped": skipped_count,
                    "errors": error_count,
                    "railway_total": final_railway_books
                },
                "sample_books": [dict(book) for book in sample_books]
            }
            
        finally:
            await supabase_conn.close()
            await railway_conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@migrate_supabase_router.get("/status")
async def check_migration_status():
    """Check the status of Supabase to Railway migration"""
    try:
        railway_conn = await asyncpg.connect(RAILWAY_URL)
        
        # Count books in Railway
        railway_books = await railway_conn.fetchval("SELECT COUNT(*) FROM books")
        
        # Sample books
        sample_books = await railway_conn.fetch("""
            SELECT id, filename, title, author, document_type, created_at
            FROM books 
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        await railway_conn.close()
        
        return {
            "railway_books": railway_books,
            "migration_needed": railway_books == 0,
            "sample_books": [dict(book) for book in sample_books],
            "supabase_url_configured": bool(SUPABASE_URL),
            "message": "Migration complete" if railway_books > 0 else "Migration needed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@migrate_supabase_router.get("/test-connections")
async def test_database_connections():
    """Test connections to both Supabase and Railway"""
    try:
        results = {}
        
        # Test Railway connection
        try:
            railway_conn = await asyncpg.connect(RAILWAY_URL)
            railway_books = await railway_conn.fetchval("SELECT COUNT(*) FROM books")
            await railway_conn.close()
            results['railway'] = {
                "status": "connected",
                "books_count": railway_books
            }
        except Exception as e:
            results['railway'] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test Supabase connection
        if SUPABASE_URL:
            try:
                supabase_conn = await asyncpg.connect(SUPABASE_URL)
                supabase_books = await supabase_conn.fetchval("SELECT COUNT(*) FROM books")
                await supabase_conn.close()
                results['supabase'] = {
                    "status": "connected", 
                    "books_count": supabase_books
                }
            except Exception as e:
                results['supabase'] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results['supabase'] = {
                "status": "not_configured",
                "error": "SUPABASE_DATABASE_URL not set"
            }
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")