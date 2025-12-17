#!/usr/bin/env python3
"""
Complete verification of frontend display after chat metadata enrichment fix.
Tests all requirements from task 5.3.
"""

import requests
import json
import sys
import time

# Railway backend URL
API_URL = "https://mcpress-chatbot-production.up.railway.app"

def test_specific_requirements():
    """Test specific requirements from task 5.3"""
    print("🎯 Verifying Frontend Display Requirements")
    print("=" * 60)
    
    # Test queries designed to return different types of content
    test_cases = [
        {
            "query": "Tell me about DB2 10 for z/OS upgrade",
            "description": "Books with MC Store URLs",
            "expected_type": "book"
        },
        {
            "query": "What are the latest IBM i articles?",
            "description": "Articles with article URLs", 
            "expected_type": "article"
        },
        {
            "query": "Show me RPG programming guides",
            "description": "Mixed content types",
            "expected_type": "mixed"
        }
    ]
    
    results = {
        "enriched_sources": 0,
        "total_sources": 0,
        "buy_buttons": 0,
        "read_buttons": 0,
        "author_links": 0,
        "unknown_authors": 0
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print("-" * 40)
        
        try:
            # Send chat request
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "message": test_case["query"],
                    "conversation_id": f"verify-{int(time.time())}-{i}",
                    "user_id": "verify-user"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                continue
            
            # Parse streaming response
            sources = None
            for line in response.text.strip().split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if data.get('type') == 'done' and 'sources' in data:
                            sources = data['sources']
                            break
                    except json.JSONDecodeError:
                        continue
            
            if not sources:
                print("❌ No sources found")
                continue
            
            print(f"✅ Retrieved {len(sources)} sources")
            results["total_sources"] += len(sources)
            
            # Analyze each source
            for j, source in enumerate(sources, 1):
                filename = source.get('filename', 'Unknown')
                author = source.get('author', 'Unknown')
                authors = source.get('authors', [])
                document_type = source.get('document_type', 'book')
                mc_press_url = source.get('mc_press_url', '')
                article_url = source.get('article_url')
                
                print(f"\n  📄 Source {j}: {filename}")
                
                # Check author enrichment (Requirement: sources show actual author names, not "Unknown")
                if author != 'Unknown':
                    print(f"    ✅ Author: {author}")
                    results["enriched_sources"] += 1
                else:
                    print(f"    ❌ Author: Unknown (not enriched)")
                    results["unknown_authors"] += 1
                
                # Check multi-author data and website links
                if authors:
                    print(f"    📝 Authors: {len(authors)} author(s)")
                    for author_obj in authors:
                        name = author_obj.get('name', 'Unknown')
                        site_url = author_obj.get('site_url')
                        
                        # Requirement: author names with site_url are clickable links
                        if site_url:
                            print(f"      🔗 {name} -> {site_url}")
                            results["author_links"] += 1
                        else:
                            print(f"      👤 {name} (no website)")
                
                # Check Buy buttons (Requirement: "Buy" buttons appear for books with mc_press_url)
                if document_type == 'book' and mc_press_url:
                    print(f"    🛒 Buy button: {mc_press_url}")
                    results["buy_buttons"] += 1
                
                # Check Read buttons (Requirement: "Read" buttons appear for articles with article_url)
                elif document_type == 'article' and article_url:
                    print(f"    📖 Read button: {article_url}")
                    results["read_buttons"] += 1
                
                print(f"    📋 Type: {document_type}")
                
                # Only show first 3 sources to avoid clutter
                if j >= 3:
                    if len(sources) > 3:
                        print(f"    ... and {len(sources) - 3} more sources")
                    break
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Final verification summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    print(f"Total sources analyzed: {results['total_sources']}")
    print(f"Enriched sources (not 'Unknown'): {results['enriched_sources']}")
    print(f"Unknown authors: {results['unknown_authors']}")
    print(f"Buy buttons found: {results['buy_buttons']}")
    print(f"Read buttons found: {results['read_buttons']}")
    print(f"Author website links: {results['author_links']}")
    
    # Check requirements compliance
    print("\n🎯 REQUIREMENTS VERIFICATION:")
    
    # Requirement: sources show actual author names (not "Unknown")
    if results["enriched_sources"] > 0:
        print("✅ Sources show actual author names (not 'Unknown')")
    else:
        print("❌ No enriched author names found")
    
    # Requirement: "Buy" buttons appear for books with mc_press_url
    if results["buy_buttons"] > 0:
        print("✅ 'Buy' buttons appear for books with MC Store URLs")
    else:
        print("⚠️  No 'Buy' buttons found (may be expected if no books have MC Store URLs)")
    
    # Requirement: "Read" buttons appear for articles with article_url
    if results["read_buttons"] > 0:
        print("✅ 'Read' buttons appear for articles with article URLs")
    else:
        print("⚠️  No 'Read' buttons found (may be expected if no articles returned)")
    
    # Requirement: author names with site_url are clickable links
    if results["author_links"] > 0:
        print("✅ Author names with website URLs are clickable links")
    else:
        print("⚠️  No author website links found (may be expected if authors don't have websites)")
    
    # Overall assessment
    enrichment_rate = results["enriched_sources"] / max(results["total_sources"], 1) * 100
    print(f"\n📈 Enrichment Success Rate: {enrichment_rate:.1f}%")
    
    if enrichment_rate >= 80:
        print("🎉 FRONTEND DISPLAY VERIFICATION: PASSED")
        print("The chat metadata enrichment fix is working correctly!")
    elif enrichment_rate >= 50:
        print("⚠️  FRONTEND DISPLAY VERIFICATION: PARTIAL")
        print("Some enrichment is working, but there may be issues.")
    else:
        print("❌ FRONTEND DISPLAY VERIFICATION: FAILED")
        print("Enrichment is not working properly.")
    
    return results

def test_frontend_component_behavior():
    """Test that the frontend component handles the enriched data correctly"""
    print("\n" + "=" * 60)
    print("🖥️  FRONTEND COMPONENT BEHAVIOR TEST")
    print("=" * 60)
    
    # Test with a single query to get detailed component behavior
    test_query = "Tell me about DB2 programming"
    
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": test_query,
                "conversation_id": f"component-test-{int(time.time())}",
                "user_id": "component-test"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return
        
        # Parse response
        sources = None
        for line in response.text.strip().split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'done' and 'sources' in data:
                        sources = data['sources']
                        break
                except json.JSONDecodeError:
                    continue
        
        if not sources:
            print("❌ No sources to test component behavior")
            return
        
        print(f"📋 Testing component behavior with {len(sources)} sources")
        
        # Simulate what CompactSources.tsx does
        grouped_sources = {}
        for source in sources:
            filename = source['filename'].replace('.pdf', '')
            if filename not in grouped_sources:
                grouped_sources[filename] = {
                    'pages': [],
                    'author': source.get('author', 'Unknown Author'),
                    'mc_press_url': source.get('mc_press_url', ''),
                    'article_url': source.get('article_url', ''),
                    'document_type': source.get('document_type', 'book'),
                    'authors': source.get('authors', [])
                }
            grouped_sources[filename]['pages'].append(source.get('page', 'N/A'))
        
        print(f"\n📊 Component will group into {len(grouped_sources)} unique documents:")
        
        for filename, data in list(grouped_sources.items())[:3]:  # Show first 3
            print(f"\n  📖 {filename}")
            print(f"    Author display: {data['author']}")
            print(f"    Authors array: {len(data['authors'])} authors")
            
            # Check what buttons will be shown
            if data['document_type'] == 'article' and data['article_url']:
                print(f"    🟢 Will show: Green 'Read' button -> {data['article_url']}")
            elif data['document_type'] == 'book' and data['mc_press_url']:
                print(f"    🔵 Will show: Blue 'Buy' button -> {data['mc_press_url']}")
            else:
                print(f"    ⚪ Will show: Disabled button (no URL available)")
            
            # Check author links
            for author in data['authors']:
                if author.get('site_url'):
                    print(f"    🔗 Will show: Clickable link for {author['name']} -> {author['site_url']}")
                else:
                    print(f"    📝 Will show: Plain text for {author['name']}")
        
        print("\n✅ Component behavior test complete")
        
    except Exception as e:
        print(f"❌ Component behavior test failed: {e}")

if __name__ == "__main__":
    # Run comprehensive verification
    results = test_specific_requirements()
    
    # Test frontend component behavior
    test_frontend_component_behavior()
    
    print("\n" + "=" * 60)
    print("🏁 COMPLETE FRONTEND VERIFICATION FINISHED")
    print("=" * 60)
    print("\n📋 Manual Browser Testing Instructions:")
    print("1. Open: https://mcpress-chatbot.netlify.app")
    print("2. Submit query: 'Tell me about DB2 programming'")
    print("3. Verify in the References section:")
    print("   ✓ Author names are NOT 'Unknown'")
    print("   ✓ Blue 'Buy' buttons appear for books")
    print("   ✓ Green 'Read' buttons appear for articles")
    print("   ✓ Author names with websites are clickable")
    print("   ✓ Multiple authors are displayed correctly")
    print("\n🎯 Task 5.3 verification complete!")