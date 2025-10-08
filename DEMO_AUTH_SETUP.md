# Demo Password Protection Setup

**Created:** October 8, 2025
**Purpose:** Replace Netlify Pro password protection with custom authentication to save $20/mo

---

## 🎯 What This Does

Adds a simple password protection screen to your entire site, allowing you to:
- ✅ Share demo with business partner securely
- ✅ Downgrade from Netlify Pro ($19/mo) to Starter ($0/mo)
- ✅ **Save $20/month ($240/year)**

---

## 🚀 Deployment Steps

### Step 1: Set Environment Variable in Netlify

**Important:** You need to set your demo password in Netlify before deploying!

1. Go to Netlify Dashboard → Your site
2. Navigate to: **Site settings → Environment variables**
3. Click **Add a variable**
4. Add:
   ```
   Key: DEMO_PASSWORD
   Value: YourSecurePassword123!
   ```
   (Replace with your own secure password - share this with your biz partner)

5. **Important:** Select "Same value for all" (or set differently for deploy contexts if needed)
6. Click **Save**

---

### Step 2: Deploy to Netlify

The code is ready to commit and deploy:

```bash
cd /Users/kevinvandever/kev-dev/mcpress-chatbot
git add frontend/
git commit -m "Add demo password protection to replace Netlify Pro feature"
git push origin main
```

Netlify will automatically:
- Detect the changes
- Build the new version
- Deploy with password protection enabled

---

### Step 3: Test the Protection

1. Visit your site: `https://mcpress-chatbot.netlify.app`
2. You should be **redirected to `/login`**
3. Enter the password you set in Step 1
4. Click "Access Demo"
5. You should be redirected to the main chatbot
6. **Test logout button** (top right) - should return to login

---

### Step 4: Downgrade Netlify Plan

**Only after confirming Step 3 works!**

1. Go to Netlify Dashboard → Your team/account
2. Navigate to: **Billing**
3. Click on your current plan (Pro - $19/mo)
4. Select **Downgrade to Starter**
5. Confirm downgrade

**Result:** Billing changes to $0/mo on next cycle 🎉

---

## 🔐 How It Works

### Architecture:

```
User visits site
    ↓
Middleware checks for 'demo_auth' cookie
    ↓
    ├─ Cookie exists? → Allow access
    └─ No cookie? → Redirect to /login
              ↓
         Enter password
              ↓
         POST to /api/auth/login
              ↓
         Password correct?
              ↓
              ├─ Yes → Set cookie, redirect to home
              └─ No → Show error
```

### Security Features:

- ✅ **HTTP-only cookies** (can't be accessed by JavaScript)
- ✅ **Secure flag** (HTTPS only in production)
- ✅ **7-day expiration** (session expires after 1 week)
- ✅ **Server-side validation** (middleware runs on server)
- ✅ **Environment variable** (password not in code)

### Files Created/Modified:

**New files:**
- `frontend/app/login/page.tsx` - Login UI
- `frontend/app/api/auth/login/route.ts` - Login API
- `frontend/app/api/auth/logout/route.ts` - Logout API
- `frontend/.env.local` - Local dev password

**Modified files:**
- `frontend/middleware.ts` - Auth protection logic
- `frontend/app/page.tsx` - Added logout button
- `frontend/.env.production` - Demo password placeholder

---

## 🔧 Configuration

### Change Password

**In Netlify:**
1. Site settings → Environment variables
2. Edit `DEMO_PASSWORD`
3. Save (triggers automatic redeploy)

### Change Session Duration

Edit `frontend/app/api/auth/login/route.ts`:

```typescript
maxAge: 60 * 60 * 24 * 7, // 7 days (in seconds)
```

Change `7` to number of days you want.

### Disable Password Protection

If you want to remove password protection later:

1. Delete or comment out the auth check in `middleware.ts`:
   ```typescript
   export function middleware(request: NextRequest) {
     return NextResponse.next(); // Allow all requests
   }
   ```

2. Deploy changes

---

## 🐛 Troubleshooting

### Issue: "Redirect loop" or constant login screen

**Cause:** Cookie not being set properly

**Fix:**
1. Clear browser cookies for your site
2. Check Netlify environment variables are set correctly
3. Verify `DEMO_PASSWORD` is set (no typos)
4. Try in incognito/private browsing mode

---

### Issue: "Login works but redirects to /login again"

**Cause:** Middleware matcher pattern issue

**Fix:**
Check `middleware.ts` config excludes static files:
```typescript
matcher: [
  '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
]
```

---

### Issue: Password not working

**Possible causes:**
1. **Typo in password** - Check Netlify env var exactly matches what you're typing
2. **Environment variable not deployed** - Redeploy after setting env var
3. **Case sensitivity** - Password is case-sensitive
4. **Spaces** - Check for accidental spaces in env var value

**Debug:**
Check Netlify deploy logs for environment variable confirmation.

---

## 💡 Future Enhancements

If you want to make this more sophisticated later:

1. **Multiple users** - Add user accounts with email/password in database
2. **JWT tokens** - More secure token-based auth
3. **OAuth** - Google/GitHub login
4. **Rate limiting** - Prevent brute force attacks
5. **2FA** - Two-factor authentication
6. **User roles** - Admin vs regular user permissions
7. **Session management** - View/revoke active sessions

For now, simple password is perfect for demo purposes!

---

## 📊 Cost Savings Summary

| Before | After | Savings |
|--------|-------|---------|
| Netlify Pro ($19/mo) | Netlify Starter ($0/mo) | **$19/mo** |
| Netlify password protection | Custom auth | **$228/year** |

---

## 📞 Support

**Password forgotten?**
- Check your password manager or where you saved it
- Or reset by updating `DEMO_PASSWORD` in Netlify env vars

**Questions?**
- Kevin Vandever: kevin@kevinvandever.com

---

**Document Version:** 1.0
**Last Updated:** October 8, 2025
