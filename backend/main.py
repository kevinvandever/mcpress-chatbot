import os
import warnings
# Set tokenizer environment variable to suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Suppress specific warnings that clutter logs
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*tokenizers.*")

# Version marker to force Railway rebuild
__version__ = "1.0.4-story-005-aiohttp"

# Run startup check if on Railway
if os.getenv("RAILWAY_ENVIRONMENT"):
    try:
        from startup_check import check_storage
    except ImportError:
        from backend.startup_check import check_storage
    check_storage()

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
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
    from auth_routes import router as auth_router
except ImportError:
    # Fall back to local development imports
    from backend.pdf_processor_full import PDFProcessorFull
    from backend.chat_handler import ChatHandler
    from backend.auth_routes import router as auth_router

# Import conversation modules separately with better error handling
conversation_router = None
set_conversation_service = None
ConversationService = None
try:
    from conversation_routes import router as conversation_router, set_conversation_service
    from conversation_service import ConversationService
    print("✅ Conversation modules imported (Railway style)")
except ImportError:
    try:
        from backend.conversation_routes import router as conversation_router, set_conversation_service
        from backend.conversation_service import ConversationService
        print("✅ Conversation modules imported (local style)")
    except ImportError as e:
        print(f"⚠️ Could not import conversation modules: {e}")
        conversation_router = None

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

# Import regenerate embeddings router
try:
    try:
        from regenerate_embeddings import router as regenerate_router, set_vector_store as set_regen_store
        print("✅ Using regenerate embeddings endpoint")
    except ImportError:
        from backend.regenerate_embeddings import router as regenerate_router, set_vector_store as set_regen_store
        print("✅ Using regenerate embeddings endpoint (local)")
except Exception as e:
    print(f"⚠️ Regenerate embeddings not available: {e}")
    regenerate_router = None
    set_regen_store = None

# Import UsageGate for freemium question limiting
try:
    try:
        from usage_gate import UsageGate
    except ImportError:
        from backend.usage_gate import UsageGate
    USAGE_GATE_AVAILABLE = True
    print("✅ UsageGate module loaded")
except Exception as e:
    print(f"⚠️ UsageGate not available: {e}")
    USAGE_GATE_AVAILABLE = False

# Import SubscriptionAuthService for cookie-based auth detection in /chat
subscription_auth_service = None
try:
    try:
        from subscription_auth import SubscriptionAuthService
    except ImportError:
        from backend.subscription_auth import SubscriptionAuthService
    subscription_auth_service = SubscriptionAuthService()
    print("✅ SubscriptionAuthService loaded for chat auth detection")
except Exception as e:
    print(f"⚠️ SubscriptionAuthService not available for chat: {e}")

# Import ingestion modules
ingestion_service = None
ingestion_scheduler_instance = None
try:
    try:
        from ingestion_service import IngestionService
        from ingestion_routes import router as ingestion_router, set_ingestion_service
        from ingestion_scheduler import setup_ingestion_scheduler, start_scheduler, stop_scheduler
        INGESTION_AVAILABLE = True
        print("✅ Ingestion modules imported (Railway style)")
    except ImportError:
        from backend.ingestion_service import IngestionService
        from backend.ingestion_routes import router as ingestion_router, set_ingestion_service
        from backend.ingestion_scheduler import setup_ingestion_scheduler, start_scheduler, stop_scheduler
        INGESTION_AVAILABLE = True
        print("✅ Ingestion modules imported (local style)")
except Exception as e:
    print(f"⚠️ Ingestion modules not available: {e}")
    INGESTION_AVAILABLE = False
    ingestion_router = None

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
        raise
else:
    print("❌ CRITICAL: USE_POSTGRESQL must be true - no other vector store backends available")
    raise RuntimeError("USE_POSTGRESQL must be set to 'true'")

try:
    from category_mapper import get_category_mapper
    from async_upload import process_pdf_async, create_upload_job, get_job_status, cleanup_old_jobs
except ImportError:
    from backend.category_mapper import get_category_mapper
    from backend.async_upload import process_pdf_async, create_upload_job, get_job_status, cleanup_old_jobs

