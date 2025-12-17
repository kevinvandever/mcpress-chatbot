#!/usr/bin/env python3
"""
Test script to debug enrichment functionality on Railway.
This script tests:
1. DATABASE_URL environment variable access
2. Direct database connection
3. _enrich_source_metadata method functionality
"""

import os
import sys
import asyncio
import asyncpg
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_database_url():
    """Test if DATABASE_URL environment variable is accessible."""
    logger.info("=== Testing DATABASE_URL Environment Variable ===")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable is not set")
        return False
    
    logger.info(f"✅ DATABASE_URL is set (length: {len(database_url)} chars)")
    # Don't log the full URL for security
    if database_url.startswith('postgresql://'):
        logger.info("✅ DATABASE_URL has correct postgresql:// prefix")
    else:
        logger.warning("⚠️  DATABASE_URL doesn't start with postgresql://")
    
    return True

async def test_database_connection():
    """Test direct database connection using asyncpg."""
    logger.info("=== Testing Database Connection ===")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("❌ Cannot test connection - DATABASE_URL not set")
        return False
    
    try:
        logger.info("Attempting to connect to database...")
        conn = await asyncpg.connect(database_url)
        logger.info("✅ Successfully connected to database")
        
        # Test a simple query
        result = await conn.fetchval("SELECT version()")
        logger.info(f"✅ Database version: {result[:50]}...")
        
        # Test if required tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('books', 'authors', 'document_authors')
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        logger.info(f"✅ Found tables: {table_names}")
        
        if len(table_names) == 3:
            logger.info("✅ All required tables exist")
        else:
            logger.warning(f"⚠️  Missing tables: {set(['books', 'authors', 'document_authors']) - set(table_names)}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

async def test_enrichment_method():
    """Test the _enrich_source_metadata method directly."""
    logger.info("=== Testing Enrichment Method ===")
    
    # Import the chat handler
    try:
        sys.path.append('/app/backend')  # Railway path
        from chat_handler import ChatHandler
        logger.info("✅ Successfully imported ChatHandler")
    except ImportError as e:
        logger.error(f"❌ Failed to import ChatHandler: {e}")
        try:
            # Try alternative import path
            from backend.chat_handler import ChatHandler
            logger.info("✅ Successfully imported ChatHandler (alternative path)")
        except ImportError as e2:
            logger.error(f"❌ Failed to import ChatHandler (alternative): {e2}")
            return False
    
    # Create ChatHandler instance
    try:
        chat_handler = ChatHandler()
        logger.info("✅ Successfully created ChatHandler instance")
    except Exception as e:
        logger.error(f"❌ Failed to create ChatHandler: {e}")
        return False
    
    # Test with a known filename
    test_filenames = [
        "db2-for-the-cobol-programmer-part-1.pdf",
        "rpg-iv-jump-start-fourth-edition.pdf",
        "sql-built-in-functions-and-stored-procedures.pdf"
    ]
    
    for filename in test_filenames:
        logger.info(f"Testing enrichment for: {filename}")
        try:
            result = await chat_handler._enrich_source_metadata(filename)
            logger.info(f"✅ Enrichment result for {filename}: {result}")
            
            if result:
                logger.info("✅ Enrichment returned data")
                if 'author' in result:
                    logger.info(f"  - Author: {result['author']}")
                if 'authors' in result:
                    logger.info(f"  - Authors count: {len(result['authors'])}")
                if 'document_type' in result:
                    logger.info(f"  - Document type: {result['document_type']}")
            else:
                logger.warning("⚠️  Enrichment returned empty result")
                
        except Exception as e:
            logger.error(f"❌ Enrichment failed for {filename}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    return True

async def main():
    """Run all tests."""
    logger.info("Starting Railway enrichment debug tests...")
    
    # Test 1: Environment variable
    env_ok = await test_database_url()
    
    # Test 2: Database connection
    db_ok = await test_database_connection()
    
    # Test 3: Enrichment method
    enrichment_ok = await test_enrichment_method()
    
    # Summary
    logger.info("=== Test Summary ===")
    logger.info(f"Environment variable: {'✅' if env_ok else '❌'}")
    logger.info(f"Database connection: {'✅' if db_ok else '❌'}")
    logger.info(f"Enrichment method: {'✅' if enrichment_ok else '❌'}")
    
    if env_ok and db_ok and enrichment_ok:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)