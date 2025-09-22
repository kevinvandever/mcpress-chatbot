# Admin Authentication Deployment Guide

## Overview
This guide covers deploying the admin authentication system to production (Railway + Netlify).

## Prerequisites
- Railway project with PostgreSQL database
- Netlify site for frontend
- Environment variables configured

## Production Deployment Steps

### 1. Railway Backend Setup

#### Environment Variables
Add these to your Railway project settings:

```bash
# Required
ADMIN_EMAIL=admin@mcpress.com          # Initial admin email
ADMIN_PASSWORD=YourSecurePassword123!   # Initial admin password (12+ chars)
JWT_SECRET_KEY=<generate-random-32-char-string>  # JWT signing key

# Already configured (verify these exist)
DATABASE_URL=<your-postgresql-url>      # PostgreSQL connection string
OPENAI_API_KEY=<your-openai-key>       # For chat functionality
```

**Generate JWT_SECRET_KEY:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

#### Database Setup
The admin tables will be created automatically on first deployment when the backend starts.

#### Deploy Backend
1. Push your code to GitHub
2. Railway will auto-deploy from your repository
3. Check Railway logs to confirm admin user creation:
   ```
   ✅ Created default admin user: admin@mcpress.com
   ```

### 2. Netlify Frontend Setup

#### Environment Variables
Add to Netlify environment variables (Site Settings > Environment Variables):

```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app  # Your Railway backend URL
```

#### Deploy Frontend
1. Push code to GitHub
2. Netlify will auto-build and deploy
3. Admin login will be available at: `https://your-site.netlify.app/admin/login`

## Testing Production Deployment

### 1. Verify Backend
```bash
# Test auth endpoint
curl https://your-app.railway.app/api/admin/verify

# Should return 401 (no auth) - this means it's working
```

### 2. Test Admin Login
1. Navigate to: `https://your-site.netlify.app/admin/login`
2. Login with credentials set in Railway env vars
3. You should be redirected to `/admin/dashboard`

### 3. Verify Protected Routes
- Try accessing `/admin/dashboard` without logging in
- Should redirect to `/admin/login`

## Creating Additional Admin Users

### Option 1: Via API (After First Admin Login)
```bash
# Login first to get token
curl -X POST https://your-app.railway.app/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mcpress.com","password":"YourSecurePassword123!"}'

# Use the token to create new admin
curl -X POST https://your-app.railway.app/api/admin/create-user \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"david@mcpress.com","password":"AnotherSecure123!@#"}'
```

### Option 2: Direct Database (Railway Dashboard)
```sql
-- Connect to your Railway PostgreSQL
-- Use the create_admin.py logic but run SQL directly
INSERT INTO admin_users (email, password_hash, created_at, is_active)
VALUES ('david@mcpress.com', '<bcrypt-hash>', NOW(), true);
```

## Security Checklist

- [ ] JWT_SECRET_KEY is unique and secure (not the default)
- [ ] ADMIN_PASSWORD meets requirements (12+ chars, mixed case, numbers, special)
- [ ] DATABASE_URL is using SSL connection
- [ ] HTTPS enabled on both Railway and Netlify
- [ ] CORS properly configured (not using wildcard in production)
- [ ] Rate limiting is active (5 attempts per 15 minutes)

## Monitoring

### Check Admin Activity
```sql
-- In Railway PostgreSQL dashboard
SELECT email, last_login, created_at 
FROM admin_users;

SELECT COUNT(*) as active_sessions 
FROM admin_sessions 
WHERE expires_at > NOW();
```

### View Logs
- **Railway**: Dashboard > Your Service > Logs
- **Netlify**: Site Dashboard > Functions > Logs

## Troubleshooting

### "Invalid email or password"
- Check credentials match Railway env vars exactly
- Password must be 12+ characters
- Verify DATABASE_URL is set correctly

### "Too many login attempts"
- Rate limiting triggered (5 attempts per 15 min)
- Wait 15 minutes or restart Railway service to reset

### Admin user not created on deployment
- Check Railway logs for errors
- Verify ADMIN_EMAIL and ADMIN_PASSWORD env vars are set
- Manually run SQL to create user if needed

### Frontend can't connect to backend
- Verify NEXT_PUBLIC_API_URL in Netlify matches Railway URL
- Check CORS settings in backend
- Ensure Railway service is running

## Rollback Plan

If issues occur:

1. **Disable Admin Routes:**
   - Set env var: `DISABLE_ADMIN=true` in Railway
   - Redeploy

2. **Clear Sessions:**
   ```sql
   DELETE FROM admin_sessions;
   ```

3. **Reset Admin Password:**
   ```sql
   UPDATE admin_users 
   SET password_hash = '<new-bcrypt-hash>' 
   WHERE email = 'admin@mcpress.com';
   ```

## Next Steps

After successful deployment:
1. Change the default admin password
2. Create individual admin accounts for each user
3. Delete the default admin account
4. Set up monitoring/alerting for failed login attempts
5. Consider implementing 2FA in the future

---

**Note**: Since the site isn't public yet and has no active users, you can safely test these features in production. Just ensure you change credentials before any public launch.