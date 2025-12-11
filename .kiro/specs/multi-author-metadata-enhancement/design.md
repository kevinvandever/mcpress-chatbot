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
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ DocumentList     │  │ BatchUpload      │                │
│  │ - Multi-author   │  │ - Author parsing │                │
│  │   management     │  │ - Type detection │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ admin_documents  │  │ Author Service   │                │
│  │ - CRUD endpoints │  │ - Author lookup  │                │
│  │ - CSV export     │  │ - Deduplication  │                │
│  └──────────────────┘  └──────────────────┘                │
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
│                                       │ - book_url   │     │
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

#### MigrationService
Handles data migration:

```python
class MigrationService:
    async def migrate_authors(self) -> Dict[str, Any]:
        """
        Extract unique authors from books table,
        create author records, and establish relationships
        """
        
    async def rollback_migration(self) -> None:
        """Rollback migration if needed"""
        
    async def verify_migration(self) -> Dict[str, Any]:
        """Verify migration integrity"""
```

### 3. API Endpoints

#### Author Management
```python
# Get authors for autocomplete
GET /api/authors/search?q={query}
Response: [{"id": 1, "name": "John Doe", "site_url": "..."}]

# Get author details
GET /api/authors/{author_id}
Response: {"id": 1, "name": "John Doe", "site_url": "...", "document_count": 5}

# Update author
PATCH /api/authors/{author_id}
Body: {"name": "John Doe", "site_url": "https://..."}

# Get documents by author
GET /api/authors/{author_id}/documents
Response: [{"id": 1, "title": "...", "filename": "..."}]
```

#### Document-Author Management
```python
# Add author to document
POST /api/documents/{document_id}/authors
Body: {"author_name": "John Doe", "author_site_url": "https://...", "order": 0}

# Remove author from document
DELETE /api/documents/{document_id}/authors/{author_id}

# Reorder authors
PUT /api/documents/{document_id}/authors/order
Body: {"author_ids": [1, 2, 3]}

# Get document with authors
GET /api/documents/{document_id}
Response: {
    "id": 1,
    "title": "...",
    "document_type": "book",
    "authors": [
        {"id": 1, "name": "John Doe", "site_url": "...", "order": 0},
        {"id": 2, "name": "Jane Smith", "site_url": "...", "order": 1}
    ],
    "book_purchase_url": "...",
    ...
}
```

### 4. Frontend Components

#### MultiAuthorInput Component
```typescript
interface Author {
    id?: number
    name: string
    site_url?: string
    order: number
}

interface MultiAuthorInputProps {
    authors: Author[]
    onChange: (authors: Author[]) => void
    onAuthorSearch: (query: string) => Promise<Author[]>
}

// Features:
// - Autocomplete from existing authors
// - Add new authors inline
// - Drag-and-drop reordering
// - Edit author site URLs
// - Remove authors (with validation for last author)
```

#### DocumentTypeSelector Component
```typescript
interface DocumentTypeSelectorProps {
    type: 'book' | 'article'
    onChange: (type: 'book' | 'article') => void
    articleUrl?: string
    bookPurchaseUrl?: string
    onUrlChange: (field: string, value: string) => void
}

// Features:
// - Radio buttons for book/article selection
// - Conditional URL fields based on type
// - URL validation
```

## Data Models

### Author Model
```python
class Author(BaseModel):
    id: Optional[int] = None
    name: str
    site_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    document_count: Optional[int] = None  # For display purposes
```

### DocumentAuthor Model
```python
class DocumentAuthor(BaseModel):
    id: Optional[int] = None
    book_id: int
    author_id: int
    author_order: int = 0
    created_at: Optional[datetime] = None
```

### Enhanced Document Model
```python
class Document(BaseModel):
    id: int
    filename: str
    title: str
    authors: List[Author]  # Changed from single author string
    document_type: Literal['book', 'article'] = 'book'
    article_url: Optional[str] = None
    mc_press_url: Optional[str] = None  # Existing field for book purchase links
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    year: Optional[int] = None
    total_pages: int
    processed_at: datetime
```

