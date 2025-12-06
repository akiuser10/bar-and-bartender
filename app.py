"""
Bar & Bartender Flask Application Factory
Clean, modular application structure using blueprints
"""
from flask import Flask
from datetime import datetime
import os

# Import extensions
from extensions import db, login_manager, mail

# Import models (must import after extensions to avoid circular imports)
# Models import db from extensions
from models import User, Product, HomemadeIngredient, HomemadeIngredientItem, Recipe, RecipeIngredient, VerificationCode

# Import blueprints
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.products import products_bp
from blueprints.secondary import secondary_bp
from blueprints.recipes import recipes_bp

# Import utilities
from utils.helpers import inject_now
from utils.db_helpers import ensure_schema_updates


def create_app(config_object='config.Config'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(secondary_bp)
    app.register_blueprint(recipes_bp)
    
    # Register CLI commands
    @app.cli.command('link-ingredient')
    def link_ingredient():
        """Link a product/ingredient to a secondary ingredient"""
        import click
        from utils.link_ingredients import link_ingredient_to_secondary
        
        secondary_id = click.prompt('Secondary ingredient ID', type=int)
        product_id = click.prompt('Product ID', type=int)
        quantity = click.prompt('Quantity', type=float)
        unit = click.prompt('Unit', default='ml', type=str)
        
        if link_ingredient_to_secondary(secondary_id, product_id, quantity, unit):
            click.echo('✓ Successfully linked ingredient!')
        else:
            click.echo('✗ Failed to link ingredient')
    
    @app.cli.command('list-secondary')
    def list_secondary():
        """List all secondary ingredients"""
        from utils.link_ingredients import list_secondary_ingredients
        list_secondary_ingredients()
    
    @app.cli.command('show-secondary')
    def show_secondary():
        """Show details of a secondary ingredient"""
        import click
        from utils.link_ingredients import show_secondary_ingredient_details
        
        secondary_id = click.prompt('Secondary ingredient ID', type=int)
        show_secondary_ingredient_details(secondary_id)
    
    # Context processor
    @app.context_processor
    def inject_context():
        return inject_now()
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        app.logger.error(f'Internal Server Error: {str(error)}', exc_info=True)
        return render_template('error.html', error=str(error)), 500
    
    # Initialize database and run schema updates
    with app.app_context():
        try:
            # Create upload directories
            upload_folder = app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            os.makedirs(os.path.join(upload_folder, 'products'), exist_ok=True)
            os.makedirs(os.path.join(upload_folder, 'recipes'), exist_ok=True)
            
            # Create all tables
            db.create_all()
            
            # Run schema updates
            ensure_schema_updates()
        except Exception as e:
            # Log error but don't crash - allow app to start
            # Database/table creation will happen on first request if needed
            app.logger.warning(f'Initialization warning: {str(e)}')
    
    return app


# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)

