#!/usr/bin/env python3
"""
Railway Backend-Only Startup Script
Runs just the FastAPI backend without frontend
"""
import os
import sys

def main():
    print("[RAILWAY] Starting backend-only deployment v2")
    
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