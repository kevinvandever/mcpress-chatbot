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
    
    # Check volume mount
    if Path("/data").exists():
        print("✅ Volume mount /data exists")
        
        # Check permissions
        if os.access("/data", os.W_OK):
            print("✅ Volume mount is writable")
        else:
            print("❌ Volume mount is NOT writable")
        
        # List contents
        try:
            contents = list(Path("/data").iterdir())
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
    else:
        print("⚠️  Volume mount /data does not exist")
        if is_railway:
            print("   This is a problem - volume should be mounted!")
    
    # Check ChromaDB directory
    chroma_dir = Path("/data/chroma_db") if is_railway else Path("./backend/chroma_db")
    if chroma_dir.exists():
        print(f"✅ ChromaDB directory exists: {chroma_dir}")
        # Check if it has data
        chroma_files = list(chroma_dir.glob("**/*"))
        if chroma_files:
            print(f"   Contains {len(chroma_files)} files")
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