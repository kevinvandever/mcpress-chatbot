"""
Endpoint to regenerate embeddings for all existing documents
Useful when documents were uploaded before embedding support was added
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Will be set by main.py
vector_store = None

# Import background task module
try:
    from background_embeddings import start_background_regeneration, get_regeneration_status
except ImportError:
    from backend.background_embeddings import start_background_regeneration, get_regeneration_status

def set_vector_store(vs):
    global vector_store
    vector_store = vs
    logger.info("✅ Regenerate embeddings router initialized with vector store")

@router.get("/admin/regenerate-embeddings-status")
async def regenerate_embeddings_status() -> Dict[str, Any]:
    """Check status of embedding regeneration (both pending and in-progress)"""
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        # Get background task status
        bg_status = get_regeneration_status()

        # Also check database status
        if not vector_store.pool:
            await vector_store.init_database()

        async with vector_store.pool.acquire() as conn:
            # Count documents without embeddings
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM documents
                WHERE embedding IS NULL OR embedding::text = 'null'
            """)

            return {
                "documents_needing_embeddings": result['count'],
                "vector_store_type": "pgvector" if vector_store.has_pgvector else "pure_postgresql",
                "background_task": bg_status
            }
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/regenerate-embeddings-start")
async def regenerate_embeddings_start(batch_size: int = 100) -> Dict[str, Any]:
    """
    Start background embedding regeneration

    Args:
        batch_size: Number of documents to process per batch (default 100)

    This runs in the background and you can check progress with /admin/regenerate-embeddings-status
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        result = start_background_regeneration(vector_store, batch_size)
        return result
    except Exception as e:
        logger.error(f"Error starting background regeneration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/regenerate-embeddings")
async def regenerate_embeddings(limit: int = 10) -> Dict[str, Any]:
    """
    Regenerate embeddings for documents in the database

    Args:
        limit: Number of documents to process (default 10, use 0 for all)

    This fixes the issue where documents exist but have NULL embeddings
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        logger.info(f"🔄 Starting embedding regeneration (limit: {limit if limit > 0 else 'all'})...")

        # Get vector store pool
        if not vector_store.pool:
            await vector_store.init_database()

        async with vector_store.pool.acquire() as conn:
            # Get documents without embeddings
            query = """
                SELECT id, content, filename, page_number, chunk_index, metadata
                FROM documents
                WHERE embedding IS NULL OR embedding::text = 'null'
                ORDER BY id
            """
            if limit > 0:
                query += f" LIMIT {limit}"

            rows = await conn.fetch(query)

            total_docs = len(rows)
            logger.info(f"📊 Found {total_docs} documents without embeddings")

            if total_docs == 0:
                return {
                    "success": True,
                    "message": "All documents already have embeddings",
                    "documents_processed": 0
                }

            # Generate embeddings in batches
            batch_size = 50
            processed = 0

            for i in range(0, total_docs, batch_size):
                batch = rows[i:i+batch_size]

                for row in batch:
                    try:
                        # Generate embedding for this document
                        content = row['content']
                        embedding = vector_store.embedding_model.encode(content).tolist()

                        # Update document with embedding
                        if vector_store.has_pgvector:
                            # Use vector type
                            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                            await conn.execute("""
                                UPDATE documents
                                SET embedding = $1::vector
                                WHERE id = $2
                            """, embedding_str, row['id'])
                        else:
                            # Use JSONB type
                            import json
                            await conn.execute("""
                                UPDATE documents
                                SET embedding = $1::jsonb
                                WHERE id = $2
                            """, json.dumps(embedding), row['id'])

                        processed += 1

                        if processed % 10 == 0:
                            logger.info(f"  ⏳ Processed {processed}/{total_docs} documents...")

                    except Exception as e:
                        logger.error(f"❌ Error processing document {row['id']}: {e}")
                        continue

            logger.info(f"✅ Embedding regeneration complete! Processed {processed}/{total_docs} documents")

            return {
                "success": True,
                "message": f"Successfully regenerated embeddings for {processed} documents",
                "documents_processed": processed,
                "documents_total": total_docs,
                "documents_failed": total_docs - processed
            }

    except Exception as e:
        logger.error(f"❌ Embedding regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding regeneration failed: {str(e)}")
