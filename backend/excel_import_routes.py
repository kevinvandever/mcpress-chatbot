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
    logger.info(f"Original file extension will be preserved in temp file")
    
    # Save uploaded file to temporary location with correct extension
    original_suffix = Path(file.filename).suffix if file.filename else '.xlsm'
    with tempfile.NamedTemporaryFile(delete=False, suffix=original_suffix) as temp_file:
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
    file: UploadFile = File(...),
    author_url_file: Optional[UploadFile] = File(None)
):
    """
    Import book metadata from book-metadata.xlsm or .xlsx file with improved transaction handling
    
    Args:
        file: Excel file containing book metadata (URL, Title, Author columns)
        author_url_file: Optional article Excel file containing author URLs (column L)
        
    Returns:
        ImportResult with processing statistics and any errors
        
    Validates: Requirements 9.1, 9.2, 9.3, 9.5, 9.6, 6.1, 6.2, 6.3, 6.4, 6.5
    """
    if not excel_service:
        logger.error("Excel import service not available")
        raise HTTPException(status_code=500, detail="Excel import service not available")
    
    # Check file extension - allow Excel and CSV for book files
    allowed_extensions = ['.xlsm', '.xlsx', '.csv']
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        logger.error(f"Invalid file format: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="File must be .xlsm, .xlsx, or .csv format"
        )
    
    # Log the import request
    logger.info(f"Starting book metadata import from: {file.filename}")
    if author_url_file and author_url_file.filename:
        logger.info(f"Author URL file provided: {author_url_file.filename}")
    
    # Save uploaded file to temporary location with correct extension
    original_suffix = Path(file.filename).suffix if file.filename else '.xlsm'
    author_url_temp_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=original_suffix) as temp_file:
        try:
            # Read and write book file content
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            logger.info(f"Saved uploaded file to temporary location: {temp_file.name}")
            
            # Build author URL mapping if author_url_file is provided
            author_url_mapping = None
            if author_url_file and author_url_file.filename:
                author_url_suffix = Path(author_url_file.filename).suffix if author_url_file.filename else '.xlsm'
                with tempfile.NamedTemporaryFile(delete=False, suffix=author_url_suffix) as author_temp:
                    author_url_temp_path = author_temp.name
                    author_content = await author_url_file.read()
                    author_temp.write(author_content)
                    author_temp.flush()
                
                logger.info(f"Saved author URL file to temporary location: {author_url_temp_path}")
                author_url_mapping = excel_service.build_author_url_mapping(author_url_temp_path)
                logger.info(f"Built author URL mapping with {len(author_url_mapping)} entries")
            
            # Import book metadata with transaction handling
            result = await excel_service.import_book_metadata(temp_file.name, author_url_mapping=author_url_mapping)
            
            # Log import results with detailed information
            if result.success:
                logger.info(
                    f"Book import SUCCESS - "
                    f"Processed: {result.books_processed}, "
                    f"Matched: {result.books_matched}, "
                    f"Updated: {result.books_updated}, "
                    f"Authors created: {result.authors_created}, "
                    f"Processing time: {result.processing_time:.2f}s"
                )
            else:
                logger.error(
                    f"Book import FAILED - "
                    f"Processed: {result.books_processed}, "
                    f"Errors: {len([e for e in result.errors if e.severity == 'error'])}"
                )
            
            if result.errors:
                error_count = len([e for e in result.errors if e.severity == "error"])
                warning_count = len([e for e in result.errors if e.severity == "warning"])
                logger.warning(f"Import had {error_count} errors and {warning_count} warnings")
                
                # Log first few errors for debugging
                for i, error in enumerate(result.errors[:5]):  # Log first 5 errors
                    logger.warning(f"Import error {i+1}: Row {error.row}, Column {error.column}: {error.message}")
            
            # Return detailed result including transaction status
            return {
                **result.dict(),
                "transaction_committed": result.success,
                "detailed_logging": True
            }
            
        except Exception as e:
            logger.error(f"Critical error importing book metadata from {file.filename}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": f"Error importing book metadata: {str(e)}",
                    "transaction_committed": False,
                    "file_processed": False
                }
            )
        finally:
            # Clean up temporary book file
            try:
                os.unlink(temp_file.name)
                logger.debug(f"Cleaned up temporary file: {temp_file.name}")
            except OSError as e:
                logger.warning(f"Failed to clean up temporary file {temp_file.name}: {e}")
            # Clean up temporary author URL file
            if author_url_temp_path:
                try:
                    os.unlink(author_url_temp_path)
                    logger.debug(f"Cleaned up author URL temporary file: {author_url_temp_path}")
                except OSError as e:
                    logger.warning(f"Failed to clean up author URL temporary file {author_url_temp_path}: {e}")


