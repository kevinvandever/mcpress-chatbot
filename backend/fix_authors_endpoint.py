#!/usr/bin/env python3
"""
API endpoint to fix author issues
This runs on Railway and has access to the internal database
"""

from fastapi import APIRouter, HTTPException
import os
import asyncpg
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/fix-authors")
async def fix_authors():
    """Fix the specific author association issues"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not available")
    
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("Connected to database successfully")
        
        results = {
            "status": "success",
            "steps": [],
            "books_fixed": [],
            "authors_created": []
        }
        
        # Step 1: Check current state
        results["steps"].append("Checking current state of problematic books...")
        
        test_books = [
            ("Complete CL: Sixth Edition", "Ted Holt"),
            ("Subfiles in Free-Format RPG", "Kevin Vandever"), 
            ("Control Language Programming for IBM i", "Jim Buck, Bryan Meyers, Dan Riehl")
        ]
        
        current_state = {}
        for book_pattern, expected_authors in test_books:
            book = await conn.fetchrow("""
                SELECT id, title FROM books WHERE title ILIKE $1
            """, f"%{book_pattern}%")
            
            if book:
                current_authors = await conn.fetch("""
                    SELECT a.name, da.author_order
                    FROM document_authors da
                    JOIN authors a ON da.author_id = a.id
                    WHERE da.book_id = $1
                    ORDER BY da.author_order
                """, book['id'])
                
                current_names = ", ".join([author['name'] for author in current_authors]) if current_authors else "No authors"
                current_state[book['title']] = {
                    "current": current_names,
                    "expected": expected_authors
                }
        
        results["current_state"] = current_state
        
        # Step 2: Check if correct authors exist
        results["steps"].append("Checking if correct authors exist...")
        
        required_authors = ['Ted Holt', 'Kevin Vandever', 'Jim Buck', 'Bryan Meyers', 'Dan Riehl']
        author_ids = {}
        
        for author_name in required_authors:
            author = await conn.fetchrow("""
                SELECT id, name FROM authors WHERE name = $1
            """, author_name)
            
            if author:
                author_ids[author_name] = author['id']
            else:
                # Create missing author
                author_id = await conn.fetchval("""
                    INSERT INTO authors (name, site_url, created_at, updated_at)
                    VALUES ($1, NULL, NOW(), NOW())
                    RETURNING id
                """, author_name)
                author_ids[author_name] = author_id
                results["authors_created"].append(author_name)
        
        # Step 3: Fix book-author associations
        results["steps"].append("Fixing book-author associations...")
        
        fixes = [
            {
                'pattern': 'Complete CL: Sixth Edition',
                'authors': [('Ted Holt', 0)]
            },
            {
                'pattern': 'Subfiles in Free-Format RPG',
                'authors': [('Kevin Vandever', 0)]
            },
            {
                'pattern': 'Control Language Programming for IBM i',
                'authors': [('Jim Buck', 0), ('Bryan Meyers', 1), ('Dan Riehl', 2)]
            }
        ]
        
        for fix in fixes:
            book = await conn.fetchrow("""
                SELECT id, title FROM books WHERE title ILIKE $1
            """, f"%{fix['pattern']}%")
            
            if book:
                # Remove existing associations
                await conn.execute("""
                    DELETE FROM document_authors WHERE book_id = $1
                """, book['id'])
                
                # Add correct authors
                for author_name, order in fix['authors']:
                    if author_name in author_ids:
                        await conn.execute("""
                            INSERT INTO document_authors (book_id, author_id, author_order)
                            VALUES ($1, $2, $3)
                        """, book['id'], author_ids[author_name], order)
                
                results["books_fixed"].append(book['title'])
        
        # Step 4: Verify fixes
        results["steps"].append("Verifying fixes...")
        
        final_state = {}
        for book_pattern, expected_authors in test_books:
            book_authors = await conn.fetch("""
                SELECT b.title, a.name, da.author_order
                FROM books b
                JOIN document_authors da ON b.id = da.book_id
                JOIN authors a ON da.author_id = a.id
                WHERE b.title ILIKE $1
                ORDER BY da.author_order
            """, f"%{book_pattern}%")
            
            if book_authors:
                actual_authors = ", ".join([author['name'] for author in book_authors])
                final_state[book_authors[0]['title']] = {
                    "actual": actual_authors,
                    "expected": expected_authors,
                    "match": actual_authors == expected_authors
                }
        
        results["final_state"] = final_state
        
        await conn.close()
        
        results["steps"].append("Author fixes completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/check-authors")
async def check_authors():
    """Check current author state without making changes"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not available")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check the 3 specific books
        test_books = [
            "Complete CL: Sixth Edition",
            "Subfiles in Free-Format RPG", 
            "Control Language Programming for IBM i"
        ]
        
        results = {}
        
        for book_pattern in test_books:
            book_authors = await conn.fetch("""
                SELECT b.title, a.name, da.author_order
                FROM books b
                JOIN document_authors da ON b.id = da.book_id
                JOIN authors a ON da.author_id = a.id
                WHERE b.title ILIKE $1
                ORDER BY da.author_order
            """, f"%{book_pattern}%")
            
            if book_authors:
                author_names = ", ".join([author['name'] for author in book_authors])
                results[book_authors[0]['title']] = author_names
            else:
                # Check if book exists but has no authors
                book = await conn.fetchrow("""
                    SELECT id, title FROM books WHERE title ILIKE $1
                """, f"%{book_pattern}%")
                
                if book:
                    results[book['title']] = "No authors found"
                else:
                    results[book_pattern] = "Book not found"
        
        await conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")