#!/usr/bin/env python3
"""
Fix article URLs - replace 'ww.mcpressonline.com' with 'www.mcpressonline.com'
"""

import asyncpg
import os

async def fix_article_urls():
    """Fix the URL typo in article_url column"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    conn = await asyncpg.connect(database_url)
    
    try:
        print("🔍 Checking for URLs with typo...")
        
        # Count URLs with the typo
        typo_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM books 
            WHERE article_url LIKE 'https://ww.mcpressonline.com%'
        """)
        
        print(f"📊 Found {typo_count} URLs with 'ww' typo")
        
        if typo_count == 0:
            print("✅ No URLs need fixing")
            return
        
        # Show some examples
        examples = await conn.fetch("""
            SELECT filename, article_url 
            FROM books 
            WHERE article_url LIKE 'https://ww.mcpressonline.com%'
            LIMIT 5
        """)
        
        print("\n📋 Examples of URLs to fix:")
        for example in examples:
            print(f"  {example['filename']}: {example['article_url']}")
        
        # Fix the URLs
        print(f"\n🔧 Fixing {typo_count} URLs...")
        
        result = await conn.execute("""
            UPDATE books 
            SET article_url = REPLACE(article_url, 'https://ww.mcpressonline.com', 'https://www.mcpressonline.com')
            WHERE article_url LIKE 'https://ww.mcpressonline.com%'
        """)
        
        # Extract the number of updated rows
        updated_count = int(result.split()[-1])
        
        print(f"✅ Fixed {updated_count} article URLs")
        
        # Verify the fix
        remaining_typos = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM books 
            WHERE article_url LIKE 'https://ww.mcpressonline.com%'
        """)
        
        if remaining_typos == 0:
            print("🎉 All URLs fixed successfully!")
        else:
            print(f"⚠️ {remaining_typos} URLs still have typos")
        
        # Show some fixed examples
        fixed_examples = await conn.fetch("""
            SELECT filename, article_url 
            FROM books 
            WHERE article_url LIKE 'https://www.mcpressonline.com%'
            LIMIT 5
        """)
        
        print("\n✅ Examples of fixed URLs:")
        for example in fixed_examples:
            print(f"  {example['filename']}: {example['article_url']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(fix_article_urls())