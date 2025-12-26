#!/usr/bin/env python3
"""
Debug the article import process to understand why articles aren't showing proper titles
"""

import requests
import pandas as pd

def main():
    print("🔍 Debugging article import process...")
    
    # First, let's examine the Excel file structure
    print("\n📋 Step 1: Examining Excel file structure...")
    try:
        file_path = ".kiro/specs/multi-author-metadata-enhancement/data/article-links.xlsm"
        
        # Read the export_subset sheet
        df = pd.read_excel(file_path, sheet_name='export_subset', engine='openpyxl')
        
        print(f"   Excel file loaded successfully")
        print(f"   Total rows: {len(df)}")
        print(f"   Total columns: {len(df.columns)}")
        
        # Show column names
        print(f"\n   Column names:")
        for i, col in enumerate(df.columns):
            print(f"   {chr(65+i)} ({i}): {col}")
        
        # Show first few rows
        print(f"\n   First 3 rows of key columns:")
        key_columns = [0, 7, 9, 10, 11]  # A, H, J, K, L
        for i in range(min(3, len(df))):
            print(f"\n   Row {i+1}:")
            for col_idx in key_columns:
                if col_idx < len(df.columns):
                    col_name = chr(65 + col_idx)
                    value = df.iloc[i, col_idx] if col_idx < len(df.columns) else "N/A"
                    print(f"     {col_name}: {value}")
        
        # Count Feature Article = "yes"
        if len(df.columns) > 7:
            feature_col = df.iloc[:, 7]  # Column H
            yes_count = sum(1 for val in feature_col if str(val).strip().lower() == 'yes')
            print(f"\n   Articles with Feature Article = 'yes': {yes_count}")
        
    except Exception as e:
        print(f"   ❌ Error reading Excel file: {e}")
        return
    
    # Test the validation endpoint
    print("\n📋 Step 2: Testing validation endpoint...")
    try:
        api_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/validate"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            data = {'file_type': 'article'}
            
            response = requests.post(api_url, files=files, data=data)
            result = response.json()
            
            print(f"   Validation result: {result.get('valid', False)}")
            print(f"   Preview rows: {len(result.get('preview_rows', []))}")
            
            # Show validation errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n   Validation errors:")
                for error in errors:
                    print(f"     {error}")
            
            # Show preview data
            preview_rows = result.get('preview_rows', [])
            if preview_rows:
                print(f"\n   Preview of first 2 rows:")
                for i, row in enumerate(preview_rows[:2]):
                    print(f"     Row {i+1}: {row}")
    
    except Exception as e:
        print(f"   ❌ Error testing validation: {e}")
    
    # Test the import endpoint
    print("\n📤 Step 3: Testing import endpoint...")
    try:
        import_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/import/articles"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            
            response = requests.post(import_url, files=files)
            result = response.json()
            
            print(f"   Import success: {result.get('success', False)}")
            print(f"   Articles processed: {result.get('articles_processed', 0)}")
            print(f"   Articles matched: {result.get('articles_matched', 0)}")
            print(f"   Documents updated: {result.get('documents_updated', 0)}")
            print(f"   Authors created: {result.get('authors_created', 0)}")
            print(f"   Authors updated: {result.get('authors_updated', 0)}")
            print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
            
            # Show import errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n   Import errors (first 5):")
                for error in errors[:5]:
                    print(f"     Row {error.get('row', 'N/A')}: {error.get('message', 'Unknown error')}")
    
    except Exception as e:
        print(f"   ❌ Error testing import: {e}")
    
    # Check specific articles after import
    print("\n📰 Step 4: Checking specific articles after import...")
    test_ids = ["5805", "6274", "7672", "15981"]
    
    for article_id in test_ids:
        try:
            response = requests.get(f"https://mcpress-chatbot-production.up.railway.app/api/books?search={article_id}&limit=1")
            if response.status_code == 200:
                books = response.json()
                if books:
                    book = books[0]
                    print(f"\n   Article {article_id}:")
                    print(f"     Filename: {book.get('filename')}")
                    print(f"     Title: {book.get('title', 'NO TITLE')}")
                    print(f"     Document Type: {book.get('document_type', 'book')}")
                    print(f"     Article URL: {book.get('article_url', 'NO URL')}")
                    print(f"     Authors: {len(book.get('authors', []))} authors")
                else:
                    print(f"   ❌ Article {article_id}: Not found")
        except Exception as e:
            print(f"   ❌ Article {article_id}: Error {e}")
    
    print("\n" + "="*60)
    print("📊 SUMMARY:")
    print("="*60)
    print("\nThis script will help identify:")
    print("1. Whether the Excel file has the right structure")
    print("2. Whether the validation endpoint works")
    print("3. Whether the import endpoint processes articles correctly")
    print("4. Whether articles are updated in the database")
    print("\nIf articles still show ID numbers, the issue is likely:")
    print("- Missing article titles in the Excel file")
    print("- Import not updating the 'title' column")
    print("- Frontend displaying filename instead of title")

if __name__ == "__main__":
    main()