### CSV Export Format
```
id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,...
1,example.pdf,Example Book,"John Doe|Jane Smith","book","https://john.com|https://jane.com",,https://mcpress.com/book,Database,...
```

Authors are pipe-delimited (|) to support multiple authors in a single field.


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Multiple author association
*For any* document and any list of authors, when associating those authors with the document, all authors should be retrievable from the document in the same order
**Validates: Requirements 1.1, 1.3**

### Property 2: Author deduplication
*For any* author name, when that author is associated with multiple documents, only one author record should exist in the authors table
**Validates: Requirements 1.2**

### Property 3: No duplicate author associations
*For any* document and author, attempting to associate the same author with the document multiple times should result in only one association record
**Validates: Requirements 1.4**

### Property 4: Cascade deletion preserves shared authors
*For any* author associated with multiple documents, when deleting one document, the author record should still exist and remain associated with the other documents
**Validates: Requirements 1.5**

### Property 5: Document type validation
*For any* document creation attempt, the document type must be either "book" or "article", and invalid types should be rejected
**Validates: Requirements 2.1**

### Property 6: Type-specific URL fields
*For any* document, when the type is "book", a book purchase URL can be stored, and when the type is "article", an article URL can be stored
**Validates: Requirements 2.2, 2.3**

### Property 7: Document type in responses
*For any* document retrieval, the response should include the document_type field
**Validates: Requirements 2.4**

### Property 8: Filter by document type
*For any* document type filter, only documents matching that type should be returned
**Validates: Requirements 2.5**

### Property 9: Optional author site URL
*For any* author, the site URL field should be optional and accept both null values and valid URLs
**Validates: Requirements 3.1**

### Property 10: URL validation
*For any* author site URL provided, invalid URL formats should be rejected while valid URLs are accepted
**Validates: Requirements 3.2**

### Property 11: Author site URL in responses
*For any* author with a site URL, retrieving that author should include the site URL in the response
**Validates: Requirements 3.3**

### Property 12: Consistent author URLs across documents
*For any* author associated with multiple documents, retrieving any of those documents should return the same author site URL
**Validates: Requirements 3.4**

### Property 13: Migration preserves metadata
*For any* document before migration, all metadata fields (title, category, URLs) should have identical values after migration
**Validates: Requirements 4.4**

### Property 14: Create or reuse author on add
*For any* author name, when adding it to a document, if the author exists it should be reused, otherwise a new author record should be created
**Validates: Requirements 5.3, 5.4**

### Property 15: Author updates propagate
*For any* author associated with multiple documents, when updating the author's information, all documents should reflect the updated information
**Validates: Requirements 5.6**

### Property 16: Require at least one author
*For any* document with exactly one author, attempting to remove that author should be rejected
**Validates: Requirements 5.7**

### Property 17: Batch upload creates authors
*For any* batch of documents with author metadata, all authors should be created or associated after the batch upload completes
**Validates: Requirements 6.1**

### Property 18: Parse multiple authors
*For any* document metadata containing multiple authors in delimited format, all authors should be correctly parsed and associated
**Validates: Requirements 6.2**

### Property 19: Batch upload deduplicates authors
*For any* batch upload containing documents with duplicate author names, only one author record per unique name should be created
**Validates: Requirements 6.5**

### Property 20: CSV export includes all authors
*For any* document with multiple authors, exporting to CSV should include all author names in the output
**Validates: Requirements 7.1**

### Property 21: CSV export includes all URL fields
*For any* CSV export, the output should include columns for document_type, author_site_urls, article_url, and book_purchase_url
**Validates: Requirements 7.2**

### Property 22: CSV multi-author formatting
*For any* document with multiple authors, the CSV export should format authors as a delimited list
**Validates: Requirements 7.3**

