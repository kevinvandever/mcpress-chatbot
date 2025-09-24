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

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from datetime import datetime
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
    from auth_routes import router as auth_router
except ImportError:
    # Fall back to local development imports
    from backend.pdf_processor_full import PDFProcessorFull
    from backend.chat_handler import ChatHandler
    from backend.backup_manager import backup_manager
    from backend.auth_routes import router as auth_router

# Import the fixed admin documents router
try:
    # Try Railway-style import first
    try:
        from admin_documents_fixed import router as admin_docs_router, set_vector_store
        admin_docs_available = True
        print("✅ Using fixed admin documents endpoints")
    except ImportError:
        # Fallback to local development import
        from backend.admin_documents_fixed import router as admin_docs_router, set_vector_store
        admin_docs_available = True
        print("✅ Using fixed admin documents endpoints (local)")
except Exception as e:
    print(f"⚠️ Admin documents not available: {e}")
    admin_docs_router = None
    set_vector_store = None
    admin_docs_available = False

# Check vector store preference - try multiple variable names due to Railway caching issues
use_postgresql_env = os.getenv('USE_POSTGRESQL', '')
enable_postgresql_env = os.getenv('ENABLE_POSTGRESQL', '')
database_url = os.getenv('DATABASE_URL', '')

# Check both variable names to work around Railway caching
use_postgresql = (use_postgresql_env.lower() == 'true' or enable_postgresql_env.lower() == 'true')

print(f"🔍 DEBUG: USE_POSTGRESQL env = '{use_postgresql_env}'")
print(f"🔍 DEBUG: ENABLE_POSTGRESQL env = '{enable_postgresql_env}'")
print(f"🔍 DEBUG: DATABASE_URL present = {bool(database_url)}")
print(f"🔍 DEBUG: use_postgresql = {use_postgresql}")

if use_postgresql:
    # Use modern PostgreSQL with pgvector for semantic search
    try:
        # Try both local and Railway import paths
        try:
            from vector_store_postgres import PostgresVectorStore
        except ImportError:
            from backend.vector_store_postgres import PostgresVectorStore
        VectorStoreClass = PostgresVectorStore
        print("✅ Using PostgreSQL with semantic embeddings (persistent, reliable)")
    except ImportError as e:
        print(f"❌ CRITICAL: PostgresVectorStore import failed: {e}")
        print("🔍 This is why you're getting text search instead of vector search!")
        # Fallback to old PostgreSQL implementation
        try:
            from vector_store import VectorStore
        except ImportError:
            from backend.vector_store import VectorStore
        VectorStoreClass = VectorStore
        print("⚠️ Using PostgreSQL text search (fallback)")
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

# Add upload endpoints for Railway batch uploads
import subprocess
import sys
from datetime import datetime
from fastapi import BackgroundTasks
from fastapi.responses import HTMLResponse

# Global status tracking for uploads
upload_status = {
    "running": False,
    "last_run": None,
    "result": None,
    "logs": []
}

def run_upload_batch(batch_size: int = 15):
    """Run upload in background"""
    global upload_status
    
    upload_status["running"] = True
    upload_status["last_run"] = datetime.now().isoformat()
    upload_status["logs"] = [f"Starting batch upload with {batch_size} PDFs..."]
    
    try:
        # Run the upload script
        result = subprocess.run([
            sys.executable,
            "/app/backend/railway_batch_upload.py",
            "--batch-size", str(batch_size)
        ], 
        capture_output=True, 
        text=True, 
        timeout=1800  # 30 minutes
        )
        
        upload_status["result"] = {
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],  # Last 2000 chars
            "stderr": result.stderr[-1000:] if result.stderr else None
        }
        upload_status["logs"].append(f"Upload completed with code {result.returncode}")
        
    except subprocess.TimeoutExpired:
        upload_status["result"] = {"error": "Upload timed out after 30 minutes"}
        upload_status["logs"].append("Upload timed out")
    except Exception as e:
        upload_status["result"] = {"error": str(e)}
        upload_status["logs"].append(f"Upload error: {e}")
    finally:
        upload_status["running"] = False

# Configure CORS with proper origins for authentication
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://mc-press-chatbot.netlify.app",  # Production frontend
    "https://mcpress-chatbot.netlify.app",  # Alternative production URL
]

