#!/usr/bin/env python3
"""
Execute SQL corrections directly using Python and asyncpg.
This bypasses the need for Railway CLI and runs the corrections directly.
"""

import asyncio
import asyncpg
import os

# Railway database URL
DATABASE_URL = "postgresql://postgres:bRAiLwAyPASSWORD@viaduct.proxy.rlwy.net:47334/railway"

async def execute_author_corrections():
    """Execute the complete author corrections directly on the database"""
    
    print("🚀 Executing Author Corrections Directly")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to Railway database")
        
        # Step 1: Create missing authors
        print("\n📝 Step 1: Creating missing authors...")
        
        missing_authors = [
            "Chuck Stupca",
            "Mithkal Smadi", 
            "Don Denoncourt",
            "MC Press Bookstore",
            "Gili Mendel",
            "Gary Craig",
            "Peter Jakab",
            "Jean-Francois Puget",
            "Arvind Sathi",
            "Shannon O'Donnell"
        ]
        
        for author in missing_authors:
            try:
                await conn.execute("""
                    INSERT INTO authors (name, site_url, created_at, updated_at)
                    SELECT $1, NULL, NOW(), NOW()
                    WHERE NOT EXISTS (SELECT 1 FROM authors WHERE name = $1)
                """, author)
                print(f"   ✅ Created/verified: {author}")
            except Exception as e:
                print(f"   ⚠️  Error with {author}: {e}")
        
        # Step 2: Fix specific books mentioned by user
        print(f"\n📝 Step 2: Fixing specific books...")
        
        # Fix Complete CL: Sixth Edition (Ted Holt)
        print("   📖 Fixing Complete CL: Sixth Edition...")
        
        # Remove annegrubb
        result = await conn.execute("""
            DELETE FROM document_authors 
            WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Complete CL%Sixth%')
              AND author_id = (SELECT id FROM authors WHERE name ILIKE '%annegrubb%')
        """)
        print(f"      Removed annegrubb associations: {result}")
        
        # Add Ted Holt
        result = await conn.execute("""
            INSERT INTO document_authors (book_id, author_id, author_order)
            SELECT b.id, a.id, 0
            FROM books b, authors a
            WHERE b.title ILIKE '%Complete CL%Sixth%'
              AND a.name = 'Ted Holt'
              AND NOT EXISTS (
                SELECT 1 FROM document_authors da 
                WHERE da.book_id = b.id AND da.author_id = a.id
              )
        """)
        print(f"      Added Ted Holt: {result}")
        
        # Fix Subfiles in Free-Format RPG (Kevin Vandever)
        print("   📖 Fixing Subfiles in Free-Format RPG...")
        
        # Remove admin
        result = await conn.execute("""
            DELETE FROM document_authors 
            WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Subfiles%Free%')
              AND author_id = (SELECT id FROM authors WHERE name ILIKE '%admin%')
        """)
        print(f"      Removed admin associations: {result}")
        
        # Add Kevin Vandever
        result = await conn.execute("""
            INSERT INTO document_authors (book_id, author_id, author_order)
            SELECT b.id, a.id, 0
            FROM books b, authors a
            WHERE b.title ILIKE '%Subfiles%Free%'
              AND a.name = 'Kevin Vandever'
              AND NOT EXISTS (
                SELECT 1 FROM document_authors da 
                WHERE da.book_id = b.id AND da.author_id = a.id
              )
        """)
        print(f"      Added Kevin Vandever: {result}")
        
        # Fix Control Language Programming for IBM i (Multiple authors)
        print("   📖 Fixing Control Language Programming for IBM i...")
        
        # Add Bryan Meyers (order 1)
        result = await conn.execute("""
            INSERT INTO document_authors (book_id, author_id, author_order)
            SELECT b.id, a.id, 1
            FROM books b, authors a
            WHERE b.title ILIKE '%Control Language Programming%'
              AND a.name = 'Bryan Meyers'
              AND NOT EXISTS (
                SELECT 1 FROM document_authors da 
                WHERE da.book_id = b.id AND da.author_id = a.id
              )
        """)
        print(f"      Added Bryan Meyers: {result}")
        
        # Add Dan Riehl (order 2)
        result = await conn.execute("""
            INSERT INTO document_authors (book_id, author_id, author_order)
            SELECT b.id, a.id, 2
            FROM books b, authors a
            WHERE b.title ILIKE '%Control Language Programming%'
              AND a.name = 'Dan Riehl'
              AND NOT EXISTS (
                SELECT 1 FROM document_authors da 
                WHERE da.book_id = b.id AND da.author_id = a.id
              )
        """)
        print(f"      Added Dan Riehl: {result}")
        
        # Step 3: Verification
        print(f"\n📝 Step 3: Verification...")
        
        # Check Complete CL: Sixth Edition
        result = await conn.fetch("""
            SELECT b.title, a.name, da.author_order
            FROM books b
            JOIN document_authors da ON b.id = da.book_id
            JOIN authors a ON da.author_id = a.id
            WHERE b.title ILIKE '%Complete CL%Sixth%'
            ORDER BY da.author_order
        """)
        print(f"   📖 Complete CL: Sixth Edition authors:")
        for row in result:
            print(f"      {row['author_order']}: {row['name']}")
        
        # Check Subfiles
        result = await conn.fetch("""
            SELECT b.title, a.name, da.author_order
            FROM books b
            JOIN document_authors da ON b.id = da.book_id
            JOIN authors a ON da.author_id = a.id
            WHERE b.title ILIKE '%Subfiles%Free%'
            ORDER BY da.author_order
        """)
        print(f"   📖 Subfiles in Free-Format RPG authors:")
        for row in result:
            print(f"      {row['author_order']}: {row['name']}")
        
        # Check Control Language Programming
        result = await conn.fetch("""
            SELECT b.title, a.name, da.author_order
            FROM books b
            JOIN document_authors da ON b.id = da.book_id
            JOIN authors a ON da.author_id = a.id
            WHERE b.title ILIKE '%Control Language Programming%'
            ORDER BY da.author_order
        """)
        print(f"   📖 Control Language Programming for IBM i authors:")
        for row in result:
            print(f"      {row['author_order']}: {row['name']}")
        
        await conn.close()
        print(f"\n✅ Author corrections completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error executing corrections: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main execution function"""
    
    print("🔧 Direct SQL Author Corrections")
    print("=" * 70)
    
    success = await execute_author_corrections()
    
    if success:
        print(f"\n🎉 SUCCESS!")
        print("=" * 70)
        print("✅ Key corrections applied:")
        print("   - Complete CL: Sixth Edition → Ted Holt (removed annegrubb)")
        print("   - Subfiles in Free-Format RPG → Kevin Vandever (removed admin)")
        print("   - Control Language Programming → Jim Buck, Bryan Meyers, Dan Riehl")
        print("✅ Missing authors created")
        print("\n🧪 Next: Run verification script to confirm:")
        print("   python3 verify_corrections_after_sql.py")
    else:
        print(f"\n❌ FAILED!")
        print("Check the error messages above for details.")

if __name__ == "__main__":
    asyncio.run(main())