# Story-005: Document Processing Pipeline
try:
    try:
        from processing_integration import (
            init_processing_service,
            processing_router,
            get_processing_service
        )
    except ImportError:
        from backend.processing_integration import (
            init_processing_service,
            processing_router,
            get_processing_service
        )
    PROCESSING_PIPELINE_AVAILABLE = True
    print("📦 Story-005: Processing pipeline module loaded")
except ImportError as e:
    print(f"⚠️  Story-005 processing pipeline not available: {e}")
    PROCESSING_PIPELINE_AVAILABLE = False
    processing_router = None

# Story-006: Code File Upload System
try:
    try:
        from code_upload_integration import (
            init_code_upload_system,
            shutdown_code_upload_system,
            router as code_upload_router,
            get_code_upload_health
        )
    except ImportError:
        from backend.code_upload_integration import (
            init_code_upload_system,
            shutdown_code_upload_system,
            router as code_upload_router,
            get_code_upload_health
        )
    CODE_UPLOAD_AVAILABLE = True
    print("📦 Story-006: Code upload system module loaded")
except ImportError as e:
    print(f"⚠️  Story-006 code upload system not available: {e}")
    CODE_UPLOAD_AVAILABLE = False
    code_upload_router = None

load_dotenv()

app = FastAPI(title="MC Press Chatbot API")

# Temporary storage for PDFs awaiting metadata
temp_storage = {}

from datetime import datetime
import re

# Configure CORS with proper origins for authentication
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://mc-chatmaster.netlify.app",  # Production frontend
    "https://staging--mc-chatmaster.netlify.app",  # Staging frontend
    "https://mc-press-chatbot.netlify.app",  # Legacy URL (keep for transition)
    "https://mcpress-chatbot.netlify.app",  # Legacy URL (keep for transition)
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
    expose_headers=[],
)

# Include auth router
app.include_router(auth_router)

# Include subscription auth router (customer auth via Appstle)
try:
    try:
        from subscription_auth_routes import router as subscription_auth_router
    except ImportError:
        from backend.subscription_auth_routes import router as subscription_auth_router
    
    app.include_router(subscription_auth_router)
    print("✅ Subscription auth endpoints enabled at /api/auth/*")
except Exception as e:
    print(f"⚠️ Subscription auth endpoints not available: {e}")

# Multi-Author Books API v2
try:
    try:
        from books_api import router as books_v2_router
    except ImportError:
        from backend.books_api import router as books_v2_router
    
    app.include_router(books_v2_router)
    print("✅ Books API v2 endpoints enabled at /api/v2/books")
except Exception as e:
    print(f"⚠️ Books API v2 not available: {e}")

# Migration 004: Customer Password Authentication
try:
    try:
        from run_migration_004 import router as migration_004_router
    except ImportError:
        from backend.run_migration_004 import router as migration_004_router
    
    app.include_router(migration_004_router)
    print("✅ Migration 004 endpoint enabled at /run-migration-004")
except Exception as e:
    print(f"⚠️ Migration 004 endpoint not available: {e}")

print(f"🚀 Backend version: {__version__}")
pdf_processor = PDFProcessorFull()

# Initialize vector store and verify configuration
print("="*60)
print("🔍 VECTOR STORE INITIALIZATION")
print("="*60)
vector_store = VectorStoreClass()
print(f"✅ Vector Store Class: {VectorStoreClass.__name__}")

# Additional verification for PostgresVectorStore
if VectorStoreClass.__name__ == "PostgresVectorStore":
    import asyncio
    async def verify_pgvector():
        await vector_store.init_database()
        has_pgvector = getattr(vector_store, 'has_pgvector', False)
        doc_count = await vector_store.get_document_count()
        print(f"📊 pgvector enabled: {has_pgvector}")
        print(f"📊 Total documents in database: {doc_count:,}")
        if has_pgvector:
            print("✅ Using native pgvector with cosine distance operator")
        else:
            print("⚠️ pgvector NOT available - using fallback Python calculation")
        print("="*60)

    try:
        asyncio.run(verify_pgvector())
    except Exception as e:
        print(f"⚠️ Could not verify pgvector status: {e}")
        print("="*60)

