#!/usr/bin/env python3
"""
Execute SQL on Railway using Railway CLI
This script helps you run the author corrections via Railway CLI
"""

import os
import subprocess
import sys

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Railway CLI found: {result.stdout.strip()}")
            return True
        else:
            return False
    except FileNotFoundError:
        return False

def install_railway_cli():
    """Install Railway CLI"""
    print("📦 Installing Railway CLI...")
    
    # Try npm install
    try:
        result = subprocess.run(['npm', 'install', '-g', '@railway/cli'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Railway CLI installed successfully via npm")
            return True
    except FileNotFoundError:
        pass
    
    # Try curl install
    try:
        print("Trying curl installation...")
        result = subprocess.run(['bash', '-c', 
                               'curl -fsSL https://railway.app/install.sh | sh'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Railway CLI installed successfully via curl")
            return True
    except:
        pass
    
    print("❌ Failed to install Railway CLI automatically")
    print("Please install manually:")
    print("  npm install -g @railway/cli")
    print("  OR")
    print("  curl -fsSL https://railway.app/install.sh | sh")
    return False

def login_to_railway():
    """Login to Railway"""
    print("🔐 Logging into Railway...")
    result = subprocess.run(['railway', 'login'], 
                          capture_output=False)
    return result.returncode == 0

def execute_sql_via_railway():
    """Execute SQL via Railway CLI"""
    print("🚀 Executing SQL via Railway CLI...")
    
    # Check if SQL file exists
    if not os.path.exists('complete_author_audit_corrections.sql'):
        print("❌ complete_author_audit_corrections.sql not found")
        return False
    
    # Try to execute via railway run
    print("Attempting to execute SQL...")
    
    # Method 1: Direct psql execution
    cmd = ['railway', 'run', 'psql', '$DATABASE_URL', '-f', 'complete_author_audit_corrections.sql']
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("✅ SQL executed successfully!")
        return True
    else:
        print(f"❌ SQL execution failed with code {result.returncode}")
        
        # Method 2: Try with python script
        print("Trying alternative method with Python...")
        cmd2 = ['railway', 'run', 'python3', 'run_sql_on_railway.py']
        result2 = subprocess.run(cmd2, capture_output=False)
        
        if result2.returncode == 0:
            print("✅ SQL executed successfully via Python!")
            return True
        else:
            print("❌ Both methods failed")
            return False

def main():
    print("=" * 60)
    print("RAILWAY SQL EXECUTION HELPER")
    print("=" * 60)
    
    # Step 1: Check Railway CLI
    if not check_railway_cli():
        print("❌ Railway CLI not found")
        if not install_railway_cli():
            return 1
    
    # Step 2: Login to Railway
    if not login_to_railway():
        print("❌ Failed to login to Railway")
        return 1
    
    # Step 3: Execute SQL
    if not execute_sql_via_railway():
        print("❌ Failed to execute SQL")
        print("\nAlternative options:")
        print("1. Try the Railway dashboard database console")
        print("2. Get DATABASE_URL and run locally:")
        print("   railway variables | grep DATABASE_URL")
        print("   psql 'your-database-url' -f complete_author_audit_corrections.sql")
        return 1
    
    print("\n🎉 SUCCESS! Author corrections completed!")
    print("Test the chat interface to verify the fixes.")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)