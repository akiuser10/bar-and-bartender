# Railway Deployment Guide for Bar & Bartender

## Quick Setup on Railway

Railway is simpler than Render - it auto-detects Flask and handles most configuration automatically!

### Step 1: Push Your Code to GitHub

Make sure your latest changes (including psycopg3) are pushed:

```bash
git add .
git commit -m "Ready for Railway deployment"
git push
```

### Step 2: Deploy on Railway

1. **Sign up/Login**: Go to [railway.app](https://railway.app)
   - Click "Login" → "Login with GitHub"
   - Authorize Railway to access your repositories

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `bar-and-bartender` repository
   - Railway will automatically detect it's a Flask app

3. **Add PostgreSQL Database**:
   - In your project dashboard, click "+ New"
   - Select "Database" → "Add PostgreSQL"
   - Railway automatically creates the database and sets `DATABASE_URL` environment variable
   - **No manual configuration needed!**

4. **Set Environment Variables**:
   - Click on your web service
   - Go to "Variables" tab
   - Add:
     - **Key**: `SECRET_KEY`
     - **Value**: Generate one with:
       ```bash
       python3 -c "import secrets; print(secrets.token_hex(32))"
       ```
   - `DATABASE_URL` is automatically set by Railway (don't add it manually)

5. **Deploy**:
   - Railway automatically deploys when you push to GitHub
   - Or click "Deploy" in the dashboard
   - Watch the build logs

### Step 3: Get Your Public URL

1. Click on your web service
2. Go to "Settings" tab
3. Under "Domains", you'll see your Railway URL:
   ```
   https://your-app-name.up.railway.app
   ```
4. (Optional) Click "Generate Domain" to get a custom subdomain

## Railway vs Render Differences

✅ **Railway Advantages:**
- Auto-detects Flask (no Procfile needed, but we have one)
- Automatically sets `DATABASE_URL` when you add PostgreSQL
- No sleep/spin-down on free tier (always on)
- Simpler setup process
- $5 free credit/month

✅ **Your App is Ready:**
- `Procfile` is correct: `web: gunicorn app:app`
- `requirements.txt` has all dependencies including `psycopg[binary]==3.2.0`
- `config.py` handles `DATABASE_URL` automatically
- Works with Python 3.13 (psycopg3)

## Troubleshooting

### Build Fails
- Check build logs in Railway dashboard
- Make sure `requirements.txt` is committed
- Verify Python version (Railway auto-detects, but you can specify in `runtime.txt`)

### Database Connection Errors
- Railway automatically sets `DATABASE_URL` - don't add it manually
- Make sure PostgreSQL service is running (green status)
- Check that both services (web + database) are in the same project

### App Crashes
- Check logs in Railway dashboard
- Verify `SECRET_KEY` is set
- Make sure `DATABASE_URL` exists (should be automatic)

### Static Files Not Loading
- Railway handles static files automatically
- Check file paths in templates use `url_for('static', ...)`

## Environment Variables Summary

**Required:**
- ✅ `DATABASE_URL` - Automatically set by Railway (don't add manually)
- ✅ `SECRET_KEY` - You need to add this

**Optional:**
- `FLASK_ENV` - Set to `production` if needed
- `PORT` - Railway sets this automatically

## After Deployment

Your app will be live at your Railway URL:
```
https://your-app-name.up.railway.app
```

**Features:**
- ✅ Accessible from any device
- ✅ HTTPS enabled automatically
- ✅ Always on (no sleep)
- ✅ Automatic deployments on git push

## Monitoring

- **Logs**: Click on your service → "Deployments" → View logs
- **Metrics**: See CPU, memory usage in dashboard
- **Database**: Click on PostgreSQL service to see connection info

## Next Steps

1. Test your deployed app
2. Register a new user
3. Add some products/recipes
4. Share the URL with others!

---

**Need Help?** Railway has excellent documentation: [docs.railway.app](https://docs.railway.app)
