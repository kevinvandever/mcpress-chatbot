"""
Excel Import Service for Multi-Author Metadata Enhancement
Feature: multi-author-metadata-enhancement

Handles Excel file processing for book and article metadata including:
- File format validation
- Data preview with validation status
- Book metadata import from book-metadata.xlsm
- Article metadata import from article-links.xlsm
- Author parsing and fuzzy title matching
"""

import os
import re
import time
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
import pandas as pd
from fuzzywuzzy import fuzz, process
import asyncpg
from pydantic import BaseModel

from backend.author_service import AuthorService


class ExcelValidationError(BaseModel):
    """Represents a validation error in Excel data"""
    row: int
    column: str
    message: str
    severity: Literal['error', 'warning']


class ValidationResult(BaseModel):
    """Result of Excel file validation"""
    valid: bool
    errors: List[ExcelValidationError]
    preview_rows: List[Dict[str, Any]]


class ImportResult(BaseModel):
    """Result of Excel import operation"""
    success: bool
    books_processed: Optional[int] = None
    books_matched: Optional[int] = None
    books_updated: Optional[int] = None
    articles_processed: Optional[int] = None
    articles_matched: Optional[int] = None
    documents_updated: Optional[int] = None
    authors_created: int = 0
    authors_updated: int = 0
    errors: List[ExcelValidationError] = []
    processing_time: float


class BookMetadataRow(BaseModel):
    """Represents a row in book metadata Excel"""
    url: str
    title: str
    author: str


class ArticleMetadataRow(BaseModel):
    """Represents a row in article metadata Excel"""
    id: str
    feature_article: str
    author: str
    article_url: str
    author_url: str


