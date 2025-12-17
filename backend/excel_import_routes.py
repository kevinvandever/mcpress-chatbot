"""
Excel Import API Routes for Multi-Author Metadata Enhancement
Feature: multi-author-metadata-enhancement

Provides REST API endpoints for Excel file validation and import:
- POST /api/excel/validate - Validate Excel file and generate preview
- POST /api/excel/import/books - Import book metadata from Excel
- POST /api/excel/import/articles - Import article metadata from Excel
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse

try:
    from excel_import_service import ExcelImportService, ValidationResult, ImportResult
    from author_service import AuthorService
except ImportError:
    from backend.excel_import_service import ExcelImportService, ValidationResult, ImportResult
    from backend.author_service import AuthorService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/excel", tags=["excel-import"])

# Global service instances (will be set by main.py)
excel_service: Optional[ExcelImportService] = None


def set_excel_service(service: ExcelImportService):
    """Set the Excel import service instance"""
    global excel_service
    excel_service = service
    logger.info("Excel import service configured")


@router.post("/validate")
async def validate_excel_file(
    file: UploadFile = File(...),
    file_type: str = Form(...)
):
    """
    Validate Excel file format and generate preview
    
    Args:
        file: Excel file (.xlsm format)
        file_type: Type of file ("book" or "article")
        
    Returns:
        ValidationResult with validation status, errors, and preview
        
    Validates: Requirements 11.1, 11.4, 11.5
    """
    if not excel_service:
        raise HTTPException(status_code=500, detail="Excel import service not available")
    
    # Validate file type parameter
    if file_type not in ["book", "article"]:
        raise HTTPException(
            status_code=400, 
            detail="file_type must be 'book' or 'article'"
        )
    
    # Check file extension - allow Excel and CSV for book files
    if file_type == "book":
        allowed_extensions = ['.xlsm', '.xlsx', '.csv']
        format_message = "File must be .xlsm, .xlsx, or .csv format"
    else:
        allowed_extensions = ['.xlsm']
        format_message = "File must be .xlsm format"
        
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=format_message
        )
    
    # Log the validation request  
    logger.info(f"Validating file: {file.filename}, type: {file_type}, extension: {Path(file.filename).suffix if file.filename else 'none'}")
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsm') as temp_file:
        try:
            # Read and write file content
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Validate the file
            result = await excel_service.validate_excel_file(temp_file.name, file_type)
            
            # Log validation results
            error_count = len([e for e in result.errors if e.severity == "error"])
            warning_count = len([e for e in result.errors if e.severity == "warning"])
            logger.info(
                f"Validation complete - Valid: {result.valid}, "
                f"Errors: {error_count}, Warnings: {warning_count}, "
                f"Preview rows: {len(result.preview_rows)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating Excel file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error validating Excel file: {str(e)}"
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass


@router.post("/import/books")
async def import_book_metadata(
    file: UploadFile = File(...)
):
    """
    Import book metadata from book-metadata.xlsm or .xlsx file
    
    Args:
        file: Excel file containing book metadata (URL, Title, Author columns)
        
    Returns:
        ImportResult with processing statistics and any errors
        
    Validates: Requirements 9.1, 9.2, 9.3, 9.5, 9.6
    """
    if not excel_service:
        raise HTTPException(status_code=500, detail="Excel import service not available")
    
    # Check file extension - allow Excel and CSV for book files
    allowed_extensions = ['.xlsm', '.xlsx', '.csv']
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="File must be .xlsm, .xlsx, or .csv format"
        )
    
    # Log the import request
    logger.info(f"Starting book metadata import from: {file.filename}")
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsm') as temp_file:
        try:
            # Read and write file content
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Import book metadata
            result = await excel_service.import_book_metadata(temp_file.name)
            
            # Log import results
            logger.info(
                f"Book import complete - Success: {result.success}, "
                f"Processed: {result.books_processed}, "
                f"Matched: {result.books_matched}, "
                f"Updated: {result.books_updated}, "
                f"Authors created: {result.authors_created}, "
                f"Processing time: {result.processing_time:.2f}s"
            )
            
            if result.errors:
                error_count = len([e for e in result.errors if e.severity == "error"])
                warning_count = len([e for e in result.errors if e.severity == "warning"])
                logger.warning(f"Import had {error_count} errors and {warning_count} warnings")
            
            return result
            
        except Exception as e:
            logger.error(f"Error importing book metadata from {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error importing book metadata: {str(e)}"
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass


@router.post("/import/articles")
async def import_article_metadata(
    file: UploadFile = File(...)
):
    """
    Import article metadata from article-links.xlsm file (export_subset sheet)
    
    Args:
        file: Excel file containing article metadata
        
    Returns:
        ImportResult with processing statistics and any errors
        
    Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
    """
    if not excel_service:
        raise HTTPException(status_code=500, detail="Excel import service not available")
    
    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.xlsm'):
        raise HTTPException(
            status_code=400,
            detail="File must be .xlsm format"
        )
    
    # Log the import request
    logger.info(f"Starting article metadata import from: {file.filename}")
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsm') as temp_file:
        try:
            # Read and write file content
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Import article metadata
            result = await excel_service.import_article_metadata(temp_file.name)
            
            # Log import results
            logger.info(
                f"Article import complete - Success: {result.success}, "
                f"Processed: {result.articles_processed}, "
                f"Matched: {result.articles_matched}, "
                f"Updated: {result.documents_updated}, "
                f"Authors created: {result.authors_created}, "
                f"Processing time: {result.processing_time:.2f}s"
            )
            
            if result.errors:
                error_count = len([e for e in result.errors if e.severity == "error"])
                warning_count = len([e for e in result.errors if e.severity == "warning"])
                logger.warning(f"Import had {error_count} errors and {warning_count} warnings")
            
            return result
            
        except Exception as e:
            logger.error(f"Error importing article metadata from {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error importing article metadata: {str(e)}"
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass


# Health check endpoint for Excel import service
@router.get("/health")
async def excel_import_health():
    """
    Check Excel import service health and dependencies
    
    Returns:
        Service status and dependency information
    """
    try:
        status = {
            "service_available": excel_service is not None,
            "dependencies": {
                "pandas": True,
                "openpyxl": True,
                "fuzzywuzzy": True
            }
        }
        
        # Test basic service functionality if available
        if excel_service:
            # Test author parsing
            test_authors = excel_service.parse_authors("John Doe, Jane Smith and Bob Wilson")
            status["test_author_parsing"] = len(test_authors) == 3
            
            # Test URL validation
            status["test_url_validation"] = excel_service._is_valid_url("https://example.com")
        
        return status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "service_available": False,
            "error": str(e)
        }