#!/usr/bin/env python3
"""
Quick fix script for specific author association issues identified by user:

1. Control Language Programming for IBM i - should show multiple authors including Jim Buck
2. Complete CL - Sixth Edition - should be Ted Holt, not annegrubb  
3. Subfiles in Free Format RPG - should be Kevin Vandever, not admin

This script will make targeted corrections to the database.
"""

import requests
import json

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def fix_book_author_association(book_title_pattern, correct_author_name, remove_wrong_authors=None):
    """
    Fix a specific book's author association
    
    Args:
        book_title_pattern: Pattern to search for the book
        correct_author_name: The correct author name
        remove_wrong_authors: List of wrong author names to remove
    """
    
    print(f"\n🔧 Fixing: {book_title_pattern}")
    print(f"   Correct author: {correct_author_name}")
    if remove_wrong_authors:
        print(f"   Remove wrong authors: {', '.join(remove_wrong_authors)}")
    
    # This would need to be implemented with proper API calls
    # For now, let's create the correction commands
    
    corrections = {
        "book_pattern": book_title_pattern,
        "correct_author": correct_author_name,
        "wrong_authors": remove_wrong_authors or []
    }
    
    return corrections

def create_author_correction_plan():
    """Create a plan for fixing the specific author issues"""
    
    print("📋 Author Correction Plan")
    print("=" * 50)
    
    corrections = []
    
    # 1. Complete CL - Sixth Edition: Ted Holt instead of annegrubb
    corrections.append(fix_book_author_association(
        "Complete CL",
        "Ted Holt", 
        ["annegrubb", "Annegrubb"]
    ))
    
    # 2. Subfiles in Free Format RPG: Kevin Vandever instead of admin
    corrections.append(fix_book_author_association(
        "Subfiles in Free",
        "Kevin Vandever",
        ["admin", "Admin"]
    ))
    
    # 3. Control Language Programming for IBM i: Should have multiple authors
    corrections.append(fix_book_author_association(
        "Control Language Programming for IBM i",
        "Jim Buck",  # Primary author
        None  # Don't remove, just ensure Jim Buck is included
    ))
    
    return corrections

def generate_sql_corrections():
    """Generate SQL commands to fix the author associations"""
    
    print("\n💾 SQL Correction Commands")
    print("=" * 50)
    
    sql_commands = []
    
    # Find Ted Holt's author ID and associate with Complete CL books
    sql_commands.append("""
-- Fix Complete CL - Sixth Edition author (Ted Holt instead of annegrubb)
-- Step 1: Find the book and wrong author association
SELECT b.id as book_id, b.title, a.name as current_author, da.id as doc_author_id
FROM books b
JOIN document_authors da ON b.id = da.book_id  
JOIN authors a ON da.author_id = a.id
WHERE b.title ILIKE '%Complete CL%' AND a.name ILIKE '%annegrubb%';

-- Step 2: Get Ted Holt's author ID
SELECT id FROM authors WHERE name = 'Ted Holt';

-- Step 3: Update the association (replace annegrubb with Ted Holt)
-- UPDATE document_authors 
-- SET author_id = (SELECT id FROM authors WHERE name = 'Ted Holt')
-- WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Complete CL%')
--   AND author_id = (SELECT id FROM authors WHERE name ILIKE '%annegrubb%');
""")

    sql_commands.append("""
-- Fix Subfiles in Free Format RPG author (Kevin Vandever instead of admin)
-- Step 1: Find the book and wrong author association  
SELECT b.id as book_id, b.title, a.name as current_author, da.id as doc_author_id
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id  
WHERE b.title ILIKE '%Subfiles%Free%' AND a.name ILIKE '%admin%';

-- Step 2: Get Kevin Vandever's author ID
SELECT id FROM authors WHERE name = 'Kevin Vandever';

-- Step 3: Update the association (replace admin with Kevin Vandever)
-- UPDATE document_authors
-- SET author_id = (SELECT id FROM authors WHERE name = 'Kevin Vandever') 
-- WHERE book_id = (SELECT id FROM books WHERE title ILIKE '%Subfiles%Free%')
--   AND author_id = (SELECT id FROM authors WHERE name ILIKE '%admin%');
""")

    sql_commands.append("""
-- Check Control Language Programming for IBM i authors
SELECT b.id as book_id, b.title, a.name as author_name, da.author_order
FROM books b
JOIN document_authors da ON b.id = da.book_id
JOIN authors a ON da.author_id = a.id
WHERE b.title ILIKE '%Control Language Programming%'
ORDER BY da.author_order;

-- If Jim Buck is missing, add him:
-- INSERT INTO document_authors (book_id, author_id, author_order)
-- SELECT b.id, a.id, 0
-- FROM books b, authors a  
-- WHERE b.title ILIKE '%Control Language Programming%'
--   AND a.name = 'Jim Buck'
--   AND NOT EXISTS (
--     SELECT 1 FROM document_authors da2 
--     WHERE da2.book_id = b.id AND da2.author_id = a.id
--   );
""")
    
    for i, cmd in enumerate(sql_commands, 1):
        print(f"\n-- Command {i}:")
        print(cmd)
    
    return sql_commands

def create_api_correction_script():
    """Create API-based correction script"""
    
    print(f"\n🔌 API Correction Script")
    print("=" * 50)
    
    api_script = f"""
# API-based corrections using the multi-author endpoints

# 1. Fix Complete CL - Sixth Edition
# Remove annegrubb and add Ted Holt

# First, find the book ID
curl -X GET "{API_URL}/api/documents" | grep -i "complete cl"

# Remove wrong author (if endpoint exists)
# curl -X DELETE "{API_URL}/api/documents/[BOOK_ID]/authors/[ANNEGRUBB_AUTHOR_ID]"

# Add correct author  
# curl -X POST "{API_URL}/api/documents/[BOOK_ID]/authors" \\
#   -H "Content-Type: application/json" \\
#   -d '{{"author_name": "Ted Holt", "order": 0}}'

# 2. Fix Subfiles in Free Format RPG
# Remove admin and add Kevin Vandever

# 3. Verify Control Language Programming for IBM i has Jim Buck
"""
    
    print(api_script)

def check_frontend_author_buttons():
    """Check what needs to be added to frontend for author website buttons"""
    
    print(f"\n🖥️  Frontend Author Button Requirements")
    print("=" * 50)
    
    frontend_changes = """
The CompactSources.tsx component already supports:
✅ Multiple author display (authors.map)
✅ Clickable author names with site_url
✅ Buy/Read buttons for books/articles

Missing feature identified by user:
❌ Separate "View Author" button for each book

Proposed addition:
- Add author profile/website button next to Buy button
- Show when any author has a site_url
- Link to author's website or author profile page
"""
    
    print(frontend_changes)
    
    return frontend_changes

if __name__ == "__main__":
    print("🔧 Quick Author Association Fixes")
    print("=" * 60)
    
    # Create correction plan
    corrections = create_author_correction_plan()
    
    # Generate SQL commands
    sql_commands = generate_sql_corrections()
    
    # Create API script
    create_api_correction_script()
    
    # Check frontend requirements
    check_frontend_author_buttons()
    
    print(f"\n📋 Next Steps:")
    print("=" * 50)
    print("1. 💾 Run SQL corrections on Railway database")
    print("2. 🔌 Test API endpoints for author management") 
    print("3. 🖥️  Add author website buttons to frontend")
    print("4. ✅ Verify corrections in chat interface")
    print("5. 📊 Run comprehensive author audit")