# Deployment Guide for Bar & Bartender

This guide covers multiple deployment options for your Flask application.

## Pre-Deployment Checklist

### 1. Update Configuration for Production

Before deploying, you need to:

- Set a secure `SECRET_KEY` (currently using default)
- Consider migrating from SQLite to PostgreSQL (recommended for production)
- Set up environment variables for sensitive data

### 2. Create Production Config

Updated `config.py` to support production environment variables.

--

## Deployment Options

### Option 1: Render (Recommended for Beginners) ⭐

**Pros:** Free tier, easy setup, PostgreSQL support, automatic HTTPS

**Steps:**

1. **Create account:** Sign up at [render.com](https://render.com)

2. **Create a PostgreSQL database:**
   - Dashboard → New → PostgreSQL
   - Copy the Internal Database URL

3. **Update config.py** to support environment variables:

   python
   import os

   class Config:
       SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey'
       SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///bar_bartender.db')
       # Handle Render's PostgreSQL URL format
       if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
           SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
       SQLALCHEMY_TRACK_MODIFICATIONS = False
       UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
       MAX_CONTENT_LENGTH = 16 * 1024 * 1024
       ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

4. **Create `render.yaml`** in your project root:

   yaml
   services:
     - type: web
       name: bar-and-bartender
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: gunicorn app:app
       envVars:
         - key: SECRET_KEY
           generateValue: true
         - key: DATABASE_URL
           fromDatabase:
             name: bar-bartender-db
             property: connectionString
       healthCheckPath: /

5. **Add `gunicorn` to requirements.txt:**

   text
   gunicorn==21.2.0

6. **Create `.gitignore`** if not exists:

   gitignore
   venv/
   __pycache__/
   *.pyc
   instance/
   .env
   *.db

7. **Push to GitHub** and connect to Render

---

### Option 2: Railway

**Pros:** Free tier, simple setup, PostgreSQL included

**Steps:**

1. Sign up at [railway.app](https://railway.app)

2. **Update config.py** (same as Render above)

3. **Create `Procfile`:**

    text
   web: gunicorn app:app
    

4. **Add `gunicorn` to requirements.txt**

5. Push to GitHub and connect Railway to your repo

6. Add environment variables in Railway dashboard:
   - `SECRET_KEY` (generate a random string)
   - `DATABASE_URL` (automatically provided if you add PostgreSQL)

---

### Option 3: PythonAnywhere

**Pros:** Free tier, good for beginners, web-based console

**Steps:**

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)

2. Upload your code via Files tab or Git

3. **Create a Web app:**
   - Dashboard → Web → Add a new web app
   - Choose Flask and Python version

4. **Configure WSGI:**
   - Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:

    python
   import sys
   path = '/home/yourusername/path/to/Bar&Bartender'
   if path not in sys.path:
       sys.path.append(path)
   
   from app import app as application
    

5. **Set up virtual environment** and install dependencies

6. **Configure static files** mapping:
   - `/static/` → `/home/yourusername/path/to/Bar&Bartender/static/`

---

### Option 4: DigitalOcean App Platform

**Pros:** Reliable, scalable, good documentation

**Steps:**

1. Sign up at [digitalocean.com](https://www.digitalocean.com)

2. Create an App via the dashboard

3. Connect your GitHub repository

4. Add PostgreSQL database component

5. Set environment variables

6. DigitalOcean will auto-detect Flask and deploy

---

## Required Changes for Production

### 1. Update requirements.txt

Add production server:

 text
gunicorn==21.2.0
 

If migrating to PostgreSQL:

 text
psycopg2-binary==2.9.9
 

### 2. Create .gitignore

 gitignore
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
instance/
.env
*.db
.DS_Store
static/uploads/*
!static/uploads/.gitkeep
 

### 3. Generate Secure Secret Key

Run this in Python:

 python
import secrets
print(secrets.token_hex(32))
 

Use this as your `SECRET_KEY` environment variable.

### 4. Database Migration (SQLite to PostgreSQL)

If you want to migrate your existing SQLite data:

1. Install `alembic` for migrations:

    bash
   pip install alembic psycopg2-binary
    

2. Or use a simpler approach - export/import via CSV or use SQLAlchemy to copy data programmatically.

---

## Post-Deployment

1. **Test all features:** Login, uploads, database operations
2. **Set up backups:** Configure automatic database backups
3. **Monitor logs:** Check for errors in the hosting platform's logs
4. **Set up domain:** Configure custom domain if needed

---

## Troubleshooting

### File Uploads Not Working

- Ensure `static/uploads/` directory has write permissions
- Check MAX_CONTENT_LENGTH setting
- Verify file paths are correct

### Database Errors

- Ensure DATABASE_URL is correctly set
- Check database connection limits
- Verify tables are created (run migrations)

### Static Files Not Loading

- Verify static file mapping in hosting platform
- Check file paths in templates
- Ensure `url_for('static', ...)` is used correctly

---

## Recommended: Render Setup (Detailed)

This is the easiest option to get started:

1. **Prepare your code:**

    bash
   # Add gunicorn
   echo "gunicorn==21.2.0" >> requirements.txt
   
   # Commit everything
   git init
   git add .
   git commit -m "Initial commit"
   
   # Push to GitHub
    

2. **On Render:**
   - New → Web Service
   - Connect GitHub repo
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Add environment variables:
     - `SECRET_KEY`: (generate one)
     - `DATABASE_URL`: (from PostgreSQL service)

3. **Create PostgreSQL:**
   - New → PostgreSQL
   - Copy connection string to DATABASE_URL

Your app will be live at `https://your-app.onrender.com`
