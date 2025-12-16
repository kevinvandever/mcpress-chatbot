# Multi-Author Metadata Enhancement API Documentation

## Overview

This document describes the API endpoints and data formats for the multi-author metadata enhancement feature. The enhancement adds support for multiple authors per document, distinguishes between books and articles, and provides comprehensive author management capabilities.

## Base URL

- **Production**: `https://mcpress-chatbot-production.up.railway.app`
- **API Prefix**: `/api`

## Authentication

All endpoints require admin authentication via JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Author Management Endpoints

### Search Authors (Autocomplete)

Search for authors by name to support autocomplete functionality.

**Endpoint**: `GET /api/authors/search`

**Query Parameters**:
- `q` (required): Search query string
- `limit` (optional): Maximum number of results (default: 10, max: 50)

**Example Request**:
```bash
curl -X GET "$API_URL/api/authors/search?q=John&limit=5" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "site_url": "https://johndoe.com",
    "document_count": 3
  },
  {
    "id": 15,
    "name": "John Smith", 
    "site_url": null,
    "document_count": 1
  }
]
```

### Get Author Details

Retrieve detailed information about a specific author.

**Endpoint**: `GET /api/authors/{author_id}`

**Path Parameters**:
- `author_id` (required): Unique identifier for the author

**Example Request**:
```bash
curl -X GET "$API_URL/api/authors/1" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "id": 1,
  "name": "John Doe",
  "site_url": "https://johndoe.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "document_count": 3
}
```

### Update Author Information

Update an author's name and/or site URL. Changes propagate to all documents by this author.

**Endpoint**: `PATCH /api/authors/{author_id}`

**Path Parameters**:
- `author_id` (required): Unique identifier for the author

**Request Body**:
```json
{
  "name": "John A. Doe",           // Optional: New author name
  "site_url": "https://newsite.com" // Optional: New site URL (empty string to clear)
}
```

**Example Request**:
```bash
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John A. Doe",
    "site_url": "https://johnadoe.com"
  }'
```

**Response**:
```json
{
  "message": "Author updated successfully",
  "author_id": 1
}
```

**Validation Rules**:
- `name`: Must be 1-255 characters, unique across all authors
- `site_url`: Must be valid HTTP/HTTPS URL or empty string to clear

### Get Documents by Author

List all documents written by a specific author.

**Endpoint**: `GET /api/authors/{author_id}/documents`

**Path Parameters**:
- `author_id` (required): Unique identifier for the author

**Query Parameters**:
- `limit` (optional): Maximum number of results (default: 50)
- `offset` (optional): Number of results to skip (default: 0)

**Example Request**:
```bash
curl -X GET "$API_URL/api/authors/1/documents?limit=10&offset=0" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
[
  {
    "id": 101,
    "filename": "rpg-guide.pdf",
    "title": "RPG Programming Guide",
    "category": "Programming",
    "subcategory": "RPG",
    "document_type": "book",
    "total_pages": 350,
    "processed_at": "2024-01-10T08:00:00Z"
  },
  {
    "id": 102,
    "filename": "ile-concepts.pdf", 
    "title": "ILE Concepts and Programming",
    "category": "Programming",
    "subcategory": "ILE",
    "document_type": "book",
    "total_pages": 280,
    "processed_at": "2024-01-12T14:30:00Z"
  }
]
```

## Document-Author Relationship Endpoints

### Add Author to Document

Associate an author with a document. Creates new author if name doesn't exist.

**Endpoint**: `POST /api/documents/{document_id}/authors`

**Path Parameters**:
- `document_id` (required): Unique identifier for the document

**Request Body**:
```json
{
  "author_name": "John Doe",                    // Required: Author name
  "author_site_url": "https://johndoe.com",    // Optional: Author website URL
  "order": 0                                   // Required: Display order (0-based)
}
```

**Example Request**:
```bash
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Jane Smith",
    "author_site_url": "https://janesmith.com",
    "order": 1
  }'
```

**Response**:
```json
{
  "message": "Author added to document successfully",
  "author_id": 2,
  "document_id": 101,
  "created_new_author": true
}
```

**Business Rules**:
- Prevents duplicate author associations for the same document
- Creates new author record if name doesn't exist
- Reuses existing author record if name matches (case-sensitive)
- Author order determines display sequence (0 = first author)

### Remove Author from Document

