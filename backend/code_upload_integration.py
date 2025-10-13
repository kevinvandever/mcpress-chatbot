"""
Code Upload System Integration
Story: STORY-006
Created: 2025-10-13

Integration module for code upload system
Initializes all components and provides router for FastAPI
"""

import os
from fastapi import FastAPI

try:
    from code_upload_service import init_upload_service, get_upload_service, CodeUploadService
    from code_upload_scheduler import init_scheduler, start_scheduler, stop_scheduler
    from code_upload_routes import router as code_upload_router
except ImportError:
    from backend.code_upload_service import init_upload_service, get_upload_service, CodeUploadService
    from backend.code_upload_scheduler import init_scheduler, start_scheduler, stop_scheduler
    from backend.code_upload_routes import router as code_upload_router


# Module exports
router = code_upload_router


async def init_code_upload_system(database_url: str, storage_dir: str = "/tmp/code-uploads") -> CodeUploadService:
    """
    Initialize code upload system

    Args:
        database_url: PostgreSQL connection URL
        storage_dir: Directory for file storage (default /tmp/code-uploads)

    Returns:
        CodeUploadService instance

    Example:
        # In main.py startup event:
        upload_service = await init_code_upload_system(
            database_url=os.getenv("DATABASE_URL"),
            storage_dir="/tmp/code-uploads"
        )
    """
    print("📦 Initializing Code Upload System (Story-006)...")

    # Initialize upload service
    service = init_upload_service(database_url, storage_dir)
    await service.init_database()

    print(f"✅ Upload Service: Database connection established")
    print(f"✅ Upload Service: Storage directory: {storage_dir}")

    # Initialize and start cleanup scheduler
    scheduler = init_scheduler(service)
    scheduler.start()

    print("✅ Code Upload System: Ready")

    return service


async def shutdown_code_upload_system():
    """
    Shutdown code upload system gracefully

    Example:
        # In main.py shutdown event:
        await shutdown_code_upload_system()
    """
    print("📦 Shutting down Code Upload System...")

    try:
        # Stop scheduler
        await stop_scheduler()
        print("✅ Cleanup scheduler stopped")
    except Exception as e:
        print(f"⚠️  Error stopping scheduler: {e}")

    try:
        # Close service connections
        service = get_upload_service()
        await service.close()
        print("✅ Upload service closed")
    except Exception as e:
        print(f"⚠️  Error closing service: {e}")

    print("✅ Code Upload System: Shutdown complete")


def register_code_upload_routes(app: FastAPI):
    """
    Register code upload routes with FastAPI app

    Args:
        app: FastAPI application instance

    Example:
        # In main.py:
        register_code_upload_routes(app)
    """
    app.include_router(router)
    print("✅ Code Upload Routes: Registered at /api/code/*")


# Health check endpoint data
def get_code_upload_health() -> dict:
    """
    Get health status of code upload system

    Returns:
        Health check dictionary

    Example:
        # In main.py /health endpoint:
        health_data = get_code_upload_health()
    """
    try:
        service = get_upload_service()
        return {
            "code_upload_system": "healthy",
            "storage_initialized": True,
            "database_connected": service.pool is not None
        }
    except Exception as e:
        return {
            "code_upload_system": "unhealthy",
            "error": str(e),
            "storage_initialized": False,
            "database_connected": False
        }


# Export convenience functions
__all__ = [
    'router',
    'init_code_upload_system',
    'shutdown_code_upload_system',
    'register_code_upload_routes',
    'get_code_upload_health',
    'get_upload_service'
]
