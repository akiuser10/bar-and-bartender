# Quick Email Setup for Railway

## The Problem
Registration requires email verification, but email is not configured in Railway.

## Solution: Configure Gmail SMTP

### Step 1: Get Gmail App Password

1. Go to your Google Account: https://myaccount.google.com
2. Click **Security** (left sidebar)
3. Enable **2-Step Verification** (if not already enabled)
4. Scroll down to **App passwords**
5. Click **App passwords**
6. Select app: **Mail**
7. Select device: **Other (Custom name)** → Type "Railway"
8. Click **Generate**
9. **Copy the 16-character password** (you'll need this!)

### Step 2: Add to Railway

1. Go to Railway Dashboard
2. Click your **bar-and-bartender** service
3. Click **Variables** tab
4. Click **+ New Variable** for each:

**Variable 1:**
- Key: `MAIL_SERVER`
- Value: `smtp.gmail.com`

**Variable 2:**
- Key: `MAIL_PORT`
- Value: `587`

**Variable 3:**
- Key: `MAIL_USE_TLS`
- Value: `true`

**Variable 4:**
- Key: `MAIL_USERNAME`
- Value: `your-email@gmail.com` (your actual Gmail address)

**Variable 5:**
- Key: `MAIL_PASSWORD`
- Value: `xxxx xxxx xxxx xxxx` (the 16-character app password from Step 1, remove spaces)

**Variable 6:**
- Key: `MAIL_DEFAULT_SENDER`
- Value: `your-email@gmail.com` (same as MAIL_USERNAME)

### Step 3: Redeploy

After adding all variables:
1. Railway will automatically redeploy
2. Wait 1-2 minutes for deployment
3. Try registering again
4. Check your email for the 6-digit code!

## Alternative: Other Email Providers

### Outlook/Hotmail:
```
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=your-email@outlook.com
```

### Yahoo:
```
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@yahoo.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@yahoo.com
```

## Troubleshooting

### Still not receiving emails?
1. Check spam/junk folder
2. Verify all 6 variables are set correctly in Railway
3. Check Railway logs for email errors
4. Make sure you're using App Password (not regular password) for Gmail

### Email sending fails?
- Check Railway logs for specific error
- Verify MAIL_USERNAME and MAIL_PASSWORD are correct
- For Gmail, make sure 2-Step Verification is enabled

## After Setup

Once email is configured:
- ✅ Users will receive 6-digit code via email
- ✅ Code expires in 10 minutes
- ✅ Users can complete registration
- ✅ Code is NEVER shown on the page (security)
