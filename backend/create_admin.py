#!/usr/bin/env python3
"""
Create an admin user for the MC Press Chatbot
"""
import asyncio
import os
import sys
from getpass import getpass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import AuthService
from admin_db import AdminDatabase, InMemoryAdminDatabase


async def create_admin():
    """Interactive script to create an admin user"""
    print("=" * 50)
    print("MC Press Chatbot - Create Admin User")
    print("=" * 50)
    print()
    
    # Get email
    while True:
        email = input("Enter admin email: ").strip()
        if "@" in email and "." in email:
            break
        print("❌ Please enter a valid email address")
    
    # Get password
    auth_service = AuthService()
    while True:
        password = getpass("Enter password (min 12 chars): ")
        confirm = getpass("Confirm password: ")
        
        if password != confirm:
            print("❌ Passwords don't match")
            continue
        
        valid, message = auth_service.validate_password_strength(password)
        if not valid:
            print(f"❌ {message}")
            continue
        
        break
    
    # Initialize database
    if os.getenv("DATABASE_URL"):
        print("📊 Using PostgreSQL database...")
        db = AdminDatabase()
    else:
        print("📊 Using in-memory database (development mode)...")
        db = InMemoryAdminDatabase()
    
    try:
        await db.init_pool()
        
        # Check if user already exists
        existing = await db.get_admin_by_email(email)
        if existing:
            print(f"⚠️ User {email} already exists")
            update = input("Update password for existing user? (y/n): ").lower()
            if update != 'y':
                print("Cancelled")
                return
        
        # Hash password and create user
        password_hash = auth_service.hash_password(password)
        user = await db.create_admin_user(email, password_hash)
        
        if user:
            print(f"✅ Admin user created successfully!")
            print(f"📧 Email: {email}")
            print(f"🔑 ID: {user['id']}")
            print()
            print("You can now log in at: /admin/login")
        else:
            if existing:
                print("❌ Failed to update user")
            else:
                print("❌ Failed to create user (may already exist)")
    
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\n⛔ Cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()