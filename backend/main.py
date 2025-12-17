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

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# Add upload endpoints for Railway batch uploads
import subprocess
import sys
from datetime import datetime
from fastapi import BackgroundTasks
from fastapi.responses import HTMLResponse
import re

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

# Debug endpoint for books schema
try:
    try:
        from debug_books_schema import router as debug_router
    except ImportError:
        from backend.debug_books_schema import router as debug_router
    
    app.include_router(debug_router)
    print("✅ Debug endpoints enabled at /debug/*")
except Exception as e:
    print(f"⚠️ Debug endpoints not available: {e}")

# Enrichment Debug endpoints
try:
    try:
        from debug_enrichment_endpoint import router as enrichment_debug_router
    except ImportError:
        from backend.debug_enrichment_endpoint import router as enrichment_debug_router
    
    app.include_router(enrichment_debug_router)
    print("✅ Enrichment debug endpoints enabled at /debug/enrichment/*")
except Exception as e:
    print(f"⚠️ Enrichment debug endpoints not available: {e}")

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

# REMOVING ALL CUSTOM ENDPOINTS TO DEBUG
# The app stops responding when we add ANY new code
print("⚠️ All custom endpoints disabled for debugging")

# Story 004 migration endpoint
try:
    # Try Railway-style import first
    try:
        from migration_story_004_endpoint import router as story4_migration_router, set_migration_store
        migration_available = True
    except ImportError:
        # Fallback to local development import
        from backend.migration_story_004_endpoint import router as story4_migration_router, set_migration_store
        migration_available = True
    print("✅ Story 004 migration endpoint enabled")
except Exception as e:
    print(f"⚠️ Story 004 migration endpoint not available: {e}")
    story4_migration_router = None
    set_migration_store = None
    migration_available = False

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

# Story 011 conversation history migration endpoint
try:
    # Try Railway-style import first
    try:
        from conversation_migration_endpoint import router as story11_migration_router, set_vector_store as set_story11_store
        story11_available = True
    except ImportError:
        # Fallback to local development import
        from backend.conversation_migration_endpoint import router as story11_migration_router, set_vector_store as set_story11_store
        story11_available = True
    print("✅ Story 011 conversation migration endpoint enabled")
except Exception as e:
    print(f"⚠️ Story 011 migration endpoint not available: {e}")
    story11_migration_router = None
    set_story11_store = None
    story11_available = False

# Set vector store for Story 011 migration if available
if story11_available:
    try:
        if set_story11_store:
            set_story11_store(vector_store)
        app.include_router(story11_migration_router)
        print("✅ Story 011 migration endpoint enabled at /run-story11-conversation-migration")
    except Exception as e:
        print(f"⚠️ Could not enable Story 011 migration endpoint: {e}")

# Migration 003: Multi-Author Metadata Enhancement
try:
    try:
        from migration_003_endpoint import migration_003_router
        migration_003_available = True
    except ImportError:
        from backend.migration_003_endpoint import migration_003_router
        migration_003_available = True
    print("✅ Migration 003 endpoint loaded")
except Exception as e:
    print(f"⚠️ Migration 003 endpoint not available: {e}")
    migration_003_router = None
    migration_003_available = False

if migration_003_available:
    try:
        app.include_router(migration_003_router)
        print("✅ Migration 003 endpoint enabled at /migration-003/*")
    except Exception as e:
        print(f"⚠️ Could not enable Migration 003 endpoint: {e}")

# Test 003: Property-based tests for Migration 003
try:
    try:
        from test_003_endpoint import test_003_router
        test_003_available = True
    except ImportError:
        from backend.test_003_endpoint import test_003_router
        test_003_available = True
    print("✅ Test 003 endpoint loaded")
except Exception as e:
    print(f"⚠️ Test 003 endpoint not available: {e}")
    test_003_router = None
    test_003_available = False

if test_003_available:
    try:
        app.include_router(test_003_router)
        print("✅ Test 003 endpoint enabled at /test-003/*")
    except Exception as e:
        print(f"⚠️ Could not enable Test 003 endpoint: {e}")

# AuthorService Test Endpoint
try:
    try:
        from author_service_test_endpoint import author_service_test_router
        author_service_test_available = True
    except ImportError:
        from backend.author_service_test_endpoint import author_service_test_router
        author_service_test_available = True
    print("✅ AuthorService test endpoint loaded")
