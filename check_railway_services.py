#!/usr/bin/env python3
"""
Check Railway services and find database access options
"""

import subprocess
import json

def run_railway_command(cmd):
    """Run a railway CLI command and return output"""
    try:
        result = subprocess.run(['railway'] + cmd, 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except FileNotFoundError:
        return "Railway CLI not found"

def main():
    print("=" * 60)
    print("RAILWAY PROJECT INSPECTION")
    print("=" * 60)
    
    # Check if logged in
    print("🔍 Checking Railway login status...")
    login_status = run_railway_command(['whoami'])
    print(f"Login: {login_status}")
    
    # List projects
    print("\n📋 Listing projects...")
    projects = run_railway_command(['list'])
    print(f"Projects:\n{projects}")
    
    # Show current project
    print("\n🎯 Current project status...")
    status = run_railway_command(['status'])
    print(f"Status:\n{status}")
    
    # List services
    print("\n🔧 Listing services...")
    services = run_railway_command(['service'])
    print(f"Services:\n{services}")
    
    # Show variables (including DATABASE_URL)
    print("\n🔑 Environment variables...")
    variables = run_railway_command(['variables'])
    print(f"Variables:\n{variables}")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Look for DATABASE_URL in the variables above")
    print("2. Use: railway run psql $DATABASE_URL")
    print("3. Or copy DATABASE_URL and use with local psql")
    print("=" * 60)

if __name__ == "__main__":
    main()