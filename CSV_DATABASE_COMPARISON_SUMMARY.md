# CSV vs Database Comparison Summary

## Investigation Date
January 26, 2026

## Objective
Compare the authoritative `book-metadata.csv` file with the database to validate author data, buy links, and metadata accuracy.

## Current Status: READY TO RUN (Updated Approach)

### NEW: API Endpoint Solution

Since `railway shell` still runs locally and can't access Railway's internal database hostname, I've created an API endpoint that runs the comparison ON Railway itself.

**How it works:**
1. Backend endpoint `/api/compare-csv-database` runs on Railway
2. It has direct database access (internal network)
3. Local script calls the endpoint via HTTPS
4. Results are returned as JSON

### How to Run

**Option 1: Using the API endpoint (RECOMMENDED)**

```bash
# Just run this locally - no Railway shell needed!
python3 run_csv_comparison.py
```

This script:
- Calls the Railway API endpoint
- Displays results on screen
- Saves detailed JSON to `csv_database_comparison_results.json`

**Option 2: Deploy first, then run**

If the endpoint isn't deployed yet:
```bash
# 1. Commit and push the new endpoint
git add backend/csv_comparison_endpoint.py backend/main.py run_csv_comparison.py
git commit -m "Add CSV comparison API endpoint"
git push origin main

# 2. Wait 10-15 minutes for Railway deployment

# 3. Run the comparison
python3 run_csv_comparison.py
```

## What the Script Checks

The comparison detects:

1. **Books in CSV but not in database** - Missing books that should be imported
2. **Books in database but not in CSV** - Extra books (may be articles or other content)
3. **Author mismatches** - Books where CSV authors don't match database authors
   - Count mismatches (different number of authors)
   - Name mismatches (different author names)
4. **Placeholder authors** - Books with "Admin", "Unknown", "Annegrubb", etc.
5. **Ordering issues** - Multi-author books with `author_order = -1`
6. **Perfect matches** - Books where everything matches correctly

### Why Railway Shell Doesn't Work

Both `railway run` and `railway shell` execute commands **locally** on your machine:
- They just set Railway environment variables
- Your local machine still can't resolve Railway's internal hostname: `pgvector-railway.railway.internal`
- This hostname only works inside Railway's private network

**Solution**: The API endpoint runs ON Railway where it can access the database directly.

## Expected Output

The script will display:
- Detailed lists of each issue type (first 10 examples)
- Summary statistics
- Save complete results to `csv_database_comparison_results.json`

## CSV File Contents

The `book-metadata.csv` file contains 113 books including:

1. **21st Century RPG: /Free, ILE, and MVC** by David Shirey
2. **Complete CL** by Ted Holt  
3. **Complete CL: Sixth Edition** by Ted Holt
4. **Control Language Programming for IBM i** by Jim Buck, Bryan Meyers, and Dan Riehl
5. **Subfiles in Free-Format RPG** by Kevin Vandever
6. ... and 108 more books

All with mc-store.com URLs that should be in the database.

## Next Steps After Running

Once you run the script and get results, we'll:

1. **Analyze the JSON output** to identify specific issues
2. **Create correction scripts** for books with author mismatches
3. **Fix placeholder authors** by replacing them with correct authors from CSV
4. **Fix ordering issues** for multi-author books
5. **Import missing books** if any are found

## Related Tasks

This work relates to task 2.4 in the author-display-investigation spec:
- **Task 2.4**: Create verification script for Excel comparison
- **Requirement 4.4**: Compare Excel data against database records to find mismatches

## Files Created

1. `compare_csv_books_simple.py` - Enhanced comparison script (READY TO RUN)
2. `compare_csv_with_database.py` - Original direct DB comparison
3. `compare_csv_with_database_api.py` - API comparison (blocked by API issues)
4. `CSV_DATABASE_COMPARISON_SUMMARY.md` - This summary

## Troubleshooting

### If you see "nodename nor servname provided, or not known"
This means you're trying to run the script locally. Use `railway shell` instead.

### If you see "RAILWAY_ENVIRONMENT not found"
The script detected it's not running on Railway. Use `railway shell` to enter Railway's environment.

### If you see "DATABASE_URL not found"
The Railway environment variable is missing. Check your Railway project configuration.

## Conclusion

The comparison script is ready to run. Use `railway shell` to enter Railway's environment, then run `python3 compare_csv_books_simple.py` to get detailed comparison results.