# Global cache for documents - define functions before using them
_documents_cache = None
_cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes

def invalidate_global_documents_cache():
    """Invalidate the global documents cache"""
    global _documents_cache, _cache_timestamp
    _documents_cache = None
    _cache_timestamp = 0
    print("📤 Global documents cache invalidated")

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

# Set vector store for admin_documents if available
if admin_docs_available:
    try:
        if set_vector_store:
            set_vector_store(vector_store)
        
        # Set global cache invalidator for admin documents
        try:
            from admin_documents_fixed import set_global_cache_invalidator
            set_global_cache_invalidator(invalidate_global_documents_cache)
        except ImportError:
            try:
                from backend.admin_documents_fixed import set_global_cache_invalidator
                set_global_cache_invalidator(invalidate_global_documents_cache)
            except ImportError:
                print("⚠️ Could not set global cache invalidator for admin documents")
        
        app.include_router(admin_docs_router)
        print("✅ Admin documents endpoints enabled at /admin/documents")
    except Exception as e:
        print(f"⚠️ Could not enable admin documents: {e}")

# Author Management API Routes
author_service = None
doc_author_service = None
author_routes_available = False

try:
    try:
        from author_routes import author_router, set_author_services
        from author_service import AuthorService
        from document_author_service import DocumentAuthorService
        author_routes_available = True
    except ImportError:
        from backend.author_routes import author_router, set_author_services
        from backend.author_service import AuthorService
        from backend.document_author_service import DocumentAuthorService
        author_routes_available = True
    print("✅ Author routes loaded")
except Exception as e:
    print(f"⚠️ Author routes not available: {e}")
    author_router = None
    author_routes_available = False

# Document-Author Relationship API Routes
document_author_routes_available = False
try:
    try:
        from document_author_routes import document_author_router, set_document_author_services
        document_author_routes_available = True
    except ImportError:
        from backend.document_author_routes import document_author_router, set_document_author_services
        document_author_routes_available = True
    print("✅ Document-author routes loaded")
except Exception as e:
    print(f"⚠️ Document-author routes not available: {e}")
    document_author_router = None
    document_author_routes_available = False

# Excel Import API Routes (Task 12)
excel_import_routes_available = False
excel_import_router = None
excel_import_service = None

try:
    try:
        from excel_import_routes import router as excel_import_router, set_excel_service
        from excel_import_service import ExcelImportService
        excel_import_routes_available = True
    except ImportError:
        from backend.excel_import_routes import router as excel_import_router, set_excel_service
        from backend.excel_import_service import ExcelImportService
        excel_import_routes_available = True
    print("✅ Excel import routes loaded")
except Exception as e:
    print(f"⚠️ Excel import routes not available: {e}")
    excel_import_router = None
    excel_import_routes_available = False

# Initialize and include conversation router (Story-011)
# Must be after vector_store is initialized
conversation_service = None  # Will be set if initialization succeeds
if conversation_router and ConversationService and set_conversation_service:
    try:
        print("🔄 Initializing conversation service...")
        conversation_service = ConversationService(vector_store)
        set_conversation_service(conversation_service)
        app.include_router(conversation_router)
        print("✅ Conversation history endpoints enabled at /api/conversations")
        # Note: chat_handler will be updated with conversation_service later (after it's created)
    except Exception as e:
        print(f"⚠️ Could not enable conversation service: {e}")
        import traceback
        print(traceback.format_exc())
        print("⚠️ Chat handler will work WITHOUT conversation persistence")
        conversation_service = None
else:
    print("⚠️ Conversation modules not available - chat will work WITHOUT persistence")

# Story-012: Conversation Export System
try:
    try:
        from export_routes import router as export_router, set_export_service
        from export_service import ConversationExportService
    except ImportError:
        from backend.export_routes import router as export_router, set_export_service
        from backend.export_service import ConversationExportService

    EXPORT_AVAILABLE = True
    print("📦 Story-012: Export module loaded")
except ImportError as e:
    print(f"⚠️  Story-012 export system not available: {e}")
    EXPORT_AVAILABLE = False
    export_router = None
    set_export_service = None
    ConversationExportService = None

