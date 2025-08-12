# 🔧 Fix Data Persistence - Railway Volume Setup

## The Problem
Your ChromaDB data gets erased after each deployment because it's stored in ephemeral `/app/data` instead of a persistent Railway volume.

## The Solution
Set up a Railway volume to persist your data across deployments.

## Step 1: Create Railway Volume

1. **Go to Railway Dashboard** → Your Project → Your Backend Service
2. **Click "Settings"** in the left sidebar
3. **Click "Volumes"** tab
4. **Click "+ Add Volume"** button
5. **Configure the volume:**
   - **Mount Path**: `/data` (exactly this)
   - **Size**: `2 GB` (sufficient for 115+ documents + backups)
6. **Click "Create Volume"**

## Step 2: Deploy the Fix

Push the code changes (already done):

```bash
git add -A
git commit -m "Fix Railway persistence - use volume instead of ephemeral storage"
git push
```

Railway will automatically redeploy with the volume mounted.

## Step 3: Verify the Fix

After deployment completes, check your Railway logs for these success messages:

```
✅ Using Railway VOLUME (persistent) at /data
✅ Railway VOLUME found at /data
✅ Volume /data is writable
✅ ChromaDB directory exists: /data/chroma_db
```

**BAD messages that indicate the volume isn't set up:**
```
❌ NO RAILWAY VOLUME FOUND!
⚠️ Using Railway ephemeral storage at /app/data
❌ WARNING: Data will be LOST on redeploys!
```

## Step 4: Re-upload Your Documents (One Time Only)

Since your current data is in the ephemeral location, you'll need to upload once more:

```bash
python simple_railway_upload.py
```

## Step 5: Test Persistence

To verify it's working:

1. **Force a redeploy** (push a small change or redeploy in Railway dashboard)
2. **Check document count** at your app URL
3. **Should still show 115 documents** after redeploy

## Alternative Volume Mount Paths

If `/data` doesn't work, try these alternatives in Railway:

- `/mnt/data` 
- `/persistent`
- `/storage`

The code will automatically detect whichever path you use.

## Emergency Recovery

If you lose data again, use the backup system:

```bash
# Check available backups
curl https://your-railway-url.railway.app/backup/list

# Restore latest backup  
curl -X POST "https://your-railway-url.railway.app/backup/restore?backup_name=latest"
```

## Success Indicators

✅ **Persistent volume mounted**  
✅ **Documents survive redeploys**  
✅ **No more "data will be lost" warnings**  
✅ **Backup system active**

## If It Still Doesn't Work

1. Check Railway logs for volume mount messages
2. Try different mount path (`/mnt/data`)
3. Contact me - might need PostgreSQL fallback

**After following these steps, your 115 documents will NEVER be lost again!** 🛡️