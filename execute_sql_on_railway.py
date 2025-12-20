#!/usr/bin/env python3
"""
Execute the complete author corrections SQL on Railway database
"""
import os
import psycopg2
from psycopg2 import sql

def execute_sql_file():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Get it from Railway dashboard and run:")
        print("export DATABASE_URL='your-database-url-here'")
        return False
    
    try:
        # Read the SQL file
        with open('complete_author_audit_corrections.sql', 'r') as f:
            sql_content = f.read()
        
        print("Connecting to Railway database...")
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("Executing author corrections SQL...")
        
        # Execute the SQL
        cursor.execute(sql_content)
        
        # Commit changes
        conn.commit()
        
        print("✅ SUCCESS! Author corrections applied.")
        print("\nVerifying results...")
        
        # Run verification queries
        cursor.execute("""
            SELECT b.title, a.name as suspicious_author
            FROM books b
            JOIN document_authors da ON b.id = da.book_id
            JOIN authors a ON da.author_id = a.id
            WHERE a.name IN ('admin', 'Admin', 'annegrubb', 'Annegrubb', 'USA Sales', 'Unknown')
            ORDER BY b.title;
        """)
        
        suspicious = cursor.fetchall()
        if suspicious:
            print(f"⚠️  Still found {len(suspicious)} books with suspicious authors:")
            for book, author in suspicious:
                print(f"  - {book}: {author}")
        else:
            print("✅ No suspicious authors found!")
        
        # Check specific books
        test_books = [
            "Complete CL: Sixth Edition",
            "Subfiles in Free-Format RPG", 
            "Control Language Programming for IBM i"
        ]
        
        for book_title in test_books:
            cursor.execute("""
                SELECT a.name 
                FROM books b
                JOIN document_authors da ON b.id = da.book_id
                JOIN authors a ON da.author_id = a.id
                WHERE b.title ILIKE %s
                ORDER BY da.author_order;
            """, (f'%{book_title}%',))
            
            authors = [row[0] for row in cursor.fetchall()]
            if authors:
                print(f"✅ {book_title}: {', '.join(authors)}")
            else:
                print(f"❌ {book_title}: No authors found")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Author corrections complete!")
        print("Test your chatbot now - the authors should be fixed!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    execute_sql_file()