#!/usr/bin/env python3
"""
Simple test to check if author corrections worked
"""
import requests
import json

def test_chat_streaming():
    """Test the streaming chat endpoint"""
    
    api_url = "https://mcpress-chatbot-production.up.railway.app"
    
    test_queries = [
        "Complete CL programming",
        "Subfiles RPG", 
        "Control Language Programming for IBM i"
    ]
    
    print("🔍 Testing author corrections via streaming chat...\n")
    
    for query in test_queries:
        print(f"Testing: {query}")
        
        try:
            response = requests.post(
                f"{api_url}/chat",
                json={"message": query},
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse streaming response
                sources_found = []
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                if data.get('type') == 'done' and 'sources' in data:
                                    sources_found = data.get('sources', [])
                                    break  # We found sources, that's all we need
                            except json.JSONDecodeError:
                                continue
                
                # Check sources for correct authors
                if sources_found:
                    print(f"  📚 Found {len(sources_found)} sources")
                    for source in sources_found[:3]:  # Show first 3
                        title = source.get('title', 'Unknown')
                        authors = source.get('authors', [])
                        author_names = [author.get('name', '') for author in authors]
                        print(f"    📖 {title}")
                        print(f"    👥 Authors: {', '.join(author_names) if author_names else 'No authors'}")
                        
                        # Check for suspicious authors
                        suspicious = ['admin', 'annegrubb', 'USA Sales', 'Unknown']
                        for sus in suspicious:
                            if any(sus.lower() in name.lower() for name in author_names):
                                print(f"    ❌ Still has suspicious author: {sus}")
                        
                        # Check for expected authors
                        if 'Complete CL' in title and 'Ted Holt' in author_names:
                            print(f"    ✅ Complete CL has Ted Holt!")
                        elif 'Subfiles' in title and 'Kevin Vandever' in author_names:
                            print(f"    ✅ Subfiles has Kevin Vandever!")
                        elif 'Control Language Programming' in title:
                            expected = ['Jim Buck', 'Bryan Meyers', 'Dan Riehl']
                            if all(author in author_names for author in expected):
                                print(f"    ✅ Control Language Programming has all 3 authors!")
                else:
                    print(f"  ❌ No sources found")
                    
            else:
                print(f"  ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        print()

if __name__ == "__main__":
    test_chat_streaming()