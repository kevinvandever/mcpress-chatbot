# Freemium Usage Export Guide

How to pull free-tier usage reports from MC ChatMaster.

## Quick Start (Export Script)

The easiest way to export data. Handles login and file saving automatically.

```bash
# Set your admin credentials
export ADMIN_EMAIL="your-admin@email.com"
export ADMIN_PASSWORD="your-password"

# Export CSV from production (default)
python3 export_freemium_usage.py

# Export CSV from staging
API_URL="https://mcpress-chatbot-staging.up.railway.app" python3 export_freemium_usage.py
```

This creates a file like `freemium-usage-export-2026-04-30.csv` in the current directory.

### Script Options

```bash
# Export as JSON instead of CSV
python3 export_freemium_usage.py --format json

# Filter by date range
python3 export_freemium_usage.py --start-date 2025-01-01 --end-date 2025-06-30

# Save to a specific file
python3 export_freemium_usage.py --output ~/Desktop/report.csv

# Combine options
python3 export_freemium_usage.py --format json --start-date 2025-01-01 --output ~/Desktop/q1-report.json
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_EMAIL` | Yes | — | Your admin login email |
| `ADMIN_PASSWORD` | Yes | — | Your admin login password |
| `API_URL` | No | `https://mcpress-chatbot-production.up.railway.app` | Backend URL |

## Manual Testing with curl

If you prefer curl, it's a two-step process: login first, then call the export.

### Step 1: Get an auth token

```bash
TOKEN=$(curl -s -X POST "https://mcpress-chatbot-staging.up.railway.app/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "YOUR_EMAIL", "password": "YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo $TOKEN
```

### Step 2: Call the export endpoint

**View CSV in terminal:**
```bash
curl -s "https://mcpress-chatbot-staging.up.railway.app/api/admin/freemium-export" \
  -H "Authorization: Bearer $TOKEN"
```

**Save CSV to file:**
```bash
curl -s "https://mcpress-chatbot-staging.up.railway.app/api/admin/freemium-export" \
  -H "Authorization: Bearer $TOKEN" \
  -o freemium-export.csv
```

**Get JSON format:**
```bash
curl -s "https://mcpress-chatbot-staging.up.railway.app/api/admin/freemium-export?format=json" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Filter by date range:**
```bash
curl -s "https://mcpress-chatbot-staging.up.railway.app/api/admin/freemium-export?start_date=2025-01-01&end_date=2025-06-30" \
  -H "Authorization: Bearer $TOKEN" \
  -o freemium-q1-q2.csv
```

### One-liner (login + export in one command)

```bash
# Save CSV — replace YOUR_EMAIL and YOUR_PASSWORD
curl -s "https://mcpress-chatbot-staging.up.railway.app/api/admin/freemium-export" \
  -H "Authorization: Bearer $(curl -s -X POST 'https://mcpress-chatbot-staging.up.railway.app/api/admin/login' \
    -H 'Content-Type: application/json' \
    -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)[\"access_token\"])')" \
  -o freemium-export.csv
```

## Production vs Staging URLs

| Environment | URL |
|-------------|-----|
| Staging | `https://mcpress-chatbot-staging.up.railway.app` |
| Production | `https://mcpress-chatbot-production.up.railway.app` |

Both environments share the same database, so the export data is identical. Use staging for testing.

## What's in the Export

### CSV Format

The CSV file contains:

1. **Header row:** `email,questions_used,first_seen,last_active`
2. **User rows:** One per free-tier user, sorted by most questions asked first
3. **Summary rows:** After a blank line, prefixed with `#`

Example:
```
email,questions_used,first_seen,last_active
user1@example.com,8,2025-01-15T10:30:00,2025-06-20T14:22:00
user2@example.com,5,2025-02-01T09:00:00,2025-06-18T11:15:00

# Summary
# total_free_users,142
# reached_soft_warning,45
# reached_strong_warning,30
# reached_limit,22
# average_questions_used,4.3
# questions_limit,8
```

### JSON Format

```json
{
  "users": [
    {
      "email": "user1@example.com",
      "questions_used": 8,
      "first_seen": "2025-01-15T10:30:00",
      "last_active": "2025-06-20T14:22:00"
    }
  ],
  "summary": {
    "total_free_users": 142,
    "reached_soft_warning": 45,
    "reached_strong_warning": 30,
    "reached_limit": 22,
    "average_questions_used": 4.3,
    "questions_limit": 8
  }
}
```

### Summary Fields Explained

| Field | Meaning |
|-------|---------|
| `total_free_users` | Total users who started with free questions |
| `reached_soft_warning` | Users who hit 6+ questions (soft warning shown) |
| `reached_strong_warning` | Users who hit 7+ questions (strong warning shown) |
| `reached_limit` | Users who hit 8+ questions (paywall reached) |
| `average_questions_used` | Average questions asked across all free users |
| `questions_limit` | Current free question limit (from `FREE_QUESTION_LIMIT` env var) |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required` | Missing credentials | Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` env vars |
| `Authentication failed: 401` | Wrong credentials | Check your admin email and password |
| `Connection error` | Server unreachable | Check the API_URL and that Railway is running |
| `Not authenticated` (in browser) | No auth token | Use the script or curl with a Bearer token — can't test in browser directly |
