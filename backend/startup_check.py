#!/usr/bin/env python3
"""
Startup check for Railway deployment
Verifies volume mount and storage configuration
"""

import os
from pathlib import Path

def check_storage():
    """Check storage configuration on startup"""
    print("=" * 60)
    print("🚀 Railway Storage Configuration Check")
    print("=" * 60)
    
    # Check if running on Railway
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    print(f"📍 Environment: {'Railway' if is_railway else 'Local'}")
    
    if is_railway:
        print(f"🚂 Railway Environment: {os.getenv('RAILWAY_ENVIRONMENT')}")
    
    # Check for Railway volume mounts
    volume_paths = ["/data", "/mnt/data"]
    volume_found = None
    
    for dir_path in volume_paths:
        if Path(dir_path).exists():
            print(f"✅ Railway VOLUME found at {dir_path}")
            volume_found = dir_path
            
            # Check permissions
            if os.access(dir_path, os.W_OK):
                print(f"✅ Volume {dir_path} is writable")
            else:
                print(f"❌ Volume {dir_path} is NOT writable")
            
            # List contents
            try:
                contents = list(Path(dir_path).iterdir())
                if contents:
                    print(f"📁 Volume contains {len(contents)} items:")
                    for item in contents[:5]:
                        print(f"   - {item.name}")
                    if len(contents) > 5:
                        print(f"   ... and {len(contents) - 5} more")
                else:
                    print("📁 Volume is empty (fresh mount)")
            except Exception as e:
                print(f"❌ Error listing volume contents: {e}")
            break
    
    if not volume_found:
        print("❌ NO RAILWAY VOLUME FOUND!")
        if is_railway:
            print("   This is the problem - your data is stored in ephemeral /app/data")
            print("   SET UP A RAILWAY VOLUME to fix data persistence!")
            print("   Go to Railway Dashboard → Your Service → Settings → Volumes")
            print("   Create volume with mount path: /data")
        
        # Check ephemeral directory anyway
        ephemeral_path = "/app/data"
        if Path(ephemeral_path).exists():
            print(f"📁 Using ephemeral storage at {ephemeral_path} (will be lost on redeploy)")
        else:
            print(f"📁 Ephemeral directory will be created at: {ephemeral_path}")
    
    # Check ChromaDB directory
    if is_railway:
        if volume_found:
            chroma_dir = Path(volume_found) / "chroma_db"
        else:
            chroma_dir = Path("/app/data/chroma_db")
    else:
        chroma_dir = Path("./backend/chroma_db")
        
    if chroma_dir.exists():
        print(f"✅ ChromaDB directory exists: {chroma_dir}")
        # Check if it has data
        chroma_files = list(chroma_dir.glob("**/*"))
        if chroma_files:
            print(f"   Contains {len(chroma_files)} files - YOUR DATA IS PRESERVED!")
        else:
            print("   Directory is empty")
    else:
        print(f"📁 ChromaDB directory will be created at: {chroma_dir}")
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    important_vars = [
        "RAILWAY_ENVIRONMENT",
        "DATA_DIR", 
        "CHROMA_DB_PATH",
        "UPLOAD_DIR"
    ]
    for var in important_vars:
        value = os.getenv(var, "Not set")
        if var == "OPENAI_API_KEY" and value != "Not set":
            value = value[:10] + "..." if len(value) > 10 else value
        print(f"   {var}: {value}")
    
    print("=" * 60)

if __name__ == "__main__":
    check_storage()