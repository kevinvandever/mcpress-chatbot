# Manual Testing Guide for Multi-Author Metadata Enhancement

This guide provides curl commands for manually testing the multi-author metadata enhancement features on Railway.

## Environment Setup

Set your Railway backend URL:
```bash
export API_URL="https://mcpress-chatbot-production.up.railway.app"
```

## Author Management Endpoints

### 1. Search Authors (Autocomplete)

Search for authors by name:
```bash
# Search for authors containing "John"
curl -X GET "$API_URL/api/authors/search?q=John" \
  -H "Content-Type: application/json"

# Search for authors containing "Smith"
curl -X GET "$API_URL/api/authors/search?q=Smith&limit=5" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "site_url": "https://johndoe.com",
    "document_count": 3
  }
]
```

### 2. Get Author Details

Retrieve detailed information about a specific author:
```bash
# Get author with ID 1
curl -X GET "$API_URL/api/authors/1" \
  -H "Content-Type: application/json"
```

**Expected Response:**
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

### 3. Update Author Information

Update an author's name and/or site URL:
```bash
# Update author name and URL
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John A. Doe",
    "site_url": "https://johnadoe.com"
  }'

# Update only the URL
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Content-Type: application/json" \
  -d '{
    "site_url": "https://newsite.com"
  }'

# Clear the URL (set to null)
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Content-Type: application/json" \
  -d '{
    "site_url": ""
  }'
```

**Expected Response:**
```json
{
  "message": "Author updated successfully",
  "author_id": 1
}
```

### 4. Get Documents by Author

List all documents written by a specific author:
```bash
# Get all documents by author ID 1
curl -X GET "$API_URL/api/authors/1/documents" \
  -H "Content-Type: application/json"

# With pagination
curl -X GET "$API_URL/api/authors/1/documents?limit=10&offset=0" \
  -H "Content-Type: application/json"
```

**Expected Response:**
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
  }
]
```

## Document-Author Relationship Endpoints

### 5. Add Author to Document

Associate an author with a document:
```bash
# Add existing author to document
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "John Doe",
    "author_site_url": "https://johndoe.com",
    "order": 0
  }'

# Add new author (will be created automatically)
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Jane Smith",
    "author_site_url": "https://janesmith.com",
    "order": 1
  }'
```

**Expected Response:**
```json
{
  "message": "Author added to document successfully",
  "author_id": 2,
  "document_id": 101
}
```

### 6. Remove Author from Document

Remove an author association (requires at least one author to remain):
```bash
# Remove author ID 2 from document ID 101
curl -X DELETE "$API_URL/api/documents/101/authors/2" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "message": "Author removed from document successfully",
  "author_id": 2,
  "document_id": 101
}
```

**Error Response (last author):**
```json
{
  "detail": "Cannot remove last author from document. Documents must have at least one author."
}
```

### 7. Reorder Document Authors

Change the order of authors for a document:
```bash
# Reorder authors (first author becomes second, second becomes first)
curl -X PUT "$API_URL/api/documents/101/authors/order" \
  -H "Content-Type: application/json" \
  -d '{
    "author_ids": [2, 1, 3]
  }'
```

**Expected Response:**
```json
{
  "message": "Authors reordered successfully",
  "document_id": 101
}
```

### 8. Get Document with Authors

Retrieve a document with its full author list:
```bash
# Get document ID 101 with all authors
curl -X GET "$API_URL/api/documents/101" \
  -H "Content-Type: application/json"
```

**Expected Response:**
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

## Testing Property 15: Author Updates Propagate

To manually verify that author updates propagate to all documents:

```bash
# Step 1: Get initial author info
curl -X GET "$API_URL/api/authors/1" | jq

# Step 2: Get documents by this author
curl -X GET "$API_URL/api/authors/1/documents" | jq

# Step 3: Update the author
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John A. Doe (Updated)",
    "site_url": "https://updated-site.com"
  }'

# Step 4: Verify update in author endpoint
curl -X GET "$API_URL/api/authors/1" | jq

# Step 5: Verify update propagated to each document
# Replace 101, 102, 103 with actual document IDs from step 2
curl -X GET "$API_URL/api/documents/101" | jq '.authors[] | select(.id == 1)'
curl -X GET "$API_URL/api/documents/102" | jq '.authors[] | select(.id == 1)'
curl -X GET "$API_URL/api/documents/103" | jq '.authors[] | select(.id == 1)'
```

All documents should show the updated author name and URL.

## Error Cases to Test

### Invalid URL Format
```bash
# Should fail with 400 Bad Request
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Test Author",
    "author_site_url": "not-a-valid-url",
    "order": 0
  }'
```

### Duplicate Author Association
```bash
# Add author first time (should succeed)
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "John Doe",
    "order": 0
  }'

# Try to add same author again (should fail with 409 Conflict)
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "John Doe",
    "order": 1
  }'
```

### Remove Last Author
```bash
# Should fail with 400 Bad Request
curl -X DELETE "$API_URL/api/documents/101/authors/1" \
  -H "Content-Type: application/json"
```

## Tips for Testing

1. **Use jq for pretty output**: Pipe curl output through `jq` for formatted JSON
2. **Save responses**: Use `-o response.json` to save responses for comparison
3. **Check status codes**: Add `-w "\nHTTP Status: %{http_code}\n"` to see status codes
4. **Verbose mode**: Add `-v` to see full request/response headers

## Example Test Workflow

Complete workflow to test multi-author functionality:

```bash
# 1. Search for an existing author
curl -X GET "$API_URL/api/authors/search?q=Doe" | jq

# 2. Get a document
curl -X GET "$API_URL/api/documents/101" | jq

# 3. Add a second author to the document
curl -X POST "$API_URL/api/documents/101/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Jane Smith",
    "author_site_url": "https://janesmith.com",
    "order": 1
  }' | jq

# 4. Verify both authors appear
curl -X GET "$API_URL/api/documents/101" | jq '.authors'

# 5. Update first author
curl -X PATCH "$API_URL/api/authors/1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John A. Doe"
  }' | jq

# 6. Verify update propagated
curl -X GET "$API_URL/api/documents/101" | jq '.authors'

# 7. Reorder authors
curl -X PUT "$API_URL/api/documents/101/authors/order" \
  -H "Content-Type: application/json" \
  -d '{
    "author_ids": [2, 1]
  }' | jq

# 8. Verify new order
curl -X GET "$API_URL/api/documents/101" | jq '.authors'
```

## Notes

- All endpoints require the database migration 003 to be completed
- Author names are deduplicated automatically (case-sensitive)
- URLs must start with `http://` or `https://`
- Documents must always have at least one author
- Author order starts at 0 (first author)
