#!/usr/bin/env python3
"""
Add author website URLs to make author names clickable in chat
"""

import requests
import json

def add_author_website(author_name, website_url):
    """Add website URL to an author"""
    base_url = "https://mcpress-chatbot-production.up.railway.app"
    
    # First, find the author
    search_response = requests.get(f"{base_url}/api/authors/search?q={author_name}&limit=1")
    if search_response.status_code != 200:
        print(f"❌ Error searching for {author_name}: {search_response.status_code}")
        return False
    
    authors = search_response.json()
    if not authors:
        print(f"❌ Author not found: {author_name}")
        return False
    
    author = authors[0]
    author_id = author['id']
    
    # Update the author with website URL
    update_response = requests.patch(
        f"{base_url}/api/authors/{author_id}",
        json={"site_url": website_url},
        headers={"Content-Type": "application/json"}
    )
    
    if update_response.status_code == 200:
        print(f"✅ Added website for {author_name}: {website_url}")
        return True
    else:
        print(f"❌ Error updating {author_name}: {update_response.status_code}")
        return False

def main():
    print("🔗 Adding author website URLs...")
    
    # Common MC Press authors and their websites
    # You can research and add more author websites here
    author_websites = {
        "Ted Holt": "https://tedholt.com",  # Example - verify this URL
        "Kevin Vandever": "https://kevinvandever.com",  # Example - verify this URL  
        "Jim Buck": "https://jimbuck.com",  # Example - verify this URL
        "Dave Beulke": "https://davebeulke.com",  # Example - verify this URL
        "Carol Woodbury": "https://carolwoodbury.com",  # Example - verify this URL
        "Bob Cozzi": "https://bobcozzi.com",  # Example - verify this URL
        "Rafael Victoria-Pereira": "https://rafaelvp.com",  # Example - verify this URL
    }
    
    print("⚠️  WARNING: These are example URLs - please verify they are correct before running!")
    print("You should research the actual websites for these authors.")
    print()
    
    for author_name, website_url in author_websites.items():
        print(f"Would add: {author_name} -> {website_url}")
    
    print()
    print("To actually add these URLs, uncomment the lines below and verify the URLs first:")
    print()
    
    # Uncomment these lines after verifying the URLs:
    # for author_name, website_url in author_websites.items():
    #     add_author_website(author_name, website_url)

if __name__ == "__main__":
    main()