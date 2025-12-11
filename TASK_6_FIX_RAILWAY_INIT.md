# Task 6: Fix Railway Initialization Issue

## Problem
The Railway deployment was failing during initialization because:
1. `asyncio.run()` was being called during module import (not allowed in async context)
2. Services were being initialized synchronously during module load
3. Variables were not properly scoped for later use

## Solution
Moved all service initialization to the `startup_event()` async function:
- Author services now initialize during app startup (async context)
- Routers are registered dynamically after services are ready
- All variables properly declared at module level

## Changes Made

### backend/main.py
1. Declared `author_service`, `doc_author_service`, and availability flags at module level
2. Removed synchronous `asyncio.run()` calls during import
3. Moved all initialization to `startup_event()` function
4. Routers are now registered during startup after services are initialized

## Deploy and Test

```bash
# Commit the fix
git add backend/main.py TASK_6_FIX_RAILWAY_INIT.md
git commit -m "Fix: Move author service initialization to startup event

- Remove asyncio.run() from module import
- Initialize services in async startup_event
- Register routers after services are ready
- Fixes Railway initialization hang"

# Push to Railway
git push origin main
```

## Verification

After deployment, check:
1. Railway logs show successful initialization
2. All services print "✅" messages
3. Test endpoint is accessible: `/test-task-6/run-property-tests`

## Expected Log Output

```
✅ Author routes loaded
✅ Document-author routes loaded
✅ Task 6 test endpoint loaded
...
🚀 Pre-loading documents cache...
✅ Documents cache ready - X documents loaded!
✅ Author management endpoints enabled at /api/authors/*
✅ Document-author relationship endpoints enabled at /api/documents/*
✅ Task 6 test endpoints enabled at /test-task-6/*
```
