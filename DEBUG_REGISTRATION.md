# Debugging Registration Error

## To Find the Actual Error:

1. **Go to Railway Dashboard**
2. **Click on your service** (bar-and-bartender)
3. **Click "Logs" tab**
4. **Try to register again**
5. **Look for red error messages** in the logs
6. **Copy the full error traceback** and share it

## Common Issues:

### 1. Import Error
- Check if `VerificationCode` is imported correctly
- Check if `Flask-Mail` is installed

### 2. Database Error
- Check if `VerificationCode` table exists
- Check database connection

### 3. Email Configuration Error
- Check if MAIL_* variables are set (optional)
- Mail should be optional, not required

## Quick Test:

Try accessing these URLs to see which one fails:
- `/register` (GET) - Should show registration form
- `/register` (POST) - This is where the error likely occurs

## What to Share:

When you find the error in Railway logs, share:
1. The full error message
2. The traceback (stack trace)
3. Any warnings or info messages before the error

This will help identify the exact issue.
