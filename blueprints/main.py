"""
Main blueprint - handles index, errors, and file uploads
"""
from flask import Blueprint, render_template, send_from_directory, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@main_bp.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404


@main_bp.errorhandler(500)
def internal_error(error):
    from extensions import db
    db.session.rollback()
    current_app.logger.error(f'Internal Server Error: {str(error)}', exc_info=True)
    return render_template('error.html', error=str(error)), 500

