"""
Dead simple metadata update endpoint that works
Just updates the documents table metadata directly
"""

from fastapi import APIRouter, HTTPException
import os
import asyncpg
import json
import asyncio

router = APIRouter()

@router.get("/simple/test")
async def simple_test():
    """Ultra simple test that should always work"""
    return {"status": "working", "message": "Simple endpoint is responsive"}

@router.get("/simple/db-info")
async def db_info():
    """Check database URL format without connecting"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        return {"error": "DATABASE_URL not set"}

    # Parse the URL to hide password
    if '@' in database_url:
        parts = database_url.split('@')
        if '://' in parts[0]:
            protocol = parts[0].split('://')[0]
            host_part = parts[1] if len(parts) > 1 else 'unknown'
            masked = f"{protocol}://[CREDENTIALS]@{host_part}"
        else:
            masked = "Invalid format"
    else:
        masked = database_url

    return {
        "database_url_present": True,
        "url_format": masked,
        "url_length": len(database_url),
        "starts_with": database_url[:10] if len(database_url) > 10 else database_url
    }

@router.get("/simple/list")
async def simple_list():
    """List documents without any complex initialization"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return {"error": "No DATABASE_URL"}

    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=5.0
        )

        # Just get unique documents from documents table
        rows = await conn.fetch("""
            SELECT DISTINCT ON (filename)
                filename,
                metadata
            FROM documents
            ORDER BY filename
            LIMIT 20
        """)

        docs = []
        for row in rows:
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                except:
                    pass

            docs.append({
                'filename': row['filename'],
                'title': metadata.get('title', row['filename'].replace('.pdf', '')),
                'author': metadata.get('author', 'Unknown'),
                'category': metadata.get('category', 'General')
            })

        await conn.close()
        return {"documents": docs, "count": len(docs)}

    except Exception as e:
        return {"error": str(e)}

@router.post("/simple/update-metadata")
async def update_metadata(filename: str, author: str = None, mc_press_url: str = None):
    """Update metadata for a document - simple version"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return {"error": "No DATABASE_URL"}

    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=5.0
        )

        # Get current metadata
        current = await conn.fetchrow(
            "SELECT metadata FROM documents WHERE filename = $1 LIMIT 1",
            filename
        )

        if not current:
            await conn.close()
            return {"error": f"Document {filename} not found"}

        # Parse current metadata
        metadata = {}
        if current['metadata']:
            try:
                metadata = json.loads(current['metadata']) if isinstance(current['metadata'], str) else current['metadata']
            except:
                pass

        # Update fields
        if author:
            metadata['author'] = author
        if mc_press_url:
            metadata['mc_press_url'] = mc_press_url

        # Update all chunks for this document
        result = await conn.execute("""
            UPDATE documents
            SET metadata = $1
            WHERE filename = $2
        """, json.dumps(metadata), filename)

        await conn.close()

        # Parse result to get update count
        count = int(result.split()[-1]) if result else 0

        return {
            "success": True,
            "filename": filename,
            "chunks_updated": count,
            "new_metadata": metadata
        }

    except Exception as e:
        return {"error": str(e)}