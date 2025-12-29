#!/usr/bin/env python3
"""
Check for existing URLs in the database that need normalization
"""

import asyncio
import asyncpg
import os

async def check_bad_urls():
    """Check for URLs that need normalization in the database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check for bad URLs in article_url field
        bad_article_urls = await conn.fetch("""
            SELECT id, filename, title, article_url 
            FROM books 
            WHERE article_url LIKE '%ww.mcpressonline.com%'
            ORDER BY id
        """)
        
        # Check for bad URLs in mc_press_url field
        bad_mc_press_urls = await conn.fetch("""
            SELECT id, filename, title, mc_press_url 
            FROM books 
            WHERE mc_press_url LIKE '%ww.mcpressonline.com%'
            ORDER BY id
        """)
        
        print("🔍 Checking for URLs that need normalization...")
        
        if bad_article_urls:
            print(f"\n📄 Found {len(bad_article_urls)} articles with bad article_url:")
            for row in bad_article_urls:
                print(f"  ID {row['id']}: {row['filename']} -> {row['article_url']}")
        else:
            print("\n✅ No bad article_url found")
        
        if bad_mc_press_urls:
            print(f"\n📚 Found {len(bad_mc_press_urls)} books with bad mc_press_url:")
            for row in bad_mc_press_urls:
                print(f"  ID {row['id']}: {row['filename']} -> {row['mc_press_url']}")
        else:
            print("\n✅ No bad mc_press_url found")
        
        total_bad = len(bad_article_urls) + len(bad_mc_press_urls)
        
        if total_bad > 0:
            print(f"\n⚠️  Total URLs needing normalization: {total_bad}")
            print("\n💡 To fix these URLs, you can:")
            print("   1. Re-import the Excel files (recommended)")
            print("   2. Run a one-time SQL update script")
        else:
            print("\n🎉 All URLs are already properly formatted!")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error checking URLs: {e}")

if __name__ == "__main__":
    asyncio.run(check_bad_urls())