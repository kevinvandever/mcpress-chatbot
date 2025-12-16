# Multi-Author Operations Examples

## Overview

This document provides practical examples for using the multi-author metadata enhancement API. All examples use curl commands that can be executed against the Railway production environment.

## Environment Setup

```bash
# Set your API base URL
export API_URL="https://mcpress-chatbot-production.up.railway.app"

# Set your admin JWT token (obtain from login endpoint)
export AUTH_TOKEN="your_jwt_token_here"

# Helper function for authenticated requests
auth_curl() {
  curl -H "Authorization: Bearer $AUTH_TOKEN" -H "Content-Type: application/json" "$@"
}
```

## Basic Author Management

### Example 1: Creating and Managing Authors

```bash
# Search for existing authors
auth_curl -X GET "$API_URL/api/authors/search?q=Smith"

# Response:
# [
#   {
#     "id": 15,
#     "name": "John Smith",
#     "site_url": "https://johnsmith.dev",
#     "document_count": 3
#   }
# ]

# Get detailed author information
auth_curl -X GET "$API_URL/api/authors/15"

# Response:
# {
#   "id": 15,
#   "name": "John Smith",
#   "site_url": "https://johnsmith.dev",
#   "created_at": "2024-01-15T10:30:00Z",
#   "updated_at": "2024-01-15T10:30:00Z",
#   "document_count": 3
# }

# Update author information
auth_curl -X PATCH "$API_URL/api/authors/15" -d '{
  "name": "John A. Smith",
  "site_url": "https://johnasmith.com"
}'

# Response:
# {
#   "message": "Author updated successfully",
#   "author_id": 15
# }
```

### Example 2: Author Search and Discovery

```bash
# Search with different queries
auth_curl -X GET "$API_URL/api/authors/search?q=John&limit=5"
auth_curl -X GET "$API_URL/api/authors/search?q=RPG&limit=10"
auth_curl -X GET "$API_URL/api/authors/search?q=IBM&limit=3"

# Get all documents by a specific author
auth_curl -X GET "$API_URL/api/authors/15/documents"

# Response:
# [
#   {
#     "id": 101,
#     "filename": "rpg-programming-guide.pdf",
#     "title": "Modern RPG Programming Techniques",
#     "category": "Programming",
#     "subcategory": "RPG",
#     "document_type": "book",
#     "total_pages": 450,
#     "processed_at": "2024-01-10T08:00:00Z"
#   },
#   {
#     "id": 205,
#     "filename": "ile-concepts.pdf",
#     "title": "ILE Concepts for RPG Programmers",
#     "category": "Programming", 
#     "subcategory": "ILE",
#     "document_type": "book",
#     "total_pages": 320,
#     "processed_at": "2024-01-12T14:30:00Z"
#   }
# ]
```

## Document-Author Relationships

### Example 3: Adding Multiple Authors to a Document

```bash
# Start with a document that has one author
auth_curl -X GET "$API_URL/api/documents/101"

# Response shows current single author:
# {
#   "id": 101,
#   "title": "Modern RPG Programming Techniques",
#   "authors": [
#     {
#       "id": 15,
#       "name": "John A. Smith",
#       "site_url": "https://johnasmith.com",
#       "order": 0
#     }
#   ]
# }

# Add a second author (existing author)
auth_curl -X POST "$API_URL/api/documents/101/authors" -d '{
  "author_name": "Jane Wilson",
  "author_site_url": "https://janewilson.dev",
  "order": 1
}'

# Response:
# {
#   "message": "Author added to document successfully",
#   "author_id": 23,
#   "document_id": 101,
#   "created_new_author": false
# }

# Add a third author (new author)
auth_curl -X POST "$API_URL/api/documents/101/authors" -d '{
  "author_name": "Robert Chen",
  "author_site_url": "https://robertchen.com",
  "order": 2
}'

# Response:
# {
#   "message": "Author added to document successfully", 
#   "author_id": 47,
#   "document_id": 101,
#   "created_new_author": true
# }

# Verify all three authors are now associated
auth_curl -X GET "$API_URL/api/documents/101" | jq '.authors'

# Response:
# [
#   {
#     "id": 15,
#     "name": "John A. Smith",
#     "site_url": "https://johnasmith.com",
#     "order": 0
#   },
#   {
#     "id": 23,
#     "name": "Jane Wilson",
#     "site_url": "https://janewilson.dev",
#     "order": 1
#   },
#   {
#     "id": 47,
#     "name": "Robert Chen",
#     "site_url": "https://robertchen.com",
#     "order": 2
#   }
# ]
```

### Example 4: Reordering Authors

