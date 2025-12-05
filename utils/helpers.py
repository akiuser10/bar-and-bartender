"""
Helper utility functions
"""
from datetime import datetime
from flask import current_app


def inject_now():
    """Context processor to inject current year"""
    return {'current_year': datetime.now().year}


def ensure_schema_updates():
    """
    Ensure database schema is up to date.
    This is a placeholder for any schema migration logic.
    """
    pass

