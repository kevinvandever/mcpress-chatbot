# Ingestion Monitoring & Notifications

## How the Ingestion Runs

- **Schedule**: 1st of each month at 3:00 AM UTC (configurable in `backend/ingestion_scheduler.py`)
- **On-demand**: `POST /api/ingestion/trigger` (requires admin auth)
- **Status check**: `GET /api/ingestion/status` (most recent run)
- **History**: `GET /api/ingestion/history` (paginated audit trail)

---

## Option 1: Manual Monitoring (Available Now)

Check the most recent run:
```bash
curl -s "https://mcpress-chatbot-production.up.railway.app/api/ingestion/status" \
  -H "Authorization: Bearer <admin-token>"
```

Check run history:
```bash
curl -s "https://mcpress-chatbot-production.up.railway.app/api/ingestion/history?limit=5" \
  -H "Authorization: Bearer <admin-token>"
```

Get an admin token:
```bash
curl -s -X POST "https://mcpress-chatbot-production.up.railway.app/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mcpressonline.com","password":"YOUR_PASSWORD"}'
```

---

## Option 2: Slack Webhook Notifications (Recommended)

Posts a summary to a Slack channel after each ingestion run.

### Setup Steps

1. Go to https://api.slack.com/apps
2. Create a new app → "From scratch" → name it something like "MC ChatMaster Bot"
3. Select your workspace
4. Go to **Incoming Webhooks** → toggle ON
5. Click **Add New Webhook to Workspace**
6. Pick the channel for notifications (e.g., `#ingestion-alerts`)
7. Copy the webhook URL (format: `https://hooks.slack.com/services/T.../B.../xxx`)
8. Add to Railway as environment variable: `SLACK_WEBHOOK_URL`

### What You'll Get

After each run (scheduled or manual), a Slack message like:

> ✅ **Ingestion Run Completed**
> - Discovered: 6,500 files
> - Skipped: 6,445 (already in database)
> - Processed: 55 new articles
> - Failed: 0
> - Duration: 6m 42s

Or if something fails:

> ❌ **Ingestion Run Failed**
> - Stage: discovery
> - Error: FTP connection timed out
> - Duration: 1m 03s

### Implementation

Once `SLACK_WEBHOOK_URL` is set, ask Kiro to wire it into the ingestion scheduler. The code change is small — just a POST to the webhook URL with the run result after `run_ingestion()` completes.

---

## Option 3: Email Notifications

Sends an email summary after each run.

### Setup Steps

Requires SMTP credentials. Add these Railway env vars:

| Variable | Example | Notes |
|----------|---------|-------|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | Usually 587 (TLS) or 465 (SSL) |
| `SMTP_USER` | `alerts@yourdomain.com` | SMTP username |
| `SMTP_PASSWORD` | `app-password` | SMTP password or app password |
| `ALERT_EMAIL_TO` | `kevin@kevinvandever.com` | Recipient |

For Gmail: use an App Password (not your regular password). Go to Google Account → Security → 2-Step Verification → App Passwords.

For SendGrid: use `smtp.sendgrid.net`, port 587, username `apikey`, password is your SendGrid API key.

---

## Environment Variables Summary

| Variable | Required For | Description |
|----------|-------------|-------------|
| `FTP_HOST` | Ingestion | FTP server IP (default: 209.142.66.171) |
| `FTP_PORT` | Ingestion | FTP port (default: 21) |
| `FTP_USER` | Ingestion | FTP username |
| `FTP_PASSWORD` | Ingestion | FTP password |
| `FTP_REMOTE_DIR` | Ingestion | Remote directory (default: /) |
| `SLACK_WEBHOOK_URL` | Slack alerts | Slack incoming webhook URL |
| `SMTP_HOST` | Email alerts | SMTP server hostname |
| `SMTP_PORT` | Email alerts | SMTP port |
| `SMTP_USER` | Email alerts | SMTP username |
| `SMTP_PASSWORD` | Email alerts | SMTP password |
| `ALERT_EMAIL_TO` | Email alerts | Notification recipient |

---

## Changing the Schedule

Edit `backend/ingestion_scheduler.py`, the `CronTrigger` line:

```python
# Monthly on the 1st at 3:00 AM UTC (current)
CronTrigger(day=1, hour=3, minute=0)

# Weekly on Sundays at 3:00 AM UTC
CronTrigger(day_of_week="sun", hour=3, minute=0)

# Daily at 3:00 AM UTC
CronTrigger(hour=3, minute=0)

# Every 6 hours
CronTrigger(hour="*/6", minute=0)
```

Requires a deploy after changing.
