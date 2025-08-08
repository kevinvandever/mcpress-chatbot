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
    log(f"Backend environment overrides: {env}")
    
    try:
        backend_process = subprocess.Popen(cmd, env=env, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.STDOUT,
                                         universal_newlines=True)
        log(f"Backend process PID: {backend_process.pid}")
    except Exception as e:
        log(f"❌ Failed to start backend: {e}")
        import traceback
        log(f"Backend start traceback: {traceback.format_exc()}")
        raise
    
    # Simple wait instead of health check that might fail
    log("Waiting for backend to initialize...")
    time.sleep(3)
    
    # Check if process is still alive
    if backend_process.poll() is None:
        log("✅ Backend process is running")
    else:
        log(f"❌ Backend process exited with code: {backend_process.poll()}")
        # Try to get some output
        try:
            output, _ = backend_process.communicate(timeout=1)
            log(f"Backend output: {output}")
        except:
            pass
    
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
    log(f"Build command: {' '.join(build_cmd)}")
    
    try:
        result = subprocess.run(build_cmd, env=env, check=True, 
                              capture_output=True, text=True)
        log("Frontend build completed successfully")
        if result.stdout:
            log(f"Build stdout: {result.stdout}")
    except subprocess.CalledProcessError as e:
        log(f"❌ Frontend build failed with code {e.returncode}")
        log(f"Build stderr: {e.stderr}")
        log(f"Build stdout: {e.stdout}")
        raise
    
    log(f"Starting Next.js on port {port}...")
    start_cmd = ["npm", "run", "start-frontend"]
    log(f"Start command: {' '.join(start_cmd)}")
    
    try:
        frontend_process = subprocess.Popen(start_cmd, env=env,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, 
                                          universal_newlines=True)
        log(f"Frontend process PID: {frontend_process.pid}")
    except Exception as e:
        log(f"❌ Failed to start frontend: {e}")
        import traceback
        log(f"Frontend start traceback: {traceback.format_exc()}")
        raise
    
    return frontend_process

def main():
    log("🚀 Starting Railway Full-Stack Deployment")
    
    # Log Python executable and version
    log(f"Python executable: {sys.executable}")
    log(f"Python version: {sys.version}")
    
    # Run debug script first
    log("Running deployment debug script...")
    try:
        result = subprocess.run([sys.executable, "debug_deployment.py"], 
                              capture_output=True, text=True, check=False)
        log(f"Debug script stdout: {result.stdout}")
        if result.stderr:
            log(f"Debug script stderr: {result.stderr}")
    except Exception as e:
        log(f"Debug script error: {e}")
        import traceback
        log(f"Debug script traceback: {traceback.format_exc()}")
    
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    log(f"Working directory: {os.getcwd()}")
    
    # Log environment variables
    log("Key environment variables:")
    for key in ["PORT", "RAILWAY_ENVIRONMENT", "DATA_DIR", "NODE_ENV"]:
        log(f"  {key}: {os.environ.get(key, 'NOT SET')}")
    
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