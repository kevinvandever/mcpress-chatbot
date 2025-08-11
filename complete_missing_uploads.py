#!/usr/bin/env python3
"""
Complete uploads that need author information
"""

import requests
import time

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"

# PDFs that need author completion
PENDING_UPLOADS = [
    ("An Introduction to IBM Rational Application Developer.pdf", "Unknown Author"),
    ("IBM System i APIs at Work.pdf", "Bruce Vining and Craig Pelkie"),
    ("IBM i5-iSeries Primer.pdf", "Unknown Author"),
    ("Programming Portlets.pdf", "Ron Lynn and Joey Bernal"),
    ("The Modern RPG IV Language.pdf", "Robert Cozzi")
]

def complete_upload(filename, author):
    """Complete an upload with author information"""
    print(f"📝 Completing: {filename}")
    print(f"   Author: {author}")
    
    try:
        response = requests.post(
            f"{API_URL}/complete-upload",
            json={
                "filename": filename,
                "author": author
            },
            timeout=60
        )
        
        if response.status_code == 200:
            print(f"   ✅ Completed successfully!")
            return True
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 Completing Pending Uploads")
    print(f"📍 API: {API_URL}")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for filename, author in PENDING_UPLOADS:
        if complete_upload(filename, author):
            successful += 1
        else:
            failed += 1
        time.sleep(2)  # Small delay between requests
    
    print("\n" + "=" * 60)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    # Final verification
    print("\n🔍 Verifying final count...")
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            final_count = len(response.json()['documents'])
            print(f"📊 Total documents in system: {final_count}/115")
            if final_count == 115:
                print("🎉 ALL 115 DOCUMENTS SUCCESSFULLY UPLOADED!")
        else:
            print("❌ Could not verify final count")
    except Exception as e:
        print(f"❌ Error verifying: {e}")

if __name__ == "__main__":
    main()