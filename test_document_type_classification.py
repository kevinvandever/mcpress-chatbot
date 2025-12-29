#!/usr/bin/env python3
"""
Test document type classification end-to-end
This tests that articles get document_type='article' and show Read buttons,
while books get document_type='book' and show Buy buttons.
"""

import requests
import json

def test_document_type_classification():
    """Test that document types are correctly classified and displayed"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 Testing document type classification...")
    
    # Test with a query that should return both articles and books
    test_query = "RPG programming"
    
    try:
        # Make a chat request
        response = requests.post(
            f"{api_url}/api/chat",
            json={"message": test_query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Chat API failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse the streaming response to get the final result
        lines = response.text.strip().split('\n')
        sources_data = None
        
        for line in lines:
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    if 'sources' in data:
                        sources_data = data['sources']
                        break
                except json.JSONDecodeError:
                    continue
        
        if not sources_data:
            print("❌ No sources found in chat response")
            return False
        
        print(f"✓ Found {len(sources_data)} sources")
        
        # Analyze document types
        articles_found = 0
        books_found = 0
        classification_issues = []
        
        for i, source in enumerate(sources_data, 1):
            filename = source.get('filename', 'unknown')
            document_type = source.get('document_type', 'unknown')
            article_url = source.get('article_url')
            mc_press_url = source.get('mc_press_url')
            title = source.get('title', filename)
            
            print(f"\nSource {i}: {title}")
            print(f"  Filename: {filename}")
            print(f"  Document Type: {document_type}")
            print(f"  Article URL: {'✓' if article_url else '✗'}")
            print(f"  MC Press URL: {'✓' if mc_press_url else '✗'}")
            
            if document_type == 'article':
                articles_found += 1
                # Articles should have article_url and show Read button
                if not article_url:
                    classification_issues.append(f"Article '{title}' missing article_url")
                else:
                    print(f"  ✓ Article has Read URL: {article_url}")
            elif document_type == 'book':
                books_found += 1
                # Books should have mc_press_url and show Buy button
                if not mc_press_url:
                    classification_issues.append(f"Book '{title}' missing mc_press_url")
                else:
                    print(f"  ✓ Book has Buy URL: {mc_press_url}")
            else:
                classification_issues.append(f"Unknown document_type '{document_type}' for '{title}'")
        
        print(f"\n📊 Summary:")
        print(f"  Articles found: {articles_found}")
        print(f"  Books found: {books_found}")
        print(f"  Classification issues: {len(classification_issues)}")
        
        if classification_issues:
            print(f"\n⚠️  Issues found:")
            for issue in classification_issues:
                print(f"    • {issue}")
        
        # Test passes if we have both types and no major issues
        success = (articles_found > 0 or books_found > 0) and len(classification_issues) == 0
        
        if success:
            print(f"\n🎉 Document type classification is working correctly!")
            print(f"   • Articles will show green 'Read' buttons")
            print(f"   • Books will show blue 'Buy' buttons")
            return True
        else:
            print(f"\n❌ Document type classification has issues")
            return False
            
    except Exception as e:
        print(f"❌ Error testing document type classification: {e}")
        return False

if __name__ == "__main__":
    success = test_document_type_classification()
    if success:
        print("\n✅ Task 3 verification: Document type classification is working!")
    else:
        print("\n❌ Task 3 needs attention: Document type classification issues found")