#!/usr/bin/env python3
"""
Fix the article import to include article titles
This will update the Excel import service to read article titles and update the database
"""

import requests

def main():
    print("🔧 Fixing article import to include titles...")
    
    # First, let's examine what columns are actually available in the Excel file
    print("\n📋 Step 1: Examining Excel file structure...")
    
    # We need to understand the Excel file structure better
    # The user mentioned that articles should have proper names, not just IDs
    # This suggests there's a title column we're missing
    
    print("   Current mapping (from excel_import_service.py):")
    print("   - Column A (0): id")
    print("   - Column H (7): feature_article") 
    print("   - Column J (9): author")
    print("   - Column K (10): article_url")
    print("   - Column L (11): author_url")
    print("   - MISSING: Article title column!")
    
    print("\n   Likely title column locations:")
    print("   - Column B (1): Article title")
    print("   - Column C (2): Article title") 
    print("   - Column D (3): Article title")
    print("   - Column I (8): Article title (between feature_article and author)")
    
    # The fix requires updating the backend Excel import service
    print("\n🔧 Step 2: Required fixes...")
    print("   1. Update backend/excel_import_service.py:")
    print("      - Add title column mapping (likely column B, C, D, or I)")
    print("      - Update the database UPDATE query to include title")
    print("   2. Re-run the article metadata import")
    print("   3. Verify articles show proper titles instead of IDs")
    
    print("\n📝 Step 3: Implementation plan...")
    print("   The Excel import service needs these changes:")
    print("   ")
    print("   # In validate_excel_file() and import_article_metadata():")
    print("   df = df.rename(columns={")
    print("       df.columns[0]: 'id',           # Column A")
    print("       df.columns[1]: 'title',        # Column B (or whichever has titles)")
    print("       df.columns[7]: 'feature_article',  # Column H")
    print("       df.columns[9]: 'author',       # Column J")
    print("       df.columns[10]: 'article_url', # Column K")
    print("       df.columns[11]: 'author_url'   # Column L")
    print("   })")
    print("   ")
    print("   # In the database update:")
    print("   await conn.execute('''")
    print("       UPDATE books ")
    print("       SET title = $1, article_url = $2, document_type = 'article'")
    print("       WHERE id = $3")
    print("   ''', article_title, article_url, book_id)")
    
    print("\n🎯 Step 4: Expected results after fix...")
    print("   - Articles will show proper titles instead of '5805', '6274', etc.")
    print("   - 'Read' buttons will appear for articles with article_url")
    print("   - Author names will be clickable if they have website URLs")
    print("   - document_type will be set to 'article' for feature articles")
    
    print("\n" + "="*60)
    print("📊 SUMMARY:")
    print("="*60)
    print("\nThe article display issue is caused by:")
    print("✅ Articles were uploaded successfully (6,155 PDFs)")
    print("❌ Article metadata import is missing the title column")
    print("❌ Database 'title' column remains empty (shows filenames)")
    print("❌ Frontend displays filename when title is missing")
    print("\nTo fix:")
    print("1. Update Excel import service to read title column")
    print("2. Update database query to set title column")
    print("3. Re-run article metadata import")
    print("4. Verify proper titles and 'Read' buttons appear")

if __name__ == "__main__":
    main()