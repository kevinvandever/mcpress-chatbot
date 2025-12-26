"""
Fix Article URLs Endpoint
Fixes the URL typo in article_url column (ww -> www)
"""

from fastapi import APIRouter, HTTPException
import asyncpg
import os
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fix-article-urls", tags=["fixes"])

@router.post("")
async def fix_article_urls() -> Dict[str, Any]:
    """
    Fix article URLs - replace 'ww.mcpressonline.com' with 'www.mcpressonline.com'
    """
    start_time = time.time()
    
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            logger.info("🔍 Checking for URLs with typo...")
            
            # Count URLs with the typo
            typo_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM books 
                WHERE article_url LIKE 'https://ww.mcpressonline.com%'
            """)
            
            logger.info(f"Found {typo_count} URLs with 'ww' typo")
            
            if typo_count == 0:
                return {
                    "success": True,
                    "urls_fixed": 0,
                    "processing_time": time.time() - start_time,
                    "message": "No URLs needed fixing"
                }
            
            # Show some examples
            examples = await conn.fetch("""
                SELECT filename, article_url 
                FROM books 
                WHERE article_url LIKE 'https://ww.mcpressonline.com%'
                LIMIT 3
            """)
            
            logger.info("Examples of URLs to fix:")
            for example in examples:
                logger.info(f"  {example['filename']}: {example['article_url']}")
            
            # Fix the URLs
            logger.info(f"🔧 Fixing {typo_count} URLs...")
            
            result = await conn.execute("""
                UPDATE books 
                SET article_url = REPLACE(article_url, 'https://ww.mcpressonline.com', 'https://www.mcpressonline.com')
                WHERE article_url LIKE 'https://ww.mcpressonline.com%'
            """)
            
            # Extract the number of updated rows
            updated_count = int(result.split()[-1])
            
            logger.info(f"✅ Fixed {updated_count} article URLs")
            
            # Verify the fix
            remaining_typos = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM books 
                WHERE article_url LIKE 'https://ww.mcpressonline.com%'
            """)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "urls_fixed": updated_count,
                "typos_found": typo_count,
                "remaining_typos": remaining_typos,
                "processing_time": processing_time,
                "message": f"Successfully fixed {updated_count} article URLs"
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"URL fix failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time
        }