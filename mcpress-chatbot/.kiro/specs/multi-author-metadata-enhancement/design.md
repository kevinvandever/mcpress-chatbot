# Design Document

## Overview

This design enhances the document management system to support many-to-many relationships between authors and documents, distinguish between books and articles, and add additional metadata fields for external links. The current system stores author information as a single text field in the `books` table, limiting documents to one author. This design normalizes the database schema to support multiple authors per document while maintaining backward compatibility with existing functionality.

The enhancement will:
- Create a normalized `authors` table to store unique author information
- Create a `document_authors` junction table for many-to-many relationships
- Add a `document_type` field to distinguish books from articles
- Add URL fields for author websites, article links, and book purchase links
- Migrate existing single-author data to the new schema
- Update the admin interface to manage multiple authors per document
- Maintain existing batch upload and CSV export/import functionality
- **Add Excel import functionality for book and article metadata from MC Press data sources**

## Architecture

### Database Schema Changes

The new schema introduces three main changes:

1. **Authors Table**: Stores unique author information with optional website URLs
2. **Document Authors Junction Table**: Links documents to authors in a many-to-many relationship
3. **Books Table Modifications**: Adds document type and URL fields, removes the single `author` column

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Admin Interface (React)                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐│
│  │ DocumentList     │  │ BatchUpload      │  │ExcelImport  ││
│  │ - Multi-author   │  │ - Author parsing │  │- Book data  ││
│  │   management     │  │ - Type detection │  │- Article data││
│  └──────────────────┘  └──────────────────┘  └─────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐│
│  │ admin_documents  │  │ Author Service   │  │Excel Service││
│  │ - CRUD endpoints │  │ - Author lookup  │  │- File parse ││
│  │ - CSV export     │  │ - Deduplication  │  │- Validation ││
│  └──────────────────┘  └──────────────────┘  │- Fuzzy match││
│                                               └─────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   authors    │  │document_     │  │    books     │     │
│  │              │◄─┤authors       │─►│              │     │
│  │ - id         │  │              │  │ - id         │     │
│  │ - name       │  │ - book_id    │  │ - filename   │     │
│  │ - site_url   │  │ - author_id  │  │ - title      │     │
│  │ - created_at │  │ - order      │  │ - type       │     │
│  └──────────────┘  └──────────────┘  │ - article_url│     │
│                                       │ - mc_press_url│    │
│                                       └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```
## Components and Interfaces

### 1. Database Layer

#### Authors Table
```sql
CREATE TABLE authors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    site_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_authors_name ON authors(name);
```

#### Document Authors Junction Table
```sql
CREATE TABLE document_authors (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, author_id)
);

CREATE INDEX idx_document_authors_book ON document_authors(book_id);
CREATE INDEX idx_document_authors_author ON document_authors(author_id);
```

#### Books Table Modifications
```sql
ALTER TABLE books
    ADD COLUMN document_type TEXT NOT NULL DEFAULT 'book' CHECK (document_type IN ('book', 'article')),
    ADD COLUMN article_url TEXT,
    DROP COLUMN author;  -- Removed after migration
    -- Note: mc_press_url already exists, no need to add