Remove an author association from a document.

**Endpoint**: `DELETE /api/documents/{document_id}/authors/{author_id}`

**Path Parameters**:
- `document_id` (required): Unique identifier for the document
- `author_id` (required): Unique identifier for the author

**Example Request**:
```bash
curl -X DELETE "$API_URL/api/documents/101/authors/2" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Success Response**:
```json
{
  "message": "Author removed from document successfully",
  "author_id": 2,
  "document_id": 101
}
```

**Error Response (Last Author)**:
```json
{
  "detail": "Cannot remove last author from document. Documents must have at least one author.",
  "status_code": 400
}
```

**Business Rules**:
- Documents must always have at least one author
- Removing the last author is prevented with 400 error
- Author record is preserved (only association is removed)

### Reorder Document Authors

Change the display order of authors for a document.

**Endpoint**: `PUT /api/documents/{document_id}/authors/order`

**Path Parameters**:
- `document_id` (required): Unique identifier for the document

**Request Body**:
```json
{
  "author_ids": [2, 1, 3]  // Array of author IDs in desired order
}
```

**Example Request**:
```bash
curl -X PUT "$API_URL/api/documents/101/authors/order" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "author_ids": [2, 1, 3]
  }'
```

**Response**:
```json
{
  "message": "Authors reordered successfully",
  "document_id": 101
}
```

**Business Rules**:
- All author IDs must be currently associated with the document
- Order array must include all current authors (no partial updates)
- First ID in array becomes order 0, second becomes order 1, etc.

## Enhanced Document Endpoints

### Get Document with Authors

Retrieve a document with its complete author list and metadata.

**Endpoint**: `GET /api/documents/{document_id}`

**Path Parameters**:
- `document_id` (required): Unique identifier for the document

**Example Request**:
```bash
curl -X GET "$API_URL/api/documents/101" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "id": 101,
  "filename": "rpg-guide.pdf",
  "title": "RPG Programming Guide",
  "document_type": "book",
  "mc_press_url": "https://mcpress.com/rpg-guide",
  "article_url": null,
  "category": "Programming",
  "subcategory": "RPG",
  "description": "Comprehensive guide to RPG programming on IBM i",
  "tags": ["RPG", "Programming", "IBM i"],
  "year": 2023,
  "total_pages": 350,
  "processed_at": "2024-01-10T08:00:00Z",
  "authors": [
    {
      "id": 1,
      "name": "John Doe",
      "site_url": "https://johndoe.com",
      "order": 0
    },
    {
      "id": 2,
      "name": "Jane Smith", 
      "site_url": "https://janesmith.com",
      "order": 1
    }
  ]
}
```

**Key Changes from Legacy Format**:
- `authors` is now an array instead of single string
- Added `document_type` field ("book" or "article")
- Added `article_url` field for article-type documents
- Authors include `id`, `site_url`, and `order` fields

### List Documents (Admin)

Enhanced document listing with multi-author support.

**Endpoint**: `GET /api/admin/documents`

**Query Parameters**:
- `limit` (optional): Maximum results (default: 50)
- `offset` (optional): Results to skip (default: 0)
- `author` (optional): Filter by exact author name
- `document_type` (optional): Filter by "book" or "article"
- `category` (optional): Filter by category
- `search` (optional): Text search in title/filename

**Example Request**:
```bash
curl -X GET "$API_URL/api/admin/documents?author=John%20Doe&document_type=book&limit=20" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "documents": [
    {
      "id": 101,
      "filename": "rpg-guide.pdf",
      "title": "RPG Programming Guide",
      "document_type": "book",
      "authors": [
        {
          "id": 1,
          "name": "John Doe",
          "site_url": "https://johndoe.com",
          "order": 0
        }
      ],
      "category": "Programming",
      "total_pages": 350,
      "processed_at": "2024-01-10T08:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Update Document Metadata

Enhanced document update with multi-author support.

**Endpoint**: `PATCH /api/admin/documents/{document_id}`

**Path Parameters**:
- `document_id` (required): Unique identifier for the document

**Request Body**:
```json
{
  "title": "Updated Title",
  "document_type": "article",
  "article_url": "https://example.com/article",
  "mc_press_url": "https://mcpress.com/book",
  "category": "Programming",
  "subcategory": "RPG",
  "description": "Updated description",
  "tags": ["RPG", "Updated"],
  "year": 2024,
  "authors": [
    {
      "name": "John Doe",
      "site_url": "https://johndoe.com",
      "order": 0
    },
    {
      "name": "Jane Smith",
      "site_url": "https://janesmith.com", 
      "order": 1
    }
  ]
}
```

**Example Request**:
```bash
curl -X PATCH "$API_URL/api/admin/documents/101" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated RPG Guide",
    "document_type": "book",
    "authors": [
      {
        "name": "John A. Doe",
        "site_url": "https://johnadoe.com",
        "order": 0
      }
    ]
  }'
```

**Response**:
```json
{
  "message": "Document updated successfully",
  "document_id": 101,
  "authors_created": 0,
  "authors_updated": 1
}
```

**Business Rules**:
- `document_type` must be "book" or "article"
- `article_url` only valid when `document_type` is "article"
- `mc_press_url` typically used when `document_type` is "book"
- Authors array replaces all current authors (not additive)
- Creates new author records for unknown names
- Updates existing author records if site_url differs

## CSV Export/Import Format

### Enhanced CSV Export Format

The CSV export now includes multi-author support with pipe-delimited fields.

**Endpoint**: `GET /api/admin/export/csv`

**New CSV Columns**:
```csv
id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,subcategory,description,tags,year,total_pages,processed_at
101,rpg-guide.pdf,"RPG Programming Guide","John Doe|Jane Smith",book,"https://johndoe.com|https://janesmith.com",,https://mcpress.com/rpg-guide,Programming,RPG,"Comprehensive RPG guide","RPG|Programming|IBM i",2023,350,2024-01-10T08:00:00Z
102,web-article.pdf,"Modern Web Development","Alice Johnson",article,"https://alicejohnson.dev",https://example.com/web-dev,,Web,Frontend,"Web development article","Web|Frontend|JavaScript",2024,25,2024-01-15T10:30:00Z
```

**Field Descriptions**:
- `authors`: Pipe-delimited list of author names (`Author1|Author2|Author3`)
- `author_site_urls`: Pipe-delimited list of author URLs in same order as authors
- `document_type`: Either "book" or "article"
- `article_url`: Direct link to online article (for article-type documents)
- `mc_press_url`: Purchase link (typically for book-type documents)

**Multi-Author Formatting Rules**:
- Multiple authors separated by pipe character (`|`)
- Author URLs in same order as author names
- Empty URL represented as empty string between pipes
- Example: `"John Doe|Jane Smith"` with URLs `"https://john.com|"`

### CSV Import Format

**Endpoint**: `POST /api/admin/import/csv`

**Request**: Multipart form data with CSV file

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/import/csv" \
  -H "Authorization: Bearer <token>" \
  -F "file=@documents.csv"
```

**CSV Import Rules**:
- Parses pipe-delimited authors and URLs
- Creates new author records for unknown names
- Updates existing documents if ID matches
- Creates new documents if ID is empty or not found
- Validates URLs before storing
- Sets document_type based on CSV value

**Response**:
```json
{
  "message": "CSV import completed",
  "documents_created": 5,
  "documents_updated": 12,
  "authors_created": 8,
  "authors_updated": 3,
  "errors": [
    {
      "row": 15,
      "error": "Invalid URL format: not-a-url"
    }
  ]
}
```

## Spreadsheet Import Endpoints

### Author Metadata Import

Import comprehensive author information from Excel/CSV files.

**Endpoint**: `POST /api/admin/import/authors`

**Request**: Multipart form data with spreadsheet file

**Expected Columns**:
- `name` (required): Author full name
- `site_url` (optional): Author website URL
- `bio` (optional): Author biography
- `email` (optional): Contact email

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/import/authors" \
  -H "Authorization: Bearer <token>" \
  -F "file=@author-metadata.xlsx"
```

**Response**:
```json
{
  "message": "Author import completed",
  "authors_created": 25,
  "authors_updated": 12,
  "validation_errors": [
    {
      "row": 8,
      "column": "site_url",
      "error": "Invalid URL format"
    }
  ]
}
```

### Article Metadata Import

Import article linking information to update document records.

**Endpoint**: `POST /api/admin/import/articles`

**Request**: Multipart form data with spreadsheet file

**Expected Columns**:
- `document_id` (required): Existing document ID
- `article_url` (required): Direct link to online article
- `title` (optional): Updated document title
- `category` (optional): Document category

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/import/articles" \
  -H "Authorization: Bearer <token>" \
  -F "file=@article-links.csv"
```

**Response**:
```json
{
  "message": "Article import completed", 
  "documents_updated": 45,
  "documents_not_found": 3,
  "validation_errors": [
    {
      "row": 12,
      "column": "article_url",
      "error": "Invalid URL format"
    }
  ]
}
```

### Import Validation and Preview

Validate spreadsheet data before importing.

**Endpoint**: `POST /api/admin/import/validate`

**Request**: Multipart form data with spreadsheet file and import type

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/import/validate" \
  -H "Authorization: Bearer <token>" \
  -F "file=@data.xlsx" \
  -F "import_type=authors"
```

**Response**:
```json
{
  "valid": true,
  "total_rows": 50,
  "preview_rows": [
    {
      "row_number": 1,
      "data": {
        "name": "John Doe",
        "site_url": "https://johndoe.com"
      },
      "validation_status": "valid"
    },
    {
      "row_number": 2,
      "data": {
        "name": "Jane Smith",
        "site_url": "invalid-url"
      },
      "validation_status": "error",
      "errors": ["Invalid URL format"]
    }
  ],
  "validation_summary": {
    "valid_rows": 48,
    "error_rows": 2,
    "missing_required_fields": 0,
    "invalid_urls": 2
  }
}
```

## Database Migration Procedure

### Migration Overview

The multi-author enhancement requires database schema changes and data migration from the existing single-author format.

### Pre-Migration Requirements

1. **Database Backup**: Create full backup before migration
2. **Maintenance Window**: Plan for 30-60 minutes downtime
3. **Verification Scripts**: Prepare rollback procedures

### Migration Steps

#### Step 1: Schema Migration

**Endpoint**: `POST /api/admin/migration/003/schema`

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/migration/003/schema" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "message": "Schema migration completed successfully",
  "tables_created": ["authors", "document_authors"],
  "columns_added": ["document_type", "article_url"],
  "indexes_created": 4,
  "execution_time_seconds": 12.5
}
```

#### Step 2: Data Migration

**Endpoint**: `POST /api/admin/migration/003/data`

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/migration/003/data" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "message": "Data migration completed successfully",
  "documents_processed": 1250,
  "authors_created": 342,
  "associations_created": 1250,
  "duplicate_authors_merged": 15,
  "execution_time_seconds": 45.2,
  "errors": []
}
```

#### Step 3: Migration Verification

**Endpoint**: `GET /api/admin/migration/003/verify`

**Example Request**:
```bash
curl -X GET "$API_URL/api/admin/migration/003/verify" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "verification_passed": true,
  "checks": {
    "all_documents_have_authors": true,
    "author_count_matches": true,
    "no_orphaned_associations": true,
    "schema_integrity": true
  },
  "statistics": {
    "total_documents": 1250,
    "total_authors": 342,
    "total_associations": 1250,
    "documents_without_authors": 0
  }
}
```

### Migration Rollback

**Endpoint**: `POST /api/admin/migration/003/rollback`

**Example Request**:
```bash
curl -X POST "$API_URL/api/admin/migration/003/rollback" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "message": "Migration rollback completed successfully",
  "tables_dropped": ["authors", "document_authors"],
  "columns_removed": ["document_type", "article_url"],
  "author_column_restored": true,
  "execution_time_seconds": 8.3
}
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "author_name",
      "message": "Author name is required"
    },
    {
      "field": "site_url", 
      "message": "Invalid URL format"
    }
  ]
}
```

#### 404 Not Found
```json
{
  "detail": "Author not found",
  "author_id": 999
}
```

#### 409 Conflict
```json
{
  "detail": "Author already associated with this document",
  "author_id": 1,
  "document_id": 101
}
```

#### 422 Validation Error
```json
{
  "detail": "Validation failed",
  "errors": [
    {
      "loc": ["body", "author_name"],
      "msg": "ensure this value has at most 255 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

### Business Logic Errors

#### Last Author Removal
```json
{
  "detail": "Cannot remove last author from document. Documents must have at least one author.",
  "status_code": 400,
  "document_id": 101,
  "remaining_authors": 1
}
```

#### Duplicate Author Association
```json
{
  "detail": "Author 'John Doe' is already associated with this document",
  "status_code": 409,
  "author_name": "John Doe",
  "document_id": 101
}
```

#### Invalid Document Type
```json
{
  "detail": "Invalid document type. Must be 'book' or 'article'",
  "status_code": 400,
  "provided_type": "magazine",
  "valid_types": ["book", "article"]
}
```

## Rate Limiting

All endpoints are subject to rate limiting:
- **Search endpoints**: 100 requests per minute
- **CRUD operations**: 60 requests per minute  
- **Bulk operations**: 10 requests per minute
- **Migration endpoints**: 5 requests per hour

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Testing Examples

### Complete Multi-Author Workflow

```bash
# 1. Search for existing authors
curl -X GET "$API_URL/api/authors/search?q=Doe" | jq

# 2. Get a document to work with
curl -X GET "$API_URL/api/documents/101" | jq

# 3. Add a second author
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Jane Smith",
    "author_site_url": "https://janesmith.com",
    "order": 1
  }' | jq

