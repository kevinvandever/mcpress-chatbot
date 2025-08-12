import os
import warnings
# Set tokenizer environment variable to suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Suppress specific warnings that clutter logs
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*tokenizers.*")

# Run startup check if on Railway
if os.getenv("RAILWAY_ENVIRONMENT"):
    try:
        from startup_check import check_storage
    except ImportError:
        from backend.startup_check import check_storage
    check_storage()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    # Try Railway-style imports first (when running from /app)
    from pdf_processor_full import PDFProcessorFull
    from chat_handler import ChatHandler
    from backup_manager import backup_manager
except ImportError:
    # Fall back to local development imports
    from backend.pdf_processor_full import PDFProcessorFull
    from backend.chat_handler import ChatHandler
    from backend.backup_manager import backup_manager

# For local development, FORCE ChromaDB usage
# Check if we should use PostgreSQL (only if explicitly set to "true")
use_postgresql = os.getenv('USE_POSTGRESQL', '').lower() == 'true'

if use_postgresql:
    # Use PostgreSQL only if explicitly requested
    try:
        from vector_store import VectorStore
    except ImportError:
        from backend.vector_store import VectorStore
    VectorStoreClass = VectorStore
    print("⚠️ Using PostgreSQL vector store")
else:
    # Default to ChromaDB (for both local and Railway)
    try:
        from vector_store_chroma import ChromaVectorStore
    except ImportError:
        from backend.vector_store_chroma import ChromaVectorStore
    VectorStoreClass = ChromaVectorStore
    print("✅ Using ChromaDB vector store (semantic search)")

try:
    from category_mapper import get_category_mapper
    from async_upload import process_pdf_async, create_upload_job, get_job_status, cleanup_old_jobs
except ImportError:
    from backend.category_mapper import get_category_mapper
    from backend.async_upload import process_pdf_async, create_upload_job, get_job_status, cleanup_old_jobs

load_dotenv()

app = FastAPI(title="MC Press Chatbot API")

# Temporary storage for PDFs awaiting metadata
temp_storage = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Set to False when using wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

pdf_processor = PDFProcessorFull()
vector_store = VectorStoreClass()

# Global cache for documents
_documents_cache = None
_cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes

async def get_cached_documents(force_refresh: bool = False):
    """Get documents with intelligent caching"""
    global _documents_cache, _cache_timestamp
    
    current_time = time.time()
    cache_expired = (current_time - _cache_timestamp) > CACHE_TTL
    
    if _documents_cache is None or cache_expired or force_refresh:
        print(f"📊 Refreshing documents cache...")
        start_time = time.time()
        _documents_cache = await vector_store.list_documents()
        _cache_timestamp = current_time
        elapsed = time.time() - start_time
        print(f"✅ Cache refreshed in {elapsed:.1f}s - {len(_documents_cache.get('documents', []))} documents")
    else:
        print(f"⚡ Serving cached documents ({len(_documents_cache.get('documents', []))} documents)")
    
    return _documents_cache

# Initialize the database on startup
@app.on_event("startup")
async def startup_event():
    # Create automatic backup of existing data
    backup_manager.auto_backup_on_startup()
    
    if hasattr(vector_store, 'init_database'):
        await vector_store.init_database()
    else:
        print("✅ ChromaDB initialized successfully")
    
    # Pre-load documents cache for fast responses
    print("🚀 Pre-loading documents cache...")
    try:
        await get_cached_documents(force_refresh=True)
        print("✅ Documents cache ready - fast responses enabled!")
    except Exception as e:
        print(f"⚠️  Cache preload failed: {e} (will load on first request)")
chat_handler = ChatHandler(vector_store)
category_mapper = get_category_mapper()

# Global upload progress tracking
upload_progress = {}

# Thread pool for concurrent processing
executor = ThreadPoolExecutor(max_workers=3)

class ChatMessage(BaseModel):
    message: str
    conversation_id: str = "default"

class ProcessingStatus(BaseModel):
    status: str
    message: str
    progress: int = 0

class BatchUploadProgress(BaseModel):
    batch_id: str
    total_files: int
    processed_files: int
    current_file: Optional[str] = None
    files_status: Dict[str, Dict[str, Any]] = {}
    overall_progress: int = 0
    status: str = "processing"

