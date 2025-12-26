#!/usr/bin/env python3
"""
Migrate articles from documents table to books table
This creates book records for all articles so the metadata import can find them
"""

import requests

def main():
    print("🚀 Migrating articles from documents table to books table...")
    
    # Use the Railway API to trigger the migration
    api_url = "https://mcpress-chatbot-production.up.railway.app/migrate-articles-to-books"
    
    try:
        print("📤 Calling migration endpoint...")
        
        response = requests.post(api_url)
        result = response.json()
        
        print(f"✅ Migration result: {result.get('success', False)}")
        print(f"📊 Articles found: {result.get('articles_found', 0)}")
        print(f"📝 Books created: {result.get('books_created', 0)}")
        print(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
        
        # Show any errors
        errors = result.get('errors', [])
        if errors:
            print(f"\n⚠️ Migration errors:")
            for error in errors:
                print(f"  {error}")
        
        if result.get('success', False):
            print(f"\n🎉 Migration completed successfully!")
            print("Now you can run the article metadata import:")
            print("python3 import_article_metadata.py")
        else:
            print(f"\n❌ Migration failed")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()