```bash
# Current order: John (0), Jane (1), Robert (2)
# Change to: Jane (0), Robert (1), John (2)

auth_curl -X PUT "$API_URL/api/documents/101/authors/order" -d '{
  "author_ids": [23, 47, 15]
}'

# Response:
# {
#   "message": "Authors reordered successfully",
#   "document_id": 101
# }

# Verify new order
auth_curl -X GET "$API_URL/api/documents/101" | jq '.authors[] | {name, order}'

# Response:
# {
#   "name": "Jane Wilson",
#   "order": 0
# }
# {
#   "name": "Robert Chen", 
#   "order": 1
# }
# {
#   "name": "John A. Smith",
#   "order": 2
# }
```

### Example 5: Removing Authors

```bash
# Try to remove the last remaining author (should fail)
# First, remove two authors to leave only one
auth_curl -X DELETE "$API_URL/api/documents/101/authors/23"  # Remove Jane
auth_curl -X DELETE "$API_URL/api/documents/101/authors/47"  # Remove Robert

# Now try to remove the last author (John)
auth_curl -X DELETE "$API_URL/api/documents/101/authors/15"

# Response (error):
# {
#   "detail": "Cannot remove last author from document. Documents must have at least one author.",
#   "status_code": 400,
#   "document_id": 101,
#   "remaining_authors": 1
# }

# Add back an author first, then remove John
auth_curl -X POST "$API_URL/api/documents/101/authors" -d '{
  "author_name": "Jane Wilson",
  "order": 1
}'

# Now remove John (should succeed)
auth_curl -X DELETE "$API_URL/api/documents/101/authors/15"

# Response:
# {
#   "message": "Author removed from document successfully",
#   "author_id": 15,
#   "document_id": 101
# }
```

## Document Type Management

### Example 6: Working with Book vs Article Types

```bash
# Create a book-type document
auth_curl -X PATCH "$API_URL/api/admin/documents/101" -d '{
  "title": "RPG Programming Guide",
  "document_type": "book",
  "mc_press_url": "https://mcpress.com/rpg-guide",
  "authors": [
    {
      "name": "John Smith",
      "site_url": "https://johnsmith.dev",
      "order": 0
    }
  ]
}'

# Create an article-type document  
auth_curl -X PATCH "$API_URL/api/admin/documents/102" -d '{
  "title": "Modern RPG Techniques",
  "document_type": "article", 
  "article_url": "https://example.com/modern-rpg-techniques",
  "authors": [
    {
      "name": "Jane Wilson",
      "site_url": "https://janewilson.dev",
      "order": 0
    }
  ]
}'

# Verify document types
auth_curl -X GET "$API_URL/api/documents/101" | jq '{document_type, mc_press_url, article_url}'
# Response:
# {
#   "document_type": "book",
#   "mc_press_url": "https://mcpress.com/rpg-guide",
#   "article_url": null
# }

auth_curl -X GET "$API_URL/api/documents/102" | jq '{document_type, mc_press_url, article_url}'
# Response:
# {
#   "document_type": "article",
#   "mc_press_url": null,
#   "article_url": "https://example.com/modern-rpg-techniques"
# }
```

## CSV Export and Import

### Example 7: Enhanced CSV Export

```bash
# Export all documents with multi-author data
auth_curl -X GET "$API_URL/api/admin/export/csv" -o documents_export.csv

# View the header and first few rows
head -3 documents_export.csv

# Expected format:
# id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,subcategory,description,tags,year,total_pages,processed_at
# 101,rpg-guide.pdf,"RPG Programming Guide","John Smith|Jane Wilson",book,"https://johnsmith.dev|https://janewilson.dev",,https://mcpress.com/rpg-guide,Programming,RPG,"Comprehensive RPG guide","RPG|Programming|IBM i",2023,450,2024-01-10T08:00:00Z
# 102,modern-rpg.pdf,"Modern RPG Techniques","Jane Wilson",article,"https://janewilson.dev",https://example.com/modern-rpg-techniques,,Programming,RPG,"Modern techniques article","RPG|Modern|Techniques",2024,25,2024-01-15T10:30:00Z

# Extract just the multi-author fields
cut -d',' -f4,5 documents_export.csv | head -5

# Expected output:
# authors,author_site_urls
# "John Smith|Jane Wilson","https://johnsmith.dev|https://janewilson.dev"
# "Jane Wilson","https://janewilson.dev"
```

### Example 8: CSV Import with Multi-Author Data

