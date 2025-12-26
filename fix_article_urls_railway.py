#!/usr/bin/env python3
"""
Fix article URLs via Railway API endpoint
"""

import requests

def main():
    print("🔧 Fixing article URL typos via Railway...")
    
    # Use Railway API to execute the fix
    api_url = "https://mcpress-chatbot-production.up.railway.app/api/fix-article-urls"
    
    try:
        print("📤 Calling fix endpoint...")
        
        response = requests.post(api_url)
        result = response.json()
        
        print(f"✅ Fix result: {result.get('success', False)}")
        print(f"🔧 URLs fixed: {result.get('urls_fixed', 0)}")
        print(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
        
        if result.get('success', False):
            print(f"\n🎉 URL fix completed successfully!")
        else:
            print(f"\n❌ URL fix failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Error during URL fix: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()