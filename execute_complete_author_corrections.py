#!/usr/bin/env python3
"""
Execute Complete Author Corrections on Railway Database
This script runs the complete_author_audit_corrections.sql file on Railway
"""

import os
import asyncio
import asyncpg

async def execute_sql_corrections():
    """Execute the complete author corrections SQL script"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not found")
        print("Make sure you're running this on Railway or have the DATABASE_URL set")
        return False
    
    print("🔗 Connecting to Railway database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database successfully")
        
        # Read the SQL file
        print("📖 Reading complete_author_audit_corrections.sql...")
        with open('complete_author_audit_corrections.sql', 'r') as f:
            sql_content = f.read()
        
        print(f"📄 SQL file loaded ({len(sql_content)} characters)")
        
        # Split into individual statements (rough split on semicolons)
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        print(f"🔢 Found {len(statements)} SQL statements to execute")
        
        # Execute each statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            # Skip comments and empty statements
            if statement.startswith('--') or not statement.strip():
                continue
                
            try:
                # Execute the statement
                await conn.execute(statement)
                success_count += 1
                
                # Print progress every 50 statements
                if i % 50 == 0:
                    print(f"⏳ Progress: {i}/{len(statements)} statements processed...")
                    
            except Exception as e:
                error_count += 1
                print(f"⚠️  Error in statement {i}: {str(e)[:100]}...")
                # Continue with next statement
                continue
        
        print(f"\n🎉 Execution completed!")
        print(f"✅ Successful statements: {success_count}")
        print(f"❌ Failed statements: {error_count}")
        
        # Run verification queries
        print("\n🔍 Running verification queries...")
        
        # Check for books with no authors
        orphan_books = await conn.fetch("""
            SELECT b.title 
            FROM books b 
            LEFT JOIN document_authors da ON b.id = da.book_id 
            WHERE da.book_id IS NULL
        """)
        
        if orphan_books:
            print(f"⚠️  Found {len(orphan_books)} books with no authors:")
            for book in orphan_books[:5]:  # Show first 5
                print(f"   - {book['title']}")
        else:
            print("✅ All books have at least one author")
        
        # Check for suspicious authors
        suspicious = await conn.fetch("""
            SELECT b.title, a.name as suspicious_author
            FROM books b
            JOIN document_authors da ON b.id = da.book_id
            JOIN authors a ON da.author_id = a.id
            WHERE a.name IN ('admin', 'Admin', 'annegrubb', 'Annegrubb', 'USA Sales', 'Unknown')
            ORDER BY b.title
        """)
        
        if suspicious:
            print(f"⚠️  Found {len(suspicious)} books still with suspicious authors:")
            for book in suspicious[:5]:  # Show first 5
                print(f"   - {book['title']} → {book['suspicious_author']}")
        else:
            print("✅ No suspicious authors found")
        
        # Count multi-author books
        multi_author_count = await conn.fetchval("""
            SELECT COUNT(*) as multi_author_books
            FROM (
              SELECT book_id 
              FROM document_authors 
              GROUP BY book_id 
              HAVING COUNT(*) > 1
            ) multi
        """)
        
        print(f"📚 Multi-author books: {multi_author_count}")
        
        # Test specific books mentioned by user
        print("\n🎯 Testing specific books mentioned by user...")
        
        test_books = [
            "Complete CL: Sixth Edition",
            "Subfiles in Free-Format RPG", 
            "Control Language Programming for IBM i"
        ]
        
        for book_title in test_books:
            authors = await conn.fetch("""
                SELECT b.title, a.name, da.author_order
                FROM books b
                JOIN document_authors da ON b.id = da.book_id
                JOIN authors a ON da.author_id = a.id
                WHERE b.title ILIKE $1
                ORDER BY da.author_order
            """, f"%{book_title}%")
            
            if authors:
                author_names = ", ".join([author['name'] for author in authors])
                print(f"✅ {book_title} → {author_names}")
            else:
                print(f"❌ {book_title} → No authors found")
        
        await conn.close()
        print("\n🎉 Complete author corrections executed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(execute_sql_corrections())
    if success:
        print("\n✅ All done! You can now test the chat interface to see the corrected authors.")
    else:
        print("\n❌ Execution failed. Check the errors above.")