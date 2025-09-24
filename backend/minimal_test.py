"""
Absolutely minimal endpoint with NO database imports
Just to verify the app can respond
"""

from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/minimal/ping")
async def ping():
    """The simplest possible endpoint"""
    return {"pong": True}

@router.get("/minimal/env")
async def check_env():
    """Check environment variables without any imports"""
    return {
        "DATABASE_URL_exists": "DATABASE_URL" in os.environ,
        "OPENAI_KEY_exists": "OPENAI_API_KEY" in os.environ,
        "USE_POSTGRESQL": os.getenv("USE_POSTGRESQL", "not set"),
        "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT", "not set")
    }