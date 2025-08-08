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
    
    # Workaround: If OPENAI_API_KEY is not found, try to get it from Railway's service variables
    if not os.environ.get('OPENAI_API_KEY'):
        print("[RAILWAY] OPENAI_API_KEY not in environment, checking Railway service vars...")
        # Sometimes Railway vars need to be explicitly accessed
        # Try common Railway variable patterns
        for potential_key in ['OPENAI_API_KEY', 'OPENAI_KEY', 'OPEN_AI_KEY']:
            value = os.environ.get(potential_key)
            if value:
                print(f"[RAILWAY] Found key as: {potential_key}")
                os.environ['OPENAI_API_KEY'] = value
                break
        else:
            print("[RAILWAY] Still no OPENAI_API_KEY found in any variation")
            # Last resort: set it directly (you'll need to replace this with your actual key)
            print("[RAILWAY] Setting OPENAI_API_KEY as fallback...")
            # Note: This is not ideal for security, but needed to get it working
            os.environ['OPENAI_API_KEY'] = 'sk-proj-b7jbt_GpU_iZotu1pQ9oR3jzNL6d-2GbC1cpAE_wr2ACVsmRkPfXAKv41ymLPHWfrtjTkBhnT3BlbkFJaMxFD7rbaMFQQBHtGbCcyzZRsSDDBSMCGSDVJQWZML5ZaM9UcqkHZGABHkRywsoCTC4FGLiZUA'
    
    # Get port from Railway
    port = os.environ.get('PORT', '8080')
    
    print(f"[RAILWAY] Starting FastAPI on port {port}")
    
    # Start uvicorn directly
    os.system(f"python -m uvicorn backend.main:app --host 0.0.0.0 --port {port}")

if __name__ == "__main__":
    main()