# Initialize export service if conversation service is available
if EXPORT_AVAILABLE and conversation_service:
    try:
        print("🔄 Initializing export service...")
        export_service = ConversationExportService(conversation_service, vector_store)
        set_export_service(export_service)
        app.include_router(export_router)
        print("✅ Export endpoints enabled at /api/conversations/{id}/export")
    except Exception as e:
        print(f"⚠️ Could not enable export service: {e}")
        import traceback
        print(traceback.format_exc())
elif EXPORT_AVAILABLE and not conversation_service:
    print("⚠️ Export service requires conversation service - skipping")
elif not EXPORT_AVAILABLE:
    print("⚠️ Export modules not available")

# Set vector store for regenerate embeddings if available
if regenerate_router:
    try:
        if set_regen_store:
            set_regen_store(vector_store)
        app.include_router(regenerate_router)
        print("✅ Regenerate embeddings endpoint enabled at /admin/regenerate-embeddings")
    except Exception as e:
        print(f"⚠️ Could not enable regenerate embeddings endpoint: {e}")

# Include Story-005 processing routes
if PROCESSING_PIPELINE_AVAILABLE and processing_router:
    try:
        app.include_router(processing_router)
        print("✅ Processing pipeline endpoints enabled at /api/process/*")
    except Exception as e:
        print(f"⚠️ Could not enable processing pipeline endpoints: {e}")

# Include Story-006 code upload routes
if CODE_UPLOAD_AVAILABLE and code_upload_router:
    try:
        app.include_router(code_upload_router)
        print("✅ Code upload endpoints enabled at /api/code/*")
    except Exception as e:
        print(f"⚠️ Could not enable code upload endpoints: {e}")

# Initialize the database on startup
@app.on_event("startup")
async def startup_event():
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

    # Story-005: Initialize processing service
    if PROCESSING_PIPELINE_AVAILABLE:
        try:
            processing_service = init_processing_service(vector_store, pdf_processor)
            print("✅ Document Processing Service ready (Story-005)")
        except Exception as e:
            print(f"⚠️  Could not initialize processing service: {e}")

    # Story-006: Initialize code upload system
    if CODE_UPLOAD_AVAILABLE:
        try:
            database_url = os.getenv("DATABASE_URL")
            storage_dir = os.getenv("CODE_UPLOAD_STORAGE_DIR", "/tmp/code-uploads")
            upload_service = await init_code_upload_system(
                database_url=database_url,
                storage_dir=storage_dir
            )
            print(f"✅ Code Upload System ready (Story-006) - Storage: {storage_dir}")
        except Exception as e:
            print(f"⚠️  Could not initialize code upload system: {e}")
    
    # Initialize Author Services (Task 6)
    # Note: Services initialize lazily on first use to avoid blocking startup
    global author_service, doc_author_service
    if author_routes_available:
        try:
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                print("🔄 Setting up author services (lazy initialization)...")
                author_service = AuthorService(database_url)
                doc_author_service = DocumentAuthorService(database_url)
                
                # Set services in routes (they'll initialize on first use)
                set_author_services(author_service, doc_author_service)
                
                # Include routers
                app.include_router(author_router)
                print("✅ Author management endpoints enabled at /api/authors/*")
                
                # Include document-author routes if available
                if document_author_routes_available:
                    set_document_author_services(author_service, doc_author_service, vector_store)
                    app.include_router(document_author_router)
                    print("✅ Document-author relationship endpoints enabled at /api/documents/*")
                
                # Initialize Excel Import Service (Task 12)
                if excel_import_routes_available and author_service:
                    try:
                        excel_import_service = ExcelImportService(author_service, database_url)
                        set_excel_service(excel_import_service)
                        app.include_router(excel_import_router)
                        print("✅ Excel import endpoints enabled at /api/excel/*")
                    except Exception as e:
                        print(f"⚠️ Could not enable Excel import routes: {e}")
                        import traceback
                        print(traceback.format_exc())
                elif excel_import_routes_available and not author_service:
                    print("⚠️ Excel import service requires author service - skipping")
                
                # Register book authors migration fix endpoint
                try:
                    try:
                        from fix_book_authors_migration import fix_book_authors_router
                    except ImportError:
                        from backend.fix_book_authors_migration import fix_book_authors_router
                    app.include_router(fix_book_authors_router)
                    print("✅ Book authors migration fix endpoint enabled at /api/fix-book-authors/*")
                except Exception as e:
                    print(f"⚠️ Could not enable book authors migration fix: {e}")
            else:
                print("⚠️ DATABASE_URL not set - author routes disabled")
        except Exception as e:
            print(f"⚠️ Could not enable author routes: {e}")
            import traceback
            print(traceback.format_exc())

    # Initialize Usage Gate for freemium question limiting
    if USAGE_GATE_AVAILABLE:
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                usage_gate = UsageGate(database_url)
                await usage_gate.init()
                print(f"✅ UsageGate ready (limit={usage_gate.free_question_limit})")
            else:
                print("⚠️ DATABASE_URL not set - usage gate disabled")
        except Exception as e:
            print(f"⚠️ Could not initialize usage gate: {e}")
            import traceback
            print(traceback.format_exc())

    # Initialize Auto Content Ingestion
    global ingestion_service, ingestion_scheduler_instance, usage_gate
    if INGESTION_AVAILABLE:
        try:
            ingestion_service = IngestionService(
                vector_store=vector_store,
                pdf_processor=pdf_processor,
                category_mapper=category_mapper,
            )
            await ingestion_service.ensure_table()
            await ingestion_service.mark_interrupted_runs()
            set_ingestion_service(ingestion_service)
            app.include_router(ingestion_router)
            print("✅ Ingestion endpoints enabled at /api/ingestion/*")

            # Start monthly scheduler
            ingestion_scheduler_instance = setup_ingestion_scheduler(ingestion_service)
            await start_scheduler(ingestion_scheduler_instance)
        except Exception as e:
            print(f"⚠️ Could not initialize ingestion service: {e}")
            import traceback
            print(traceback.format_exc())

