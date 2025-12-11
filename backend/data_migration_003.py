"""
Data Migration 003: Populate Authors from Existing Books
Feature: multi-author-metadata-enhancement

Migrates existing author data from books.author column to the new normalized schema:
1. Extracts unique authors from books.author column
2. Creates author records with deduplication
3. Creates document_authors associations for all books
4. Verifies all documents have at least one author
"""

import os
import asyncio
import asyncpg
from typing import Dict, List, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import services
try:
    from author_service import AuthorService
    from document_author_service import DocumentAuthorService
except ImportError:
    from backend.author_service import AuthorService
    from backend.document_author_service import DocumentAuthorService

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    exit(1)


async def run_data_migration():
    """
    Execute the data migration to populate authors from existing books
    """
    print("🚀 Starting Data Migration 003: Populate Authors")
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    # Initialize services
    author_service = AuthorService(DATABASE_URL)
    doc_author_service = DocumentAuthorService(DATABASE_URL)
    await author_service.init_database()
    await doc_author_service.init_database()
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Step 1: Check if books table has author column
        print("📋 Step 1: Checking books table schema...")
        
        author_column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'books' AND column_name = 'author'
            )
        """)
        
        if not author_column_exists:
            print("⚠️  Warning: books.author column does not exist")
            print("   This might mean the migration has already been run")
            response = input("   Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                return
        else:
            print("✅ books.author column found")
        
        # Step 2: Get all books with their current author
        print("\n📋 Step 2: Fetching existing books...")
        
        books = await conn.fetch("""
            SELECT id, filename, title, author
            FROM books
            ORDER BY id
        """)
        
        total_books = len(books)
        print(f"✅ Found {total_books} books")
        
        if total_books == 0:
            print("⚠️  No books found in database")
            print("   Migration complete (nothing to migrate)")
            return
        
        # Step 3: Extract unique authors and create author records
        print("\n📋 Step 3: Creating author records...")
        
        author_map: Dict[str, int] = {}  # author_name -> author_id
        books_without_author = []
        
        for book in books:
            author_name = book['author']
            
            # Handle missing authors
            if not author_name or author_name.strip() == '':
                books_without_author.append({
                    'id': book['id'],
                    'filename': book['filename'],
                    'title': book['title']
                })
                continue
            
            author_name = author_name.strip()
            
            # Create or get author (with deduplication)
            if author_name not in author_map:
                try:
                    author_id = await author_service.get_or_create_author(author_name)
                    author_map[author_name] = author_id
                    print(f"  ✅ Created/found author: {author_name} (ID: {author_id})")
                except Exception as e:
                    print(f"  ⚠️  Error creating author '{author_name}': {e}")
                    continue
        
        print(f"\n✅ Created {len(author_map)} unique author records")
        
        # Handle books without authors
        if books_without_author:
            print(f"\n⚠️  Found {len(books_without_author)} books without authors:")
            for book in books_without_author[:5]:  # Show first 5
                print(f"  - {book['filename']}: {book['title']}")
            if len(books_without_author) > 5:
                print(f"  ... and {len(books_without_author) - 5} more")
            
            print("\n❓ How should we handle books without authors?")
            print("  1. Assign to 'Unknown' author")
            print("  2. Skip these books (they won't have authors)")
            print("  3. Cancel migration")
            
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == '1':
                # Create 'Unknown' author
                unknown_author_id = await author_service.get_or_create_author("Unknown")
                print(f"✅ Created 'Unknown' author (ID: {unknown_author_id})")
                
                # Assign all books without authors to 'Unknown'
                for book in books_without_author:
                    author_map[f"_unknown_{book['id']}"] = unknown_author_id
            elif choice == '2':
                print("⚠️  Skipping books without authors")
            else:
                print("❌ Migration cancelled")
                return
        
        # Step 4: Create document_authors associations
        print("\n📋 Step 4: Creating document-author associations...")
        
        associations_created = 0
        associations_skipped = 0
        
        for book in books:
            author_name = book['author']
            
            # Skip if no author
            if not author_name or author_name.strip() == '':
                # Check if we assigned to 'Unknown'
                unknown_key = f"_unknown_{book['id']}"
                if unknown_key in author_map:
                    author_id = author_map[unknown_key]
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
                    order=0  # First (and only) author
                )
                associations_created += 1
                
                if associations_created % 10 == 0:
                    print(f"  ✅ Created {associations_created} associations...")
                    
            except Exception as e:
                # Might already exist
                if "already associated" in str(e):
                    print(f"  ℹ️  Book {book['id']} already has author association")
                else:
                    print(f"  ⚠️  Error associating author with book {book['id']}: {e}")
                associations_skipped += 1
        
        print(f"\n✅ Created {associations_created} document-author associations")
        if associations_skipped > 0:
            print(f"⚠️  Skipped {associations_skipped} associations")
        
        # Step 5: Verify all documents have at least one author
        print("\n📋 Step 5: Verifying migration...")
        
        books_without_authors = await conn.fetch("""
            SELECT b.id, b.filename, b.title
            FROM books b
            LEFT JOIN document_authors da ON b.id = da.book_id
            WHERE da.book_id IS NULL
        """)
        
        if books_without_authors:
            print(f"⚠️  Warning: {len(books_without_authors)} books still have no authors:")
            for book in books_without_authors[:10]:
                print(f"  - Book {book['id']}: {book['filename']}")
            if len(books_without_authors) > 10:
                print(f"  ... and {len(books_without_authors) - 10} more")
        else:
            print("✅ All books have at least one author")
        
        # Step 6: Show statistics
        print("\n📊 Migration Statistics:")
        
        total_authors = await conn.fetchval("SELECT COUNT(*) FROM authors")
        total_associations = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        total_books_with_authors = await conn.fetchval("""
            SELECT COUNT(DISTINCT book_id) FROM document_authors
        """)
        
        print(f"  📚 Total books: {total_books}")
        print(f"  👤 Total authors: {total_authors}")
        print(f"  🔗 Total associations: {total_associations}")
        print(f"  ✅ Books with authors: {total_books_with_authors}")
        print(f"  ⚠️  Books without authors: {total_books - total_books_with_authors}")
        
        # Step 7: Optional - Remove old author column
        if author_column_exists:
            print("\n❓ Remove old books.author column?")
            print("  This column is no longer needed after migration.")
            print("  (You can always add it back if needed)")
            
            remove = input("Remove books.author column? (y/N): ").strip().lower()
            
            if remove == 'y':
                await conn.execute("ALTER TABLE books DROP COLUMN author")
                print("✅ Removed books.author column")
            else:
                print("ℹ️  Keeping books.author column (you can remove it later)")
        
        print("\n🎉 Data Migration 003 completed successfully!")
        print()
        print("📋 Next steps:")
        print("   1. Verify the data looks correct")
        print("   2. Test the application with the new schema")
        print("   3. Update frontend to use new multi-author endpoints")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        print(traceback.format_exc())
        raise
    finally:
        await conn.close()
        await author_service.close()
        await doc_author_service.close()


if __name__ == "__main__":
    asyncio.run(run_data_migration())
