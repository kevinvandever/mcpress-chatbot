# Book Author Correction Guide

## Overview

This guide explains how to correct book authors in the database using the authoritative `book-metadata.csv` file.

## Current Status

Based on the comparison results:
- **Total books in CSV**: 113
- **Total books in database**: 103
- **Perfect matches**: 16 (14%)
- **Books with author mismatches**: 87 (84%)
- **Books with placeholder authors**: 19 (Admin, Unknown, Test Author, etc.)
- **Books missing from database**: 10

## The Problem

Most books in the database have incorrect authors:
- Some have placeholder names like "Admin", "Unknown", "Test Author", "USA Sales", "Annegrubb"
- Some have wrong author names (e.g., "Loop Safari" instead of "Kevin Schroeder")
- Multi-author books are missing co-authors (e.g., only 1 author when there should be 3)

## The Solution

We've created an API endpoint that:
1. Reads the authoritative `book-metadata.csv` file
2. Compares each book's authors with the database
3. Creates missing author records
4. Replaces incorrect author associations with correct ones
5. Maintains proper author ordering for multi-author books

## How to Fix the Books

### Step 1: Deploy the Correction Endpoint

```bash
# Commit and push the new endpoint
git add backend/bulk_author_correction_endpoint.py backend/main.py run_author_corrections.py
git commit -m "Add bulk author correction endpoint"
git push origin main

# Wait 10-15 minutes for Railway deployment
```

### Step 2: Run the Correction Script

```bash
# Run the correction script locally
python3 run_author_corrections.py
```

The script will:
1. **Dry run first**: Show you what would be changed without making changes
2. **Ask for confirmation**: You must type "yes" to proceed
3. **Apply corrections**: Update all book authors to match the CSV
4. **Save results**: Create JSON files with before/after data

### Step 3: Verify the Corrections

```bash
# Run the comparison again to verify
python3 run_csv_comparison.py
```

You should see:
- **Perfect matches**: 103 (100% of books in database)
- **Author mismatches**: 0
- **Placeholder authors**: 0

## What Gets Fixed

### Example 1: Placeholder Author
**Before:**
- Book: "21st Century RPG: /Free, ILE, and MVC"
- Database author: "Annegrubb" ❌
- CSV author: "David Shirey" ✅

**After:**
- Database author: "David Shirey" ✅

### Example 2: Missing Co-Authors
**Before:**
- Book: "5 Keys to Business Analytics Program Success"
- Database authors: "Test Author" ❌
- CSV authors: "John Boyer, Bill Frank, Brian Green, Tracy Harris, and Kay Van De Vanter" ✅

**After:**
- Database authors: All 5 authors with correct ordering ✅

### Example 3: Wrong Author Name
**Before:**
- Book: "Advanced Guide to PHP on IBM i"
- Database author: "Loop Safari" ❌
- CSV author: "Kevin Schroeder" ✅

**After:**
- Database author: "Kevin Schroeder" ✅

## Files Created

1. **`backend/bulk_author_correction_endpoint.py`** - API endpoint that does the corrections
2. **`run_author_corrections.py`** - Script to run the corrections
3. **`author_corrections_dry_run.json`** - Preview of what will be changed
4. **`author_corrections_results.json`** - Record of what was changed

## Safety Features

- **Dry run mode**: Always runs first to show what would change
- **Confirmation required**: You must explicitly type "yes" to proceed
- **Detailed logging**: Every change is recorded in JSON files
- **Preserves correct data**: Only changes books with mismatches
- **Creates missing authors**: Automatically creates author records as needed
- **Maintains ordering**: Multi-author books keep correct author order

## What About the 10 Missing Books?

The 10 books in CSV but not in database need to be uploaded as PDFs first:
1. Complete CL
2. AS/400 TCP/IP Handbook
3. DB2 9.7 for Linux, UNIX, and Windows Database Administration (Exam 541)
4. And 7 more...

These can be uploaded through the admin interface after the author corrections are complete.

## Troubleshooting

### "Endpoint not found" error
The endpoint hasn't been deployed yet. Wait for Railway deployment to complete.

### "Request timed out" error
The correction is taking longer than expected. The endpoint has a 3-minute timeout. If it times out, check the database to see if partial corrections were made.

### "CSV file not found" error
The `book-metadata.csv` file needs to be on Railway. Make sure it's committed to the repository.

## Next Steps After Correction

1. **Verify corrections**: Run comparison again
2. **Test chat interface**: Check that books show correct authors
3. **Test admin interface**: Verify authors display correctly
4. **Upload missing books**: Add the 10 books that are in CSV but not in database
5. **Update task status**: Mark task 2.4 as complete in the spec

## Related Files

- `book-metadata.csv` - Authoritative source of truth
- `csv_database_comparison_results.json` - Current state analysis
- `CSV_DATABASE_COMPARISON_SUMMARY.md` - Comparison documentation
- `.kiro/specs/author-display-investigation/` - Full spec for this work
