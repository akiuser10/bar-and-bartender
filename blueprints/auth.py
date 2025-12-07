"""
Authentication blueprint - handles login, register, logout
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User, VerificationCode
from utils.email_helpers import generate_verification_code, send_verification_email
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Initial registration step - collect user info and send code
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')

            # Validate inputs
            if not username or not email or not password or not password_confirm:
                flash('Please fill in all fields.')
                return render_template('register.html')
            
            # Validate passwords match
            if password != password_confirm:
                flash('Passwords do not match. Please try again.')
                return render_template('register.html')
            
            # Validate password length
            if len(password) < 6:
                flash('Password must be at least 6 characters long.')
                return render_template('register.html')

            # Validate email format
            if '@' not in email or '.' not in email.split('@')[1]:
                flash('Please enter a valid email address.')
                return render_template('register.html')

            # Check if email already registered
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please log in instead.')
                return redirect(url_for('auth.login'))

            # Check if username already taken
            if User.query.filter_by(username=username).first():
                flash('Username already taken. Please choose another.')
                return render_template('register.html')

            # Generate verification code
            code = generate_verification_code()
            
            # Store registration data in session temporarily
            session['reg_username'] = username
            session['reg_email'] = email
            session['reg_password'] = generate_password_hash(password)
            
            # Ensure VerificationCode table exists
            from flask import current_app
            try:
                # Try to create all tables if they don't exist
                db.create_all()
            except Exception as e:
                current_app.logger.warning(f'Table creation check: {str(e)}')
            
            # Delete any existing verification codes for this email
            try:
                VerificationCode.query.filter_by(email=email).delete()
                db.session.commit()
            except Exception as e:
                current_app.logger.warning(f'Could not delete old verification codes: {str(e)}')
                db.session.rollback()
            
            # Create new verification code record
            try:
                verification = VerificationCode(
                    email=email,
                    code=code,
                    username=username,
                    password_hash=session['reg_password'],
                    expires_at=datetime.utcnow() + timedelta(minutes=10)
                )
                db.session.add(verification)
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f'Database error creating verification code: {str(e)}', exc_info=True)
                db.session.rollback()
                # Try creating table again and retry
                try:
                    db.create_all()
                    db.session.add(verification)
                    db.session.commit()
                except Exception as e2:
                    db.session.rollback()
                    current_app.logger.error(f'Failed to create verification code after retry: {str(e2)}', exc_info=True)
                    flash(f'Database error. Please try again or contact administrator. Error: {str(e2)}')
                    return render_template('register.html')
            
            # Email verification is MANDATORY - send verification email
            # Code is ONLY sent via email, never shown on page
            email_sent = send_verification_email(email, code)
            
            if email_sent:
                flash('Verification code sent to your email. Please check your inbox (and spam folder).')
                return render_template('verify_email.html', email=email)
            else:
                # If email not configured or failed, show detailed error
                # Email verification is required - registration cannot proceed without it
                mail_username = current_app.config.get('MAIL_USERNAME')
                mail_password = current_app.config.get('MAIL_PASSWORD')
                mail_server = current_app.config.get('MAIL_SERVER', 'Not set')
                
                # Check what specifically failed
                if not mail_username or not mail_password:
                    error_detail = 'Email service is not configured. Please contact the administrator to set up email service.'
                    current_app.logger.error(f'Email not configured - MAIL_USERNAME={bool(mail_username)}, MAIL_PASSWORD={bool(mail_password)}')
                else:
                    error_detail = f'Email service is configured but failed to send. Server: {mail_server}. Please try again or contact administrator.'
                    current_app.logger.error(f'Email sending failed - MAIL_SERVER={mail_server}, email={email}')
                
                flash(f'⚠️ Unable to send verification email. Email verification is required to complete registration.\n\n{error_detail}\n\nPlease contact the administrator if this problem persists.', 'error')
                
                # Clean up the verification code since we can't send it
                try:
                    db.session.delete(verification)
                    db.session.commit()
                except:
                    db.session.rollback()
                session.clear()
                return render_template('register.html')
            
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'Registration error: {str(e)}', exc_info=True)
            flash(f'An error occurred during registration: {str(e)}. Please try again.')
            return render_template('register.html')

    return render_template('register.html')


@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_registration():
    """Handle email verification step"""
    if request.method == 'GET':
        # If no registration in progress, redirect to register
        if 'reg_email' not in session:
            flash('Please start registration first.')
            return redirect(url_for('auth.register'))
        return render_template('verify_email.html', email=session.get('reg_email', ''))
    
    # POST - verify the code
    entered_code = request.form.get('verification_code', '').strip()
    email = session.get('reg_email')
    
    if not email:
        flash('Session expired. Please register again.')
        return redirect(url_for('auth.register'))
    
    # Find verification code
    verification = VerificationCode.query.filter_by(
        email=email,
        verified=False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if not verification:
        flash('No verification code found. Please register again.')
        session.clear()
        return redirect(url_for('auth.register'))
    
    if verification.is_expired():
        flash('Verification code has expired. Please register again.')
        db.session.delete(verification)
        db.session.commit()
        session.clear()
        return redirect(url_for('auth.register'))
    
    if entered_code != verification.code:
        flash('Invalid verification code. Please try again.')
        return render_template('verify_email.html', email=email)
    
    # Code is valid - create user account
    try:
        user = User(
            username=verification.username,
            email=verification.email,
            password=verification.password_hash
        )
        db.session.add(user)
        
        # Mark verification as used
        verification.verified = True
        db.session.commit()
        
        # Clean up session
        session.pop('reg_username', None)
        session.pop('reg_email', None)
        session.pop('reg_password', None)
        
        # Delete old verification codes for this email
        VerificationCode.query.filter_by(email=email, verified=True).delete()
        db.session.commit()
        
        flash('Account created successfully! Please log in.')
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        flash('Error creating account. Please try again.')
        return render_template('verify_email.html', email=email)


@auth_bp.route('/resend-code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    email = session.get('reg_email')
    
    if not email:
        flash('Session expired. Please register again.')
        return redirect(url_for('auth.register'))
    
    try:
        # Delete old codes
        VerificationCode.query.filter_by(email=email).delete()
        
        # Generate new code
        code = generate_verification_code()
        verification = VerificationCode(
            email=email,
            code=code,
            username=session.get('reg_username', ''),
            password_hash=session.get('reg_password', ''),
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(verification)
        db.session.commit()
        
        email_sent = send_verification_email(email, code)
        if email_sent:
            flash('New verification code sent to your email. Please check your inbox (and spam folder).')
        else:
            from flask import current_app
            current_app.logger.error(f'Email not configured - cannot resend verification code to {email}')
            flash('⚠️ Email service is not configured. Please contact administrator.', 'error')
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error resending code: {str(e)}', exc_info=True)
        db.session.rollback()
        flash('Error generating new code. Please try again.')
    
    return redirect(url_for('auth.verify_registration'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not login_input or not password:
            flash('Please enter both email/username and password.')
            return render_template('login.html')
        
        # Try to find user by email first, then by username
        user = User.query.filter_by(email=login_input).first()
        if not user:
            # If not found by email, try username
            user = User.query.filter_by(username=login_input).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Welcome back!')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email/username or password.')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

