#!/usr/bin/env python3
"""
Simple script to check Excel column names
This will help us see what the actual column names are in the file
"""

import requests
import json

def check_excel_columns():
    """Check what columns are in the Excel file by examining the validation response"""
    
    # The validation response shows us the actual data structure
    # Let's make a request and examine the preview data more carefully
    
    url = "https://mcpress-chatbot-production.up.railway.app/api/excel/validate"
    
    # Try with the original Excel file
    files = {
        'file': ('MC Press Books - URL-Title-Author.xlsx', 
                open('.kiro/specs/multi-author-metadata-enhancement/data/MC Press Books - URL-Title-Author.xlsx', 'rb'))
    }
    data = {'file_type': 'book'}
    
    try:
        response = requests.post(url, files=files, data=data)
        result = response.json()
        
        print("=== EXCEL FILE ANALYSIS ===")
        print(f"Valid: {result.get('valid', False)}")
        print(f"Errors: {len(result.get('errors', []))}")
        
        print("\n=== PREVIEW DATA ===")
        preview_rows = result.get('preview_rows', [])
        if preview_rows:
            first_row = preview_rows[0]
            print(f"First row data keys: {list(first_row.get('data', {}).keys())}")
            
            # Show first few rows of actual data
            for i, row in enumerate(preview_rows[:3]):
                print(f"\nRow {i+1}:")
                for key, value in row.get('data', {}).items():
                    print(f"  {key}: '{value}'")
        
        print("\n=== ERRORS ===")
        for error in result.get('errors', []):
            print(f"  {error}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        files['file'][1].close()

if __name__ == "__main__":
    check_excel_columns()