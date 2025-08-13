#!/usr/bin/env python3
"""
Simple wrapper to run the bulk upload script
This can be executed on Railway via their console or as a scheduled job
"""
import subprocess
import sys
import os

def main():
    print("🚀 Starting Railway Bulk Upload...")
    
    try:
        # Run the bulk upload script
        result = subprocess.run([
            sys.executable, 
            "/app/backend/railway_bulk_upload.py"
        ], 
        capture_output=True, 
        text=True, 
        timeout=3600  # 1 hour timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Bulk upload completed successfully!")
        else:
            print(f"❌ Bulk upload failed with exit code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⚠️  Upload timed out after 1 hour")
    except Exception as e:
        print(f"❌ Error running upload: {e}")

if __name__ == "__main__":
    main()