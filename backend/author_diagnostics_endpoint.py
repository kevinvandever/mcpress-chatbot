"""
Author Diagnostics API Endpoint
Feature: author-display-investigation

Provides an API endpoint to run author data diagnostics via HTTP request.
"""

from fastapi import APIRouter, HTTPException
import json
import traceback

try:
    from author_data_validator import AuthorDataValidator
except ImportError:
    from backend.author_data_validator import AuthorDataValidator

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
    validator = None
    
    try:
        validator = AuthorDataValidator()
        await validator.init_database()
        report = await validator.generate_data_quality_report()
        
        # Convert datetime objects to strings for JSON serialization
        result = json.loads(json.dumps(report, default=str))
        
        return result
        
    except Exception as e:
        error_detail = f"Error running diagnostics: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Diagnostics error: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)
    
    finally:
        if validator:
            try:
                await validator.close()
            except:
                pass
