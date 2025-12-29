#!/usr/bin/env python3
"""
Fix existing URLs in the database that need normalization
This is a one-time script to fix URLs that were imported before the Task 2 fix
"""

import asyncio
import asyncpg
import os
import re

def normalize_url(url: str) -> str:
    """
    Normalize URL format, specifically fixing "ww.mcpressonline.com" to "www.mcpressonline.com"
    """
    if not url or not url.strip():
        return url
    
    url = url.strip()
    
    # Fix common typo: "ww.mcpressonline.com" -> "www.mcpressonline.com"
    url = re.sub(r'://ww\.mcpressonline\.com', '://www.mcpressonline.com', url, flags=re.IGNORECASE)
    
    # Also handle cases without protocol
    url = re.sub(r'^ww\.mcpressonline\.com', 'www.mcpressonline.com', url, flags=re.IGNORECASE)
    
    return url

async def fix_bad_urls():
    """Fix URLs that need normalization in the database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        print("🔍 Finding URLs that need normalization...")
        
        # Find bad URLs in article_url field
        bad_article_urls = await conn.fetch("""
            SELECT id, filename, title, article_url 
            FROM books 
            WHERE article_url LIKE '%ww.mcpressonline.com%'
            ORDER BY id
        """)
        
        # Find bad URLs in mc_press_url field
        bad_mc_press_urls = await conn.fetch("""
            SELECT id, filename, title, mc_press_url 
            FROM books 
            WHERE mc_press_url LIKE '%ww.mcpressonline.com%'
            ORDER BY id
        """)
        
        total_fixes = 0
        
        # Fix article URLs
        if bad_article_urls:
            print(f"\n📄 Fixing {len(bad_article_urls)} article URLs...")
            for row in bad_article_urls:
                old_url = row['article_url']
                new_url = normalize_url(old_url)
                
                if old_url != new_url:
                    await conn.execute("""
                        UPDATE books 
                        SET article_url = $1 
                        WHERE id = $2
                    """, new_url, row['id'])
                    
                    print(f"  ✓ ID {row['id']}: {old_url} -> {new_url}")
                    total_fixes += 1
        
        # Fix mc_press URLs
        if bad_mc_press_urls:
            print(f"\n📚 Fixing {len(bad_mc_press_urls)} mc_press URLs...")
            for row in bad_mc_press_urls:
                old_url = row['mc_press_url']
                new_url = normalize_url(old_url)
                
                if old_url != new_url:
                    await conn.execute("""
                        UPDATE books 
                        SET mc_press_url = $1 
                        WHERE id = $2
                    """, new_url, row['id'])
                    
                    print(f"  ✓ ID {row['id']}: {old_url} -> {new_url}")
                    total_fixes += 1
        
        if total_fixes > 0:
            print(f"\n🎉 Successfully fixed {total_fixes} URLs!")
            print("All URLs now use the correct 'www.mcpressonline.com' format.")
        else:
            print("\n✅ No URLs needed fixing - all are already properly formatted!")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error fixing URLs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 URL Normalization Fix Script")
    print("This script will fix existing URLs in the database that have 'ww.mcpressonline.com'")
    print("and change them to 'www.mcpressonline.com'\n")
    
    response = input("Do you want to proceed? (y/N): ")
    if response.lower() in ['y', 'yes']:
        asyncio.run(fix_bad_urls())
    else:
        print("Operation cancelled.")