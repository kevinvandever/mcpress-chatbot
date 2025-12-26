#!/usr/bin/env python3
"""
Examine the Excel file structure to identify the title column
"""

import requests

def main():
    print("🔍 Examining Excel file structure...")
    
    # Use the validation endpoint to see the Excel structure
    try:
        file_path = ".kiro/specs/multi-author-metadata-enhancement/data/article-links.xlsm"
        api_url = "https://mcpress-chatbot-production.up.railway.app/api/excel/validate"
        
        with open(file_path, 'rb') as f:
            files = {'file': ('article-links.xlsm', f)}
            data = {'file_type': 'article'}
            
            response = requests.post(api_url, files=files, data=data)
            result = response.json()
            
            print(f"   Validation result: {result.get('valid', False)}")
            
            # Show preview data to understand structure
            preview_rows = result.get('preview_rows', [])
            if preview_rows:
                print(f"\n   Excel file structure analysis:")
                print(f"   Currently mapped columns:")
                print(f"   - A (0): id")
                print(f"   - H (7): feature_article") 
                print(f"   - J (9): author")
                print(f"   - K (10): article_url")
                print(f"   - L (11): author_url")
                
                print(f"\n   Sample data from first row:")
                if preview_rows:
                    data = preview_rows[0].get('data', {})
                    print(f"   - ID: {data.get('id')}")
                    print(f"   - Feature Article: {data.get('feature_article')}")
                    print(f"   - Author: {data.get('author')}")
                    print(f"   - Article URL: {data.get('article_url')}")
                    print(f"   - Author URL: {data.get('author_url')}")
                
                print(f"\n   🔍 MISSING: Article Title Column!")
                print(f"   The Excel file likely has a title column that's not being imported.")
                print(f"   Common title column positions:")
                print(f"   - Column B (1): Often contains titles")
                print(f"   - Column C (2): Sometimes titles")
                print(f"   - Column D (3): Could be titles")
                print(f"   - Column E (4): Possible title location")
                print(f"   - Column F (5): Another possibility")
                print(f"   - Column G (6): Could be titles")
                print(f"   - Column I (8): Between feature_article and author")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "="*60)
    print(f"📊 SOLUTION:")
    print(f"="*60)
    print(f"\nTo fix the article display issue:")
    print(f"1. Identify which column contains article titles in the Excel file")
    print(f"2. Update the Excel import service to map that column")
    print(f"3. Update the import logic to set the 'title' column in the database")
    print(f"4. Re-run the article metadata import")
    print(f"\nThe articles are currently showing ID numbers because:")
    print(f"- The 'title' column in the database is empty or contains filenames")
    print(f"- The frontend displays the filename when title is missing")
    print(f"- The Excel import isn't updating the title column")

if __name__ == "__main__":
    main()