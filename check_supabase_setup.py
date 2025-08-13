#!/usr/bin/env python3
"""
Guide for getting correct Supabase connection details
"""

print("🔍 Supabase Connection Troubleshooting Guide")
print("=" * 50)

print("\n1. **Check Supabase Project Status**")
print("   - Go to: https://supabase.com/dashboard")
print("   - Verify your project is active (not paused)")
print("   - Note the project reference ID")

print("\n2. **Get Correct Database URL**")
print("   - In your project dashboard, click 'Settings' (gear icon)")
print("   - Click 'Database' in the left sidebar") 
print("   - Look for 'Connection string' section")
print("   - Copy the 'Direct connection' string (not pooled)")

print("\n3. **Expected Format**")
print("   Direct: postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres")
print("   Pooled: postgresql://postgres.[REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres")

print("\n4. **Verify pgvector Extension**")
print("   - In project dashboard, go to 'SQL Editor'")
print("   - Run: CREATE EXTENSION IF NOT EXISTS vector;")
print("   - Should show 'Success' or 'already exists'")

print("\n5. **Test Connection**")
print("   - Copy the correct URL")
print("   - Update SUPABASE_DATABASE_URL in .env")
print("   - Run: python test_supabase.py")

print("\n" + "=" * 50)
print("Current connection details found:")

# Check what we have
import os
from dotenv import load_dotenv
load_dotenv()

url = os.getenv('SUPABASE_DATABASE_URL', 'Not set')
if url != 'Not set':
    # Extract project ref from URL
    if 'db.' in url and '.supabase.co' in url:
        start = url.find('db.') + 3
        end = url.find('.supabase.co')
        ref = url[start:end] if start > 2 and end > start else 'Unknown'
        print(f"   Project Ref: {ref}")
        print(f"   Host: db.{ref}.supabase.co")
    else:
        print("   URL format not recognized")
        
print(f"   URL: {url[:50]}..." if len(url) > 50 else f"   URL: {url}")

print("\n⚠️  Please verify these details match your Supabase dashboard!")