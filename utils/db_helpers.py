"""
Database helper utilities
"""
from extensions import db
from flask import current_app


def ensure_schema_updates():
    """
    Ensure database schema is up to date with migrations.
    """
    with current_app.app_context():
        with db.engine.begin() as conn:
            # Recipe table updates
            recipe_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(recipe)'))]
            if 'item_level' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))
            if 'selling_price' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN selling_price FLOAT DEFAULT 0"))
            if 'vat_percentage' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN vat_percentage FLOAT DEFAULT 0"))
            if 'service_charge_percentage' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN service_charge_percentage FLOAT DEFAULT 0"))
            if 'government_fees_percentage' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN government_fees_percentage FLOAT DEFAULT 0"))
            if 'garnish' not in recipe_columns:
                conn.execute(db.text("ALTER TABLE recipe ADD COLUMN garnish TEXT"))

            # Product table updates
            product_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(product)'))]
            if 'item_level' not in product_columns:
                conn.execute(db.text("ALTER TABLE product ADD COLUMN item_level VARCHAR(20) DEFAULT 'Primary'"))

            # Recipe ingredient table updates
            recipe_ingredient_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(recipe_ingredient)'))]
            if 'ingredient_type' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_type VARCHAR(20)"))
            if 'ingredient_id' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN ingredient_id INTEGER"))
            if 'quantity' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN quantity FLOAT"))
            if 'unit' not in recipe_ingredient_columns:
                conn.execute(db.text("ALTER TABLE recipe_ingredient ADD COLUMN unit VARCHAR(20) DEFAULT 'ml'"))

            # Backfill new columns from legacy data where possible
            conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_id = product_id WHERE ingredient_id IS NULL AND product_id IS NOT NULL"))
            conn.execute(db.text("UPDATE recipe_ingredient SET ingredient_type = COALESCE(ingredient_type, product_type)"))
            conn.execute(db.text("UPDATE recipe_ingredient SET quantity = COALESCE(quantity, quantity_ml)"))
            conn.execute(db.text("UPDATE recipe_ingredient SET unit = COALESCE(unit, 'ml')"))

            # Homemade ingredient item table updates
            homemade_item_columns = [col[1] for col in conn.execute(db.text('PRAGMA table_info(homemade_ingredient_item)'))]
            if 'quantity' not in homemade_item_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN quantity FLOAT DEFAULT 0"))
            if 'unit' not in homemade_item_columns:
                conn.execute(db.text("ALTER TABLE homemade_ingredient_item ADD COLUMN unit VARCHAR(20) DEFAULT 'ml'"))
            
            # Backfill quantity_ml if it's NULL (for existing records)
            try:
                conn.execute(db.text("UPDATE homemade_ingredient_item SET quantity_ml = COALESCE(quantity_ml, COALESCE(quantity, 0)) WHERE quantity_ml IS NULL"))
            except Exception:
                pass  # Column might not exist or already updated

