#!/usr/bin/env python3
"""
Check the status of article migration and metadata import
"""

import requests
import json

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def check_migration_status():
    """Check the article migration status"""
    print("🔍 Checking article migration status...")
    
    response = requests.get(f"{BASE_URL}/migrate-articles-to-books/status")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Migration status endpoint working")
        print(f"📊 Articles in documents table: {data.get('articles_in_documents_table', 'Unknown')}")
        print(f"📊 Articles in books table: {data.get('articles_in_books_table', 'Unknown')}")
        print(f"📊 Total books: {data.get('total_books', 'Unknown')}")
        print(f"🔄 Migration needed: {data.get('migration_needed', 'Unknown')}")
        
        return data
    else:
        print(f"❌ Migration status failed: {response.status_code}")
        return None

def check_sample_articles_in_db():
    """Check specific article data to see what's wrong"""
    print("\n🔍 Checking sample article data...")
    
    # Get documents list and find some articles
    response = requests.get(f"{BASE_URL}/documents")
    
    if response.status_code == 200:
        data = response.json()
        documents = data.get('documents', [])
        
        # Find articles (numeric filenames)
        articles = [doc for doc in documents if doc.get('filename', '').replace('.pdf', '').isdigit()]
        
        if articles:
            print(f"📋 Analyzing first 3 articles:")
            
            for i, article in enumerate(articles[:3]):
                print(f"\n--- Article {i+1}: {article.get('filename')} ---")
                print(f"  Title: {article.get('title')}")
                print(f"  Author: {article.get('author')}")
                print(f"  Document Type: {article.get('document_type')}")
                print(f"  Category: {article.get('category')}")
                
                # Check what's wrong
                issues = []
                if article.get('document_type') != 'article':
                    issues.append(f"Document type is '{article.get('document_type')}' should be 'article'")
                
                if article.get('author') in ['Unknown', 'Unknown Author']:
                    issues.append("Author is 'Unknown Author'")
                
                if issues:
                    print(f"  ❌ Issues:")
                    for issue in issues:
                        print(f"    - {issue}")
                else:
                    print(f"  ✅ No issues found")
        else:
            print("❌ No articles found")
    else:
        print(f"❌ Documents request failed: {response.status_code}")

def main():
    print("🔍 CHECKING ARTICLE MIGRATION STATUS")
    print("=" * 50)
    
    # Check migration status
    migration_data = check_migration_status()
    
    # Check sample article data
    check_sample_articles_in_db()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    
    if migration_data:
        articles_migrated = migration_data.get('articles_in_books_table', 0)
        if articles_migrated > 6000:
            print("✅ Article migration completed successfully")
            print("❌ BUT: Articles have wrong document_type and missing authors")
            print("\n🔧 FIXES NEEDED:")
            print("1. Update document_type from 'book' to 'article' for articles")
            print("2. Run metadata import to populate proper authors")
            print("3. Verify author associations are created")
        else:
            print("❌ Article migration may not have completed")
    
    print("\n📋 RECOMMENDED ACTIONS:")
    print("1. Re-run article metadata import: python3 import_article_metadata.py")
    print("2. Check if document_type gets updated during import")
    print("3. Verify author associations are created in document_authors table")

if __name__ == "__main__":
    main()