# Railway Data Persistence Setup Guide

## 🚨 CRITICAL: Prevent Data Loss Forever

Your chatbot keeps losing 110 processed documents because Railway's default `/app/data` persistence isn't reliable across all deployment types. Here's the bulletproof solution:

## Option 1: Railway Volumes (Recommended) 🏆

### Step 1: Create Railway Volume
```bash
# In your Railway project dashboard:
1. Go to your backend service
2. Click "Settings" → "Volumes" 
3. Click "+ Add Volume"
4. Mount Path: `/mnt/data`
5. Size: 2GB (sufficient for 110 documents + backups)
```

### Step 2: Update Environment Variables
```bash
# No changes needed - the code automatically detects and uses the volume
```

### Step 3: Deploy and Migrate Data
```bash
# The system will automatically:
1. Detect the volume at /mnt/data
2. Create automatic backups on startup
3. Store all data persistently across deployments
```

## Option 2: External Storage (Most Reliable) 🔒

If Railway volumes aren't available, use cloud storage:

### AWS S3 Setup
```bash
# Environment Variables to add:
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=mcpress-chatbot-data
AWS_REGION=us-east-1
```

### Google Cloud Storage Setup
```bash
# Environment Variables to add:
GOOGLE_CLOUD_PROJECT=your_project
GOOGLE_CLOUD_BUCKET=mcpress-chatbot-data
# Upload service account JSON as GOOGLE_CREDENTIALS
```

## 🔄 New Backup System

### Automatic Backups
- ✅ **Startup backup**: Creates backup if data exists
- ✅ **Scheduled backups**: Before major operations
- ✅ **Keeps 5 recent backups**: Automatic cleanup
- ✅ **Compressed format**: Efficient storage

### Manual Backup Commands
```bash
# Create backup
curl -X POST https://your-railway-url.up.railway.app/backup/create

# List backups
curl https://your-railway-url.up.railway.app/backup/list

# Restore backup
curl -X POST "https://your-railway-url.up.railway.app/backup/restore?backup_name=mcpress_backup_20250811_134503.zip"
```

### Frontend Integration (Optional)
Add backup/restore buttons to your admin interface for easy management.

## 🛡️ Data Loss Prevention Checklist

- [ ] Railway volume mounted at `/mnt/data`
- [ ] Automatic backups enabled
- [ ] Environment variables correctly set
- [ ] Test deployment with sample data
- [ ] Verify data persists after redeploy

## 🚀 Deployment Steps

1. **Create Railway Volume** (2GB at `/mnt/data`)
2. **Deploy updated code** (includes backup system)
3. **Upload your 110 documents** (one-time)
4. **Test redeploy** to verify persistence
5. **Set up monitoring** to catch future issues

## 🔧 Troubleshooting

### If data is still lost:
```bash
# Check volume mounting
curl https://your-url.up.railway.app/health

# Check backup status  
curl https://your-url.up.railway.app/backup/list

# Restore latest backup
curl -X POST "https://your-url.up.railway.app/backup/restore?backup_name=latest"
```

### Warning Signs
- ⚠️ "WARNING: No Railway volume found" in logs
- ⚠️ "using ephemeral storage" messages
- ⚠️ Document count drops to 0 after redeploy

## 📞 Emergency Recovery

If you lose data again:
1. Check `/backup/list` endpoint for available backups
2. Use `/backup/restore` with the most recent backup
3. Re-run your document upload process as last resort

This system ensures your 110 processed documents are NEVER lost again! 🛡️