### Property 23: CSV import round-trip
*For any* set of documents, exporting to CSV then importing should preserve all document and author data
**Validates: Requirements 7.4**

### Property 24: CSV import creates authors
*For any* CSV import containing new author names, author records should be created for those names
**Validates: Requirements 7.5**

### Property 25: Search by author returns all documents
*For any* author name search query, all documents associated with authors matching the query should be returned
**Validates: Requirements 8.1**

### Property 26: Exact author name matching
*For any* exact author name filter, only documents with authors having that exact name should be returned
**Validates: Requirements 8.2**

### Property 27: Author document count
*For any* author, retrieving author information should include an accurate count of associated documents
**Validates: Requirements 8.3**

### Property 28: Author pagination and sorting
*For any* author list request with pagination and sorting parameters, the results should be correctly paginated and sorted by the specified field
**Validates: Requirements 8.4**

### Property 29: Filter authors without documents
*For any* author list request with the "exclude empty" filter, authors with zero associated documents should not be included in results
**Validates: Requirements 8.5**

## Error Handling

### Database Errors
- **Constraint Violations**: Return 400 Bad Request with descriptive error messages
- **Foreign Key Violations**: Return 409 Conflict when attempting invalid operations
- **Connection Failures**: Return 503 Service Unavailable with retry guidance
- **Transaction Rollback**: Ensure atomic operations with proper rollback on failures

### Validation Errors
- **Invalid URLs**: Return 400 Bad Request with URL format requirements
- **Invalid Document Type**: Return 400 Bad Request listing valid types
- **Missing Required Fields**: Return 400 Bad Request specifying missing fields
- **Duplicate Prevention**: Return 409 Conflict when attempting to create duplicate associations

### Migration Errors
- **Pre-migration Validation**: Check for required tables and columns before starting
- **Partial Failure Handling**: Log errors but continue processing remaining records
- **Rollback Capability**: Provide migration rollback script for emergency recovery
- **Verification Failures**: Report discrepancies between expected and actual results

### Business Logic Errors
- **Last Author Removal**: Return 400 Bad Request with message "Document must have at least one author"
- **Author Not Found**: Return 404 Not Found when referencing non-existent authors
- **Document Not Found**: Return 404 Not Found when referencing non-existent documents

## Testing Strategy

### Unit Testing
Unit tests will verify individual components and functions:

- **AuthorService**: Test author creation, retrieval, update, and search
- **DocumentAuthorService**: Test association creation, removal, and reordering
- **URL Validation**: Test valid and invalid URL formats
- **CSV Parsing**: Test multi-author delimiter parsing
- **Migration Logic**: Test author extraction and deduplication

### Property-Based Testing
Property-based tests will verify universal properties across all inputs using **Hypothesis** (Python property-based testing library):

- **Configuration**: Each property test will run a minimum of 100 iterations
- **Tagging**: Each test will include a comment with the format: `# Feature: multi-author-metadata-enhancement, Property {number}: {property_text}`
- **Generators**: Custom generators for authors, documents, and associations
- **Invariants**: Test data integrity constraints and business rules

Example property test structure:
```python
from hypothesis import given, strategies as st

# Feature: multi-author-metadata-enhancement, Property 2: Author deduplication
@given(
    author_name=st.text(min_size=1, max_size=100),
    document_ids=st.lists(st.integers(min_value=1), min_size=2, max_size=10)
)
async def test_author_deduplication(author_name, document_ids):
    """For any author name associated with multiple documents,
    only one author record should exist"""
    # Test implementation
    pass
```

### Integration Testing
Integration tests will verify end-to-end workflows:

- **Document Creation with Multiple Authors**: Create document, add authors, verify associations
- **Migration Execution**: Run migration on test database, verify data integrity
- **CSV Export/Import Round-trip**: Export data, import it, verify preservation
- **Batch Upload**: Upload multiple documents, verify author creation and association
- **Author Search**: Create test data, search by various criteria, verify results

