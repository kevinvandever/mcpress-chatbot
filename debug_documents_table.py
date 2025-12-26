#!/usr/bin/env python3
"""
Direct check of the documents table to see what's really in there
"""

import requests

def main():
    print("🔍 Checking documents table directly...")
    
    # Test a simple chat query to see what sources come back
    print("\n1. Testing chat to see what sources are returned...")
    
    try:
        response = requests.post(
            "https://mcpress-chatbot-production.up.railway.app/chat",
            headers={"Content-Type": "application/json"},
            json={"message": "RPG programming", "conversation_id": "debug", "user_id": "debug"},
            stream=True
        )
        
        sources = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        import json
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        if data.get('type') == 'done':
                            sources = data.get('sources', [])
                            break
                    except:
                        continue
        
        print(f"Found {len(sources)} sources in chat response:")
        
        numeric_sources = []
        for source in sources:
            filename = source.get('filename', '')
            if filename.replace('.pdf', '').isdigit():
                numeric_sources.append({
                    'filename': filename,
                    'author': source.get('author', 'Unknown'),
                    'document_type': source.get('document_type', 'unknown'),
                    'article_url': source.get('article_url'),
                    'authors': source.get('authors', [])
                })
        
        print(f"\nFound {len(numeric_sources)} numeric filename sources:")
        for source in numeric_sources[:5]:
            print(f"  {source['filename']} - {source['author']} - {source['document_type']}")
            print(f"    Article URL: {source['article_url']}")
            print(f"    Authors: {source['authors']}")
        
        # Now let's see if we can find these in the books table via API
        print(f"\n2. Checking if these files exist in books table...")
        
        for source in numeric_sources[:3]:
            filename = source['filename']
            article_id = filename.replace('.pdf', '')
            
            print(f"\nSearching for {filename} (ID: {article_id})...")
            
            # Try different search patterns
            patterns = [article_id, filename, f"filename:{filename}"]
            
            found = False
            for pattern in patterns:
                try:
                    response = requests.get(f"https://mcpress-chatbot-production.up.railway.app/api/books?search={pattern}&limit=5")
                    result = response.json()
                    
                    if result.get('total', 0) > 0:
                        book = result['books'][0]
                        print(f"  ✅ Found with pattern '{pattern}':")
                        print(f"     ID: {book['id']}")
                        print(f"     Filename: {book['filename']}")
                        print(f"     Title: {book['title']}")
                        print(f"     Document Type: {book['document_type']}")
                        found = True
                        break
                except Exception as e:
                    print(f"  Error with pattern '{pattern}': {e}")
            
            if not found:
                print(f"  ❌ Not found in books API with any pattern")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()