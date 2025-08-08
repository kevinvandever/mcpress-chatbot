#!/usr/bin/env python3
"""
Debug script to show what files are available in Railway deployment
"""
import os
import subprocess

def main():
    print("🔍 DEPLOYMENT DEBUG INFO")
    print("=" * 50)
    
    # Show current directory
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    # List all files and directories
    print(f"\n📁 Contents of {cwd}:")
    try:
        items = os.listdir(cwd)
        for item in sorted(items):
            path = os.path.join(cwd, item)
            if os.path.isdir(path):
                print(f"  📁 {item}/")
                # List contents of key directories
                if item in ['frontend', 'backend']:
                    try:
                        subitems = os.listdir(path)
                        for subitem in sorted(subitems)[:5]:  # First 5 items
                            print(f"    📄 {subitem}")
                        if len(subitems) > 5:
                            print(f"    ... and {len(subitems) - 5} more items")
                    except:
                        print(f"    ❌ Cannot read directory {item}/")
            else:
                print(f"  📄 {item}")
    except Exception as e:
        print(f"❌ Error listing directory: {e}")
    
    # Check specific paths
    print(f"\n🔍 Checking specific paths:")
    paths_to_check = [
        "frontend",
        "frontend/package.json",
        "frontend/next.config.js",
        "backend",
        "backend/main.py",
        "railway.toml",
        "requirements.txt"
    ]
    
    for path in paths_to_check:
        if os.path.exists(path):
            if os.path.isdir(path):
                count = len(os.listdir(path)) if os.path.isdir(path) else 0
                print(f"  ✅ {path}/ (contains {count} items)")
            else:
                print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path} - NOT FOUND")
    
    # Check environment variables
    print(f"\n🌍 Environment variables:")
    env_vars = ['PORT', 'RAILWAY_ENVIRONMENT', 'DATA_DIR', 'NODE_ENV']
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        print(f"  {var}: {value}")
    
    print("=" * 50)
    print("🔍 End deployment debug info")

if __name__ == "__main__":
    main()