# Shutdown event handler
@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown for background services"""
    print("🛑 Shutting down services...")

    # Excel Import Service: Close database connections
    if excel_import_service:
        try:
            await excel_import_service.close()
            print("✅ Excel import service shutdown complete")
        except Exception as e:
            print(f"⚠️  Error during Excel import service shutdown: {e}")

    # Story-006: Shutdown code upload system
    if CODE_UPLOAD_AVAILABLE:
        try:
            await shutdown_code_upload_system()
            print("✅ Code upload system shutdown complete")
        except Exception as e:
            print(f"⚠️  Error during code upload system shutdown: {e}")

    # Shutdown ingestion scheduler
    if INGESTION_AVAILABLE and ingestion_scheduler_instance:
        try:
            await stop_scheduler(ingestion_scheduler_instance)
            print("✅ Ingestion scheduler shutdown complete")
        except Exception as e:
            print(f"⚠️  Error during ingestion scheduler shutdown: {e}")

# Initialize chat_handler without persistence first (works immediately)
# Will be updated with conversation_service later if available
chat_handler = ChatHandler(vector_store)

# Update chat_handler with conversation_service if it was successfully initialized
if conversation_service:
    chat_handler.conversation_service = conversation_service
    print("✅ Chat handler updated with conversation persistence")
else:
    print("ℹ️ Chat handler running WITHOUT conversation persistence")

category_mapper = get_category_mapper()

# Global upload progress tracking
upload_progress = {}

# Usage gate for freemium question limiting (initialized in startup_event)
usage_gate = None

# Thread pool for concurrent processing
executor = ThreadPoolExecutor(max_workers=3)

class ChatMessage(BaseModel):
    message: str
    conversation_id: str = "default"
    user_id: str = "guest"  # Default to guest if not provided

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
    return {
        "message": "MC Press Chatbot API is running",
        "version": "2024-09-24-v4-story12-fix",  # Changed to verify deployment
        "timestamp": str(datetime.now())
    }

@app.get("/export/status")
def export_status():
    """Check export service status and PDF generator mode"""
    try:
        if EXPORT_AVAILABLE and 'export_service' in globals():
            pdf_gen = export_service.pdf
            return {
                "export_available": True,
                "weasyprint_available": pdf_gen.use_weasyprint,
                "pdf_mode": "PDF" if pdf_gen.use_weasyprint else "HTML",
                "expected_extension": ".pdf" if pdf_gen.use_weasyprint else ".html",
                "version": "story12-fix-deployed"
            }
        else:
            return {
                "export_available": False,
                "message": "Export service not initialized"
            }
    except Exception as e:
        return {
            "error": str(e),
            "export_available": False
        }

@app.get("/ping")
def simple_ping():
    """Ultra simple endpoint for debugging"""
    return {"pong": True}

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

def parse_authors(author_string: str) -> List[str]:
    """
    Parse multiple authors from a string with various delimiters.
    
    Supports:
    - Semicolon separation: "John Doe; Jane Smith"
    - Comma separation: "John Doe, Jane Smith"
    - "and" separation: "John Doe and Jane Smith"
    - Complex format: "John Doe, Jane Smith, and Bob Wilson"
    
    Args:
        author_string: String containing one or more author names
        
    Returns:
        List of individual author names (trimmed)
        
    Validates: Requirements 6.2
    """
    if not author_string:
        return []
    
    author_string = author_string.strip()
    if not author_string:
        return []
    
    # Handle semicolon separation first (highest priority)
    if ";" in author_string:
        return [author.strip() for author in author_string.split(";") if author.strip()]
    
    # Handle "and" separation with comma support
    if " and " in author_string:
        # Handle "A, B, and C" format
        if "," in author_string:
            parts = author_string.split(",")
            authors = []
            for i, part in enumerate(parts):
                part = part.strip()
                if i == len(parts) - 1 and part.startswith("and "):
                    part = part[4:]  # Remove "and "
                if part:
                    authors.append(part)
            return authors
        else:
            # Simple "A and B" format
            return [author.strip() for author in author_string.split(" and ") if author.strip()]
    
    # Handle edge case: string ends with " and" (incomplete)
    if author_string.endswith(" and"):
        return [author_string[:-4].strip()]
    
    # Handle comma separation
    if "," in author_string:
        return [author.strip() for author in author_string.split(",") if author.strip()]
    
    # Single author
    return [author_string.strip()]

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
        
        # Multi-author parsing and processing
        author_metadata = extracted_content.get("author")
        needs_author = author_metadata is None or author_metadata == ""
        
        print(f"📝 Batch upload status for {filename}: Author metadata = '{author_metadata}', Needs author = {needs_author}")
        
        # Handle missing author metadata with default
        if needs_author:
            print(f"⚠️ No author metadata found for {filename}, using default 'Unknown Author'")
            author_metadata = "Unknown Author"
            parsed_authors = ["Unknown Author"]
        else:
            # Parse multiple authors from metadata
            parsed_authors = parse_authors(author_metadata)
            print(f"📝 Parsed {len(parsed_authors)} authors from '{author_metadata}': {parsed_authors}")
        
        # Determine document type (default to 'book')
        document_type = extracted_content.get("document_type", "book")
        
        try:
            # Initialize database connections if needed
            if author_service and not author_service.pool:
                await author_service.init_database()
            if doc_author_service and not doc_author_service.pool:
                await doc_author_service.init_database()
            
            # Create or get author records using AuthorService
            author_ids = []
            if author_service:
                for author_name in parsed_authors:
                    author_name = author_name.strip()
                    if author_name:
                        try:
                            author_id = await author_service.get_or_create_author(author_name)
                            author_ids.append(author_id)
                            print(f"✅ Created/found author '{author_name}' with ID {author_id}")
                        except Exception as e:
                            print(f"⚠️ Error creating author '{author_name}': {e}")
                            # Continue with other authors
            
            # Create document record in books table
            book_id = None
            if vector_store and vector_store.pool:
                async with vector_store.pool.acquire() as conn:
                    try:
                        book_id = await conn.fetchval("""
                            INSERT INTO books (filename, title, document_type, category, total_pages, processed_at)
                            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                            ON CONFLICT (filename) DO UPDATE SET
                                title = EXCLUDED.title,
                                document_type = EXCLUDED.document_type,
                                category = EXCLUDED.category,
                                total_pages = EXCLUDED.total_pages,
                                processed_at = EXCLUDED.processed_at
                            RETURNING id
                        """, filename, title, document_type, category, extracted_content["total_pages"])
                        print(f"✅ Created/updated book record with ID {book_id} for {filename}")
                    except Exception as e:
                        print(f"⚠️ Error creating book record for {filename}: {e}")
                        # Continue without book record - document will still be added to vector store
            
            # Create document-author associations if services are available
            if doc_author_service and author_ids and book_id:
                try:
                    # Clear existing associations for this document (in case of re-upload)
                    await doc_author_service.clear_document_authors(book_id)
                    
                    # Create new associations in correct order
                    for order, author_id in enumerate(author_ids):
                        await doc_author_service.add_author_to_document(book_id, author_id, order)
                        print(f"✅ Associated author ID {author_id} with document ID {book_id} (order {order})")
                    
                    print(f"✅ Created {len(author_ids)} document-author associations for {filename}")
                except Exception as e:
                    print(f"⚠️ Error creating document-author associations: {e}")
                    # Continue - the document is still added to vector store
            
            # Add to vector store with enhanced metadata
            await vector_store.add_documents(
                documents=extracted_content["chunks"],
                metadata={
                    "filename": filename,
                    "title": title,
                    "category": category,
                    "author": "; ".join(parsed_authors),  # Legacy field for compatibility
                    "document_type": document_type,
                    "total_pages": extracted_content["total_pages"],
                    "has_images": len(extracted_content["images"]) > 0,
                    "has_code": len(extracted_content["code_blocks"]) > 0,
                    "upload_batch": batch_id,
                    "upload_timestamp": time.time(),
                    "book_id": book_id  # Link to books table record
                }
            )
            print(f"Successfully added all {chunks_count} chunks for {filename}")
            
        except Exception as e:
            print(f"Error processing document {filename}: {str(e)}")
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
                "category": category,
                "authors_parsed": len(parsed_authors),
                "authors_created": len(author_ids),
                "document_type": document_type,
                "book_id": book_id
            },
            "authors": parsed_authors
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
    article_url: Optional[str] = None

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
        
        # Parse multiple authors from provided author string
        parsed_authors = parse_authors(request.author)
        print(f"📝 Complete upload: Parsed {len(parsed_authors)} authors from '{request.author}': {parsed_authors}")
        
        # Create or get author records using AuthorService
        author_ids = []
        if author_service:
            for author_name in parsed_authors:
                author_name = author_name.strip()
                if author_name:
                    try:
                        author_id = await author_service.get_or_create_author(author_name)
                        author_ids.append(author_id)
                        print(f"✅ Created/found author '{author_name}' with ID {author_id}")
                    except Exception as e:
                        print(f"⚠️ Error creating author '{author_name}': {e}")
        
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
                "author": "; ".join(parsed_authors),  # Legacy field for compatibility
                "document_type": "book",  # Default for manual uploads
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
    """Update the title, author, category, MC Press URL, and article URL metadata for a document"""
    global _cache_timestamp
    
    # Input validation
    if not request.title or not request.title.strip():
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")
    
    # Validate URL formats if provided
    if request.mc_press_url and request.mc_press_url.strip():
        url = request.mc_press_url.strip()
        if not (url.startswith('http://') or url.startswith('https://')):
            raise HTTPException(status_code=400, detail="MC Press URL must start with http:// or https://")
    
    if request.article_url and request.article_url.strip():
        url = request.article_url.strip()
        if not (url.startswith('http://') or url.startswith('https://')):
            raise HTTPException(status_code=400, detail="Article URL must start with http:// or https://")
    
    try:
        # Decode filename if it was URL-encoded
        decoded_filename = filename
        
        await vector_store.update_document_metadata(
            decoded_filename, 
            request.title.strip(), 
            request.author.strip() if request.author else '', 
            request.category.strip() if request.category else None, 
            request.mc_press_url.strip() if request.mc_press_url else None,
            request.article_url.strip() if request.article_url else None
        )
        
        # Invalidate the documents cache so changes are visible immediately
        _cache_timestamp = 0
        print(f"✅ Updated metadata for {decoded_filename} - cache invalidated")
        
        return {
            "status": "success",
            "message": f"Successfully updated metadata for {decoded_filename}",
            "title": request.title.strip(),
            "author": request.author.strip() if request.author else '',
            "category": request.category.strip() if request.category else None,
            "mc_press_url": request.mc_press_url.strip() if request.mc_press_url else None,
            "article_url": request.article_url.strip() if request.article_url else None
        }
    except ValueError as e:
        # Validation errors from vector_store
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error updating metadata for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")

@app.post("/chat")
async def chat(
    request: Request,
    message: ChatMessage,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    # 1. Verify session token (required)
    session_token = request.cookies.get("session_token")
    email = ""
    subscription_status = "free"
    user_id = message.user_id if message.user_id else "guest"

    if session_token and subscription_auth_service:
        claims = subscription_auth_service.verify_token(session_token, allow_grace=False)
        if claims:
            email = claims.get("sub", "")
            subscription_status = claims.get("subscription_status", "free")
            user_id = email or user_id
            print(f"✅ Authenticated user: {email} (subscription_status={subscription_status})")
        else:
            return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})
    elif credentials:
        # Admin JWT auth fallback
        try:
            from auth_routes import get_current_user
            user = await get_current_user(credentials)
            user_id = str(user.get("id", user_id))
            subscription_status = "active"  # Admin users have full access
            print(f"✅ Authenticated admin user (JWT): {user_id}")
        except Exception as e:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})
    else:
        return JSONResponse(status_code=401, content={"error": "Authentication required"})

    # 2. Usage gate for free-tier users only
    if subscription_status != "active" and usage_gate:
        result = await usage_gate.check_usage(email)
        if not result.allowed:
            return JSONResponse(status_code=402, content={
                "error": "Free questions exhausted",
                "signup_url": result.signup_url,
                "usage": result.usage.model_dump()
            })

    # 3. Stream response
    async def generate():
        question_recorded = False
        usage_info = None

        async for chunk in chat_handler.stream_response(
            message.message,
            message.conversation_id,
            user_id
        ):
            # Record question after first content chunk (free-tier users only)
            if subscription_status != "active" and not question_recorded and usage_gate and email:
                if chunk.get("type") == "content":
                    try:
                        usage_info = await usage_gate.record_question(email)
                    except Exception as e:
                        print(f"⚠️ Failed to record question: {e}")
                    question_recorded = True

            # Inject usage into metadata event for free-tier users only
            if subscription_status != "active" and chunk.get("type") == "metadata" and usage_info:
                chunk["usage"] = usage_info.model_dump()

            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/documents")
async def list_documents():
    """List all documents with intelligent caching - fast response for frontend"""
    try:
        current_time = time.time()
        cache_invalidated = _cache_timestamp == 0
        cache_expired = (current_time - _cache_timestamp) > CACHE_TTL
        
        # If cache was explicitly invalidated (timestamp=0), force refresh
        # This ensures edits are visible immediately after save
        if cache_invalidated or _documents_cache is None:
            print(f"🔄 Cache invalidated or empty - forcing refresh")
            return await get_cached_documents(force_refresh=True)
        
        # Serve from cache, trigger background refresh if stale
        if cache_expired:
            print(f"⚡ Serving cached documents, triggering background refresh")
            asyncio.create_task(get_cached_documents(force_refresh=True))
        else:
            print(f"⚡ Serving cached documents ({len(_documents_cache.get('documents', []))} docs)")
        
        return _documents_cache
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

@app.get("/health")
def health_check():
    health_data = {
        "status": "healthy",
        "vector_store": True,
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "restart_trigger": "2025-08-13-restart"  # Force restart
    }

    # Story-006: Add code upload system health
    if CODE_UPLOAD_AVAILABLE:
        try:
            code_health = get_code_upload_health()
            health_data.update(code_health)
        except Exception as e:
            health_data["code_upload_error"] = str(e)

    return health_data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)