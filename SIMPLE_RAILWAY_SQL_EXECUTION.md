# Simple Railway SQL Execution Guide

You're logged into Railway CLI and ready to fix the author issues. Here's the simplest approach:

## Step 1: Execute the SQL Script

Since you're already logged in with `railway login --browserless`, run this single command:

```bash
railway run psql $DATABASE_URL -f complete_author_audit_corrections.sql
```

If that doesn't work, try this alternative:

```bash
railway shell
```

Then inside the Railway shell:
```bash
psql $DATABASE_URL -f complete_author_audit_corrections.sql
```

## Step 2: Verify It Worked

After the SQL executes, test the chat interface:

1. Go to your chatbot: https://mcpress-chatbot-frontend.netlify.app
2. Ask: "Complete CL programming"
3. Should now show "Ted Holt" instead of "annegrubb"
4. Ask: "Subfiles RPG" 
5. Should now show "Kevin Vandever" instead of "admin"

## What This Fixes

- ✅ **Complete CL: Sixth Edition** → Ted Holt (not annegrubb)
- ✅ **Subfiles in Free-Format RPG** → Kevin Vandever (not admin)  
- ✅ **Control Language Programming** → Jim Buck, Bryan Meyers, Dan Riehl (not just Jim Buck)
- ✅ **All 115 books** → Correct authors from CSV

## If You Get Stuck

The SQL script is safe - it only fixes author associations, doesn't delete any books or break anything. If it fails partway through, you can run it again (it has safety checks).

**Just run the command and let me know if you see any errors!**