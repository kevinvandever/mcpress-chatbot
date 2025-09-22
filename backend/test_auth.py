"""
Test authentication system
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up test environment
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["ADMIN_PASSWORD"] = "TestPassword123!@#"

from auth import AuthService, RateLimiter
from admin_db import InMemoryAdminDatabase


async def test_auth_system():
    """Test the authentication system components"""
    print("🧪 Testing Authentication System\n")
    
    # Initialize services
    auth_service = AuthService()
    db = InMemoryAdminDatabase()
    rate_limiter = RateLimiter(max_attempts=3, window_minutes=1)
    
    await db.init_pool()
    
    # Test 1: Password hashing
    print("1️⃣ Testing password hashing...")
    test_password = "TestPassword123!@#"
    hashed = auth_service.hash_password(test_password)
    assert auth_service.verify_password(test_password, hashed), "Password verification failed"
    assert not auth_service.verify_password("wrongpassword", hashed), "Wrong password should fail"
    print("✅ Password hashing works correctly\n")
    
    # Test 2: Password validation
    print("2️⃣ Testing password validation...")
    weak_passwords = [
        ("short", "Password must be at least 12 characters long"),
        ("nouppercase123!", "Password must contain at least one uppercase letter"),
        ("NOLOWERCASE123!", "Password must contain at least one lowercase letter"),
        ("NoNumbers!@#", "Password must contain at least one number"),
        ("NoSpecialChar123", "Password must contain at least one special character"),
    ]
    
    for pwd, expected_msg in weak_passwords:
        valid, msg = auth_service.validate_password_strength(pwd)
        assert not valid, f"Password '{pwd}' should be invalid"
        assert msg == expected_msg, f"Expected: {expected_msg}, Got: {msg}"
    
    strong_password = "StrongPass123!@#"
    valid, msg = auth_service.validate_password_strength(strong_password)
    assert valid, f"Strong password should be valid: {msg}"
    print("✅ Password validation works correctly\n")
    
    # Test 3: User creation
    print("3️⃣ Testing user creation...")
    user = await db.create_admin_user(
        "admin@example.com",
        auth_service.hash_password("AdminPass123!@#")
    )
    assert user is not None, "User creation failed"
    assert user["email"] == "admin@example.com", "Email mismatch"
    
    # Test duplicate user
    duplicate = await db.create_admin_user(
        "admin@example.com",
        auth_service.hash_password("AnotherPass123!@#")
    )
    assert duplicate is None, "Duplicate user should not be created"
    print("✅ User creation works correctly\n")
    
    # Test 4: JWT tokens
    print("4️⃣ Testing JWT tokens...")
    token = auth_service.create_access_token(user["id"], user["email"])
    assert token is not None, "Token creation failed"
    
    payload = auth_service.verify_token(token)
    assert payload is not None, "Token verification failed"
    assert payload["email"] == user["email"], "Token email mismatch"
    assert payload["sub"] == user["id"], "Token user ID mismatch"
    
    # Test invalid token
    invalid_payload = auth_service.verify_token("invalid.token.here")
    assert invalid_payload is None, "Invalid token should not verify"
    print("✅ JWT tokens work correctly\n")
    
    # Test 5: Sessions
    print("5️⃣ Testing sessions...")
    session = await db.create_session(user["id"], token)
    assert session is not None, "Session creation failed"
    
    verified_session = await db.verify_session(token)
    assert verified_session is not None, "Session verification failed"
    assert verified_session["email"] == user["email"], "Session email mismatch"
    
    await db.delete_session(token)
    deleted_session = await db.verify_session(token)
    assert deleted_session is None, "Deleted session should not verify"
    print("✅ Sessions work correctly\n")
    
    # Test 6: Rate limiting
    print("6️⃣ Testing rate limiting...")
    test_ip = "192.168.1.1"
    
    # Should allow first 3 attempts
    for i in range(3):
        assert rate_limiter.is_allowed(test_ip), f"Attempt {i+1} should be allowed"
    
    # 4th attempt should be blocked
    assert not rate_limiter.is_allowed(test_ip), "4th attempt should be blocked"
    
    # Reset should clear the limit
    rate_limiter.reset(test_ip)
    assert rate_limiter.is_allowed(test_ip), "Should allow after reset"
    print("✅ Rate limiting works correctly\n")
    
    # Test 7: User retrieval
    print("7️⃣ Testing user retrieval...")
    retrieved_by_email = await db.get_admin_by_email("admin@example.com")
    assert retrieved_by_email is not None, "User retrieval by email failed"
    assert retrieved_by_email["email"] == "admin@example.com", "Retrieved email mismatch"
    
    retrieved_by_id = await db.get_admin_by_id(user["id"])
    assert retrieved_by_id is not None, "User retrieval by ID failed"
    assert retrieved_by_id["id"] == user["id"], "Retrieved ID mismatch"
    print("✅ User retrieval works correctly\n")
    
    await db.close()
    
    print("🎉 All authentication tests passed!")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_auth_system())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)