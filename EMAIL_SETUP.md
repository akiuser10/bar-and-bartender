# Email Verification Setup Guide

## Overview

The registration process now includes email verification. Users must enter a 6-digit code sent to their email address before their account is created.

## Email Configuration

To enable email sending, you need to configure email settings. The app supports Gmail and other SMTP servers.

### Option 1: Gmail (Recommended for Development)

1. **Enable App Passwords in Gmail:**
   - Go to your Google Account settings
   - Security → 2-Step Verification (enable if not already)
   - App Passwords → Generate a new app password
   - Copy the 16-character password

2. **Set Environment Variables in Railway:**
   - Go to your Railway service → Variables tab
   - Add these variables:
     ```
     MAIL_SERVER=smtp.gmail.com
     MAIL_PORT=587
     MAIL_USE_TLS=true
     MAIL_USERNAME=your-email@gmail.com
     MAIL_PASSWORD=your-16-char-app-password
     MAIL_DEFAULT_SENDER=your-email@gmail.com
     ```

### Option 2: Other SMTP Servers

For other email providers (Outlook, Yahoo, custom SMTP):

1. **Set Environment Variables:**
   ```
   MAIL_SERVER=smtp.your-provider.com
   MAIL_PORT=587 (or 465 for SSL)
   MAIL_USE_TLS=true (or false for SSL)
   MAIL_USERNAME=your-email@domain.com
   MAIL_PASSWORD=your-password
   MAIL_DEFAULT_SENDER=your-email@domain.com
   ```

### Option 3: Development (No Email - Testing Only)

For local development without sending real emails, you can:
- Leave email variables unset (emails will fail but app won't crash)
- Use a mock email service
- Check logs for the verification code

## How It Works

1. **User Registration:**
   - User enters username, email, and password
   - System generates a 6-digit code
   - Code is sent to user's email
   - Code expires in 10 minutes

2. **Email Verification:**
   - User receives email with 6-digit code
   - User enters code in verification form
   - System validates code
   - Account is created upon successful verification

3. **Resend Code:**
   - User can request a new code if needed
   - Old code is invalidated when new one is sent

## Database

The `VerificationCode` model stores temporary verification codes:
- Codes expire after 10 minutes
- Codes are deleted after successful verification
- Old codes are cleaned up automatically

## Testing

1. **Register a new account**
2. **Check your email** for the 6-digit code
3. **Enter the code** in the verification form
4. **Account is created** and you can log in

## Troubleshooting

### Emails Not Sending

1. **Check Environment Variables:**
   - Verify all MAIL_* variables are set correctly
   - Check Railway logs for email errors

2. **Gmail Issues:**
   - Make sure you're using an App Password, not your regular password
   - Enable "Less secure app access" if App Passwords don't work (not recommended)

3. **Check Logs:**
   - Railway logs will show email sending errors
   - Look for "Failed to send verification email" messages

### Code Not Working

1. **Check Expiration:**
   - Codes expire after 10 minutes
   - Request a new code if expired

2. **Check Email:**
   - Verify you're checking the correct email
   - Check spam folder

3. **Resend Code:**
   - Use the "Resend Code" button to get a new code

## Security Notes

- Codes are randomly generated using secure random number generation
- Codes expire after 10 minutes
- Each code can only be used once
- Old codes are automatically cleaned up
- Email addresses are validated before sending
