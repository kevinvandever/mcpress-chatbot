#!/usr/bin/env python3
"""
Wait for Railway deployment to complete and test the document count fix
"""

import requests
import time
import json

BASE_URL = "https://mcpress-chatbot-production.up.railway.app"

def check_deployment_status():
    """Check if the deployment is ready by testing the health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        return response.status_code == 200
    except:
        return False

def test_document_count():
    """Test the document count after the fix"""
    print("🔍 Testing document count fix...")
    
    # First, refresh the cache to ensure we get the latest data
    print("📊 Refreshing documents cache...")
    refresh_response = requests.get(f"{BASE_URL}/documents/refresh")
    
    if refresh_response.status_code == 200:
        refresh_data = refresh_response.json()
        print(f"✅ Cache refresh successful")
        print(f"📋 Documents found: {len(refresh_data.get('documents', []))}")
        
        # Check if we have the expected number (should be 6,270+ not 200)
        doc_count = len(refresh_data.get('documents', []))
        if doc_count > 6000:
            print(f"🎉 SUCCESS: Document count is {doc_count} (expected 6,270+)")
            return True
        elif doc_count == 200:
            print(f"❌ STILL BROKEN: Document count is still limited to 200")
            return False
        else:
            print(f"⚠️ UNEXPECTED: Document count is {doc_count}")
            return False
    else:
        print(f"❌ Cache refresh failed: {refresh_response.status_code}")
        return False

def main():
    print("🚀 Waiting for Railway deployment to complete...")
    print("⏳ This usually takes 10-15 minutes...")
    
    # Wait for deployment to be ready
    max_attempts = 30  # 15 minutes with 30-second intervals
    for attempt in range(max_attempts):
        print(f"🔍 Checking deployment status... (attempt {attempt + 1}/{max_attempts})")
        
        if check_deployment_status():
            print("✅ Deployment appears to be ready!")
            break
        else:
            if attempt < max_attempts - 1:
                print("⏳ Still deploying, waiting 30 seconds...")
                time.sleep(30)
            else:
                print("❌ Deployment taking too long, testing anyway...")
    
    # Test the fix
    print("\n" + "="*50)
    success = test_document_count()
    
    if success:
        print("\n🎉 DOCUMENT COUNT FIX SUCCESSFUL!")
        print("✅ Frontend should now show 6,270+ documents instead of 200")
        print("\n📋 Next steps from FINAL_ISSUES_FIX_PLAN.md:")
        print("  3. Investigate Article Titles/Authors")
        print("  4. Fix Author Button Dropdown") 
        print("  5. Test All Fixes")
    else:
        print("\n❌ Document count fix did not work as expected")
        print("🔍 May need further investigation")

if __name__ == "__main__":
    main()