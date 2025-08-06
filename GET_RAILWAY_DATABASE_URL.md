# How to Get Your Railway DATABASE_URL

## Steps:

1. **Go to Railway Dashboard**
   - Visit: https://railway.app/dashboard
   - Log in to your account

2. **Select Your Project**
   - Click on your `pdf-chatbot` or `mc-press-chatbot` project

3. **Click on PostgreSQL Service**
   - You should see a PostgreSQL database service (usually has a database icon)
   - Click on it

4. **Go to "Connect" Tab**
   - Once in the PostgreSQL service, click the "Connect" tab

5. **Copy the DATABASE_URL**
   - You'll see something like:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_HOST.railway.app:PORT/railway
   ```
   - Click the copy button next to it

6. **Create .env File**
   - In your terminal, run:
   ```bash
   echo "DATABASE_URL=YOUR_COPIED_URL_HERE" > .env
   ```
   - Replace YOUR_COPIED_URL_HERE with the actual URL you copied

## Alternative: Using Railway CLI

If you have Railway CLI installed:

```bash
# Login to Railway
railway login

# Link to your project
railway link

# Get the DATABASE_URL
railway variables

# Or connect directly to see the URL
railway connect postgresql
```

## Security Note

⚠️ **NEVER commit the .env file to git!** 

The `.gitignore` should already include `.env`, but double-check:
```bash
grep "\.env" .gitignore
```

Once you have the DATABASE_URL in your .env file, you can run:
```bash
python cleanup_railway_db.py
```