@app.get("/")
def read_root():
    return {"message": "MC Press Chatbot API is running"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
    if file.size > max_size:
        raise HTTPException(status_code=400, detail=f"File size exceeds {max_size}MB limit")
    
    try:
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        extracted_content = await pdf_processor.process_pdf(file_path)
        
        # Get category from CSV mapping
        category = category_mapper.get_category(file.filename)
        
        # Check if author metadata is missing
        author = extracted_content.get("author")
        needs_author = author is None or author == ""
        
        # DEFAULT TO "Unknown" FOR MISSING AUTHORS - Temporary fix for remaining 5 books
        if needs_author:
            author = "Unknown"
            print(f"⚠️  No author found for {file.filename}, defaulting to 'Unknown'")
        
        print(f"📝 Upload status for {file.filename}: Author = '{author}'")
        
        # Always proceed with upload now (no more temp storage for missing authors)
        await vector_store.add_documents(
            documents=extracted_content["chunks"],
            metadata={
                "filename": file.filename,
                "total_pages": extracted_content["total_pages"],
                "has_images": len(extracted_content["images"]) > 0,
                "has_code": len(extracted_content["code_blocks"]) > 0,
                "category": category,
                "title": file.filename.replace('.pdf', ''),
                "author": author
            }
        )
        
        # Invalidate cache after successful upload
        global _cache_timestamp
        _cache_timestamp = 0
        print(f"📚 Uploaded {file.filename} - cache invalidated")
        
        return {
            "status": "success",
            "message": f"Successfully processed {file.filename}",
            "chunks_created": len(extracted_content["chunks"]),
            "images_processed": len(extracted_content["images"]),
            "code_blocks_found": len(extracted_content["code_blocks"]),
            "total_pages": extracted_content["total_pages"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_single_pdf(file_content: bytes, filename: str, batch_id: str, file_index: int, total_files: int):
    """Process a single PDF file as part of a batch"""
    try:
        # Update progress: uploading
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "uploading",
            "progress": 0,
            "message": "Uploading..."
        }
        
        # Save file
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Update progress: processing
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "processing",
            "progress": 30,
            "message": "Processing PDF..."
        }
        upload_progress[batch_id]["current_file"] = filename
        
        # Process PDF
        extracted_content = await pdf_processor.process_pdf(file_path)
        
        # Get metadata and category from CSV mapping
        title = filename.replace('.pdf', '')
        category = category_mapper.get_category(filename)
        
        # Add to vector store with enhanced metadata (with batch splitting for large documents)
        chunks_count = len(extracted_content["chunks"])
        print(f"Adding {chunks_count} chunks to vector store for {filename}")
        
        # Check if author metadata is missing
        author = extracted_content.get("author")
        needs_author = author is None or author == ""
        
        print(f"📝 Batch upload status for {filename}: Author = '{author}', Needs author = {needs_author}")
        
        if needs_author:
            # Store temporarily and mark as needing metadata
            temp_storage[filename] = {
                "extracted_content": extracted_content,
                "category": category,
                "file_path": file_path,
                "batch_id": batch_id
            }
            
            # Update progress with special status
            upload_progress[batch_id]["files_status"][filename] = {
                "status": "needs_metadata",
                "progress": 90,
                "message": "Author extraction failed - manual input required",
                "stats": {
                    "chunks_created": len(extracted_content["chunks"]),
                    "images_processed": len(extracted_content["images"]),
                    "code_blocks_found": len(extracted_content["code_blocks"]),
                    "total_pages": extracted_content["total_pages"],
                    "category": category
                },
                "extraction_details": "Author extraction attempted using PDF metadata and text patterns"
            }
            print(f"📋 File {filename} needs author metadata - stored in temp_storage")
            return "needs_metadata"
        
        try:
            await vector_store.add_documents(
                documents=extracted_content["chunks"],
                metadata={
                    "filename": filename,
                    "title": title,
                    "category": category,
                    "author": author,
                    "total_pages": extracted_content["total_pages"],
                    "has_images": len(extracted_content["images"]) > 0,
                    "has_code": len(extracted_content["code_blocks"]) > 0,
                    "upload_batch": batch_id,
                    "upload_timestamp": time.time()
                }
            )
            print(f"Successfully added all {chunks_count} chunks for {filename}")
        except Exception as e:
            print(f"Error adding chunks to vector store for {filename}: {str(e)}")
            raise
        
        # Update progress: completed
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "completed",
            "progress": 100,
            "message": "Processing complete",
            "stats": {
                "chunks_created": len(extracted_content["chunks"]),
                "images_processed": len(extracted_content["images"]),
                "code_blocks_found": len(extracted_content["code_blocks"]),
                "total_pages": extracted_content["total_pages"],
                "category": category
            }
        }
        
        upload_progress[batch_id]["processed_files"] += 1
        upload_progress[batch_id]["overall_progress"] = int(
            (upload_progress[batch_id]["processed_files"] / total_files) * 100
        )
        
        return True
        
    except Exception as e:
        upload_progress[batch_id]["files_status"][filename] = {
            "status": "error",
            "progress": 0,
            "message": str(e)
        }
        return False