# Add any additional origins from environment variable
cors_env = os.getenv("CORS_ORIGINS")
if cors_env:
    try:
        import json
        additional_origins = json.loads(cors_env)
        if isinstance(additional_origins, list):
            allowed_origins.extend(additional_origins)
    except:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Required for authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)

# Story 004 migration endpoint
try:
    # Try Railway-style import first
    try:
        from migration_story_004_endpoint import router as story4_migration_router, set_vector_store as set_migration_store
        migration_available = True
    except ImportError:
        from backend.migration_story_004_endpoint import router as story4_migration_router, set_migration_store
        migration_available = True
    print("✅ Story 004 migration endpoint enabled")
except Exception as e:
    print(f"⚠️ Story 004 migration endpoint not available: {e}")
    story4_migration_router = None
    set_migration_store = None
    migration_available = False

pdf_processor = PDFProcessorFull()
vector_store = VectorStoreClass()

# Set vector store for admin_documents if available
if admin_docs_available:
    try:
        if set_vector_store:
            set_vector_store(vector_store)
        app.include_router(admin_docs_router)
        print("✅ Admin documents endpoints enabled at /admin/documents")
    except Exception as e:
        print(f"⚠️ Could not enable admin documents: {e}")

# Set vector store for migration if available
if migration_available:
    try:
        if set_migration_store:
            set_migration_store(vector_store)
        app.include_router(story4_migration_router)
        print("✅ Story 004 migration endpoint enabled at /run-story4-migration-safe")
    except Exception as e:
        print(f"⚠️ Could not enable migration endpoint: {e}")

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
        
        # Defensive: ensure cache is always a dict with 'documents' key
        if not isinstance(_documents_cache, dict):
            print(f"⚠️ Vector store returned unexpected format: {type(_documents_cache)}")
            _documents_cache = {'documents': [] if _documents_cache is None else _documents_cache}
        elif 'documents' not in _documents_cache:
            print(f"⚠️ Vector store missing 'documents' key, fixing...")
            _documents_cache = {'documents': []}
        
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
        cache_result = await get_cached_documents(force_refresh=True)
        doc_count = len(cache_result.get('documents', []) if isinstance(cache_result, dict) else [])
        print(f"✅ Documents cache ready - {doc_count} documents loaded!")
    except Exception as e:
        print(f"⚠️  Cache preload failed: {e} (will load on first request)")
        import traceback
        print(f"🔍 Debug traceback: {traceback.format_exc()}")
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

# Search endpoint removed - will be replaced with conversation history search in future stories

# Upload Batch Management Endpoints
@app.get("/upload/trigger/{batch_size}")
async def trigger_upload(batch_size: int, background_tasks: BackgroundTasks):
    """Trigger batch upload"""
    if upload_status["running"]:
        return {"error": "Upload already running", "status": upload_status}
    
    background_tasks.add_task(run_upload_batch, batch_size)
    return {"message": f"Upload started for {batch_size} PDFs", "status": "started"}

@app.get("/upload/status")
async def get_upload_status():
    """Get upload status"""
    return upload_status

