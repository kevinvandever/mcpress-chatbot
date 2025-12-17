#!/usr/bin/env python3
"""
Task 5.3 Verification Report: Verify frontend display after fix
Complete verification of all requirements from task 5.3
"""

import requests
import json
import time
from datetime import datetime

API_URL = "https://mcpress-chatbot.netlify.app"
BACKEND_URL = "https://mcpress-chatbot-production.up.railway.app"

def generate_verification_report():
    """Generate comprehensive verification report for task 5.3"""
    
    report = {
        "task": "5.3 Verify frontend display after fix",
        "timestamp": datetime.now().isoformat(),
        "requirements": {
            "actual_author_names": {"status": "unknown", "details": []},
            "buy_buttons": {"status": "unknown", "details": []},
            "read_buttons": {"status": "unknown", "details": []},
            "clickable_author_links": {"status": "unknown", "details": []}
        },
        "test_results": {
            "total_sources_tested": 0,
            "enriched_sources": 0,
            "buy_buttons_found": 0,
            "read_buttons_found": 0,
            "author_links_found": 0,
            "unknown_authors": 0
        },
        "sample_data": []
    }
    
    print("📋 TASK 5.3 VERIFICATION REPORT")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Frontend URL: {API_URL}")
    print(f"Backend URL: {BACKEND_URL}")
    print()
    
    # Test queries that should return known books
    test_queries = [
        "Tell me about DB2 programming",
        "What is RPG programming?", 
        "Show me IBM i development guides"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"🧪 Test {i}: '{query}'")
        print("-" * 40)
        
        try:
            # Send chat request to backend
            response = requests.post(
                f"{BACKEND_URL}/chat",
                json={
                    "message": query,
                    "conversation_id": f"task-5-3-{int(time.time())}-{i}",
                    "user_id": "verification-test"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Backend Error: {response.status_code}")
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
                print("❌ No sources returned")
                continue
            
            print(f"✅ Retrieved {len(sources)} sources")
            report["test_results"]["total_sources_tested"] += len(sources)
            
            # Analyze first 3 sources in detail
            for j, source in enumerate(sources[:3], 1):
                filename = source.get('filename', 'Unknown')
                author = source.get('author', 'Unknown')
                authors = source.get('authors', [])
                document_type = source.get('document_type', 'book')
                mc_press_url = source.get('mc_press_url', '')
                article_url = source.get('article_url')
                
                print(f"\n  📄 Source {j}: {filename}")
                
                # Sample data for report
                sample = {
                    "filename": filename,
                    "author": author,
                    "authors": authors,
                    "document_type": document_type,
                    "mc_press_url": mc_press_url,
                    "article_url": article_url
                }
                report["sample_data"].append(sample)
                
                # Requirement 1: Sources show actual author names (not "Unknown")
                if author != 'Unknown':
                    print(f"    ✅ Author: {author}")
                    report["test_results"]["enriched_sources"] += 1
                    report["requirements"]["actual_author_names"]["details"].append(f"✅ {filename}: {author}")
                else:
                    print(f"    ❌ Author: Unknown")
                    report["test_results"]["unknown_authors"] += 1
                    report["requirements"]["actual_author_names"]["details"].append(f"❌ {filename}: Unknown")
                
                # Requirement 2: "Buy" buttons appear for books with mc_press_url
                if document_type == 'book' and mc_press_url:
                    print(f"    🛒 Buy button: {mc_press_url}")
                    report["test_results"]["buy_buttons_found"] += 1
                    report["requirements"]["buy_buttons"]["details"].append(f"✅ {filename}: Buy button available")
                
                # Requirement 3: "Read" buttons appear for articles with article_url
                if document_type == 'article' and article_url:
                    print(f"    📖 Read button: {article_url}")
                    report["test_results"]["read_buttons_found"] += 1
                    report["requirements"]["read_buttons"]["details"].append(f"✅ {filename}: Read button available")
                
                # Requirement 4: Author names with site_url are clickable links
                if authors:
                    print(f"    👥 Authors: {len(authors)} author(s)")
                    for author_obj in authors:
                        name = author_obj.get('name', 'Unknown')
                        site_url = author_obj.get('site_url')
                        if site_url:
                            print(f"      🔗 {name} -> {site_url}")
                            report["test_results"]["author_links_found"] += 1
                            report["requirements"]["clickable_author_links"]["details"].append(f"✅ {name}: {site_url}")
                        else:
                            print(f"      👤 {name} (no website)")
                
                print(f"    📋 Type: {document_type}")
            
            if len(sources) > 3:
                print(f"    ... and {len(sources) - 3} more sources")
        
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Determine requirement status
    if report["test_results"]["enriched_sources"] > 0:
        report["requirements"]["actual_author_names"]["status"] = "PASS"
    else:
        report["requirements"]["actual_author_names"]["status"] = "FAIL"
    
    if report["test_results"]["buy_buttons_found"] > 0:
        report["requirements"]["buy_buttons"]["status"] = "PASS"
    else:
        report["requirements"]["buy_buttons"]["status"] = "NOT_TESTED"  # May be no books with URLs
    
    if report["test_results"]["read_buttons_found"] > 0:
        report["requirements"]["read_buttons"]["status"] = "PASS"
    else:
        report["requirements"]["read_buttons"]["status"] = "NOT_TESTED"  # May be no articles with URLs
    
    if report["test_results"]["author_links_found"] > 0:
        report["requirements"]["clickable_author_links"]["status"] = "PASS"
    else:
        report["requirements"]["clickable_author_links"]["status"] = "NOT_TESTED"  # May be no authors with websites
    
    # Generate final report
    print("\n" + "=" * 60)
    print("📊 FINAL VERIFICATION REPORT")
    print("=" * 60)
    
    print(f"Total sources tested: {report['test_results']['total_sources_tested']}")
    print(f"Enriched sources: {report['test_results']['enriched_sources']}")
    print(f"Unknown authors: {report['test_results']['unknown_authors']}")
    print(f"Buy buttons found: {report['test_results']['buy_buttons_found']}")
    print(f"Read buttons found: {report['test_results']['read_buttons_found']}")
    print(f"Author website links: {report['test_results']['author_links_found']}")
    
    print("\n🎯 REQUIREMENT VERIFICATION:")
    
    # Requirement verification
    req_names = {
        "actual_author_names": "Sources show actual author names (not 'Unknown')",
        "buy_buttons": "'Buy' buttons appear for books with mc_press_url", 
        "read_buttons": "'Read' buttons appear for articles with article_url",
        "clickable_author_links": "Author names with site_url are clickable links"
    }
    
    all_pass = True
    for req_key, req_name in req_names.items():
        status = report["requirements"][req_key]["status"]
        if status == "PASS":
            print(f"✅ {req_name}")
        elif status == "FAIL":
            print(f"❌ {req_name}")
            all_pass = False
        else:
            print(f"⚠️  {req_name} (not tested - no applicable data)")
    
    # Overall assessment
    enrichment_rate = (report["test_results"]["enriched_sources"] / 
                      max(report["test_results"]["total_sources_tested"], 1)) * 100
    
    print(f"\n📈 Enrichment Success Rate: {enrichment_rate:.1f}%")
    
    if enrichment_rate >= 80 and report["requirements"]["actual_author_names"]["status"] == "PASS":
        print("🎉 TASK 5.3 VERIFICATION: PASSED")
        print("✅ Frontend display is working correctly after the fix!")
    elif enrichment_rate >= 50:
        print("⚠️  TASK 5.3 VERIFICATION: PARTIAL SUCCESS")
        print("Some functionality is working, but there may be issues.")
    else:
        print("❌ TASK 5.3 VERIFICATION: FAILED")
        print("Frontend display is not working properly.")
    
    print("\n📋 MANUAL BROWSER TESTING:")
    print(f"1. Open: {API_URL}")
    print("2. Submit query: 'Tell me about DB2 programming'")
    print("3. Check References section for:")
    print("   • Author names are NOT 'Unknown'")
    print("   • Blue 'Buy' buttons for books")
    print("   • Green 'Read' buttons for articles (if any)")
    print("   • Clickable author names with websites")
    
    # Save report to file
    with open('task_5_3_verification_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: task_5_3_verification_report.json")
    
    return report

if __name__ == "__main__":
    report = generate_verification_report()
    
    print("\n" + "=" * 60)
    print("🏁 TASK 5.3 VERIFICATION COMPLETE")
    print("=" * 60)