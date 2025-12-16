# CSV Format Specification for Multi-Author Documents

## Overview

This document specifies the CSV format used for exporting and importing document metadata with multi-author support. The format uses pipe-delimited fields to handle multiple authors per document while maintaining CSV compatibility.

## CSV Structure

### Column Headers

```csv
id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,subcategory,description,tags,year,total_pages,processed_at
```

### Column Descriptions

| Column | Type | Required | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | Integer | Yes | Unique document identifier | `101` |
| `filename` | String | Yes | Original PDF filename | `"rpg-guide.pdf"` |
| `title` | String | Yes | Document title | `"RPG Programming Guide"` |
| `authors` | String | Yes | Pipe-delimited author names | `"John Doe\|Jane Smith"` |
| `document_type` | String | Yes | Document type: "book" or "article" | `"book"` |
| `author_site_urls` | String | No | Pipe-delimited author URLs (same order as authors) | `"https://john.com\|https://jane.com"` |
| `article_url` | String | No | Direct link to online article (for article-type docs) | `"https://example.com/article"` |
| `mc_press_url` | String | No | MC Press purchase link (typically for books) | `"https://mcpress.com/book"` |
| `category` | String | No | Primary document category | `"Programming"` |
| `subcategory` | String | No | Document subcategory | `"RPG"` |
| `description` | String | No | Document description | `"Comprehensive RPG guide"` |
| `tags` | String | No | Pipe-delimited tags | `"RPG\|Programming\|IBM i"` |
| `year` | Integer | No | Publication year | `2023` |
| `total_pages` | Integer | Yes | Total number of pages | `350` |
| `processed_at` | DateTime | Yes | Processing timestamp (ISO 8601) | `"2024-01-10T08:00:00Z"` |

## Multi-Author Field Format

### Authors Field (`authors`)

**Format**: Pipe-delimited list of author names
**Delimiter**: `|` (pipe character)
**Escaping**: Author names containing pipes must be escaped or quoted

**Examples**:
```csv
"John Doe"                    # Single author
"John Doe|Jane Smith"         # Two authors  
"John Doe|Jane Smith|Bob Lee" # Three authors
```

### Author Site URLs Field (`author_site_urls`)

**Format**: Pipe-delimited list of URLs in same order as authors
**Delimiter**: `|` (pipe character)
**Empty URLs**: Represented as empty string between delimiters
**Validation**: Each URL must be valid HTTP/HTTPS format or empty

**Examples**:
```csv
"https://johndoe.com"                           # Single author with URL
"https://johndoe.com|https://janesmith.com"     # Two authors, both have URLs
"https://johndoe.com|"                          # Two authors, second has no URL
"|https://janesmith.com"                        # Two authors, first has no URL
"https://johndoe.com||https://boblee.com"       # Three authors, middle has no URL
```

### Tags Field (`tags`)

**Format**: Pipe-delimited list of tags
**Delimiter**: `|` (pipe character)
**Case**: Preserved as entered

**Examples**:
```csv
"RPG"                           # Single tag
"RPG|Programming"               # Two tags
"RPG|Programming|IBM i|Modern"  # Multiple tags
```

## Document Type Specifications

### Book Type Documents

**Required Fields**:
- `document_type`: Must be `"book"`
- Standard document fields (id, filename, title, authors, etc.)

**Optional Fields**:
- `mc_press_url`: Purchase link (typically present for books)
- `article_url`: Should be empty/null for book-type documents

**Example**:
```csv
101,rpg-guide.pdf,"RPG Programming Guide","John Doe|Jane Smith",book,"https://johndoe.com|https://janesmith.com",,https://mcpress.com/rpg-guide,Programming,RPG,"Comprehensive RPG guide","RPG|Programming",2023,450,2024-01-10T08:00:00Z
```

### Article Type Documents

**Required Fields**:
- `document_type`: Must be `"article"`
- Standard document fields (id, filename, title, authors, etc.)