@app.post("/batch-upload")
async def batch_upload_pdfs(files: List[UploadFile] = File(...)):
    """Upload and process multiple PDF files concurrently"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate all files are PDFs
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF file")
    
    # Create batch ID
    batch_id = f"batch_{int(time.time())}"
    
    # Initialize progress tracking
    upload_progress[batch_id] = {
        "batch_id": batch_id,
        "total_files": len(files),
        "processed_files": 0,
        "current_file": None,
        "files_status": {},
        "overall_progress": 0,
        "status": "processing"
    }
    
    # Read all files first to avoid file handle issues
    print(f"Reading {len(files)} files into memory...")
    file_data = []
    total_size = 0
    max_batch_size = int(os.getenv("MAX_BATCH_SIZE_MB", 500)) * 1024 * 1024  # 500MB default
    
    for file in files:
        content = await file.read()
        file_size = len(content)
        total_size += file_size
        
        # Check individual file size
        max_file_size = int(os.getenv("MAX_FILE_SIZE_MB", 100)) * 1024 * 1024
        if file_size > max_file_size:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} exceeds {max_file_size/(1024*1024):.0f}MB limit"
            )
        
        # Check total batch size
        if total_size > max_batch_size:
            raise HTTPException(
                status_code=400, 
                detail=f"Total batch size exceeds {max_batch_size/(1024*1024):.0f}MB limit"
            )
        
        file_data.append((content, file.filename))
    
    print(f"All files read successfully. Total size: {total_size/(1024*1024):.2f}MB")

    # Process files concurrently with rate limiting
    async def process_batch():
        tasks = []
        for i, (content, filename) in enumerate(file_data):
            # Add delay between files to avoid overwhelming the system
            if i > 0 and i % 3 == 0:
                await asyncio.sleep(1)
            
            task = process_single_pdf(content, filename, batch_id, i, len(file_data))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update final status
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        upload_progress[batch_id]["status"] = "completed"
        upload_progress[batch_id]["summary"] = {
            "successful": successful,
            "failed": failed,
            "total": len(files)
        }
    
    # Start processing in background
    asyncio.create_task(process_batch())
    
    return {
        "batch_id": batch_id,
        "message": f"Started processing {len(files)} files",
        "status_url": f"/batch-upload/status/{batch_id}"
    }

@app.get("/batch-upload/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get the status of a batch upload"""
    if batch_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return upload_progress[batch_id]

class CompleteUploadRequest(BaseModel):
    filename: str
    author: str
    mc_press_url: Optional[str] = None

class UpdateMetadataRequest(BaseModel):
    filename: str
    title: str
    author: str
    category: Optional[str] = None
    mc_press_url: Optional[str] = None