```

### 2. Backend Services

#### AuthorService
Handles author-related operations:

```python
class AuthorService:
    async def get_or_create_author(self, name: str, site_url: Optional[str] = None) -> int:
        """Get existing author ID or create new author"""
        
    async def update_author(self, author_id: int, name: str, site_url: Optional[str]) -> None:
        """Update author information"""
        
    async def get_author_by_id(self, author_id: int) -> Dict[str, Any]:
        """Retrieve author details"""
        
    async def search_authors(self, query: str) -> List[Dict[str, Any]]:
        """Search authors by name for autocomplete"""
        
    async def get_authors_for_document(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all authors for a document in order"""
```

#### DocumentAuthorService
Manages document-author relationships:

```python
class DocumentAuthorService:
    async def add_author_to_document(self, book_id: int, author_id: int, order: int) -> None:
        """Associate an author with a document"""
        
    async def remove_author_from_document(self, book_id: int, author_id: int) -> None:
        """Remove author association"""
        
    async def reorder_authors(self, book_id: int, author_ids: List[int]) -> None:
        """Update author order for a document"""
        
    async def get_documents_by_author(self, author_id: int) -> List[Dict[str, Any]]:
        """Find all documents by an author"""
```

#### ExcelImportService
**NEW**: Handles Excel file processing for book and article metadata:

```python
class ExcelImportService:
    def __init__(self, author_service: AuthorService):
        self.author_service = author_service
        self.fuzzy_matcher = FuzzyMatcher(threshold=0.8)
    
    async def validate_excel_file(self, file_path: str, file_type: str) -> ValidationResult:
        """Validate Excel file format and required columns"""
        
    async def preview_excel_data(self, file_path: str, file_type: str) -> PreviewResult:
        """Generate preview of first 10 rows with validation status"""
        
    async def import_book_metadata(self, file_path: str) -> ImportResult:
        """Import book metadata from book-metadata.xlsm"""
        
    async def import_article_metadata(self, file_path: str) -> ImportResult:
        """Import article metadata from article-links.xlsm (export_subset sheet)"""
        
    def parse_authors(self, author_string: str) -> List[str]:
        """Parse multiple authors from comma or 'and' delimited string"""
        
    async def fuzzy_match_title(self, title: str) -> Optional[int]:
        """Find best matching book by title using fuzzy matching"""
```
### 3. API Endpoints

#### Excel Import Management
**NEW**: Excel file import endpoints:

```python
# Validate Excel file
POST /api/excel/validate
Body: multipart/form-data with file and type ("book" or "article")
Response: {
    "valid": true,
    "errors": [],
    "preview": [{"row": 1, "data": {...}, "status": "valid"}]
}

# Import book metadata
POST /api/excel/import/books
Body: multipart/form-data with book-metadata.xlsm file
Response: {
    "books_processed": 150,
    "books_matched": 142,
    "books_updated": 142,
    "authors_created": 23,
    "authors_updated": 45,
    "errors": []
}

# Import article metadata
POST /api/excel/import/articles
Body: multipart/form-data with article-links.xlsm file
Response: {
    "articles_processed": 89,
    "articles_matched": 76,
    "documents_updated": 76,
    "authors_created": 12,
    "authors_updated": 18,
    "errors": []
}
```

## Data Models

### Excel Import Models
**NEW**: Models for Excel import functionality:

```python
class ExcelValidationError(BaseModel):
    row: int
    column: str
    message: str
    severity: Literal['error', 'warning']

class ValidationResult(BaseModel):
    valid: bool
    errors: List[ExcelValidationError]
    preview_rows: List[Dict[str, Any]]

class ImportResult(BaseModel):
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
    url: str
    title: str
    author: str

class ArticleMetadataRow(BaseModel):
    id: str
    feature_article: str
    author: str
    article_url: str
    author_url: str
```
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### New Excel Import Properties (30-47)

### Property 30: Excel file format validation
*For any* Excel file upload, the system should correctly identify valid .xlsm files and reject invalid formats
**Validates: Requirements 11.1**

### Property 31: Book metadata column validation
*For any* book metadata Excel file, the system should correctly identify missing required columns (URL, Title, Author) and report errors
**Validates: Requirements 11.2**

### Property 32: Article metadata sheet validation
*For any* article metadata Excel file, the system should verify the export_subset sheet exists and contains required columns (A, H, J, K, L)
**Validates: Requirements 11.3**

### Property 33: Excel data validation
*For any* Excel file with invalid URLs or missing data, the system should identify and report all validation issues
**Validates: Requirements 11.4**

### Property 34: Excel preview accuracy
*For any* Excel file, the preview should show exactly the first 10 rows with accurate validation status for each row
**Validates: Requirements 11.5**

### Property 35: Excel error reporting
*For any* validation errors found, the system should provide detailed error messages with specific row and column information
**Validates: Requirements 11.6**

### Property 36: Excel workflow control
*For any* Excel file that passes validation, the system should allow proceeding with import or canceling the operation
**Validates: Requirements 11.7**

### Property 37: Book title fuzzy matching
*For any* book title in Excel data, the fuzzy matching algorithm should consistently find the best match in the existing database
**Validates: Requirements 9.2**

### Property 38: Book URL update
*For any* successfully matched book, the mc_press_url field should be updated with the URL from the Excel file
**Validates: Requirements 9.3**

### Property 39: Book author parsing
*For any* author string in book metadata, multiple authors separated by comma or "and" should be correctly parsed and trimmed
**Validates: Requirements 9.4**

### Property 40: Book author service integration
*For any* parsed author from book metadata, the AuthorService should be called to create or update the author record
**Validates: Requirements 9.5**

### Property 41: Book import reporting
*For any* book metadata import, the system should report accurate counts of books matched, updated, and errors encountered
**Validates: Requirements 9.6**

### Property 42: Article sheet filtering
*For any* article metadata file, only the export_subset sheet should be processed, ignoring other sheets
**Validates: Requirements 10.1**

### Property 43: Article feature filtering
*For any* article record, only rows where column H equals "yes" should be processed
**Validates: Requirements 10.2**

### Property 44: Article ID matching
*For any* article ID in column A, the system should match against PDF filenames with or without .pdf extension
**Validates: Requirements 10.3**

### Property 45: Article author processing
*For any* article record, the author from column J should create/update author records and column L should be stored as site_url
**Validates: Requirements 10.4**

### Property 46: Article URL storage
*For any* article record, column K should be stored as article_url and document_type should be set to "article"
**Validates: Requirements 10.5, 10.6**

### Property 47: Article import reporting
*For any* article metadata import, the system should report accurate counts of articles processed, authors created/updated, and validation errors
**Validates: Requirements 10.7**

## Testing Strategy

### Property-Based Testing
Property-based tests will verify universal properties across all inputs using **Hypothesis** (Python property-based testing library):

- **Configuration**: Each property test will run a minimum of 100 iterations
- **Tagging**: Each test will include a comment with the format: `# Feature: multi-author-metadata-enhancement, Property {number}: {property_text}`
- **Generators**: Custom generators for authors, documents, associations, and Excel data
- **Invariants**: Test data integrity constraints and business rules

Example property test for Excel functionality:
```python
from hypothesis import given, strategies as st

# Feature: multi-author-metadata-enhancement, Property 37: Book title fuzzy matching
@given(
    original_title=st.text(min_size=5, max_size=100),
    variation_type=st.sampled_from(['typo', 'case', 'punctuation', 'spacing'])
)
async def test_book_title_fuzzy_matching(original_title, variation_type):
    """For any book title with minor variations,
    fuzzy matching should find the original title"""
    # Test implementation
    pass
```

## Dependencies

### Backend Dependencies
**NEW**: Additional dependencies for Excel processing:
- `pandas>=2.0.0` - Excel file reading and data manipulation
- `openpyxl>=3.1.0` - Excel file format support (.xlsx, .xlsm)
- `fuzzywuzzy>=0.18.0` - Fuzzy string matching for book titles
- `python-levenshtein>=0.20.0` - Fast string distance calculations

### Existing Dependencies
- Python 3.11+
- FastAPI
- asyncpg (PostgreSQL driver)
- Hypothesis (property-based testing)

## Future Enhancements

### Excel Import Enhancements
- **Advanced Excel Features**: Support for multiple Excel file formats and custom column mappings
- **Scheduled Imports**: Automated Excel import processing on a schedule
- **Import History**: Track and display history of Excel import operations
- **Batch Processing**: Process multiple Excel files simultaneously
- **Custom Validation Rules**: Allow administrators to define custom validation rules for Excel data