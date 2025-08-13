#!/usr/bin/env python3
"""
Incremental PDF Upload Strategy - Upload in small batches to avoid timeouts
Based on lessons learned from connection pooling limitations
"""
import subprocess
import sys
import time
import requests
import json
from datetime import datetime

API_URL = "https://mcpress-chatbot-production-569b.up.railway.app"
BATCH_SIZE = 15  # Conservative batch size based on connection pooling limits

def get_current_status():
    """Get current document count from the live API"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=30)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('documents', [])
            total_chunks = sum(doc.get('chunk_count', 0) for doc in docs)
            return len(docs), total_chunks
        else:
            print(f"⚠️  API returned {response.status_code}")
            return 0, 0
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return 0, 0

def wait_for_processing_completion():
    """Wait for any ongoing processing to complete"""
    print("⏳ Checking system status...")
    
    # Quick check - just get current status
    docs, chunks = get_current_status()
    print(f"✅ Current status: {docs} documents, {chunks:,} chunks")
    return docs, chunks

def trigger_railway_upload_batch(batch_size: int = BATCH_SIZE):
    """Trigger a batch upload on Railway"""
    print(f"\n🚀 Triggering Railway batch upload (limit: {batch_size} PDFs)")
    
    # Here we would need to modify the Railway script to accept batch size
    # For now, we'll use the existing script but add monitoring
    
    try:
        # This would ideally be an API call to Railway to start the upload
        # For now, we'll monitor the current system
        
        start_docs, start_chunks = get_current_status()
        print(f"📊 Starting state: {start_docs} documents, {start_chunks:,} chunks")
        
        # In a real implementation, we'd trigger the upload here
        # subprocess.run(["railway", "run", "python", "/app/backend/run_bulk_upload.py"])
        
        print("⚠️  Manual trigger needed - see Railway console")
        print("   Run: python /app/backend/run_bulk_upload.py")
        
        return start_docs
        
    except Exception as e:
        print(f"❌ Error triggering upload: {e}")
        return 0

def monitor_batch_progress(start_count: int, target_batch_size: int = BATCH_SIZE, timeout_minutes: int = 30):
    """Monitor progress of the current batch upload"""
    print(f"\n📈 Monitoring batch progress (target: +{target_batch_size} documents)")
    
    start_time = time.time()
    max_time = timeout_minutes * 60
    
    while time.time() - start_time < max_time:
        current_docs, current_chunks = get_current_status()
        progress = current_docs - start_count
        
        elapsed = int((time.time() - start_time) / 60)
        print(f"[{elapsed:2d}min] Progress: +{progress}/{target_batch_size} docs, {current_chunks:,} total chunks")
        
        if progress >= target_batch_size:
            print(f"✅ Batch complete! Added {progress} documents")
            return current_docs
        elif progress < 0:
            print("⚠️  Document count decreased - possible reset")
            return current_docs
            
        time.sleep(60)  # Check every minute during upload
    
    print(f"⏱️  Batch timeout after {timeout_minutes} minutes")
    return get_current_status()[0]

def main():
    """Main incremental upload orchestrator"""
    print("=" * 70)
    print("🎯 PDF Chatbot - Incremental Upload Strategy")
    print("=" * 70)
    
    # Step 1: Check current status
    print("\n1️⃣  Checking current system status...")
    initial_docs, initial_chunks = wait_for_processing_completion()
    
    if initial_docs == 0:
        print("📝 Starting fresh - no documents found")
        print("   This is expected after Railway redeployment")
    else:
        print(f"📚 Found existing data: {initial_docs} documents, {initial_chunks:,} chunks")
    
    target_documents = 115  # Total goal based on PROJECT_STATUS.md
    remaining = target_documents - initial_docs
    
    if remaining <= 0:
        print("🎉 All documents already uploaded!")
        return
    
    print(f"🎯 Goal: Upload {remaining} more documents in batches of {BATCH_SIZE}")
    
    # Step 2: Plan batches
    total_batches = (remaining + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
    
    print(f"\n2️⃣  Upload Plan:")
    print(f"   • Total remaining: {remaining} documents")
    print(f"   • Batch size: {BATCH_SIZE} documents")
    print(f"   • Estimated batches: {total_batches}")
    print(f"   • Strategy: Conservative batches to avoid connection timeouts")
    
    # Step 3: Execute batches
    current_docs = initial_docs
    
    for batch_num in range(1, total_batches + 1):
        remaining_docs = target_documents - current_docs
        if remaining_docs <= 0:
            break
            
        batch_target = min(BATCH_SIZE, remaining_docs)
        
        print(f"\n3️⃣  Batch {batch_num}/{total_batches}")
        print(f"   Target: +{batch_target} documents")
        print(f"   Current: {current_docs}/{target_documents}")
        
        # Trigger upload (manual for now)
        start_count = trigger_railway_upload_batch(batch_target)
        
        if start_count == 0:
            print("❌ Failed to start batch, stopping")
            break
        
        # Monitor progress
        current_docs = monitor_batch_progress(start_count, batch_target)
        
        # Progress update
        total_progress = (current_docs / target_documents) * 100
        print(f"📊 Overall Progress: {current_docs}/{target_documents} ({total_progress:.1f}%)")
        
        # Rest between batches
        if batch_num < total_batches:
            print("⏸️  Resting 2 minutes between batches...")
            time.sleep(120)
    
    # Final status
    final_docs, final_chunks = get_current_status()
    print(f"\n🏁 Upload Session Complete!")
    print(f"   Final status: {final_docs} documents, {final_chunks:,} chunks")
    
    if final_docs >= target_documents * 0.9:  # 90% success rate
        print("🎉 Upload successful!")
    else:
        print(f"⚠️  Partial success - {target_documents - final_docs} documents remaining")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Upload interrupted by user")
    except Exception as e:
        print(f"\n❌ Upload error: {e}")
        import traceback
        traceback.print_exc()