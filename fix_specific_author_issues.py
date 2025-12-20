#!/usr/bin/env python3
"""
Fix the specific author issues mentioned by the user
This script focuses on the 3 main problems:
1. Complete CL: Sixth Edition shows "annegrubb" but should be "Ted Holt"
2. Subfiles in Free-Format RPG shows "admin" but should be "Kevin Vandever"  
3. Control Language Programming shows only "Jim Buck" but should show multiple authors
"""

import os
import asyncio
import asyncpg

async def fix_specific_author_issues():
    """Fix the specific author association issues"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not found")
        print("This script must be run on Railway or with DATABASE_URL set")
        return False
    
    print("🔗 Connecting to Railway database...")
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database successfully")
        
        print("\n🔍 Step 1: Checking current state of problematic books...")
        
        # Check the 3 specific books
        test_books = [
            ("Complete CL: Sixth Edition", "Ted Holt"),
            ("Subfiles in Free-Format RPG", "Kevin Vandever"), 
            ("Control Language Programming for IBM i", "Jim Buck, Bryan Meyers, Dan Riehl")
        ]
        
        for book_pattern, expected_authors in test_books:
            print(f"\n📖 Checking: {book_pattern}")
            
            # Find the book
            book = await conn.fetchrow("""
                SELECT id, title FROM books WHERE title ILIKE $1
            """, f"%{book_pattern}%")
            
            if not book:
                print(f"   ❌ Book not found")
                continue
                
            print(f"   ✅ Found book: {book['title']} (ID: {book['id']})")
            
            # Check current authors
            current_authors = await conn.fetch("""
                SELECT a.name, da.author_order
                FROM document_authors da
                JOIN authors a ON da.author_id = a.id
                WHERE da.book_id = $1
                ORDER BY da.author_order
            """, book['id'])
            
            if current_authors:
                current_names = ", ".join([author['name'] for author in current_authors])
                print(f"   Current authors: {current_names}")
            else:
                print(f"   ❌ No authors found for this book")
            
            print(f"   Expected authors: {expected_authors}")
        
        print(f"\n🔧 Step 2: Checking if correct authors exist in database...")
        
        # Check if the correct authors exist
        required_authors = ['Ted Holt', 'Kevin Vandever', 'Jim Buck', 'Bryan Meyers', 'Dan Riehl']
        author_ids = {}
        
        for author_name in required_authors:
            author = await conn.fetchrow("""
                SELECT id, name FROM authors WHERE name = $1
            """, author_name)
            
            if author:
                author_ids[author_name] = author['id']
                print(f"   ✅ {author_name} exists (ID: {author['id']})")
            else:
                print(f"   ❌ {author_name} NOT FOUND - needs to be created")
        
        print(f"\n🛠️  Step 3: Creating missing authors...")
        
        # Create missing authors
        for author_name in required_authors:
            if author_name not in author_ids:
                try:
                    author_id = await conn.fetchval("""
                        INSERT INTO authors (name, site_url, created_at, updated_at)
                        VALUES ($1, NULL, NOW(), NOW())
                        RETURNING id
                    """, author_name)
                    author_ids[author_name] = author_id
                    print(f"   ✅ Created {author_name} (ID: {author_id})")
                except Exception as e:
                    print(f"   ❌ Failed to create {author_name}: {e}")
        
        print(f"\n🔄 Step 4: Fixing book-author associations...")
        
        # Fix each book
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
            print(f"\n📚 Fixing: {fix['pattern']}")
            
            # Find the book
            book = await conn.fetchrow("""
                SELECT id, title FROM books WHERE title ILIKE $1
            """, f"%{fix['pattern']}%")
            
            if not book:
                print(f"   ❌ Book not found")
                continue
            
            # Remove ALL current associations
            deleted_count = await conn.fetchval("""
                DELETE FROM document_authors WHERE book_id = $1
                RETURNING (SELECT COUNT(*) FROM document_authors WHERE book_id = $1)
            """, book['id'])
            
            print(f"   🗑️  Removed existing associations")
            
            # Add correct authors
            for author_name, order in fix['authors']:
                if author_name in author_ids:
                    try:
                        await conn.execute("""
                            INSERT INTO document_authors (book_id, author_id, author_order)
                            VALUES ($1, $2, $3)
                        """, book['id'], author_ids[author_name], order)
                        print(f"   ✅ Added {author_name} (order {order})")
                    except Exception as e:
                        print(f"   ❌ Failed to add {author_name}: {e}")
                else:
                    print(f"   ❌ Author {author_name} not found in database")
        
        print(f"\n🔍 Step 5: Verifying fixes...")
        
        # Verify the fixes
        for book_pattern, expected_authors in test_books:
            print(f"\n📖 Verifying: {book_pattern}")
            
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
                print(f"   ✅ Current authors: {actual_authors}")
                print(f"   Expected: {expected_authors}")
                
                if actual_authors == expected_authors:
                    print(f"   🎉 PERFECT MATCH!")
                else:
                    print(f"   ⚠️  Still needs adjustment")
            else:
                print(f"   ❌ No authors found")
        
        await conn.close()
        print(f"\n🎉 Author fixes completed!")
        print(f"\nNext steps:")
        print(f"1. Test the chat interface with queries like:")
        print(f"   - 'Complete CL programming'")
        print(f"   - 'Subfiles RPG'")
        print(f"   - 'Control Language Programming'")
        print(f"2. Verify sources show correct authors")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_specific_author_issues())
    if success:
        print("\n✅ Specific author issues fixed!")
    else:
        print("\n❌ Failed to fix author issues.")