```bash
# Create a CSV file with multi-author data
cat > import_test.csv << 'EOF'
id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,subcategory
103,new-book.pdf,"New Programming Book","Alice Johnson|Bob Davis",book,"https://alice.dev|https://bob.dev",,https://mcpress.com/new-book,Programming,General
104,web-article.pdf,"Web Development Tips","Carol Smith",article,"https://carol.dev",https://example.com/web-tips,,Web,Frontend
EOF

# Import the CSV file
auth_curl -X POST "$API_URL/api/admin/import/csv" -F "file=@import_test.csv"

# Response:
# {
#   "message": "CSV import completed",
#   "documents_created": 2,
#   "documents_updated": 0,
#   "authors_created": 3,
#   "authors_updated": 0,
#   "errors": []
# }

# Verify the imported documents
auth_curl -X GET "$API_URL/api/documents/103" | jq '{title, document_type, authors}'
# Response:
# {
#   "title": "New Programming Book",
#   "document_type": "book", 
#   "authors": [
#     {
#       "id": 48,
#       "name": "Alice Johnson",
#       "site_url": "https://alice.dev",
#       "order": 0
#     },
#     {
#       "id": 49,
#       "name": "Bob Davis",
#       "site_url": "https://bob.dev", 
#       "order": 1
#     }
#   ]
# }
```

## Advanced Scenarios

### Example 9: Author Update Propagation

```bash
# Demonstrate that updating an author affects all their documents

# First, find an author with multiple documents
auth_curl -X GET "$API_URL/api/authors/search?q=Smith" | jq '.[] | select(.document_count > 1)'

# Response:
# {
#   "id": 15,
#   "name": "John A. Smith",
#   "site_url": "https://johnasmith.com",
#   "document_count": 3
# }

# Get all documents by this author
auth_curl -X GET "$API_URL/api/authors/15/documents" | jq '.[].id'
# Response: [101, 205, 312]

# Check current author info in each document
for doc_id in 101 205 312; do
  echo "Document $doc_id:"
  auth_curl -X GET "$API_URL/api/documents/$doc_id" | jq '.authors[] | select(.id == 15) | {name, site_url}'
done

# Update the author's information
auth_curl -X PATCH "$API_URL/api/authors/15" -d '{
  "name": "John Alexander Smith",
  "site_url": "https://johnalexandersmith.com"
}'

# Verify the update propagated to all documents
for doc_id in 101 205 312; do
  echo "Document $doc_id after update:"
  auth_curl -X GET "$API_URL/api/documents/$doc_id" | jq '.authors[] | select(.id == 15) | {name, site_url}'
done

# All should show the updated name and URL
```

### Example 10: Bulk Author Management

```bash
# Scenario: Add the same co-author to multiple related documents

# Find all RPG-related documents
auth_curl -X GET "$API_URL/api/admin/documents?category=Programming&subcategory=RPG&limit=50" | jq '.documents[].id'

# Response: [101, 205, 312, 445, 567]

# Add "Technical Editor" as co-author to all RPG documents
rpg_docs=(101 205 312 445 567)
for doc_id in "${rpg_docs[@]}"; do
  echo "Adding technical editor to document $doc_id"
  auth_curl -X POST "$API_URL/api/documents/$doc_id/authors" -d '{
    "author_name": "Sarah Technical Editor",
    "author_site_url": "https://saraheditor.com",
    "order": 99
  }'
done

# Verify the technical editor appears in all documents
for doc_id in "${rpg_docs[@]}"; do
  echo "Document $doc_id authors:"
  auth_curl -X GET "$API_URL/api/documents/$doc_id" | jq '.authors[] | .name'
done
```

### Example 11: Document Search by Author

```bash
# Search for all documents by a specific author
auth_curl -X GET "$API_URL/api/admin/documents?author=John%20Alexander%20Smith&limit=20"

# Response:
# {
#   "documents": [
#     {
#       "id": 101,
#       "title": "RPG Programming Guide",
#       "authors": [
#         {
#           "name": "John Alexander Smith",
#           "site_url": "https://johnalexandersmith.com"
#         }
#       ]
#     }
#   ],
#   "total": 3,
#   "limit": 20,
#   "offset": 0
# }

# Search for documents by multiple criteria
auth_curl -X GET "$API_URL/api/admin/documents?author=Jane%20Wilson&document_type=article&category=Programming"

# Get author statistics
auth_curl -X GET "$API_URL/api/authors/23" | jq '{name, document_count}'
# Response:
# {
#   "name": "Jane Wilson",
#   "document_count": 5
# }
```

## Error Handling Examples

### Example 12: Common Error Scenarios

```bash
# 1. Try to add duplicate author to same document
auth_curl -X POST "$API_URL/api/documents/101/authors" -d '{
  "author_name": "John Alexander Smith",
  "order": 0
}'

# Response (409 Conflict):
# {
#   "detail": "Author 'John Alexander Smith' is already associated with this document",
#   "status_code": 409,
#   "author_name": "John Alexander Smith",
#   "document_id": 101
# }

# 2. Try to use invalid URL
auth_curl -X POST "$API_URL/api/documents/101/authors" -d '{
  "author_name": "New Author",
  "author_site_url": "not-a-valid-url",
  "order": 1
}'

# Response (400 Bad Request):
# {
#   "detail": "Invalid request data",
#   "errors": [
#     {
#       "field": "author_site_url",
#       "message": "Invalid URL format. Must start with http:// or https://"
#     }
#   ]
# }

# 3. Try to access non-existent author
auth_curl -X GET "$API_URL/api/authors/99999"

# Response (404 Not Found):
# {
#   "detail": "Author not found",
#   "author_id": 99999
# }

# 4. Try to remove last author
auth_curl -X DELETE "$API_URL/api/documents/101/authors/15"

# Response (400 Bad Request):
# {
#   "detail": "Cannot remove last author from document. Documents must have at least one author.",
#   "status_code": 400,
#   "document_id": 101,
#   "remaining_authors": 1
# }
```