class ExcelImportService:
    """Service for Excel file import and processing"""

    def __init__(self, author_service: AuthorService, database_url: Optional[str] = None):
        """
        Initialize Excel import service
        
        Args:
            author_service: AuthorService instance for author management
            database_url: PostgreSQL database URL (defaults to DATABASE_URL env var)
        """
        self.author_service = author_service
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.pool = None
        self.fuzzy_threshold = 80  # Minimum fuzzy match score (0-100)

    async def init_database(self):
        """Initialize database connection pool"""
        if self.pool:
            return
        
        self.pool = await asyncpg.create_pool(
            self.database_url,
            statement_cache_size=0,  # Fix for pgbouncer compatibility
            min_size=1,
            max_size=10,
            command_timeout=60
        )
    
    async def _ensure_pool(self):
        """Ensure connection pool is initialized (lazy initialization)"""
        if not self.pool:
            await self.init_database()

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def validate_excel_file(self, file_path: str, file_type: str) -> ValidationResult:
        """
        Validate Excel file format and required columns
        
        Args:
            file_path: Path to Excel file
            file_type: Type of file ("book" or "article")
            
        Returns:
            ValidationResult with validation status and errors
            
        Validates: Requirements 11.1, 11.2, 11.3
        """
        errors = []
        preview_rows = []
        
        try:
            # Check file exists and has correct extension
            if not Path(file_path).exists():
                errors.append(ExcelValidationError(
                    row=0,
                    column="file",
                    message="File does not exist",
                    severity="error"
                ))
                return ValidationResult(valid=False, errors=errors, preview_rows=[])
            
            # Allow Excel and CSV for book files, only .xlsm for articles
            if file_type == "book":
                allowed_extensions = ['.xlsm', '.xlsx', '.csv']
            else:
                allowed_extensions = ['.xlsm']
                
            if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
                if file_type == "book":
                    errors.append(ExcelValidationError(
                        row=0,
                        column="file",
                        message="File must be .xlsm, .xlsx, or .csv format",
                        severity="error"
                    ))
                else:
                    errors.append(ExcelValidationError(
                        row=0,
                        column="file",
                        message="File must be .xlsm format",
                        severity="error"
                    ))
                return ValidationResult(valid=False, errors=errors, preview_rows=[])
            
            # Try to read the file (Excel or CSV)
            if file_type == "book":
                # Determine file type and read accordingly
                file_lower = file_path.lower()
                print(f"DEBUG: Reading file {file_path}")
                print(f"DEBUG: File lower: {file_lower}")
                print(f"DEBUG: Ends with .csv: {file_lower.endswith('.csv')}")
                
                if file_lower.endswith('.csv'):
                    print(f"DEBUG: Reading as CSV")
                    df = pd.read_csv(file_path)
                else:
                    print(f"DEBUG: Reading as Excel with openpyxl")
                    df = pd.read_excel(file_path, engine='openpyxl')
                
                # Normalize column names - strip whitespace and handle case variations
                df.columns = df.columns.str.strip()
                
                # Map common variations to standard names
                column_mapping = {}
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if col_lower in ['url', 'urls', 'link', 'links']:
                        column_mapping[col] = 'URL'
                    elif col_lower in ['title', 'book title', 'name']:
                        column_mapping[col] = 'Title'  
                    elif col_lower in ['author', 'authors', 'author(s)', 'writer', 'writers']:
                        column_mapping[col] = 'Author'
                
                # Rename columns to standard names
                df = df.rename(columns=column_mapping)
                
                required_columns = ['URL', 'Title', 'Author']
            elif file_type == "article":
                # For articles, read the export_subset sheet
                try:
                    df = pd.read_excel(file_path, sheet_name='export_subset', engine='openpyxl')
                except ValueError as e:
                    if 'export_subset' in str(e):
                        errors.append(ExcelValidationError(
                            row=0,
                            column="sheet",
                            message="Sheet 'export_subset' not found",
                            severity="error"
                        ))
                        return ValidationResult(valid=False, errors=errors, preview_rows=[])
                    raise
                
                # Map column letters to names for articles
                # A=id, H=feature_article, J=author, K=article_url, L=author_url
                required_columns = ['A', 'H', 'J', 'K', 'L']
                # Rename columns to match expected names
                if len(df.columns) >= 12:  # Ensure we have at least L column
                    df = df.rename(columns={
                        df.columns[0]: 'id',           # Column A
                        df.columns[7]: 'feature_article',  # Column H
                        df.columns[9]: 'author',       # Column J
                        df.columns[10]: 'article_url', # Column K
                        df.columns[11]: 'author_url'   # Column L
                    })
                    required_columns = ['id', 'feature_article', 'author', 'article_url', 'author_url']
            else:
                errors.append(ExcelValidationError(
                    row=0,
                    column="type",
                    message="File type must be 'book' or 'article'",
                    severity="error"
                ))
                return ValidationResult(valid=False, errors=errors, preview_rows=[])
            
            # Check for required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                for col in missing_columns:
                    # Make URL column optional for now - we can add URLs later
                    severity = "warning" if col == "URL" else "error"
                    errors.append(ExcelValidationError(
                        row=0,
                        column=col,
                        message=f"Required column '{col}' is missing",
                        severity=severity
                    ))
            
            # Generate preview of first 10 rows with validation
            preview_rows = await self._generate_preview(df, file_type, errors)
            
        except Exception as e:
            errors.append(ExcelValidationError(
                row=0,
                column="file",
                message=f"Error reading file: {str(e)}",
                severity="error"
            ))
        
        return ValidationResult(
            valid=len([e for e in errors if e.severity == "error"]) == 0,
            errors=errors,
            preview_rows=preview_rows
        )

    async def preview_excel_data(self, file_path: str, file_type: str) -> ValidationResult:
        """
        Generate preview of first 10 rows with validation status
        
        Args:
            file_path: Path to Excel file
            file_type: Type of file ("book" or "article")
            
        Returns:
            ValidationResult with preview data
            
        Validates: Requirements 11.5
        """
        # This method is essentially the same as validate_excel_file
        # but focuses on preview generation
        return await self.validate_excel_file(file_path, file_type)

    async def _generate_preview(
        self, 
        df: pd.DataFrame, 
        file_type: str, 
        existing_errors: List[ExcelValidationError]
    ) -> List[Dict[str, Any]]:
        """Generate preview rows with validation status"""
        preview_rows = []
        
        # Take first 10 rows for preview
        preview_df = df.head(10)
        
        for idx, row in preview_df.iterrows():
            row_data = {}
            row_errors = []
            
            if file_type == "book":
                # Validate book metadata row with improved URL handling
                url_raw = row.get('URL', '')
                
                # Handle different data types that might come from Numbers/Excel export
                if pd.isna(url_raw) or url_raw is None:
                    url_str = ''
                elif isinstance(url_raw, (int, float)):
                    # Sometimes URLs get interpreted as numbers
                    url_str = str(url_raw) if url_raw != 0 else ''
                else:
                    url_str = str(url_raw).strip()
                
                # Debug: Log what we're actually reading
                print(f"DEBUG Row {idx+1}: URL raw = {repr(url_raw)} (type: {type(url_raw)}), URL str = {repr(url_str)}")
                
                row_data = {
                    'URL': url_str,
                    'Title': str(row.get('Title', '')).strip(),
                    'Author': str(row.get('Author', '')).strip()
                }
                
                # Validate URL (allow empty URLs for now)
                if row_data['URL'] and not self._is_valid_url(row_data['URL']):
                    row_errors.append(f"Invalid URL format")
                elif not row_data['URL']:
                    row_errors.append(f"URL is empty (will be skipped)")
                
                # Validate required fields
                if not row_data['Title'].strip():
                    row_errors.append(f"Title is required")
                if not row_data['Author'].strip():
                    row_errors.append(f"Author is required")
                    
            elif file_type == "article":
                # Validate article metadata row
                row_data = {
                    'id': str(row.get('id', '')),
                    'feature_article': str(row.get('feature_article', '')),
                    'author': str(row.get('author', '')),
                    'article_url': str(row.get('article_url', '')),
                    'author_url': str(row.get('author_url', ''))
                }
                
                # Validate required fields
                if not row_data['id'].strip():
                    row_errors.append(f"ID is required")
                if not row_data['author'].strip():
                    row_errors.append(f"Author is required")
                
                # Validate URLs
                if row_data['article_url'] and not self._is_valid_url(row_data['article_url']):
                    row_errors.append(f"Invalid article URL format")
                if row_data['author_url'] and not self._is_valid_url(row_data['author_url']):
                    row_errors.append(f"Invalid author URL format")
            
            preview_rows.append({
                'row': int(idx) + 1,  # 1-based row numbering
                'data': row_data,
                'status': 'error' if row_errors else 'valid',
                'errors': row_errors
            })
        
        return preview_rows

    def parse_authors(self, author_string: str) -> List[str]:
        """
        Parse multiple authors from comma or 'and' delimited string
        
        Args:
            author_string: String containing one or more author names
            
        Returns:
            List of individual author names (trimmed)
            
        Validates: Requirements 9.4
        """
        if not author_string or not author_string.strip():
            return []
        
        # Replace "and and" and similar patterns first
        author_string = re.sub(r'\s+and\s+and\s+', ' and ', author_string, flags=re.IGNORECASE)
        # Then replace " and " with comma for consistent splitting
        author_string = re.sub(r'\s+and\s+', ',', author_string, flags=re.IGNORECASE)
        
        # Replace semicolons with commas
        author_string = author_string.replace(';', ',')
        
        # Handle cases with multiple consecutive commas
        author_string = re.sub(r',\s*,+', ',', author_string)
        
        # Split by comma and clean up
        authors = [author.strip() for author in author_string.split(',')]
        
        # Remove empty strings
        authors = [author for author in authors if author]
        
        return authors

    async def fuzzy_match_title(self, title: str) -> Optional[int]:
        """
        Find best matching book by title using fuzzy matching
        
        Args:
            title: Book title to match
            
        Returns:
            Book ID of best match, or None if no good match found
            
        Validates: Requirements 9.2
        """
        await self._ensure_pool()
        
        if not title or not title.strip():
            return None
        
        title = title.strip()
        
        async with self.pool.acquire() as conn:
            # Get all book titles from database
            rows = await conn.fetch("SELECT id, title FROM books")
            
            if not rows:
                return None
            
            # Create list of titles for fuzzy matching
            titles = [(row['title'], row['id']) for row in rows]
            title_strings = [t[0] for t in titles]
            
            # Use fuzzywuzzy to find best match
            best_match = process.extractOne(
                title, 
                title_strings, 
                scorer=fuzz.ratio,
                score_cutoff=self.fuzzy_threshold
            )
            
            if best_match:
                matched_title, score = best_match
                # Find the book ID for the matched title
                for db_title, book_id in titles:
                    if db_title == matched_title:
                        return book_id
            
            return None

    async def _mock_fuzzy_match_with_data(self, title: str, mock_data: List[tuple]) -> Optional[int]:
        """
        Mock version of fuzzy_match_title that uses provided data instead of database
        Used for testing purposes.
        
        Args:
            title: Title to match
            mock_data: List of (id, title) tuples representing database data
            
        Returns:
            Book ID of best match, or None if no good match found
        """
        if not title or not title.strip():
            return None
        
        title = title.strip()
        
        if not mock_data:
            return None
        
        # Create list of titles for fuzzy matching
        titles = [(row[1], row[0]) for row in mock_data]
        title_strings = [t[0] for t in titles]
        
        # Use fuzzywuzzy to find best match (same logic as real method)
        best_match = process.extractOne(
            title, 
            title_strings, 
            scorer=fuzz.ratio,
            score_cutoff=self.fuzzy_threshold
        )
        
        if best_match:
            matched_title, score = best_match
            # Find the book ID for the matched title
            for db_title, book_id in titles:
                if db_title == matched_title:
                    return book_id
        
        return None

    def _is_valid_url(self, url: str) -> bool:
        """
        Check if URL has valid format
        
        Args:
            url: URL string to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        if not url or not url.strip():
            return False
        
        url = url.strip()
        
        # Basic URL validation - must start with http:// or https://
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))

    async def import_book_metadata(self, file_path: str) -> ImportResult:
        """
        Import book metadata from book-metadata.xlsm
        
        Args:
            file_path: Path to book metadata Excel file
            
        Returns:
            ImportResult with processing statistics
            
        Validates: Requirements 9.1, 9.2, 9.3, 9.5, 9.6
        """
        start_time = time.time()
        result = ImportResult(success=False, processing_time=0.0)
        
        try:
            # Validate file first
            validation = await self.validate_excel_file(file_path, "book")
            if not validation.valid:
                result.errors = validation.errors
                result.processing_time = time.time() - start_time
                return result
            
            # Read file (Excel or CSV)
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
            
            # Normalize column names - strip whitespace and handle case variations
            df.columns = df.columns.str.strip()
            
            # Map common variations to standard names
            column_mapping = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower in ['url', 'urls', 'link', 'links']:
                    column_mapping[col] = 'URL'
                elif col_lower in ['title', 'book title', 'name']:
                    column_mapping[col] = 'Title'  
                elif col_lower in ['author', 'authors', 'author(s)', 'writer', 'writers']:
                    column_mapping[col] = 'Author'
            
            # Rename columns to standard names
            df = df.rename(columns=column_mapping)
            
            books_processed = 0
            books_matched = 0
            books_updated = 0
            authors_created = 0
            authors_updated = 0
            errors = []
            
            await self._ensure_pool()
            
            for idx, row in df.iterrows():
                try:
                    books_processed += 1
                    
                    # Handle URL with improved parsing for Numbers exports
                    url_raw = row.get('URL', '')
                    if pd.isna(url_raw) or url_raw is None:
                        url = ''
                    elif isinstance(url_raw, (int, float)):
                        url = str(url_raw) if url_raw != 0 else ''
                    else:
                        url = str(url_raw).strip()
                    
                    title = str(row.get('Title', '')).strip()
                    author_string = str(row.get('Author', '')).strip()
                    
                    if not title or not author_string:
                        errors.append(ExcelValidationError(
                            row=idx + 1,
                            column="Title/Author",
                            message="Title and Author are required",
                            severity="error"
                        ))
                        continue
                    
                    # Debug: Print what we're processing
                    print(f"Processing row {idx + 1}: Title='{title}', Author='{author_string}', URL='{url}'")
                    
                    # Find matching book by title
                    book_id = await self.fuzzy_match_title(title)
                    if not book_id:
                        errors.append(ExcelValidationError(
                            row=idx + 1,
                            column="Title",
                            message=f"No matching book found for title: {title}",
                            severity="warning"
                        ))
                        continue
                    
                    books_matched += 1
                    
                    # Update book with mc_press_url
                    if url and self._is_valid_url(url):
                        async with self.pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE books SET mc_press_url = $1 WHERE id = $2",
                                url, book_id
                            )
                        books_updated += 1
                    
                    # Parse and create/update authors
                    authors = self.parse_authors(author_string)
                    for author_name in authors:
                        try:
                            author_id = await self.author_service.get_or_create_author(author_name)
                            # Check if this is a new author (simplified check)
                            # In a real implementation, you might track this more precisely
                            authors_created += 1  # This is approximate
                        except Exception as e:
                            errors.append(ExcelValidationError(
                                row=idx + 1,
                                column="Author",
                                message=f"Error processing author {author_name}: {str(e)}",
                                severity="error"
                            ))
                
                except Exception as e:
                    errors.append(ExcelValidationError(
                        row=idx + 1,
                        column="row",
                        message=f"Error processing row: {str(e)}",
                        severity="error"
                    ))
            
            result.success = True
            result.books_processed = books_processed
            result.books_matched = books_matched
            result.books_updated = books_updated
            result.authors_created = authors_created
            result.authors_updated = authors_updated
            result.errors = errors
            
        except Exception as e:
            result.errors = [ExcelValidationError(
                row=0,
                column="file",
                message=f"Error importing book metadata: {str(e)}",
                severity="error"
            )]
        
        result.processing_time = time.time() - start_time
        return result

    async def import_article_metadata(self, file_path: str) -> ImportResult:
        """
        Import article metadata from article-links.xlsm (export_subset sheet)
        
        Args:
            file_path: Path to article metadata Excel file
            
        Returns:
            ImportResult with processing statistics
            
        Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
        """
        start_time = time.time()
        result = ImportResult(success=False, processing_time=0.0)
        
        try:
            # Validate file first
            validation = await self.validate_excel_file(file_path, "article")
            if not validation.valid:
                result.errors = validation.errors
                result.processing_time = time.time() - start_time
                return result
            
            # Read Excel file (export_subset sheet)
            df = pd.read_excel(file_path, sheet_name='export_subset', engine='openpyxl')
            
            # Rename columns to match expected names
            if len(df.columns) >= 12:
                df = df.rename(columns={
                    df.columns[0]: 'id',           # Column A
                    df.columns[7]: 'feature_article',  # Column H
                    df.columns[9]: 'author',       # Column J
                    df.columns[10]: 'article_url', # Column K
                    df.columns[11]: 'author_url'   # Column L
                })
            
            articles_processed = 0
            articles_matched = 0
            documents_updated = 0
            authors_created = 0
            authors_updated = 0
            errors = []
            
            await self._ensure_pool()
            
            for idx, row in df.iterrows():
                try:
                    # Only process rows where feature_article = "yes"
                    feature_article = str(row.get('feature_article', '')).strip().lower()
                    if feature_article != 'yes':
                        continue
                    
                    articles_processed += 1
                    
                    article_id = str(row.get('id', '')).strip()
                    author_string = str(row.get('author', '')).strip()
                    article_url = str(row.get('article_url', '')).strip()
                    author_url = str(row.get('author_url', '')).strip()
                    
                    if not article_id or not author_string:
                        errors.append(ExcelValidationError(
                            row=idx + 1,
                            column="id/author",
                            message="Article ID and Author are required",
                            severity="error"
                        ))
                        continue
                    
                    # Match article ID against PDF filenames
                    async with self.pool.acquire() as conn:
                        # Try with and without .pdf extension
                        book_id = await conn.fetchval(
                            "SELECT id FROM books WHERE filename = $1 OR filename = $2",
                            f"{article_id}.pdf", article_id
                        )
                    
                    if not book_id:
                        errors.append(ExcelValidationError(
                            row=idx + 1,
                            column="id",
                            message=f"No matching document found for ID: {article_id}",
                            severity="warning"
                        ))
                        continue
                    
                    articles_matched += 1
                    
                    # Update document with article_url and document_type
                    async with self.pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE books 
                            SET article_url = $1, document_type = 'article'
                            WHERE id = $2
                        """, article_url if article_url else None, book_id)
                    documents_updated += 1
                    
                    # Parse and create/update authors
                    authors = self.parse_authors(author_string)
                    for author_name in authors:
                        try:
                            # Create author with site URL if provided
                            author_id = await self.author_service.get_or_create_author(
                                author_name, 
                                author_url if author_url else None
                            )
                            authors_created += 1  # This is approximate
                        except Exception as e:
                            errors.append(ExcelValidationError(
                                row=idx + 1,
                                column="author",
                                message=f"Error processing author {author_name}: {str(e)}",
                                severity="error"
                            ))
                
                except Exception as e:
                    errors.append(ExcelValidationError(
                        row=idx + 1,
                        column="row",
                        message=f"Error processing row: {str(e)}",
                        severity="error"
                    ))
            
            result.success = True
            result.articles_processed = articles_processed
            result.articles_matched = articles_matched
            result.documents_updated = documents_updated
            result.authors_created = authors_created
            result.authors_updated = authors_updated
            result.errors = errors
            
        except Exception as e:
            result.errors = [ExcelValidationError(
                row=0,
                column="file",
                message=f"Error importing article metadata: {str(e)}",
                severity="error"
            )]
        
        result.processing_time = time.time() - start_time
        return result