except Exception as e:
    print(f"⚠️ AuthorService test endpoint not available: {e}")
    author_service_test_router = None
    author_service_test_available = False

if author_service_test_available:
    try:
        app.include_router(author_service_test_router)
        print("✅ AuthorService test endpoint enabled at /test-author-service/*")
    except Exception as e:
        print(f"⚠️ Could not enable AuthorService test endpoint: {e}")

# DocumentAuthorService Test Endpoint
try:
    try:
        from document_author_service_test_endpoint import document_author_service_test_router
        document_author_service_test_available = True
    except ImportError:
        from backend.document_author_service_test_endpoint import document_author_service_test_router
        document_author_service_test_available = True
    print("✅ DocumentAuthorService test endpoint loaded")
except Exception as e:
    print(f"⚠️ DocumentAuthorService test endpoint not available: {e}")
    document_author_service_test_router = None
    document_author_service_test_available = False

if document_author_service_test_available:
    try:
        app.include_router(document_author_service_test_router)
        print("✅ DocumentAuthorService test endpoint enabled at /test-document-author-service/*")
    except Exception as e:
        print(f"⚠️ Could not enable DocumentAuthorService test endpoint: {e}")

# Data Migration 003 Endpoint
try:
    try:
        from data_migration_003_endpoint import data_migration_003_router
        data_migration_003_available = True
    except ImportError:
        from backend.data_migration_003_endpoint import data_migration_003_router
        data_migration_003_available = True
    print("✅ Data Migration 003 endpoint loaded")
except Exception as e:
    print(f"⚠️ Data Migration 003 endpoint not available: {e}")
    data_migration_003_router = None
    data_migration_003_available = False

if data_migration_003_available:
    try:
        app.include_router(data_migration_003_router)
        print("✅ Data Migration 003 endpoint enabled at /data-migration-003/*")
    except Exception as e:
        print(f"⚠️ Could not enable Data Migration 003 endpoint: {e}")

# Database Diagnostic Endpoint (temporary) - moved to later in file

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

# Temporary migration endpoints removed after successful migration
db_info_available = False

if db_info_available:
    try:
        app.include_router(db_info_router)
        print("✅ Database connection info endpoint enabled at /db-info/*")
    except Exception as e:
        print(f"⚠️ Could not enable database connection info endpoint: {e}")

# Task 6 Test Endpoint
test_task_6_available = False
try:
    try:
        from test_document_author_endpoint import test_task_6_router
        test_task_6_available = True
    except ImportError:
        from backend.test_document_author_endpoint import test_task_6_router
        test_task_6_available = True
    print("✅ Task 6 test endpoint loaded")
