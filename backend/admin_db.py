"""
Database operations for admin users and sessions
"""
import os
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import hashlib


class AdminDatabase:
    """Handle admin user database operations"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.pool = None
    
    async def init_pool(self):
        """Initialize database connection pool"""
        if not self.database_url:
            # For local development, use a simple SQLite approach
            # In production, this should use the DATABASE_URL
            raise ValueError("DATABASE_URL not configured")
        
        self.pool = await asyncpg.create_pool(self.database_url)
        await self.create_tables()
    
    async def create_tables(self):
        """Create admin tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Create admin_users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            """)
            
            # Create admin_sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES admin_users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index for faster lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_admin_sessions_token 
                ON admin_sessions(token_hash)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires 
                ON admin_sessions(expires_at)
            """)
    
    async def create_admin_user(self, email: str, password_hash: str) -> Dict[str, Any]:
        """Create a new admin user"""
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow("""
                    INSERT INTO admin_users (email, password_hash)
                    VALUES ($1, $2)
                    RETURNING id, email, created_at, is_active
                """, email.lower(), password_hash)
                
                return dict(row) if row else None
            except asyncpg.UniqueViolationError:
                return None  # User already exists
    
    async def get_admin_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin user by email"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, email, password_hash, created_at, last_login, is_active
                FROM admin_users
                WHERE email = $1 AND is_active = true
            """, email.lower())
            
            return dict(row) if row else None
    
    async def get_admin_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get admin user by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, email, created_at, last_login, is_active
                FROM admin_users
                WHERE id = $1 AND is_active = true
            """, uuid.UUID(user_id))
            
            return dict(row) if row else None
    
    async def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE admin_users
                SET last_login = NOW()
                WHERE id = $1
            """, uuid.UUID(user_id))
    
    async def create_session(self, user_id: str, token: str, expires_in_hours: int = 24) -> Dict[str, Any]:
        """Create a new session for a user"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO admin_sessions (user_id, token_hash, expires_at)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, expires_at, created_at
            """, uuid.UUID(user_id), token_hash, expires_at)
            
            return dict(row) if row else None
    
    async def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and return user info if valid"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        async with self.pool.acquire() as conn:
            # Get session and user info in one query
            row = await conn.fetchrow("""
                SELECT 
                    u.id, u.email, u.is_active,
                    s.expires_at
                FROM admin_sessions s
                JOIN admin_users u ON s.user_id = u.id
                WHERE s.token_hash = $1 
                    AND s.expires_at > NOW()
                    AND u.is_active = true
            """, token_hash)
            
            return dict(row) if row else None
    
    async def delete_session(self, token: str):
        """Delete a session (logout)"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM admin_sessions
                WHERE token_hash = $1
            """, token_hash)
    
    async def clean_expired_sessions(self):
        """Remove expired sessions from database"""
        async with self.pool.acquire() as conn:
            deleted = await conn.execute("""
                DELETE FROM admin_sessions
                WHERE expires_at < NOW()
            """)
            return deleted
    
    async def close(self):
        """Close database pool"""
        if self.pool:
            await self.pool.close()


# For local development without PostgreSQL
class InMemoryAdminDatabase:
    """In-memory implementation for local development"""
    
    def __init__(self):
        self.users = {}
        self.sessions = {}
    
    async def init_pool(self):
        """No-op for in-memory database"""
        pass
    
    async def create_tables(self):
        """No-op for in-memory database"""
        pass
    
    async def create_admin_user(self, email: str, password_hash: str) -> Dict[str, Any]:
        """Create a new admin user in memory"""
        if email.lower() in [u['email'] for u in self.users.values()]:
            return None
        
        user_id = str(uuid.uuid4())
        user = {
            'id': user_id,
            'email': email.lower(),
            'password_hash': password_hash,
            'created_at': datetime.utcnow(),
            'last_login': None,
            'is_active': True
        }
        self.users[user_id] = user
        return {k: v for k, v in user.items() if k != 'password_hash'}
    
    async def get_admin_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin user by email from memory"""
        for user in self.users.values():
            if user['email'] == email.lower() and user['is_active']:
                return user
        return None
    
    async def get_admin_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get admin user by ID from memory"""
        user = self.users.get(user_id)
        if user and user['is_active']:
            return {k: v for k, v in user.items() if k != 'password_hash'}
        return None
    
    async def update_last_login(self, user_id: str):
        """Update user's last login timestamp in memory"""
        if user_id in self.users:
            self.users[user_id]['last_login'] = datetime.utcnow()
    
    async def create_session(self, user_id: str, token: str, expires_in_hours: int = 24) -> Dict[str, Any]:
        """Create a new session in memory"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'token_hash': token_hash,
            'expires_at': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'created_at': datetime.utcnow()
        }
        self.sessions[token_hash] = session
        return session
    
    async def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token from memory"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session = self.sessions.get(token_hash)
        
        if not session:
            return None
        
        if session['expires_at'] < datetime.utcnow():
            del self.sessions[token_hash]
            return None
        
        user = self.users.get(session['user_id'])
        if user and user['is_active']:
            return {
                'id': user['id'],
                'email': user['email'],
                'is_active': user['is_active'],
                'expires_at': session['expires_at']
            }
        return None
    
    async def delete_session(self, token: str):
        """Delete a session from memory"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in self.sessions:
            del self.sessions[token_hash]
    
    async def clean_expired_sessions(self):
        """Remove expired sessions from memory"""
        now = datetime.utcnow()
        expired = [k for k, v in self.sessions.items() if v['expires_at'] < now]
        for k in expired:
            del self.sessions[k]
        return len(expired)
    
    async def close(self):
        """No-op for in-memory database"""
        pass