@app.post("/complete-upload")
async def complete_upload_with_metadata(request: CompleteUploadRequest):
    """Complete the upload of a PDF that was missing author metadata"""
    print(f"Complete upload request for: '{request.filename}'")
    print(f"Current temp_storage keys: {list(temp_storage.keys())}")
    
    if request.filename not in temp_storage:
        raise HTTPException(status_code=404, detail=f"File '{request.filename}' not found in temporary storage. Available files: {list(temp_storage.keys())}")
    
    try:
        # Retrieve stored data
        stored_data = temp_storage[request.filename]
        extracted_content = stored_data["extracted_content"]
        category = stored_data["category"]
        
        # Add to vector store with provided author and URL
        await vector_store.add_documents(
            documents=extracted_content["chunks"],
            metadata={
                "filename": request.filename,
                "total_pages": extracted_content["total_pages"],
                "has_images": len(extracted_content["images"]) > 0,
                "has_code": len(extracted_content["code_blocks"]) > 0,
                "category": category,
                "title": request.filename.replace('.pdf', ''),
                "author": request.author,
                "mc_press_url": request.mc_press_url
            }
        )
        
        # Clean up temp storage
        del temp_storage[request.filename]
        
        return {
            "status": "success",
            "message": f"Successfully processed {request.filename} with author: {request.author}",
            "chunks_created": len(extracted_content["chunks"]),
            "total_pages": extracted_content["total_pages"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/documents/{filename}/metadata")
async def update_document_metadata(filename: str, request: UpdateMetadataRequest):
    """Update the title, author, category, and MC Press URL metadata for a document"""
    try:
        await vector_store.update_document_metadata(filename, request.title, request.author, request.category, request.mc_press_url)
        return {
            "status": "success",
            "message": f"Successfully updated metadata for {filename}",
            "title": request.title,
            "author": request.author,
            "category": request.category
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(message: ChatMessage):
    async def generate():
        async for chunk in chat_handler.stream_response(
            message.message, 
            message.conversation_id
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/search")
async def search_documents(q: str, n_results: int = 5, filename: str = None, content_types: str = None):
    try:
        book_filter = [filename] if filename else None
        type_filter = content_types.split(',') if content_types else None
        results = await vector_store.search(q, n_results=n_results, book_filter=book_filter, type_filter=type_filter)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all documents with intelligent caching"""
    return await get_cached_documents()

@app.get("/documents/refresh")
async def refresh_documents_cache():
    """Manually refresh the documents cache (useful after uploads)"""
    return await get_cached_documents(force_refresh=True)

@app.get("/api/books")
async def get_books():
    """Frontend compatibility endpoint with caching"""
    result = await get_cached_documents()
    documents = result.get('documents', [])
    return {
        "total": len(documents),
        "books": documents
    }

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    try:
        await vector_store.delete_document(filename)
        # Invalidate cache after deletion
        global _cache_timestamp
        _cache_timestamp = 0
        print(f"🗑️  Deleted {filename} - cache invalidated")
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_database():
    """Reset the entire database - use with caution!"""
    try:
        import shutil
        import os
        
        # Reset the vector store
        vector_store.reset_database()
        
        # Clean up uploads directory
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            shutil.rmtree(uploads_dir)
        os.makedirs(uploads_dir, exist_ok=True)
        
        return {"status": "success", "message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-async")
async def upload_pdf_async(file: UploadFile = File(...)):
    """Upload PDF asynchronously to avoid timeouts"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Save file to disk
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create job and start processing in background
        job_id = create_upload_job(file.filename)
        
        # Start async processing
        asyncio.create_task(process_pdf_async(
            job_id, 
            file_path, 
            pdf_processor, 
            vector_store, 
            category_mapper
        ))
        
        return {
            "status": "accepted",
            "job_id": job_id,
            "message": "Upload started. Check status with /upload-status/{job_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/upload-status/{job_id}")
async def get_upload_status(job_id: str):
    """Check status of async upload"""
    cleanup_old_jobs()  # Clean up old jobs periodically
    return get_job_status(job_id)

@app.post("/backup/create")
async def create_backup():
    """Create a backup of all data"""
    try:
        backup_path = backup_manager.create_backup()
        return {
            "status": "success",
            "backup_path": backup_path,
            "message": "Backup created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")

@app.get("/backup/list")
async def list_backups():
    """List all available backups"""
    try:
        backups = backup_manager.list_backups()
        backup_info = []
        for backup in backups:
            path = Path(backup)
            stat = path.stat()
            backup_info.append({
                "path": backup,
                "name": path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return {"backups": backup_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@app.post("/backup/restore")
async def restore_backup(backup_name: str):
    """Restore from a backup"""
    try:
        backup_path = Path(backup_manager.backup_dir) / backup_name
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
            
        success = backup_manager.restore_backup(str(backup_path))
        if success:
            # Reinitialize vector store after restore
            if hasattr(vector_store, 'reload'):
                await vector_store.reload()
            return {"status": "success", "message": "Backup restored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Restore failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "vector_store": True,  # ChromaDB is always connected if initialized
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)