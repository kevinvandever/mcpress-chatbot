# Password Reset Email Setup Guide

## Status
The password reset feature code is fully implemented and deployed (see `.kiro/specs/chatmaster-password-auth/`). It just needs the email service configured via environment variables to start working.

## Email Provider: SendGrid (Free Tier)
- Account created
- Free tier: 100 emails/day
- Docs: https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api

## SendGrid Setup Steps

1. **Create an API Key** in SendGrid dashboard:
   - Go to Settings → API Keys → Create API Key
   - Choose "Restricted Access" and enable only "Mail Send"
   - Copy the key (starts with `SG.`) — you won't see it again

2. **Verify a Sender Identity**:
   - Go to Settings → Sender Authentication
   - Either verify a single sender email (quick) or authenticate your domain (better for deliverability)
   - Recommended sender: `noreply@mcpressonline.com` (requires domain auth) or use a verified personal email for testing

## Railway Environment Variables

### Staging (`mcpress-chatbot-staging`)
| Variable | Value |
|----------|-------|
| `EMAIL_SMTP_HOST` | `smtp.sendgrid.net` |
| `EMAIL_SMTP_PORT` | `587` |
| `EMAIL_FROM_ADDRESS` | Your verified sender email |
| `EMAIL_SMTP_PASSWORD` | Your SendGrid API key (`SG.xxx`) |
| `FRONTEND_URL` | `https://staging--mc-chatmaster.netlify.app` |

### Production (`mcpress-chatbot-production`)
| Variable | Value |
|----------|-------|
| `EMAIL_SMTP_HOST` | `smtp.sendgrid.net` |
| `EMAIL_SMTP_PORT` | `587` |
| `EMAIL_FROM_ADDRESS` | Same verified sender email |
| `EMAIL_SMTP_PASSWORD` | Same SendGrid API key |
| `FRONTEND_URL` | `https://mc-chatmaster.netlify.app` |

## Testing

Once env vars are set on staging:

1. Go to `https://staging--mc-chatmaster.netlify.app/login`
2. Click "Forgot Password?"
3. Enter an email that has a ChatMaster account
4. Check inbox for reset email (check spam too)
5. Click the reset link — should go to staging frontend
6. Set a new password and verify login works

## How It Works (Already Built)

- `POST /api/auth/forgot-password` — generates a secure token, sends email with reset link
- `POST /api/auth/validate-reset-token` — checks if token is valid/expired
- `POST /api/auth/reset-password` — validates new password, updates hash, invalidates token
- Rate limited: 3 reset requests per email per hour
- Tokens expire after 1 hour
- Same success response whether email exists or not (prevents enumeration)

## Related Files
- `backend/email_service.py` — SMTP email sending
- `backend/reset_token_service.py` — token generation/validation
- `backend/subscription_auth_routes.py` — forgot-password and reset-password routes
- `frontend/app/forgot-password/page.tsx` — forgot password UI
- `frontend/app/reset-password/page.tsx` — reset password UI

## Notes
- No code changes needed — just add the env vars and test
- The backend logs a warning at startup if email vars are missing and disables the feature gracefully
- SendGrid SMTP username is always `apikey` (literal string) — but our code uses `EMAIL_SMTP_PASSWORD` for the API key directly
