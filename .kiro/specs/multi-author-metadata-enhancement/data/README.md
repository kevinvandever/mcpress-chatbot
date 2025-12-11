# Spreadsheet Data Files

This directory contains spreadsheet files that provide author metadata and article linking information for the multi-author metadata enhancement feature.

## File Structure

Place your spreadsheet files here with the following naming convention:
- `authors-metadata.csv` - Author information with names, URLs, and other metadata
- `article-links.csv` - Mapping of document IDs to article metadata
- `[other-descriptive-name].csv` - Additional data files as needed

## File Format Guidelines

### Authors Metadata
Expected columns:
- `author_name` - Full author name
- `author_site_url` - Author's website URL (optional)
- `additional_info` - Any other author-related metadata

### Article Links  
Expected columns:
- `document_id` - Numeric ID of the document/article
- `article_url` - Direct link to the online article
- `mc_press_url` - Link to MC Press store page (if applicable)
- `title` - Article title
- `category` - Article category
- `subcategory` - Article subcategory (optional)

## Usage

These files will be processed by the spreadsheet import functionality to:
1. Populate the authors table with comprehensive author information
2. Link document IDs to their corresponding article metadata
3. Update existing documents with enhanced metadata from the spreadsheets

## Notes

- CSV files should use UTF-8 encoding
- URLs should be fully qualified (include http:// or https://)
- Empty cells are acceptable for optional fields
- Duplicate author names will be deduplicated automatically