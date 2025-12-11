# Spreadsheet Data Files

This directory contains Excel files that provide author metadata and article linking information for the multi-author metadata enhancement feature.

## File Structure

Current Excel files:
- `book-metadata.xlsm` - Book purchase URLs and author information
- `article-links.xlsm` - Article metadata and author information (uses `export_subset` sheet)

## File Format Guidelines

### book-metadata.xlsm
**Columns**:
- **A - URL**: MC Press purchase link for the book
- **B - Title**: Book title (matched against books.title in database)
- **C - Author**: Book author(s), multiple authors separated by comma or "and"

**Processing**:
- Match Title column against existing books.title in database
- Update matched books with URL and author information
- Parse multiple authors from Author column (comma or "and" delimited)

### article-links.xlsm (export_subset sheet)
**Columns Used**:
- **A - id**: Article ID matching PDF filename
- **H - feature article**: Filter (only "yes" values processed)
- **J - Author**: Article author name
- **K - Article URL**: Link to article on MC Press site  
- **L - Author URL**: Link to author's page on MC Press site

**Processing**:
1. Read only `export_subset` sheet
2. Filter rows where Column H = "yes"
3. Use Column A (id) to match against PDF filenames during upload
4. Extract author information from Column J
5. Store Article URL (Column K) as article_url in books table
6. Store Author URL (Column L) as site_url in authors table

## Usage

These files will be processed by the Excel import functionality to:
1. **Book Metadata**: Update existing book records with purchase URLs and author information
2. **Article Metadata**: Link article IDs to metadata for PDF upload processing
3. **Author Management**: Create/update author records with website URLs

## Technical Notes

- Files use Excel format (.xlsm) to support formulas and calculations
- Import system uses `pandas` or `openpyxl` for Excel file reading
- Title matching uses fuzzy matching to handle minor variations
- Author parsing handles both comma and "and" delimited multiple authors
- Only processes article records where "feature article" = "yes"
- Provides detailed import reports showing matches, updates, and errors