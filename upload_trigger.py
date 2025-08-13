#!/usr/bin/env python3
"""
Upload trigger script that can be temporarily set as the Railway start command
"""
import os
import subprocess
import sys
import time

def main():
    print("🚀 Railway Upload Trigger Script")
    print("=" * 50)
    
    # Check if this is meant to run upload
    run_upload = os.getenv('RUN_UPLOAD', 'false').lower() == 'true'
    
    if run_upload:
        print("✅ RUN_UPLOAD=true detected, starting batch upload...")
        
        try:
            # Run the batch upload
            result = subprocess.run([
                sys.executable, 
                "/app/backend/railway_batch_upload.py",
                "--batch-size", "15"
            ], timeout=1800)  # 30 minute timeout
            
            print(f"Upload completed with exit code: {result.returncode}")
            
        except subprocess.TimeoutExpired:
            print("⚠️ Upload timed out after 30 minutes")
        except Exception as e:
            print(f"❌ Upload error: {e}")
    
    else:
        print("ℹ️ RUN_UPLOAD not set, starting normal web service...")
        # Import and run the normal web service
        from start_backend_only import main as start_web
        start_web()

if __name__ == "__main__":
    main()