"""
Database helper utilities
"""
from extensions import db
from flask import current_app


def get_table_columns(conn, table_name):
    """
    Get list of column names for a table, works with both SQLite and PostgreSQL.
    """
    db_url = str(db.engine.url)
    
    if 'postgresql' in db_url or 'postgres' in db_url:
        # PostgreSQL
        result = conn.execute(db.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table_name"
        ), {'table_name': table_name})
        return [row[0] for row in result]
    else:
        # SQLite
        result = conn.execute(db.text(f'PRAGMA table_info({table_name})'))
        return [col[1] for col in result]


def ensure_schema_updates():
    """
    Ensure database schema is up to date with migrations.
    Works with both SQLite and PostgreSQL.
    """
    try:
        with current_app.app_context():
            with db.engine.begin() as conn:
                # Recipe table updates
                recipe_columns = get_table_columns(conn, 'recipe')
                if 'item_level' not in recipe_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))
                    except Exception:
                        pass  # Column might already exist
                if 'selling_price' not in recipe_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN selling_price FLOAT DEFAULT 0"))
                    except Exception:
                        pass
                if 'vat_percentage' not in recipe_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN vat_percentage FLOAT DEFAULT 0"))
                    except Exception:
                        pass
                if 'service_charge_percentage' not in recipe_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN service_charge_percentage FLOAT DEFAULT 0"))
                    except Exception:
                        pass
                if 'government_fees_percentage' not in recipe_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN government_fees_percentage FLOAT DEFAULT 0"))
                    except Exception:
                        pass
                if 'garnish' not in recipe_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe ADD COLUMN garnish TEXT"))
                    except Exception:
                        pass

                # Product table updates
                product_columns = get_table_columns(conn, 'product')
                if 'item_level' not in product_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))
                    except Exception:
                        pass

                # Recipe ingredient table updates
                recipe_ingredient_columns = get_table_columns(conn, 'recipe_ingredient')
                if 'ingredient_type' not in recipe_ingredient_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_type VARCHAR(20)"))
                    except Exception:
                        pass
                if 'ingredient_id' not in recipe_ingredient_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_id INTEGER"))
                    except Exception:
                        pass
                if 'quantity' not in recipe_ingredient_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN quantity FLOAT"))
                    except Exception:
                        pass
                if 'unit' not in recipe_ingredient_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN unit VARCHAR(20) DEFAULT 'ml'"))
                    except Exception:
                        pass

                # Backfill new columns from legacy data where possible
                try:
                    conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_id = product_id WHERE ingredient_id IS NULL AND product_id IS NOT NULL"))
                    conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_type = COALESCE(ingredient_type, product_type) WHERE ingredient_type IS NULL"))
                    conn.execute(db.text("UPDATE recipe_ingredient SET quantity = COALESCE(quantity, quantity_ml) WHERE quantity IS NULL"))
                    conn.execute(db.text("UPDATE recipe_ingredient SET unit = COALESCE(unit, 'ml') WHERE unit IS NULL"))
                except Exception:
                    pass  # Some columns might not exist

                # Homemade ingredient item table updates
                homemade_item_columns = get_table_columns(conn, 'homemade_ingredient_item')
                if 'quantity' not in homemade_item_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN quantity FLOAT DEFAULT 0"))
                    except Exception:
                        pass
                if 'unit' not in homemade_item_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN unit VARCHAR(20) DEFAULT 'ml'"))
                    except Exception:
                        pass
                
                # Backfill quantity_ml if it's NULL (for existing records)
                try:
                    conn.execute(db.text("UPDATE homemade_ingredient_item SET quantity_ml = COALESCE(quantity_ml, COALESCE(quantity, 0)) WHERE quantity_ml IS NULL"))
                except Exception:
                    pass  # Column might not exist or already updated
                
                # Add user_id columns if they don't exist
                if 'user_id' not in product_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN user_id INTEGER"))
                        conn.execute(db.text("ALTER TABLE product ADD CONSTRAINT fk_product_user FOREIGN KEY (user_id) REFERENCES user(id)"))
                    except Exception:
                        pass  # Column might already exist or constraint might fail
                
                homemade_columns = get_table_columns(conn, 'homemade_ingredient')
                if 'user_id' not in homemade_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN user_id INTEGER"))
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD CONSTRAINT fk_homemade_user FOREIGN KEY (user_id) REFERENCES user(id)"))
                    except Exception:
                        pass  # Column might already exist or constraint might fail
    except Exception as e:
        # Log error but don't crash - schema updates are best effort
        current_app.logger.warning(f'Schema update warning: {str(e)}')

