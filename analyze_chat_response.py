#!/usr/bin/env python3
"""
Analyze the chat response to extract sources and check enrichment status.
"""

import requests
import json
import re

# Railway production URL
API_URL = "https://mcpress-chatbot-production.up.railway.app"

def extract_sources_from_response(response_text):
    """Extract sources from the streaming response"""
    sources = []
    
    # Look for sources data in the "done" event
    lines = response_text.split('\n')
    for line in lines:
        if line.startswith('data: ') and '"type": "done"' in line:
            try:
                # Extract JSON from the data line
                json_str = line[6:]  # Remove 'data: ' prefix
                data = json.loads(json_str)
                if data.get('type') == 'done':
                    sources = data.get('sources', [])
                    break
            except json.JSONDecodeError:
                continue
    
    return sources

def analyze_enrichment_status(sources):
    """Analyze sources to check enrichment status"""
    print(f"📊 Found {len(sources)} sources")
    print("=" * 50)
    
    enriched_count = 0
    unknown_author_count = 0
    
    for i, source in enumerate(sources, 1):
        filename = source.get('filename', 'Unknown')
        author = source.get('author', 'Unknown')
        mc_press_url = source.get('mc_press_url', '')
        article_url = source.get('article_url')
        document_type = source.get('document_type', 'book')
        authors_list = source.get('authors', [])
        
        print(f"📄 Source {i}: {filename}")
        print(f"   👤 Author: {author}")
        print(f"   🔗 MC Press URL: {mc_press_url}")
        print(f"   📰 Article URL: {article_url}")
        print(f"   📚 Document Type: {document_type}")
        print(f"   👥 Authors List: {len(authors_list)} authors")
        
        if authors_list:
            for j, auth in enumerate(authors_list):
                print(f"      {j+1}. {auth.get('name', 'Unknown')} (site: {auth.get('site_url', 'None')})")
        
        # Check enrichment status
        if author != "Unknown" and (mc_press_url or article_url or authors_list):
            enriched_count += 1
            print(f"   ✅ ENRICHED")
        else:
            print(f"   ❌ NOT ENRICHED")
            if author == "Unknown":
                unknown_author_count += 1
        
        print()
    
    print("📈 ENRICHMENT SUMMARY:")
    print(f"   ✅ Enriched sources: {enriched_count}/{len(sources)}")
    print(f"   ❌ Unknown authors: {unknown_author_count}/{len(sources)}")
    print(f"   📊 Enrichment rate: {(enriched_count/len(sources)*100):.1f}%" if sources else "0%")

def test_and_analyze():
    """Submit chat query and analyze the response"""
    print("🔍 Testing DB2 query and analyzing enrichment...")
    
    chat_data = {
        "message": "Tell me about DB2",
        "conversation_id": "enrichment-analysis"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json=chat_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            print("✅ Chat request successful")
            
            # Extract sources from response
            sources = extract_sources_from_response(response.text)
            
            if sources:
                analyze_enrichment_status(sources)
            else:
                print("❌ No sources found in response")
                print("🔍 Looking for sources pattern in response...")
                if '"type": "done"' in response.text:
                    print("✅ Done event found - checking for sources...")
                    # Try to find the done event manually
                    lines = response.text.split('\n')
                    for line in lines:
                        if '"type": "done"' in line:
                            print(f"📄 Done event: {line[:200]}...")
                            break
                else:
                    print("❌ No done event found")
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_and_analyze()