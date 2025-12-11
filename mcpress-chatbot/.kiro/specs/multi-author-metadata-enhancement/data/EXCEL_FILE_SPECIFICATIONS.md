# Excel File Specifications

## File 1: book-metadata.xlsm

**Purpose**: Link books in the database to MC Press purchase URLs and author information

**Columns**:
- **Column A - URL**: Link to buy the book on MC Press site (mc_press_url)
- **Column B - Title**: Book title to match against books.title in database
- **Column C - Author**: Book author(s). Multiple authors separated by comma or "and"

**Matching Logic**:
- Match Title column against existing books.title in database
- Update matched books with URL and author information
- Parse multiple authors from Author column (comma or "and" delimited)

## File 2: article-links.xlsm

**Purpose**: Provide article metadata for PDF uploads and author information

**Sheet**: `export_subset` (only this tab will be processed)

**Columns Used**:
- **Column A - id**: Article ID that matches PDF filename for upload
- **Column H - feature article**: Filter - only process if value = "yes"
- **Column J - Author**: Article author (may have multiple authors)
- **Column K - Article URL**: Link to article on MC Press site
- **Column L - Author URL**: Link to author's page on MC Press site

**Processing Logic**:
1. Read only `export_subset` sheet
2. Filter rows where Column H = "yes"
3. Use Column A (id) to match against PDF filenames during upload
4. Extract author information from Column J
5. Store Article URL (Column K) as article_url in books table
6. Store Author URL (Column L) as site_url in authors table

## Data Processing Requirements

### Book Metadata Processing
1. **Title Matching**: Fuzzy match book titles to handle minor variations
2. **Author Parsing**: Split authors on comma or "and", trim whitespace
3. **URL Validation**: Ensure MC Press URLs are valid
4. **Duplicate Handling**: Update existing records, don't create duplicates

### Article Metadata Processing
1. **ID Matching**: Match article ID to PDF filename (with/without .pdf extension)
2. **Feature Filter**: Only process rows where feature article = "yes"
3. **Author Creation**: Create/update author records with site URLs
4. **Document Type**: Set document_type = "article" for matched documents
5. **URL Storage**: Store both article URL and author URL appropriately

## Implementation Notes

- Use `pandas` or `openpyxl` for Excel file reading
- Support .xlsm format (Excel with macros)
- Handle multiple sheets (specify sheet name for article-links)
- Implement robust error handling for missing columns or invalid data
- Provide detailed import reports showing matches, updates, and errors