**Optional Fields**:
- `article_url`: Direct link to online article (typically present for articles)
- `mc_press_url`: Should be empty/null for article-type documents

**Example**:
```csv
102,web-dev-tips.pdf,"Modern Web Development","Alice Johnson",article,"https://alicejohnson.dev",https://example.com/web-dev-tips,,Web,Frontend,"Web development tips","Web|Frontend|JavaScript",2024,25,2024-01-15T10:30:00Z
```

## CSV Formatting Rules

### Quoting and Escaping

1. **Field Quoting**: Fields containing commas, quotes, or newlines must be quoted with double quotes
2. **Quote Escaping**: Double quotes within fields must be escaped by doubling them (`""`)
3. **Pipe Escaping**: Pipe characters within individual values should be avoided or the entire field quoted

**Examples**:
```csv
# Field with comma - must be quoted
"Smith, John|Wilson, Jane"

# Field with quotes - quotes must be doubled
"John ""Johnny"" Doe|Jane Smith"

# Field with newline - must be quoted  
"John Doe|Jane
Smith"
```

### Character Encoding

- **Encoding**: UTF-8 (required)
- **BOM**: Optional but recommended for Excel compatibility
- **Line Endings**: CRLF (`\r\n`) or LF (`\n`) accepted

### Empty Values

- **Empty Strings**: Represented as empty field between commas
- **Null Values**: Represented as empty field (same as empty string)
- **Empty Multi-Value Fields**: Empty string (no pipes)

**Examples**:
```csv
# Empty description and tags
101,file.pdf,"Title","Author",book,"https://author.com",,https://mcpress.com/book,Category,,,350,2024-01-10T08:00:00Z

# Empty author URLs
102,file2.pdf,"Title 2","Author 1|Author 2",book,"",,https://mcpress.com/book2,Category,,,280,2024-01-11T08:00:00Z
```

## Import Validation Rules

### Required Field Validation

- `filename`: Must be non-empty string
- `title`: Must be non-empty string  
- `authors`: Must contain at least one non-empty author name
- `document_type`: Must be exactly "book" or "article"
- `total_pages`: Must be positive integer
- `processed_at`: Must be valid ISO 8601 datetime

### Multi-Author Validation

- **Author Count**: Must have at least one author
- **URL Count**: If `author_site_urls` provided, count must match author count or be empty
- **URL Format**: Each non-empty URL must be valid HTTP/HTTPS format
- **Name Uniqueness**: Duplicate author names within same document are not allowed

### Document Type Validation

- **Book Documents**: 
  - `article_url` should be empty if provided
  - `mc_press_url` is optional but recommended
- **Article Documents**:
  - `article_url` is optional but recommended
  - `mc_press_url` should be empty if provided

### Data Type Validation

- **Integer Fields**: `id`, `year`, `total_pages` must be valid integers
- **DateTime Fields**: `processed_at` must be valid ISO 8601 format
- **URL Fields**: Must start with `http://` or `https://` if non-empty
- **Enum Fields**: `document_type` must be "book" or "article"

## Export Behavior

### Author Ordering

Authors are exported in their display order (by `author_order` field):
- First author has `author_order = 0`
- Second author has `author_order = 1`
- And so on...

### URL Alignment

Author site URLs are exported in the same order as authors:
- First URL corresponds to first author
- Second URL corresponds to second author
- Empty URLs represented as empty string between pipes

### Field Population

- **Always Included**: All columns are included in export header
- **Empty Fields**: Empty/null values exported as empty strings
- **Multi-Value Fields**: Always use pipe delimiter, even for single values

## Import Behavior

### Author Processing

1. **Parse Authors**: Split `authors` field by pipe delimiter
2. **Parse URLs**: Split `author_site_urls` field by pipe delimiter (if provided)
3. **Validate Counts**: Ensure URL count matches author count or is empty
4. **Create/Update Authors**: Use `AuthorService.get_or_create_author()` for each author
5. **Associate Authors**: Create document-author associations in specified order

