#!/usr/bin/env python3
"""
Railway startup script to verify and install dependencies
"""
import sys
import subprocess
import importlib

def install_package(package):
    """Install a package using pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_chromadb():
    """Check if ChromaDB is available and install if needed"""
    try:
        import chromadb
        print("✅ ChromaDB is available")
        return True
    except ImportError:
        print("⚠️ ChromaDB not found, attempting installation...")
        try:
            install_package("chromadb==0.4.24")
            import chromadb
            print("✅ ChromaDB installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install ChromaDB: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Railway startup check...")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check ChromaDB
    chromadb_available = check_and_install_chromadb()
    
    # Check other critical packages
    critical_packages = ["fastapi", "uvicorn", "openai", "sentence_transformers"]
    for package in critical_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} available")
        except ImportError:
            print(f"❌ {package} missing")
    
    print("🏁 Startup check complete")