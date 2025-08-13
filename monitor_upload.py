#!/usr/bin/env python3
"""
Monitor the Railway bulk upload progress
"""
import requests
import json
import time
from datetime import datetime

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"

def check_progress():
    """Check current upload progress"""
    try:
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            total_chunks = sum(doc['chunk_count'] for doc in docs)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Progress: {len(docs)}/115 documents, {total_chunks:,} chunks")
            
            if len(docs) > 5:
                # Show progress
                progress_pct = (len(docs) / 115) * 100
                print(f"  🎯 {progress_pct:.1f}% complete")
                
                # Show recent additions (last 3)
                recent = sorted(docs, key=lambda x: x['uploaded_at'])[-3:]
                print("  📑 Recent uploads:")
                for doc in recent:
                    print(f"    - {doc['filename']}: {doc['chunk_count']} chunks")
            
            return len(docs)
        else:
            print(f"❌ API error: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"❌ Error checking progress: {e}")
        return 0

def main():
    print("🔄 Monitoring Railway bulk upload progress...")
    print("=" * 60)
    
    start_docs = check_progress()
    start_time = time.time()
    
    while True:
        time.sleep(30)  # Check every 30 seconds
        
        current_docs = check_progress()
        
        if current_docs >= 100:  # Near completion
            print("🎉 Bulk upload nearly complete!")
            break
        elif current_docs > start_docs:
            elapsed = time.time() - start_time
            docs_processed = current_docs - start_docs
            remaining_docs = 115 - current_docs
            
            if docs_processed > 0:
                rate = docs_processed / (elapsed / 60)  # docs per minute
                eta_minutes = remaining_docs / rate if rate > 0 else 0
                print(f"  📈 Rate: {rate:.1f} docs/min, ETA: {eta_minutes:.0f} minutes")
        
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")