#!/usr/bin/env python3
"""
Railway Backend-Only Startup Script
Runs just the FastAPI backend without frontend
"""
import os
import sys

def main():
    print("[RAILWAY] Starting backend-only deployment v3")
    
    # Debug: Check if OPENAI_API_KEY is available
    openai_key = os.environ.get('OPENAI_API_KEY')
    print(f"[RAILWAY] OPENAI_API_KEY present: {openai_key is not None}")
    if openai_key:
        print(f"[RAILWAY] OPENAI_API_KEY length: {len(openai_key)}")
    else:
        print("[RAILWAY] ❌ OPENAI_API_KEY not found!")
        print(f"[RAILWAY] Available env vars: {list(os.environ.keys())}")
    
    # Set environment variables
    os.environ['RAILWAY_ENVIRONMENT'] = 'false'
    os.environ['USE_POSTGRESQL'] = 'false'
    os.environ['DATA_DIR'] = '/tmp/data'
    
    # Get port from Railway
    port = os.environ.get('PORT', '8080')
    
    print(f"[RAILWAY] Starting FastAPI on port {port}")
    
    # Start uvicorn directly
    os.system(f"python -m uvicorn backend.main:app --host 0.0.0.0 --port {port}")

if __name__ == "__main__":
    main()