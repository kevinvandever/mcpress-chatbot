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
        # Force ChromaDB usage (same as local) - multiple ways to ensure this
        "RAILWAY_ENVIRONMENT": "false",
        "USE_CHROMADB": "true", 
        "DATABASE_URL": "",  # Clear any PostgreSQL URL
        "DATA_DIR": "/tmp/data"
    })
    
    # Start backend
    cmd = ["python", "-m", "uvicorn", "backend.main:app", 
           "--host", "0.0.0.0", "--port", backend_port]
    
    log(f"Backend command: {' '.join(cmd)}")
    backend_process = subprocess.Popen(cmd, env=env)
    
    # Simple wait instead of health check that might fail
    log("Waiting for backend to initialize...")
    time.sleep(3)
    log("✅ Backend started")
    
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
    build_cmd = ["npm", "run", "build-frontend"]
    subprocess.run(build_cmd, env=env, check=True)
    
    log(f"Starting Next.js on port {port}...")
    start_cmd = ["npm", "run", "start-frontend"]
    frontend_process = subprocess.Popen(start_cmd, env=env)
    
    return frontend_process

def main():
    log("🚀 Starting Railway Full-Stack Deployment")
    
    # Run debug script first
    log("Running deployment debug script...")
    try:
        subprocess.run([sys.executable, "debug_deployment.py"], check=False)
    except Exception as e:
        log(f"Debug script error: {e}")
    
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    log(f"Working directory: {os.getcwd()}")
    
    # Verify frontend directory exists
    if not os.path.exists("frontend"):
        log("❌ Frontend directory not found!")
        log(f"Contents of current directory: {os.listdir('.')}")
        
        # Additional debugging
        log("🔍 Checking if frontend files exist anywhere...")
        for root, dirs, files in os.walk("."):
            if "package.json" in files and "frontend" in root:
                log(f"Found frontend-like directory: {root}")
        
        sys.exit(1)
    
    try:
        # Start backend process
        backend_process = start_backend()
        
        # Give backend a moment to start
        time.sleep(5)
        
        # Start frontend (this blocks and serves HTTP traffic)
        frontend_process = start_frontend()
        
        log("✅ Full-stack deployment started successfully")
        log(f"🌐 Frontend serving on port {os.environ.get('PORT', '3000')}")
        log("📡 Backend available internally on port 8000")
        
        # Wait for either process to exit
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            backend_future = executor.submit(backend_process.wait)
            frontend_future = executor.submit(frontend_process.wait)
            
            # Wait for either to complete
            done, pending = concurrent.futures.wait(
                [backend_future, frontend_future], 
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            # If one process exits, kill the other
            for future in pending:
                future.cancel()
            
            if backend_future in done:
                log("❌ Backend process exited")
                frontend_process.kill()
            elif frontend_future in done:
                log("❌ Frontend process exited")  
                backend_process.kill()
        
    except KeyboardInterrupt:
        log("Shutting down...")
    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()