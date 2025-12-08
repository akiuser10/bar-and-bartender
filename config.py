import os

class Config:
    # Use environment variable for SECRET_KEY in production, fallback to default for development
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey'
    
    # Support both SQLite (development) and PostgreSQL (production) via DATABASE_URL
    database_url = os.environ.get('DATABASE_URL', '').strip()
    
    # If DATABASE_URL is not set or empty, use SQLite for development
    if not database_url:
        database_url = 'sqlite:///bar_bartender.db'
    # Handle PostgreSQL URL format for Render and other platforms
    # Convert to use psycopg3 (Python 3.13 compatible)
    elif database_url.startswith('postgres://'):
        # Convert postgres:// to postgresql+psycopg://
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://'):
        # If already postgresql:// but not using psycopg, add it
        if '+psycopg' not in database_url:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Email configuration for verification
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # Get password from environment - Gmail App Passwords can have spaces, but they're optional
    mail_pwd_raw = os.environ.get('MAIL_PASSWORD')
    # Only strip if password exists and is not empty
    if mail_pwd_raw:
        # Convert to string and strip whitespace
        MAIL_PASSWORD = str(mail_pwd_raw).strip()
        # If after stripping it's empty, set to None
        if not MAIL_PASSWORD:
            MAIL_PASSWORD = None
    else:
        MAIL_PASSWORD = None
    
    # Debug logging (only in development or if explicitly enabled)
    if os.environ.get('DEBUG_MAIL_CONFIG', 'false').lower() == 'true':
        import logging
        logging.info(f'MAIL config - USERNAME={bool(MAIL_USERNAME)}, PASSWORD={bool(MAIL_PASSWORD)}, PASSWORD_LEN={len(str(mail_pwd_raw)) if mail_pwd_raw else 0)}')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    # Email verification is MANDATORY for all new registrations
    # This setting is kept for backward compatibility but is no longer used
    # Email verification cannot be skipped
