#!/usr/bin/env python3
"""
Railway Full-Stack Startup Script
Runs both Next.js frontend and FastAPI backend on Railway
"""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

def log(message):
    print(f"[RAILWAY] {message}", flush=True)

def start_backend():
    """Start FastAPI backend on internal port"""
    log("Starting FastAPI backend...")
    backend_port = "8000"  # Internal backend port
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        "PORT": backend_port,
        "HOST": "0.0.0.0",
        # Force ChromaDB usage (same as local)
        "RAILWAY_ENVIRONMENT": "false",
        "DATA_DIR": "/tmp/data"
    })
    
    # Start backend
    cmd = ["python", "-m", "uvicorn", "backend.main:app", 
           "--host", "0.0.0.0", "--port", backend_port]
    
    log(f"Backend command: {' '.join(cmd)}")
    backend_process = subprocess.Popen(cmd, env=env)
    
    # Wait for backend to be ready
    import requests
    for i in range(30):
        try:
            response = requests.get(f"http://localhost:{backend_port}/health", timeout=2)
            if response.status_code == 200:
                log("✅ Backend is ready")
                break
        except:
            time.sleep(1)
    else:
        log("⚠️  Backend health check failed, continuing anyway...")
    
    return backend_process

def start_frontend():
    """Start Next.js frontend on Railway's public port"""
    log("Starting Next.js frontend...")
    
    # Get Railway's assigned port
    port = os.environ.get("PORT", "3000")
    
    # Set environment variables for frontend
    env = os.environ.copy()
    env.update({
        "PORT": port,
        "NEXT_PUBLIC_API_URL": "/api",  # Use relative API calls
        "NODE_ENV": "production"
    })
    
    # Build and start frontend
    log("Building Next.js frontend...")
    build_cmd = ["npm", "run", "build"]
    subprocess.run(build_cmd, cwd="frontend", env=env, check=True)
    
    log(f"Starting Next.js on port {port}...")
    start_cmd = ["npm", "start"]
    frontend_process = subprocess.Popen(start_cmd, cwd="frontend", env=env)
    
    return frontend_process

def main():
    log("🚀 Starting Railway Full-Stack Deployment")
    
    try:
        # Start backend in background thread
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        
        # Give backend a moment to start
        time.sleep(5)
        
        # Start frontend (this blocks and serves HTTP traffic)
        frontend_process = start_frontend()
        
        log("✅ Full-stack deployment started successfully")
        log(f"🌐 Frontend serving on port {os.environ.get('PORT', '3000')}")
        log("📡 Backend available internally on port 8000")
        
        # Wait for frontend process
        frontend_process.wait()
        
    except KeyboardInterrupt:
        log("Shutting down...")
    except Exception as e:
        log(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()