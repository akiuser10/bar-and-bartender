# Chefs & Bartenders

A comprehensive Recipe & Costing Management System for bars and restaurants

## Description

Chefs & Bartenders is a Flask-based web application designed to help bartenders, bar managers, and restaurant owners manage their recipes, ingredients, and cost calculations efficiently. The system provides a centralized platform for tracking products, creating custom recipes, calculating precise costs, and managing pricing strategies. Built with real-world bar industry experience, this application addresses the common challenges faced by professionals when calculating recipe costs, especially when creating new drinks or adjusting existing ones due to product or price changes.

The application streamlines the entire recipe management workflow, from initial product inventory tracking through complex recipe creation with nested ingredients, to automatic cost calculation and profit margin analysis. Unlike many commercial costing tools that are complicated or restrictive, Chefs & Bartenders is designed with bartenders in mind, offering an intuitive interface that makes recipe costing accessible to anyone in the bar community worldwide.

## Social Relevance

Having worked in the bar industry since 2012, I've seen firsthand how challenging it can be to calculate recipe costs—especially when creating new drinks or adjusting existing ones due to product or price changes. Many companies offer their own costing tools, but they are often complicated, restrictive, or not designed with bartenders in mind.
**"Chefs & Bartenders"** aims to solve this problem by providing an easy-to-use, accessible platform that anyone in the bar community worldwide can benefit from. By streamlining recipe costing and simplifying day-to-day operations, the project supports bartenders and bar teams in working smarter, more accurately, and more creatively.

### Key Features

#### Master List Management

The Master List serves as the central inventory hub for all products and ingredients. It provides comprehensive tracking of unique item numbers, supplier information, categories, sub-categories, and costs. The system supports bulk upload of products via Excel spreadsheet, significantly reducing data entry time for establishments with large inventories. Advanced search and filter functionality enables quick product lookup, while support for multiple units (milliliters, grams, pieces) with automatic conversions ensures accurate cost calculations regardless of how products are purchased or stored.

#### Secondary Ingredients (Homemade Ingredients)

The Secondary Ingredients module allows users to create and manage custom homemade ingredients such as syrups, infusions, and house-made liqueurs. These complex ingredients are built from base products in the master list, enabling multi-level cost calculations. The system automatically calculates the total cost and cost per unit for these secondary ingredients, which can then be used in recipes just like any other ingredient. This feature is essential for bars that create their own specialty ingredients, as it ensures accurate costing even when recipes involve multiple preparation steps.

#### Recipe Management

