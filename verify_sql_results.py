#!/usr/bin/env python3
"""
Verify the author corrections were applied successfully
"""
import requests
import json

def test_chatbot_authors():
    """Test the chatbot to see if authors are now correct"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    test_queries = [
        {
            "query": "Complete CL programming",
            "expected_author": "Ted Holt",
            "book_title": "Complete CL: Sixth Edition"
        },
        {
            "query": "Subfiles RPG",
            "expected_author": "Kevin Vandever", 
            "book_title": "Subfiles in Free-Format RPG"
        },
        {
            "query": "Control Language Programming for IBM i",
            "expected_authors": ["Jim Buck", "Bryan Meyers", "Dan Riehl"],
            "book_title": "Control Language Programming for IBM i"
        }
    ]
    
    print("🔍 Testing chatbot with corrected authors...\n")
    
    for test in test_queries:
        print(f"Testing: {test['query']}")
        
        try:
            # Send chat request
            response = requests.post(
                f"{api_url}/chat",
                json={"message": test["query"]},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])
                
                # Look for the expected book
                found_book = False
                correct_authors = False
                
                for source in sources:
                    if test["book_title"].lower() in source.get("title", "").lower():
                        found_book = True
                        authors = source.get("authors", [])
                        author_names = [author.get("name", "") for author in authors]
                        
                        print(f"  📖 Found: {source.get('title')}")
                        print(f"  👥 Authors: {', '.join(author_names)}")
                        
                        if "expected_authors" in test:
                            # Multi-author book
                            if all(author in author_names for author in test["expected_authors"]):
                                correct_authors = True
                                print(f"  ✅ All expected authors found!")
                            else:
                                print(f"  ❌ Missing authors. Expected: {', '.join(test['expected_authors'])}")
                        else:
                            # Single author book
                            if test["expected_author"] in author_names:
                                correct_authors = True
                                print(f"  ✅ Correct author found!")
                            else:
                                print(f"  ❌ Wrong author. Expected: {test['expected_author']}")
                        break
                
                if not found_book:
                    print(f"  ❌ Book not found in results")
                elif not correct_authors:
                    print(f"  ❌ Authors still incorrect")
                    
            else:
                print(f"  ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        print()

def check_suspicious_authors():
    """Check if suspicious authors are still in the database"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    print("🔍 Checking for suspicious authors...\n")
    
    suspicious_queries = [
        "annegrubb",
        "admin", 
        "USA Sales",
        "Unknown"
    ]
    
    for query in suspicious_queries:
        try:
            response = requests.post(
                f"{api_url}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])
                
                suspicious_found = False
                for source in sources:
                    authors = source.get("authors", [])
                    for author in authors:
                        if query.lower() in author.get("name", "").lower():
                            suspicious_found = True
                            print(f"  ❌ Still found '{query}' as author in: {source.get('title')}")
                
                if not suspicious_found:
                    print(f"  ✅ No books found with author '{query}'")
                    
        except Exception as e:
            print(f"  ❌ Error checking '{query}': {e}")
    
    print()

def main():
    print("=" * 60)
    print("🧪 AUTHOR CORRECTIONS VERIFICATION")
    print("=" * 60)
    print()
    
    # Test specific books
    test_chatbot_authors()
    
    # Check for suspicious authors
    check_suspicious_authors()
    
    print("=" * 60)
    print("✅ Verification complete!")
    print()
    print("If you see correct authors above, the fix worked! 🎉")
    print("If not, we may need to debug further.")
    print("=" * 60)

if __name__ == "__main__":
    main()