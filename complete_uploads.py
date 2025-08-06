#!/usr/bin/env python3
"""
Complete pending uploads that are stuck waiting for author metadata
"""

import requests
import json
import time

API_URL = "https://mcpress-chatbot-production.up.railway.app"

def get_pending_files():
    """Find all files stuck in 'needs_metadata' state"""
    try:
        # This is a hack - we'll try some recent batch IDs to find pending files
        pending_files = []
        
        # Try recent batch IDs (last hour)
        current_time = int(time.time())
        for i in range(60):  # Check last 60 batches
            batch_id = f"batch_{current_time - i}"
            try:
                response = requests.get(f"{API_URL}/batch-upload/status/{batch_id}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    files_status = data.get('files_status', {})
                    
                    for filename, status_info in files_status.items():
                        if status_info.get('status') == 'needs_metadata':
                            pending_files.append(filename)
                            print(f"Found pending file: {filename}")
            except:
                continue
        
        return list(set(pending_files))  # Remove duplicates
    except Exception as e:
        print(f"Error finding pending files: {e}")
        return []

def complete_upload(filename, author="Unknown Author"):
    """Complete an upload by providing author metadata"""
    try:
        data = {
            "filename": filename,
            "author": author,
            "mc_press_url": None
        }
        
        response = requests.post(f"{API_URL}/complete-upload", 
                               json=data, 
                               headers={'Content-Type': 'application/json'},
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Completed: {filename}")
            print(f"   Result: {result.get('message', 'Success')}")
            return True
        else:
            print(f"❌ Failed to complete {filename}: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error completing {filename}: {e}")
        return False

def main():
    print("🔧 Complete Pending Uploads")
    print("="*50)
    print("This script completes uploads stuck waiting for author metadata")
    
    # Get current count
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        if response.status_code == 200:
            initial_count = len(response.json()['documents'])
            print(f"📊 Current document count: {initial_count}/113")
        else:
            initial_count = None
            print("❌ Could not get current document count")
    except:
        initial_count = None
        print("❌ Could not connect to get document count")
    
    # Since we can't easily find pending files, let's try to complete
    # uploads for the files we know should be uploaded
    target_files = [
        "IBM i5-iSeries Primer.pdf",
        "Advanced Java EE Development for Rational Application Developer 7.5.pdf", 
        "The Modern RPG IV Language.pdf",
        "IBM System i APIs at Work.pdf",
        "You Want to Do What with PHP?.pdf",
        "IBM DB2 for z-OS- The Database for Gaining a Competitive Advantage!.pdf",
        "An Introduction to IBM Rational Application Developer.pdf",
        "Programming Portlets.pdf"
    ]
    
    print(f"\n🎯 Attempting to complete {len(target_files)} known uploads:")
    
    successful = 0
    for filename in target_files:
        print(f"\nTrying to complete: {filename}")
        if complete_upload(filename):
            successful += 1
        time.sleep(2)  # Small delay
    
    print(f"\n" + "="*50)
    print(f"📊 Summary:")
    print(f"   ✅ Completed: {successful}/{len(target_files)}")
    
    # Check final count
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        if response.status_code == 200:
            final_count = len(response.json()['documents'])
            print(f"   📚 Final count: {final_count}/113")
            if initial_count:
                added = final_count - initial_count
                print(f"   📈 Added: {added} documents")
                
            if final_count >= 113:
                print(f"\n🎉 SUCCESS! You have all 113 documents!")
        else:
            print("   ❌ Could not get final document count")
    except:
        print("   ❌ Could not connect to get final document count")

if __name__ == "__main__":
    main()