## Performance Testing Examples

### Example 13: Load Testing Author Operations

```bash
# Test author search performance
time auth_curl -X GET "$API_URL/api/authors/search?q=Smith&limit=50"

# Test document retrieval with many authors
time auth_curl -X GET "$API_URL/api/documents/101"

# Test bulk author addition (simulate batch upload)
start_time=$(date +%s)
for i in {1..10}; do
  auth_curl -X POST "$API_URL/api/documents/101/authors" -d "{
    \"author_name\": \"Test Author $i\",
    \"author_site_url\": \"https://test$i.com\",
    \"order\": $i
  }" > /dev/null 2>&1
done
end_time=$(date +%s)
echo "Added 10 authors in $((end_time - start_time)) seconds"

# Clean up test authors
for i in {1..10}; do
  author_id=$(auth_curl -X GET "$API_URL/api/authors/search?q=Test%20Author%20$i" | jq '.[0].id')
  auth_curl -X DELETE "$API_URL/api/documents/101/authors/$author_id" > /dev/null 2>&1
done
```

## Integration Testing Examples

### Example 14: End-to-End Workflow

```bash
# Complete workflow: Create document, add authors, export, modify, re-export

# 1. Create a new document with initial author
auth_curl -X POST "$API_URL/api/admin/documents" -d '{
  "filename": "test-workflow.pdf",
  "title": "Test Workflow Document",
  "document_type": "book",
  "mc_press_url": "https://mcpress.com/test-workflow",
  "category": "Testing",
  "authors": [
    {
      "name": "Primary Author",
      "site_url": "https://primary.com",
      "order": 0
    }
  ]
}'

# Get the new document ID from response
doc_id=$(auth_curl -X GET "$API_URL/api/admin/documents?filename=test-workflow.pdf" | jq '.documents[0].id')

# 2. Add additional authors
auth_curl -X POST "$API_URL/api/documents/$doc_id/authors" -d '{
  "author_name": "Secondary Author",
  "author_site_url": "https://secondary.com", 
  "order": 1
}'

auth_curl -X POST "$API_URL/api/documents/$doc_id/authors" -d '{
  "author_name": "Third Author",
  "order": 2
}'

# 3. Export to CSV and verify multi-author format
auth_curl -X GET "$API_URL/api/admin/export/csv" | grep "test-workflow.pdf"

# 4. Update author information
primary_author_id=$(auth_curl -X GET "$API_URL/api/documents/$doc_id" | jq '.authors[0].id')
auth_curl -X PATCH "$API_URL/api/authors/$primary_author_id" -d '{
  "name": "Updated Primary Author",
  "site_url": "https://updated-primary.com"
}'

# 5. Reorder authors
author_ids=$(auth_curl -X GET "$API_URL/api/documents/$doc_id" | jq '.authors | map(.id)')
auth_curl -X PUT "$API_URL/api/documents/$doc_id/authors/order" -d "{
  \"author_ids\": $(echo $author_ids | jq 'reverse')
}"

# 6. Final verification
auth_curl -X GET "$API_URL/api/documents/$doc_id" | jq '{title, authors: .authors | map({name, site_url, order})}'

# 7. Cleanup
auth_curl -X DELETE "$API_URL/api/admin/documents/$doc_id"
```

## Monitoring and Debugging

### Example 15: System Health Checks

```bash
# Check overall system health
auth_curl -X GET "$API_URL/health"

# Get database statistics
auth_curl -X GET "$API_URL/api/admin/stats" | jq '{
  total_documents: .documents,
  total_authors: .authors,
  total_associations: .document_authors,
  avg_authors_per_doc: (.document_authors / .documents)
}'

# Check for orphaned records
auth_curl -X GET "$API_URL/api/admin/diagnostics/orphaned-authors"
auth_curl -X GET "$API_URL/api/admin/diagnostics/documents-without-authors"

# Performance metrics
auth_curl -X GET "$API_URL/api/admin/performance/author-search-times"
auth_curl -X GET "$API_URL/api/admin/performance/document-retrieval-times"
```

These examples demonstrate the full range of multi-author functionality and provide practical templates for testing and using the enhanced API endpoints.