# 4. Verify both authors appear
curl -X GET "$API_URL/api/documents/101" | jq '.authors'

# 5. Update first author information
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John A. Doe",
    "site_url": "https://johnadoe.com"
  }' | jq

# 6. Verify update propagated to document
curl -X GET "$API_URL/api/documents/101" | jq '.authors'

# 7. Reorder authors (Jane first, John second)
curl -X PUT "$API_URL/api/documents/101/authors/order" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "author_ids": [2, 1]
  }' | jq

# 8. Export document data to CSV
curl -X GET "$API_URL/api/admin/export/csv" \
  -H "Authorization: Bearer <token>" \
  -o documents.csv
```

### Property Testing Examples

The following properties are validated by the system:

#### Property 15: Author Updates Propagate
```bash
# Test that updating an author affects all their documents
author_id=1
original_name=$(curl -s -X GET "$API_URL/api/authors/$author_id" | jq -r '.name')

# Update author
curl -X PATCH "$API_URL/api/authors/$author_id" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Verify all documents show updated name
curl -X GET "$API_URL/api/authors/$author_id/documents" | \
  jq -r '.[].id' | \
  while read doc_id; do
    curl -s -X GET "$API_URL/api/documents/$doc_id" | \
      jq ".authors[] | select(.id == $author_id) | .name"
  done