### Document Processing

1. **Validate Required Fields**: Check all required fields are present and valid
2. **Create/Update Document**: Create new document or update existing if ID matches
3. **Set Document Type**: Validate and set document type
4. **Set URLs**: Set appropriate URL fields based on document type
5. **Associate Authors**: Replace all existing author associations with new ones

### Error Handling

- **Row-Level Errors**: Continue processing other rows if one row fails
- **Validation Errors**: Report specific field and validation issue
- **Duplicate Handling**: Skip duplicate author associations within same document
- **Missing References**: Create new author records for unknown names

## Example Files

### Complete Example

```csv
id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,subcategory,description,tags,year,total_pages,processed_at
101,rpg-guide.pdf,"RPG Programming Guide","John Doe|Jane Smith",book,"https://johndoe.com|https://janesmith.com",,https://mcpress.com/rpg-guide,Programming,RPG,"Comprehensive guide to RPG programming","RPG|Programming|IBM i",2023,450,2024-01-10T08:00:00Z
102,ile-concepts.pdf,"ILE Concepts","Bob Wilson",book,"https://bobwilson.dev",,https://mcpress.com/ile-concepts,Programming,ILE,"Understanding ILE concepts","ILE|Programming|Concepts",2022,320,2024-01-12T14:30:00Z
103,web-article.pdf,"Modern Web Development","Alice Johnson",article,"https://alicejohnson.dev",https://example.com/web-dev,,Web,Frontend,"Modern web development techniques","Web|Frontend|JavaScript|Modern",2024,25,2024-01-15T10:30:00Z
104,database-book.pdf,"Database Design Patterns","Carol Davis|David Lee|Eve Chen",book,"https://carol.dev|https://david.dev|https://eve.dev",,https://mcpress.com/database-patterns,Database,Design,"Advanced database design patterns","Database|Design|Patterns|Advanced",2023,520,2024-01-20T09:15:00Z
```

### Minimal Example

```csv
id,filename,title,authors,document_type,author_site_urls,article_url,mc_press_url,category,subcategory,description,tags,year,total_pages,processed_at
105,simple.pdf,"Simple Document","Author Name",book,"",,,,,,,,100,2024-01-01T00:00:00Z
```

### Error Examples

```csv
# Missing required author
106,bad1.pdf,"Bad Document 1","",book,"",,,,,,,,100,2024-01-01T00:00:00Z

# Invalid document type  
107,bad2.pdf,"Bad Document 2","Author",magazine,"",,,,,,,,100,2024-01-01T00:00:00Z

# Mismatched author/URL counts
108,bad3.pdf,"Bad Document 3","Author 1|Author 2",book,"https://author1.com",,,,,,,,100,2024-01-01T00:00:00Z

# Invalid URL format
109,bad4.pdf,"Bad Document 4","Author",book,"not-a-url",,,,,,,,100,2024-01-01T00:00:00Z
```

## Testing and Validation

### Validation Tools

Use the import validation endpoint to check CSV files before importing:

```bash
curl -X POST "$API_URL/api/admin/import/validate" \
  -H "Authorization: Bearer <token>" \
  -F "file=@documents.csv" \
  -F "import_type=documents"
```

### Round-Trip Testing

Verify data integrity by exporting, then importing the same data:

```bash
# Export current data
curl -X GET "$API_URL/api/admin/export/csv" -o export.csv

# Import the exported data (should show no changes)
curl -X POST "$API_URL/api/admin/import/csv" \
  -H "Authorization: Bearer <token>" \
  -F "file=@export.csv"
```

### Field Validation

Test each field type with various inputs:
- Empty values
- Maximum length strings
- Special characters
- Unicode characters
- Invalid formats
- Boundary values

This specification ensures consistent and reliable CSV data exchange for the multi-author document management system.