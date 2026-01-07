#!/usr/bin/env python3
"""
This script must be run on Railway: railway run python3 check_documents_metadata.py
Check what metadata exists in the documents table
"""

try:
    import sys
    import os
    sys.path.append('/app')
    
    from backend.vector_store_postgres import PostgresVectorStore
    import asyncio
    import json
    
    async def main():
        print("🔍 CHECKING DOCUMENTS TABLE METADATA")
        print("=" * 60)
        
        # Initialize vector store
        vector_store = PostgresVectorStore()
        await vector_store.init_database()
        
        async with vector_store.pool.acquire() as conn:
            # Get sample documents with metadata
            print("📡 Querying documents table for metadata samples...")
            
            rows = await conn.fetch("""
                SELECT filename, metadata, created_at
                FROM documents 
                WHERE metadata IS NOT NULL 
                AND filename IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            print(f"📊 Found {len(rows)} documents with metadata:")
            
            for i, row in enumerate(rows[:5]):
                print(f"\n📄 Document {i+1}:")
                print(f"   Filename: {row['filename']}")
                
                metadata = row['metadata']
                if metadata:
                    print(f"   Metadata keys: {list(metadata.keys())}")
                    
                    # Check for author information
                    author = metadata.get('author')
                    title = metadata.get('title')
                    category = metadata.get('category')
                    
                    print(f"   Title: {title}")
                    print(f"   Author: {author}")
                    print(f"   Category: {category}")
                    
                    if author and author != 'Unknown':
                        print(f"   ✅ Found real author data!")
                    else:
                        print(f"   ❌ No author or Unknown author")
                else:
                    print(f"   ❌ No metadata")
            
            # Check how many documents have author metadata
            author_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_docs,
                    COUNT(CASE WHEN metadata->>'author' IS NOT NULL 
                               AND metadata->>'author' != 'Unknown' 
                               AND metadata->>'author' != '' 
                          THEN 1 END) as docs_with_authors,
                    COUNT(CASE WHEN metadata->>'title' IS NOT NULL 
                               AND metadata->>'title' != '' 
                          THEN 1 END) as docs_with_titles
                FROM documents 
                WHERE filename IS NOT NULL
            """)
            
            print(f"\n📊 METADATA STATISTICS:")
            print(f"   Total documents: {author_stats['total_docs']}")
            print(f"   Documents with real authors: {author_stats['docs_with_authors']}")
            print(f"   Documents with titles: {author_stats['docs_with_titles']}")
            
            # Sample some actual author values
            print(f"\n📋 SAMPLE AUTHOR VALUES:")
            author_samples = await conn.fetch("""
                SELECT DISTINCT metadata->>'author' as author, COUNT(*) as count
                FROM documents 
                WHERE metadata->>'author' IS NOT NULL 
                AND metadata->>'author' != ''
                GROUP BY metadata->>'author'
                ORDER BY count DESC
                LIMIT 10
            """)
            
            for sample in author_samples:
                print(f"   '{sample['author']}': {sample['count']} documents")

    if __name__ == "__main__":
        asyncio.run(main())
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This script must be run on Railway where dependencies are available.")
    print("Run: railway run python3 check_documents_metadata.py")
    sys.exit(1)