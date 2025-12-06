"""
Email helper utilities for sending verification codes
"""
from flask import current_app
from flask_mail import Message
from extensions import mail
import secrets
from datetime import datetime, timedelta


def generate_verification_code():
    """Generate a random 6-digit verification code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def send_verification_email(email, code):
    """
    Send verification code email to user
    Returns True if successful, False otherwise
    """
    try:
        # Check if mail extension is initialized
        if not mail or not hasattr(mail, 'send'):
            current_app.logger.warning('Mail extension not initialized')
            return False
        
        # Check if email is configured
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        
        if not mail_username or not mail_password:
            current_app.logger.warning(f'Email not configured - MAIL_USERNAME={bool(mail_username)}, MAIL_PASSWORD={bool(mail_password)}')
            return False
        
        # Validate email format
        if '@' not in email or '.' not in email.split('@')[1]:
            current_app.logger.warning(f'Invalid email format: {email}')
            return False
        
        msg = Message(
            subject='Bar & Bartender - Email Verification Code',
            recipients=[email],
            body=f'''Hello!

Thank you for registering with Bar & Bartender!

Your verification code is: {code}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
Bar & Bartender Team
''',
            html=f'''<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Bar & Bartender - Email Verification</h2>
        <p>Hello!</p>
        <p>Thank you for registering with Bar & Bartender!</p>
        <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
            <p style="margin: 0; font-size: 14px; color: #666;">Your verification code is:</p>
            <h1 style="margin: 10px 0; font-size: 32px; color: #2c3e50; letter-spacing: 5px;">{code}</h1>
        </div>
        <p style="font-size: 12px; color: #999;">This code will expire in 10 minutes.</p>
        <p>If you did not request this code, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">Best regards,<br>Bar & Bartender Team</p>
    </div>
</body>
</html>'''
        )
        mail.send(msg)
        current_app.logger.info(f'Verification email sent successfully to {email}')
        return True
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f'Failed to send verification email to {email}: {error_msg}', exc_info=True)
        # Log more details about the error
        if 'authentication' in error_msg.lower() or 'login' in error_msg.lower():
            current_app.logger.error('Email authentication failed - check MAIL_USERNAME and MAIL_PASSWORD')
        elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
            current_app.logger.error('Email connection failed - check MAIL_SERVER and network')
        return False
