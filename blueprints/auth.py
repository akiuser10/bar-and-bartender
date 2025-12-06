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
        # Initial registration step - collect user info and send code
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

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
        
        # Delete any existing verification codes for this email
        try:
            VerificationCode.query.filter_by(email=email).delete()
        except Exception as e:
            # Table might not exist yet - will be created on first use
            from flask import current_app
            current_app.logger.warning(f'Could not delete old verification codes: {str(e)}')
        
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
            # If table doesn't exist, create it
            from flask import current_app
            current_app.logger.error(f'Database error creating verification code: {str(e)}')
            try:
                db.create_all()  # Create all tables including VerificationCode
                db.session.add(verification)
                db.session.commit()
            except Exception as e2:
                db.session.rollback()
                flash(f'Database error: {str(e2)}. Please contact administrator.')
                return render_template('register.html')
        
        # Send verification email
        email_sent = send_verification_email(email, code)
        if email_sent:
            flash('Verification code sent to your email. Please check your inbox.')
        else:
            # If email not configured, show code in flash message for development/testing
            from flask import current_app
            current_app.logger.warning(f'Email not configured - showing code in flash message for {email}')
            flash(f'⚠️ Email not configured. Your verification code is: {code} (Configure email settings for production)', 'warning')
        
        return render_template('verify_email.html', email=email)

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
            flash('New verification code sent to your email.')
        else:
            from flask import current_app
            current_app.logger.warning(f'Email not configured - showing code in flash message for {email}')
            flash(f'⚠️ Email not configured. Your new verification code is: {code}', 'warning')
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error resending code: {str(e)}', exc_info=True)
        db.session.rollback()
        flash('Error generating new code. Please try again.')
    
    return redirect(url_for('auth.verify_registration'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            flash('Welcome back!')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