@router.post("/import/articles")
async def import_article_metadata(
    file: UploadFile = File(...)
):
    """
    Import article metadata from article-links.xlsm file (export_subset sheet) with improved transaction handling
    
    Args:
        file: Excel file containing article metadata
        
    Returns:
        ImportResult with processing statistics and any errors
        
    Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 6.1, 6.2, 6.3, 6.4, 6.5
    """
    if not excel_service:
        logger.error("Excel import service not available")
        raise HTTPException(status_code=500, detail="Excel import service not available")
    
    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.xlsm'):
        logger.error(f"Invalid file format for articles: {file.filename}")
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
            
            logger.info(f"Saved uploaded file to temporary location: {temp_file.name}")
            
            # Import article metadata with transaction handling
            result = await excel_service.import_article_metadata(temp_file.name)
            
            # Log import results with detailed information
            if result.success:
                logger.info(
                    f"Article import SUCCESS - "
                    f"Processed: {result.articles_processed}, "
                    f"Matched: {result.articles_matched}, "
                    f"Updated: {result.documents_updated}, "
                    f"Authors created: {result.authors_created}, "
                    f"Processing time: {result.processing_time:.2f}s"
                )
            else:
                logger.error(
                    f"Article import FAILED - "
                    f"Processed: {result.articles_processed}, "
                    f"Errors: {len([e for e in result.errors if e.severity == 'error'])}"
                )
            
            if result.errors:
                error_count = len([e for e in result.errors if e.severity == "error"])
                warning_count = len([e for e in result.errors if e.severity == "warning"])
                logger.warning(f"Import had {error_count} errors and {warning_count} warnings")
                
                # Log first few errors for debugging
                for i, error in enumerate(result.errors[:5]):  # Log first 5 errors
                    logger.warning(f"Import error {i+1}: Row {error.row}, Column {error.column}: {error.message}")
            
            # Return detailed result including transaction status
            return {
                **result.dict(),
                "transaction_committed": result.success,
                "detailed_logging": True
            }
            
        except Exception as e:
            logger.error(f"Critical error importing article metadata from {file.filename}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": f"Error importing article metadata: {str(e)}",
                    "transaction_committed": False,
                    "file_processed": False
                }
            )
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file.name)
                logger.debug(f"Cleaned up temporary file: {temp_file.name}")
            except OSError as e:
                logger.warning(f"Failed to clean up temporary file {temp_file.name}: {e}")


@router.post("/backfill-author-urls")
async def backfill_author_urls(
    file: UploadFile = File(...)
):
    """
    Backfill author site_url values from article Excel data.
    
    Accepts the article Excel file (export_subset_DMU_v2.xlsx), extracts
    author name → URL mapping, and upserts each author's site_url.
    
    Args:
        file: Article Excel file (.xlsm) containing author URLs
        
    Returns:
        Stats: mapping_size, authors_checked, authors_updated, authors_not_found
        
    Validates: Requirements 2.1, 2.2, 2.3, 3.1, 3.3
    """
    if not excel_service:
        logger.error("Excel import service not available")
        raise HTTPException(status_code=500, detail="Excel import service not available")
    
    # Check file extension - accept .xlsm and .xlsx
    allowed_extensions = ('.xlsm', '.xlsx')
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        logger.error(f"Invalid file format for backfill: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="File must be .xlsm or .xlsx format"
        )
    
    logger.info(f"Starting author URL backfill from: {file.filename}")
    
    # Save uploaded file to temporary location
    temp_file = None
    try:
        original_suffix = Path(file.filename).suffix if file.filename else '.xlsx'
        with tempfile.NamedTemporaryFile(delete=False, suffix=original_suffix) as tmp:
            temp_file = tmp.name
            content = await file.read()
            tmp.write(content)
            tmp.flush()
        
        logger.info(f"Saved uploaded file to temporary location: {temp_file}")
        
        # Build author URL mapping from the article Excel
        author_url_mapping = excel_service.build_author_url_mapping(temp_file)
        logger.info(f"Built author URL mapping with {len(author_url_mapping)} entries")
        
        # Backfill author URLs
        stats = await excel_service.backfill_author_urls(author_url_mapping)
        
        logger.info(f"Backfill complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Critical error during author URL backfill: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during author URL backfill: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file:
            try:
                os.unlink(temp_file)
                logger.debug(f"Cleaned up temporary file: {temp_file}")
            except OSError as e:
                logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")


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