```

#### Property 2: Author Deduplication
```bash
# Test that duplicate author names reuse existing records
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"author_name": "John Doe", "order": 0}'

curl -X POST "$API_URL/api/documents/102/authors" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"author_name": "John Doe", "order": 0}'

# Verify same author_id returned for both
```

## Migration Checklist

### Pre-Migration
- [ ] Create database backup
- [ ] Verify current schema state
- [ ] Test migration on staging environment
- [ ] Prepare rollback scripts
- [ ] Schedule maintenance window

### During Migration
- [ ] Execute schema migration
- [ ] Run data migration
- [ ] Verify migration results
- [ ] Test critical endpoints
- [ ] Monitor for errors

### Post-Migration
- [ ] Verify all documents have authors
- [ ] Test multi-author functionality
- [ ] Validate CSV export/import
- [ ] Update frontend components
- [ ] Monitor system performance

### Rollback Procedure
If issues occur during migration:
1. Stop application traffic
2. Execute rollback endpoint
3. Restore from backup if needed
4. Verify system functionality
5. Resume normal operations

## Support and Troubleshooting

### Common Issues

#### Migration Fails Partially
- Check migration logs for specific errors
- Use verification endpoint to identify issues
- Consider manual data cleanup before retry

#### Author Deduplication Issues
- Review author names for case sensitivity
- Check for special characters or encoding issues
- Use author search to identify duplicates

#### CSV Import Failures
- Validate file encoding (UTF-8 required)
- Check column headers match expected format
- Verify URL formats in spreadsheet

### Monitoring Endpoints

#### System Health
```bash
curl -X GET "$API_URL/health" | jq
```

#### Database Statistics
```bash
curl -X GET "$API_URL/api/admin/stats" \
  -H "Authorization: Bearer <token>" | jq
```

#### Migration Status
```bash
curl -X GET "$API_URL/api/admin/migration/status" \
  -H "Authorization: Bearer <token>" | jq
```

For additional support, refer to the system logs and contact the development team with specific error messages and request details.