### API Testing
API tests will verify endpoint behavior:

- **Author Management Endpoints**: Test CRUD operations on authors
- **Document-Author Endpoints**: Test association management
- **Search and Filter Endpoints**: Test query parameters and results
- **CSV Export/Import Endpoints**: Test file upload and download

### Database Testing
Database tests will verify schema and constraints:

- **Schema Validation**: Verify tables, columns, and indexes exist
- **Constraint Enforcement**: Test unique constraints, foreign keys, check constraints
- **Cascade Behavior**: Verify ON DELETE CASCADE works correctly
- **Transaction Isolation**: Test concurrent operations

### Migration Testing
Migration tests will verify data transformation:

- **Pre-migration State**: Capture current data
- **Migration Execution**: Run migration script
- **Post-migration Verification**: Verify all data preserved and transformed correctly
- **Rollback Testing**: Test migration rollback procedure

## Performance Considerations

### Database Optimization
- **Indexes**: Create indexes on frequently queried columns (author name, document_authors foreign keys)
- **Query Optimization**: Use JOIN operations efficiently to fetch documents with authors
- **Batch Operations**: Use bulk insert for batch uploads and migrations
- **Connection Pooling**: Maintain connection pool for concurrent requests

### Caching Strategy
- **Author Lookup Cache**: Cache author ID lookups by name to reduce database queries
- **Document Cache Invalidation**: Invalidate document cache when authors are updated
- **Autocomplete Cache**: Cache author name search results for autocomplete

### Scalability
- **Pagination**: Implement cursor-based pagination for large author lists
- **Async Operations**: Use async/await for all database operations
- **Background Jobs**: Process large batch uploads asynchronously
- **Rate Limiting**: Implement rate limiting on search endpoints

## Security Considerations

### Authentication and Authorization
- **Admin-Only Operations**: Restrict author management to authenticated admins
- **API Token Validation**: Validate JWT tokens on all protected endpoints
- **Role-Based Access**: Implement role checks for sensitive operations

### Input Validation
- **SQL Injection Prevention**: Use parameterized queries for all database operations
- **XSS Prevention**: Sanitize author names and URLs before storage and display
- **URL Validation**: Validate and sanitize all URL inputs
- **CSV Injection Prevention**: Escape special characters in CSV exports

### Data Integrity
- **Transaction Boundaries**: Use database transactions for multi-step operations
- **Constraint Enforcement**: Rely on database constraints for data integrity
- **Audit Logging**: Log all author and document modifications to metadata_history table

## Deployment Strategy

### Migration Execution
1. **Backup**: Create full database backup before migration
2. **Dry Run**: Execute migration on staging environment
3. **Verification**: Run verification queries to ensure data integrity
4. **Production Migration**: Execute migration during maintenance window
5. **Rollback Plan**: Keep rollback script ready in case of issues

### Rollout Plan
1. **Phase 1**: Deploy backend changes with backward compatibility
2. **Phase 2**: Execute database migration
3. **Phase 3**: Deploy frontend changes to use new multi-author features
4. **Phase 4**: Monitor for issues and performance impacts

### Monitoring
- **Migration Progress**: Log migration progress and any errors
- **API Performance**: Monitor response times for author-related endpoints
- **Database Performance**: Monitor query performance and index usage
- **Error Rates**: Track error rates for new endpoints

## Future Enhancements

### Potential Improvements
- **Author Profiles**: Expand author records with bio, photo, and social links
- **Author Merging**: Provide admin tool to merge duplicate author records
- **Author Aliases**: Support pen names and alternative author names
- **Contributor Roles**: Distinguish between authors, editors, translators, etc.
- **Author Analytics**: Track most popular authors and their document views
- **Author Notifications**: Notify authors when their documents are accessed
