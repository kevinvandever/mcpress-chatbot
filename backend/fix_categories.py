#!/usr/bin/env python3
"""
Fix book categories in the database
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Books to recategorize
rpg_to_programming = [
    "The RPG Programmers Guide to RPG IV and ILE.pdf",
    "Free-Format RPG IV- Third Edition.pdf",
    "21st Century RPG- -Free, ILE, and MVC.pdf",
    "Complete CL- Sixth Edition.pdf",
    "Evolve Your RPG Coding- Move from OPM to ILE ... and Beyond.pdf",
    "Free-Format RPG IV- Second Edition.pdf",
    "Complete CL- Fifth Edition.pdf",
    "Free-Format RPG IV- First Edition.pdf",
    "Eclipse- Step by Step.pdf"
]

rpg_to_database = [
    "DB2 11- The Ultimate Database for Cloud, Analytics, and Mobile.pdf"
]

# Other known mismatches from the report
other_fixes = [
    ("Data Fabric- An Intelligent Data Architecutre for AI.pdf", "Database"),
    ("Artificial Intelligence- Evolution and Revolution.pdf", "Database")
]

def update_category(filename, new_category, title=None, author=None):
    """Update book category"""
    try:
        # First get current metadata
        response = requests.get(f"{BASE_URL}/documents")
        books = response.json()['documents']
        
        # Find the book
        book = None
        for b in books:
            if b['filename'] == filename:
                book = b
                break
        
        if not book:
            print(f"❌ Book not found: {filename}")
            return False
        
        # Use existing title and author if not provided
        if not title:
            title = book['filename'].replace('.pdf', '')
        if not author:
            author = book.get('author', 'Unknown')
        
        # Update metadata
        update_data = {
            "filename": filename,
            "title": title,
            "author": author,
            "category": new_category
        }
        
        response = requests.put(
            f"{BASE_URL}/documents/{filename}/metadata",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Updated {filename}")
            print(f"   Category: RPG → {new_category}")
            return True
        else:
            print(f"❌ Failed to update {filename}: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {filename}: {e}")
        return False

def main():
    print("🔧 Fixing Book Categories")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # Fix RPG → Programming
    print("\n📚 Moving RPG books to Programming category:")
    print("-" * 40)
    for filename in rpg_to_programming:
        total_count += 1
        if update_category(filename, "Programming"):
            success_count += 1
        time.sleep(0.5)  # Small delay between requests
    
    # Fix RPG → Database
    print("\n💾 Moving DB2 book to Database category:")
    print("-" * 40)
    for filename in rpg_to_database:
        total_count += 1
        if update_category(filename, "Database"):
            success_count += 1
        time.sleep(0.5)
    
    # Fix other mismatches
    print("\n🔄 Fixing other category mismatches:")
    print("-" * 40)
    for filename, category in other_fixes:
        total_count += 1
        if update_category(filename, category):
            success_count += 1
        time.sleep(0.5)
    
    # Verify categories
    print("\n📊 Verifying final category distribution:")
    print("-" * 40)
    
    response = requests.get(f"{BASE_URL}/documents")
    if response.status_code == 200:
        books = response.json()['documents']
        categories = {}
        
        for book in books:
            cat = book['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        print("Current categories:")
        for cat, count in sorted(categories.items()):
            print(f"   {cat}: {count} books")
        
        # Check for invalid categories
        valid_categories = {
            "Programming", "Database", "Management and Career",
            "Operating Systems", "Application Development", 
            "System Administration"
        }
        
        invalid = set(categories.keys()) - valid_categories
        if invalid:
            print(f"\n⚠️  Invalid categories found: {invalid}")
        else:
            print("\n✅ All books use valid categories!")
    
    print(f"\n📈 Summary:")
    print(f"   Total updates attempted: {total_count}")
    print(f"   Successful updates: {success_count}")
    print(f"   Failed updates: {total_count - success_count}")
    
    if success_count == total_count:
        print("\n🎉 All category fixes completed successfully!")
    else:
        print(f"\n⚠️  Some updates failed. Please check the errors above.")

if __name__ == "__main__":
    main()