except Exception as e:
    print(f"⚠️ Task 6 test endpoint not available: {e}")
    test_task_6_router = None
    test_task_6_available = False

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
                
                # Include test endpoint if available
                if test_task_6_available:
                    app.include_router(test_task_6_router)
                    print("✅ Task 6 test endpoints enabled at /test-task-6/*")
                
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
            else:
                print("⚠️ DATABASE_URL not set - author routes disabled")
        except Exception as e:
            print(f"⚠️ Could not enable author routes: {e}")
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
async def chat(
    message: ChatMessage,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    async def generate():
        # Use user_id from request body (sent by frontend via guestAuth)
        # Falls back to JWT auth if needed, then to "guest" as last resort
        user_id = message.user_id if message.user_id else "guest"

        # Override with JWT auth if credentials provided (admin users)
        if credentials:
            try:
                from auth_routes import get_current_user
                # Manually call get_current_user with credentials
                user = await get_current_user(credentials)
                user_id = str(user.get("id", user_id))  # Use JWT user_id if available
                print(f"✅ Authenticated user (JWT): {user_id}")
            except Exception as e:
                print(f"⚠️ Could not authenticate via JWT, using request user_id: {user_id}")
        else:
            print(f"✅ Using user_id from request: {user_id}")

        async for chunk in chat_handler.stream_response(
            message.message,
            message.conversation_id,
            user_id
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

# Simple diagnostic endpoints
@app.get("/diag/db-test")
async def diagnostic_db_test():
    """Ultra-simple database test"""
    import asyncpg
    import asyncio

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return {"error": "No DATABASE_URL"}

    try:
        # Test with very short timeout
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url, command_timeout=2),
            timeout=3.0
        )
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        return {"success": True, "result": result}
    except asyncio.TimeoutError:
        return {"error": "timeout", "message": "Connection timed out after 3 seconds"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/test-books-table")
async def test_books_table():
    """Simple test to check if books table exists and has data"""
    try:
        if not vector_store or not vector_store.pool:
            return {"error": "Database not initialized"}

        async with vector_store.pool.acquire() as conn:
            # Check if books table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'books'
                )
            """)

            if exists:
                count = await conn.fetchval("SELECT COUNT(*) FROM books")
                return {
                    "books_table_exists": True,
                    "book_count": count,
                    "message": f"Books table has {count} records"
                }
            else:
                return {
                    "books_table_exists": False,
                    "message": "Books table does not exist yet - migration needed"
                }
    except Exception as e:
        return {"error": str(e)}

# Note: Admin endpoints removed - they were causing network errors
# The admin functionality needs to be in a separate module that handles
# database connections properly without breaking the main app

@app.get("/run-story4-migration")
async def run_story4_migration():
    """Redirect to the safe migration endpoint"""
    return {
        "message": "Please use the safe migration endpoint instead",
        "url": "/run-story4-migration-safe",
        "reason": "The old endpoint causes connection timeouts"
    }

@app.get("/run-story12-migration")
async def run_story12_migration():
    """Run Story-012 export table migration"""
    try:
        if not hasattr(vector_store, 'pool') or not vector_store.pool:
            return {"error": "Database not available"}

        async with vector_store.pool.acquire() as conn:
            results = []

            # Create conversation_exports table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_exports (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    options JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            results.append("✅ Created conversation_exports table")

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_exports_user
                ON conversation_exports(user_id, created_at DESC)
            """)
            results.append("✅ Created idx_exports_user index")

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_exports_conversation
                ON conversation_exports(conversation_id)
            """)
            results.append("✅ Created idx_exports_conversation index")

            # Get count
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM conversation_exports
            """)

            return {
                "success": True,
                "results": results,
                "export_count": count,
                "message": "Story-012 migration completed successfully"
            }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# The old implementation is commented out to prevent timeouts
# It was creating new connections instead of using the pool
async def OLD_run_story4_migration_DO_NOT_USE():
    """OLD IMPLEMENTATION - DO NOT USE - causes timeouts"""
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

# Debug endpoints for enrichment testing
@app.get("/debug-enrichment/env")
async def debug_enrichment_env():
    """Check environment variables for enrichment."""
    database_url = os.getenv('DATABASE_URL')
    return {
        "database_url_set": bool(database_url),
        "database_url_length": len(database_url) if database_url else 0,
        "database_url_prefix": database_url[:20] + "..." if database_url else None
    }

@app.get("/debug-enrichment/connection")
async def debug_enrichment_connection():
    """Test database connection for enrichment."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    try:
        import asyncpg
        conn = await asyncpg.connect(database_url)
        
        # Test basic query
        version = await conn.fetchval("SELECT version()")
        
        # Check required tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('books', 'authors', 'document_authors')
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        
        # Check sample data
        book_count = await conn.fetchval("SELECT COUNT(*) FROM books")
        author_count = await conn.fetchval("SELECT COUNT(*) FROM authors")
        doc_author_count = await conn.fetchval("SELECT COUNT(*) FROM document_authors")
        
        await conn.close()
        
        return {
            "connection_success": True,
            "database_version": version[:100],
            "tables_found": table_names,
            "book_count": book_count,
            "author_count": author_count,
            "document_author_count": doc_author_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/debug-enrichment/test/{filename}")
async def debug_enrichment_test(filename: str):
    """Test the enrichment method with a specific filename."""
    try:
        result = await chat_handler._enrich_source_metadata(filename)
        
        return {
            "filename": filename,
            "enrichment_success": bool(result),
            "enrichment_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")

@app.get("/debug-enrichment/sample-books")
async def debug_enrichment_sample_books():
    """Get a sample of books from the database to test with."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    
    try:
        import asyncpg
        conn = await asyncpg.connect(database_url)
        
        # Get sample books
        books = await conn.fetch("""
            SELECT filename, title, author as legacy_author, document_type
            FROM books 
            WHERE filename IS NOT NULL 
            ORDER BY id 
            LIMIT 10
        """)
        
        await conn.close()
        
        return {
            "sample_books": [dict(book) for book in books]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)