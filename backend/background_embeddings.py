"""
Background task to regenerate embeddings in batches
"""

import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Global state for background task
_regeneration_task = None
_regeneration_status = {
    "running": False,
    "processed": 0,
    "total": 0,
    "errors": 0,
    "current_batch": 0,
    "total_batches": 0
}

async def regenerate_embeddings_background(vector_store, batch_size: int = 100):
    """
    Regenerate embeddings in background batches
    This runs asynchronously and updates status as it goes
    """
    global _regeneration_status

    try:
        _regeneration_status["running"] = True
        _regeneration_status["processed"] = 0
        _regeneration_status["errors"] = 0

        logger.info("🔄 Starting background embedding regeneration...")

        # Get vector store pool
        if not vector_store.pool:
            await vector_store.init_database()

        async with vector_store.pool.acquire() as conn:
            # Count total documents without embeddings
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM documents
                WHERE embedding IS NULL OR embedding::text = 'null'
            """)

            total_docs = result['count']
            _regeneration_status["total"] = total_docs
            _regeneration_status["total_batches"] = (total_docs + batch_size - 1) // batch_size

            logger.info(f"📊 Found {total_docs} documents needing embeddings")
            logger.info(f"📦 Processing in {_regeneration_status['total_batches']} batches of {batch_size}")

            # Process in batches
            for batch_num in range(_regeneration_status['total_batches']):
                _regeneration_status["current_batch"] = batch_num + 1

                async with vector_store.pool.acquire() as batch_conn:
                    # Get batch of documents
                    rows = await batch_conn.fetch("""
                        SELECT id, content, filename, page_number, chunk_index, metadata
                        FROM documents
                        WHERE embedding IS NULL OR embedding::text = 'null'
                        ORDER BY id
                        LIMIT $1
                    """, batch_size)

                    if not rows:
                        break

                    logger.info(f"🔄 Processing batch {batch_num + 1}/{_regeneration_status['total_batches']} ({len(rows)} documents)")

                    # Generate embeddings for batch
                    for row in rows:
                        try:
                            # Generate embedding
                            content = row['content']
                            embedding = vector_store.embedding_model.encode(content).tolist()

                            # Update document with embedding
                            if vector_store.has_pgvector:
                                # Use vector type
                                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                                await batch_conn.execute("""
                                    UPDATE documents
                                    SET embedding = $1::vector
                                    WHERE id = $2
                                """, embedding_str, row['id'])
                            else:
                                # Use JSONB type
                                import json
                                await batch_conn.execute("""
                                    UPDATE documents
                                    SET embedding = $1::jsonb
                                    WHERE id = $2
                                """, json.dumps(embedding), row['id'])

                            _regeneration_status["processed"] += 1

                        except Exception as e:
                            logger.error(f"❌ Error processing document {row['id']}: {e}")
                            _regeneration_status["errors"] += 1
                            continue

                    # Log progress every batch
                    logger.info(f"✅ Batch {batch_num + 1} complete: {_regeneration_status['processed']}/{total_docs} documents processed")

                    # Small delay to prevent overwhelming the database
                    await asyncio.sleep(0.5)

        logger.info(f"🎉 Embedding regeneration complete! Processed {_regeneration_status['processed']}/{total_docs} documents with {_regeneration_status['errors']} errors")

    except Exception as e:
        logger.error(f"❌ Background embedding regeneration failed: {e}")
        raise
    finally:
        _regeneration_status["running"] = False

def start_background_regeneration(vector_store, batch_size: int = 100):
    """Start the background regeneration task"""
    global _regeneration_task

    if _regeneration_status["running"]:
        return {"error": "Regeneration already running", "status": _regeneration_status}

    # Create background task
    loop = asyncio.get_event_loop()
    _regeneration_task = loop.create_task(regenerate_embeddings_background(vector_store, batch_size))

    return {"message": "Background regeneration started", "status": _regeneration_status}

def get_regeneration_status() -> Dict[str, Any]:
    """Get current status of background regeneration"""
    return _regeneration_status.copy()