@app.get("/upload/dashboard")
async def upload_dashboard():
    """Simple HTML dashboard for triggering uploads"""
    html = f"""
    <html>
    <head><title>Railway PDF Upload Dashboard</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🚂 Railway PDF Upload Dashboard</h1>
        
        <div style="background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>Current Status</h3>
            <p><strong>Running:</strong> {upload_status['running']}</p>
            <p><strong>Last Run:</strong> {upload_status['last_run'] or 'Never'}</p>
        </div>
        
        <div style="margin: 20px 0;">
            <h3>Quick Actions</h3>
            <a href="/upload/trigger/15" style="background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📤 Upload 15 PDFs
            </a>
            <a href="/upload/trigger/10" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📤 Upload 10 PDFs
            </a>
            <a href="/upload/trigger/5" style="background: #ffc107; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📤 Upload 5 PDFs (test)
            </a>
            <a href="/upload/status" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📊 Check Status
            </a>
        </div>
        
        <div style="background: #e9ecef; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>Recent Logs</h3>
            <pre>{chr(10).join(upload_status['logs'][-10:])}</pre>
        </div>
        
        <div style="background: #d1ecf1; padding: 15px; margin: 10px 0; border-radius: 5px; color: #0c5460;">
            <h3>Instructions</h3>
            <p>1. Click "Upload X PDFs" to start a batch upload</p>
            <p>2. Monitor progress with "Check Status"</p>
            <p>3. Page auto-refreshes every 30 seconds</p>
            <p>4. Each batch processes PDFs already on Railway server</p>
        </div>
        
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/upload/debug")
async def upload_debug():
    """Debug endpoint to check upload directories and files"""
    debug_info = {}
    
    # Check possible upload directories
    possible_paths = [
        '/app/backend/uploads',
        '/app/data/uploads', 
        '/app/uploads',
        '/app/backend',
        '/app'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                files = os.listdir(path)
                pdf_files = [f for f in files if f.endswith('.pdf')]
                debug_info[path] = {
                    "exists": True,
                    "total_files": len(files),
                    "pdf_files": len(pdf_files),
                    "sample_files": files[:5]  # First 5 files
                }
            except Exception as e:
                debug_info[path] = {"exists": True, "error": str(e)}
        else:
            debug_info[path] = {"exists": False}
    
    # Also check environment variables
    debug_info["environment"] = {
        "UPLOAD_DIR": os.getenv('UPLOAD_DIR', 'Not set'),
        "RAILWAY_ENVIRONMENT": os.getenv('RAILWAY_ENVIRONMENT', 'Not set'),
        "current_working_directory": os.getcwd()
    }
    
    return debug_info

@app.get("/documents")
async def list_documents():
    """List all documents with intelligent caching - fast response for frontend"""
    try:
        # Try to serve from cache first for instant response
        if _documents_cache is not None:
            print(f"⚡ Serving cached documents immediately")
            # Trigger background refresh if cache is stale
            current_time = time.time()
            if (current_time - _cache_timestamp) > CACHE_TTL:
                asyncio.create_task(get_cached_documents(force_refresh=True))
            return _documents_cache
        else:
            # First load - do it sync
            return await get_cached_documents()
    except Exception as e:
        print(f"❌ Error getting documents: {e}")
        # Return empty list so frontend doesn't break
        return {"documents": []}

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

@app.post("/bulk-upload")
async def trigger_bulk_upload():
    """Trigger bulk upload of all remaining PDFs"""
    try:
        import subprocess
        import asyncio
        
        # Start the bulk upload script in background
        process = subprocess.Popen([
            "python", "/app/backend/railway_bulk_upload.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        return {
            "status": "started",
            "message": "Bulk upload started in background",
            "process_id": process.pid
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bulk upload: {str(e)}")

@app.get("/bulk-upload/status")
async def bulk_upload_status():
    """Check bulk upload status by counting documents"""
    try:
        docs = await get_all_documents()
        return {
            "status": "running" if len(docs) < 100 else "complete",
            "current_documents": len(docs),
            "target_documents": 115,
            "progress_percent": (len(docs) / 115) * 100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "vector_store": True,
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "restart_trigger": "2025-08-13-restart"  # Force restart
    }

# Note: Admin endpoints removed - they were causing network errors
# The admin functionality needs to be in a separate module that handles
# database connections properly without breaking the main app

@app.get("/run-story4-migration")
async def run_story4_migration():
    """Run Story 4 migration - accessible via GET for easy browser access"""
    import asyncpg

    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return {"error": "DATABASE_URL not configured"}

        conn = await asyncpg.connect(database_url)
        results = []

        # Create books table if needed
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                title TEXT,
                author TEXT,
                category TEXT,
                subcategory TEXT,
                description TEXT,
                tags TEXT[],
                mc_press_url TEXT,
                year INTEGER,
                total_pages INTEGER,
                file_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        results.append("Books table ready")

        # Check if migration needed
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")

        if book_count == 0:
            # Migrate from documents
            unique_docs = await conn.fetch("""
                SELECT DISTINCT ON (filename)
                    filename,
                    metadata,
                    created_at
                FROM documents
                ORDER BY filename, created_at ASC
                LIMIT 200
            """)

            migrated = 0
            for doc in unique_docs:
                try:
                    metadata = doc['metadata'] or {}
                    if isinstance(metadata, str):
                        import json
                        metadata = json.loads(metadata) if metadata else {}

                    await conn.execute("""
                        INSERT INTO books (filename, title, author, category, processed_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (filename) DO NOTHING
                    """,
                        doc['filename'],
                        metadata.get('title', doc['filename'].replace('.pdf', '')),
                        metadata.get('author', 'Unknown'),
                        metadata.get('category', 'General'),
                        doc['created_at']
                    )
                    migrated += 1
                except:
                    pass

            results.append(f"Migrated {migrated} documents")

        # Update page counts
        chunk_stats = await conn.fetch("""
            SELECT filename, COUNT(*) as chunks, MAX(page_number) as max_page
            FROM documents
            GROUP BY filename
            LIMIT 200
        """)

        updated = 0
        for stat in chunk_stats:
            pages = stat['max_page'] if stat['max_page'] else max(1, stat['chunks'] // 3)
            result = await conn.execute("""
                UPDATE books SET total_pages = $1 WHERE filename = $2
            """, pages, stat['filename'])
            if '1' in result:
                updated += 1

        results.append(f"Updated {updated} page counts")

        # Get final stats
        final = await conn.fetchrow("""
            SELECT COUNT(*) as books, AVG(total_pages) as avg_pages
            FROM books WHERE total_pages > 0
        """)

        await conn.close()

        return {
            "success": True,
            "results": results,
            "total_books": final['books'],
            "avg_pages": int(final['avg_pages'] or 0)
        }

    except Exception as e:
        return {"error": str(e)}

@app.post("/run-migration-simple-disabled")
async def run_migration_simple():
    """Simple migration endpoint that works without admin_documents"""
    try:
        # Try to get connection from vector store
        if hasattr(vector_store, '_get_connection'):
            conn = await vector_store._get_connection()
        elif hasattr(vector_store, 'get_connection'):
            conn = await vector_store.get_connection()
        else:
            # Try direct connection using asyncpg which is installed
            import asyncpg

            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return {"status": "error", "message": "DATABASE_URL not configured"}

            # Use asyncpg for migration
            conn = await asyncpg.connect(database_url)

            results = []

            try:
                # Create metadata_history table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_history (
                        id SERIAL PRIMARY KEY,
                        book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                        field_name TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        changed_by TEXT NOT NULL,
                        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                results.append("Created metadata_history table")

                # Add indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_history_book_id
                    ON metadata_history(book_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metadata_history_changed_at
                    ON metadata_history(changed_at)
                """)
                results.append("Created indexes")

                # Add missing columns
                columns = [
                    ('subcategory', 'TEXT'),
                    ('description', 'TEXT'),
                    ('tags', 'TEXT[]'),
                    ('mc_press_url', 'TEXT'),
                    ('year', 'INTEGER')
                ]

                for col_name, col_type in columns:
                    try:
                        await conn.execute(f"""
                            ALTER TABLE books
                            ADD COLUMN {col_name} {col_type}
                        """)
                        results.append(f"Added column {col_name}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            results.append(f"Column {col_name} already exists")
                        else:
                            results.append(f"Error with {col_name}: {str(e)}")

                return {"status": "success", "results": results}
            finally:
                await conn.close()

        # Original async code path
        conn = await vector_store._get_connection()
        try:
            async with conn.cursor() as cursor:
                results = []

                # Create metadata_history table
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_history (
                        id SERIAL PRIMARY KEY,
                        book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                        field_name TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        changed_by TEXT NOT NULL,
                        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                results.append("Created metadata_history table")

                # Add missing columns
                columns = [
                    ('subcategory', 'TEXT'),
                    ('description', 'TEXT'),
                    ('tags', 'TEXT[]'),
                    ('mc_press_url', 'TEXT'),
                    ('year', 'INTEGER')
                ]

                for col_name, col_type in columns:
                    try:
                        await cursor.execute(f"""
                            ALTER TABLE books
                            ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                        """)
                        results.append(f"Added column {col_name}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            results.append(f"Column {col_name} already exists")
                        else:
                            results.append(f"Error with {col_name}: {str(e)}")

                await conn.commit()
                return {"status": "success", "results": results}
        finally:
            await conn.close()
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)