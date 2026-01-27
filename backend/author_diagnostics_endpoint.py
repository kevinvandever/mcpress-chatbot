"""
Author Diagnostics API Endpoint
Feature: author-display-investigation

Provides an API endpoint to run author data diagnostics via HTTP request.
"""

from fastapi import APIRouter, HTTPException
from backend.author_data_validator import AuthorDataValidator
import json

router = APIRouter()


@router.get("/api/diagnostics/authors")
async def run_author_diagnostics():
    """
    Run comprehensive author data quality diagnostics.
    
    Returns a detailed report of all author data issues including:
    - Books without authors
    - Placeholder author names
    - Orphaned authors
    - Invalid references
    - Author ordering issues
    - Duplicate associations
    """
    validator = AuthorDataValidator()
    
    try:
        await validator.init_database()
        report = await validator.generate_data_quality_report()
        await validator.close()
        
        # Convert datetime objects to strings for JSON serialization
        return json.loads(json.dumps(report, default=str))
        
    except Exception as e:
        await validator.close()
        raise HTTPException(status_code=500, detail=f"Error running diagnostics: {str(e)}")