Recipe management is the core functionality of the application. Users can create and manage recipes for three distinct categories: Cocktails, Mocktails, and Beverages. The system supports nested recipes, allowing recipes to contain other recipes as ingredients—a powerful feature for complex bar programs. Each recipe can include detailed methods and instructions, image uploads for visual reference, and a unique recipe code system (REC-####) for easy identification. Category-based filtering and search functionality make it easy to navigate large recipe collections.

#### Costing & Pricing

The automatic cost calculation engine is one of the most sophisticated features of the application. It supports multiple ingredient types including base products from the master list, secondary/homemade ingredients, and even nested recipes. The system calculates cost percentage (cost as a percentage of selling price), enabling users to track profit margins and make informed pricing decisions. Batch summary functionality provides a breakdown by ingredient category (Alcohol, Juices, Syrups, Fruits, Vegetables, Dairy, Non-Alcohol, Other), which is invaluable for inventory planning and purchasing decisions.

#### User Interface

The application features a clean, responsive web interface designed for both desktop and mobile use. Intuitive navigation with category-based filtering, real-time search functionality, and bulk operations (such as selective deletion) enhance productivity. The recipe calculator provides interactive ingredient management with real-time cost updates as ingredients are added or quantities are adjusted.

#### Data Management

Comprehensive data management features include bulk Excel upload for products, user authentication and authorization, and secure file storage for recipe images. The system maintains data integrity through unique code generation, validation for required fields, and cascade deletion for related records.

#### Technology Stack

The application is built using Flask 3.1.2, a lightweight and flexible Python web framework. The database layer uses SQLite for development and is production-ready for PostgreSQL deployment. The frontend is built with standard HTML, CSS, and JavaScript, ensuring broad compatibility and easy customization. Key libraries include Flask-SQLAlchemy for ORM functionality, Flask-Login for authentication, Pandas and OpenPyXL for Excel processing, and Gunicorn as the production server.

##### Project Structure and File Organization

The project follows a modular blueprint-based architecture, which was a deliberate design choice to improve code organization and maintainability. Rather than having a monolithic application file, the codebase is organized into logical modules, each handling a specific domain of functionality.

###### Core Application Files

**`app.py`** - This file implements the Flask application factory pattern, which allows for flexible application configuration and testing. The factory function `create_app()` initializes all Flask extensions, registers blueprints, sets up error handlers, and configures the login manager. This pattern was chosen because it enables easy configuration switching between development and production environments, and facilitates unit testing by allowing multiple app instances. The file also includes CLI commands for ingredient linking operations and context processors that inject common variables into templates.

**`config.py`** - Configuration management is centralized in this file, which supports both development and production environments through environment variables. The configuration handles database connection settings (with automatic PostgreSQL URL format conversion for platforms like Render), secret key management, file upload settings, and content length limits. This separation of configuration from application logic follows the twelve-factor app methodology, making the application more portable and secure.

**`extensions.py`** - This file centralizes the initialization of Flask extensions (SQLAlchemy and LoginManager) before they are used elsewhere. This pattern prevents circular import issues and ensures extensions are properly configured before being imported by models or blueprints.

**`models.py`** - Contains all SQLAlchemy ORM models that define the database schema. The models include User (authentication), Product (master inventory), HomemadeIngredient and HomemadeIngredientItem (secondary ingredients), Recipe, and RecipeIngredient. Each model includes business logic methods such as `calculate_total_cost()` and `calculate_cost_per_unit()`, following the active record pattern. The models use relationships and cascade deletions to maintain referential integrity.

##### Blueprint Modules

**`blueprints/auth.py`** - Handles all authentication-related routes including user registration, login, and logout. The registration process uses Werkzeug's password hashing for secure password storage. The login route verifies credentials and manages user sessions through Flask-Login.

**`blueprints/main.py`** - Contains the main application routes including the homepage and dashboard. This blueprint also includes context processors that inject common variables (like the current year) into all templates.

**`blueprints/products.py`** - Manages the master list of products and ingredients. This module handles CRUD operations for products, bulk Excel upload functionality, automatic code generation (BB### format), and search/filter operations. The bulk upload feature uses Pandas to parse Excel files and validate data before insertion.

**`blueprints/recipes.py`** - The most complex blueprint, handling all recipe-related operations. It manages recipe creation, editing, deletion, and viewing across different categories (cocktails, mocktails, beverages). The module includes sophisticated routing logic that handles both category-based filtering and recipe code lookups (REC-####). Cost calculation is performed automatically when recipes are viewed, and batch summaries are generated for inventory planning.

**`blueprints/secondary.py`** - Manages secondary/homemade ingredients. This module allows users to create complex ingredients from base products, link products to homemade ingredients, and view detailed cost breakdowns. The cost calculation for secondary ingredients recursively calculates costs from their component products.

### Utility Modules

**`utils/constants.py`** - Defines application-wide constants including category configurations, category aliases, and type-to-category mappings. This centralization makes it easy to modify category behavior or add new categories without touching multiple files.

**`utils/db_helpers.py`** - Contains database migration utilities that ensure schema updates are applied automatically. The `ensure_schema_updates()` function checks for missing columns and adds them, then backfills data from legacy columns. This approach was chosen over traditional migration frameworks like Alembic because it provides automatic schema evolution without requiring manual migration scripts, which is particularly useful during active development.

**`utils/file_upload.py`** - Handles secure file uploads with validation, sanitization, and organized storage. Files are stored in categorized directories (products, recipes) with timestamped filenames to prevent conflicts.

**`utils/helpers.py`** - Contains general helper functions including context processors for templates and date/time utilities.

**`utils/link_ingredients.py`** - Provides utilities for linking products to secondary ingredients, including CLI commands for batch operations.

### Template Files

The `templates/` directory contains Jinja2 HTML templates organized by feature. The base template (`base.html`) provides the common layout structure including navigation, footer, and flash message display. Feature-specific templates are organized into subdirectories (master_list/, products/, recipes/, secondary_ingredients/) for better organization. Category-specific recipe views (recipes_classic.html, recipes_mocktail.html, recipes_beverages.html) provide tailored displays for different recipe types.

### Static Files

The `static/` directory contains CSS stylesheets, JavaScript files for client-side interactivity, and uploaded user content. The main stylesheet (`style.css`) implements a responsive design that works across devices. JavaScript files include `recipe_calculator.js` for dynamic ingredient management and real-time cost calculation, and `scripts.js` for general client-side functionality.

## Design Decisions and Rationale

Several key design decisions were made during development, each serving specific purposes:

**Blueprint Architecture**: The decision to use Flask blueprints instead of a monolithic application structure was made to improve code organization and maintainability. Each blueprint handles a specific domain (authentication, products, recipes, etc.), making the codebase easier to navigate and modify. This modular approach also facilitates team collaboration, as different developers can work on different blueprints without conflicts.

**Application Factory Pattern**: The use of the application factory pattern in `app.py` enables flexible configuration management and easier testing. This pattern allows the application to be instantiated with different configurations for development, testing, and production environments. It also prevents issues with circular imports and makes the application more testable.

**Automatic Schema Migration**: Rather than using a traditional migration framework, the application uses automatic schema detection and migration in `utils/db_helpers.py`. This approach was chosen because it simplifies deployment and ensures that schema updates are applied automatically without requiring manual intervention. While this approach works well for SQLite and small-scale deployments, the codebase is structured to support PostgreSQL in production, which would benefit from more formal migration tools.

**Nested Recipe Support**: The ability to use recipes as ingredients in other recipes was a deliberate design choice to support complex bar programs. This feature enables users to create base recipes (like a house margarita mix) and use it in multiple final recipes. The cost calculation engine handles this recursion automatically, ensuring accurate costing even for deeply nested recipes.

**Dual Category System**: The recipe system maintains both a `type` field (new system) and `recipe_type` field (legacy system) to support data migration and backward compatibility. The filtering logic prioritizes the `type` field but falls back to `recipe_type` when needed, ensuring that recipes created with the old system continue to work.

**Cost Calculation in Models**: Business logic for cost calculation is embedded in the model classes rather than in the view layer. This design follows the principle of keeping business logic close to data and ensures that cost calculations are consistent regardless of where they're called from. The methods include error handling to prevent calculation failures from breaking the user interface.

**File Upload Organization**: Uploaded files are organized into subdirectories (products/, recipes/) with timestamped filenames. This approach prevents filename conflicts and makes it easy to manage and clean up old files. The system validates file types and sizes before accepting uploads.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:

    ```bash
    git clone https://example.com/repository.git
    cd Bar&Bartender
    ```

2. Create and activate a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Run the application:

    ```bash
    python app.py
    ```

The application will be available at `http://localhost:5001`

## Deployment

The application is production-ready and can be deployed to various hosting platforms including Render (recommended for beginners), Railway, PythonAnywhere, DigitalOcean App Platform, or Heroku. The configuration supports environment variables for sensitive data like database URLs and secret keys. See `DEPLOYMENT.md` for detailed deployment instructions for each platform.

## Usage Workflow

1. **Register/Login**: Create an account to start managing your recipes. The authentication system uses secure password hashing to protect user credentials.
2. **Add Products**: Import products via bulk Excel upload or add them individually through the master list interface. Each product receives a unique code (BB###) automatically.
3. **Create Secondary Ingredients**: Build custom ingredients from base products. For example, create a house-made simple syrup by linking sugar and water from your master list. The system calculates the cost per unit automatically.
4. **Create Recipes**: Add recipes with ingredients, quantities, and methods. The system supports multiple ingredient types and automatically calculates total cost as you build the recipe.
5. **Calculate Costs**: View detailed cost breakdowns, profit margins, and batch summaries. The system updates costs automatically when ingredient prices change.
6. **Manage Inventory**: Use the master list to track all products, update costs, and manage your inventory efficiently.

## Future Enhancements

Planned enhancements include recipe scaling functionality (adjust quantities for batch sizes), inventory tracking with low-stock alerts, recipe versioning and history tracking, advanced reporting and analytics, mobile app support, and REST API endpoints for integration with other systems.

## License

Copyright © 2024 Chefs & Bartenders | Crafted by Akhil Soman 🍹

## Support

For issues, questions, or contributions, please refer to the project repository.
