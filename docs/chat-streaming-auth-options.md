# Chat Streaming & Auth Architecture Options

## The Problem

The freemium usage gate requires authenticated `/chat` requests. The frontend (Netlify) and backend (Railway) are on different domains. The `session_token` cookie is `httpOnly` and `sameSite: lax`, set on the Netlify domain — it never gets sent cross-origin to Railway.

Current solution: a Next.js API route proxy (`/api/chat`) reads the cookie server-side and forwards it to Railway. This works but adds a hop that buffers SSE chunks, making the streaming response feel clunkier than the direct connection on production (pre-freemium).

## Options

### Option 1: Bearer Token Auth (Recommended)

Send JWT in `Authorization` header directly to Railway instead of relying on cookies.

**How it works:**
- Backend returns JWT in login/register response body (in addition to cookie)
- Frontend stores token in memory (React context) or `sessionStorage`
- Chat and other API calls go directly to Railway with `Authorization: Bearer <token>` header
- Backend accepts token from either header or cookie (backward compatible)
- CORS configured to allow Netlify origin + Authorization header

**Pros:**
- Eliminates proxy hop — direct SSE streaming restored
- Smooth token-by-token chat response (like pre-freemium)
- Incremental migration possible (start with `/chat` only)
- No infrastructure changes needed
- ~8-12 files changed

**Cons:**
- Token in memory doesn't survive page refresh (need sessionStorage or cookie fallback for page loads)
- sessionStorage is accessible to XSS (acceptable for most apps, but less secure than httpOnly cookies)
- Need CORS configuration on Railway backend
- Dual auth path (header + cookie) adds some complexity

**Effort:** Medium (1-2 days)

---

### Option 2: Move to Vercel

Replace Netlify with Vercel for frontend hosting. Vercel's edge runtime handles SSE streaming from API routes better.

**How it works:**
- Same proxy pattern, but Vercel's edge functions stream more efficiently
- Minimal code changes (mostly config)

**Pros:**
- Better SSE streaming performance than Netlify serverless
- Next.js is Vercel's native framework — better optimization
- Same deployment model (git push to deploy)
- Edge functions run closer to users

**Cons:**
- Still has the proxy hop (just faster)
- Migration effort for DNS, environment variables, build config
- Potential cost differences at scale
- Vendor lock-in to Vercel

**Effort:** Medium (1 day migration + testing)

---

### Option 3: Same-Domain via Cloudflare

Put both Netlify and Railway behind a single domain using Cloudflare as reverse proxy.

**How it works:**
- `chatmaster.com` → Cloudflare → Netlify (frontend)
- `chatmaster.com/api` → Cloudflare → Railway (backend)
- Cookies work natively since everything is same-domain
- No proxy routes needed

**Pros:**
- Cookies just work — no proxy, no bearer tokens
- Direct SSE streaming
- Cloudflare free tier is generous
- Added DDoS protection and caching
- Clean URL structure

**Cons:**
- Requires custom domain setup
- Cloudflare configuration complexity (Workers or Page Rules)
- Another piece of infrastructure to manage
- DNS propagation during setup

**Effort:** Medium (1 day setup + DNS propagation)

---

### Option 4: AWS Full Stack

Migrate everything to AWS under one domain.

**How it works:**
- CloudFront (CDN) → S3/Amplify (frontend) + API Gateway/ECS (backend)
- RDS PostgreSQL with pgvector
- Everything under one domain, cookies work natively

**Pros:**
- Full control over infrastructure
- Scales well for many users
- Native WebSocket support via API Gateway
- Enterprise-grade reliability
- Same-domain = no cookie issues

**Cons:**
- Significant migration effort
- More infrastructure to manage (IAM, VPC, etc.)
- Higher learning curve
- Cost can be unpredictable without careful configuration
- Overkill for current stage

**Effort:** High (1-2 weeks)

---

### Option 5: Keep Current Proxy (Status Quo)

Leave the Next.js proxy in place. Accept the streaming tradeoff.

**Pros:**
- Already working
- No additional development needed
- Secure (httpOnly cookies)
- Simple architecture

**Cons:**
- Clunkier SSE streaming (chunked delivery)
- Extra latency on every chat message
- More proxy routes to maintain as features grow

**Effort:** None

---

## Recommendation

If tester feedback confirms the streaming feel is a problem:

1. **Start with Option 1 (Bearer Token)** — quickest path to smooth streaming with minimal infrastructure change. Can be done incrementally, starting with just the `/chat` endpoint.

2. **Consider Option 3 (Cloudflare)** if you're planning a custom domain anyway — solves the problem cleanly at the infrastructure level.

3. **Option 4 (AWS)** makes sense later if the product grows and you need more control, but it's premature for the current stage.
