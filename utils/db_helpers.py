"""
Database helper utilities
"""
from extensions import db
from flask import current_app


def get_table_columns(conn, table_name):
    """
    Get list of column names for a table, works with both SQLite and PostgreSQL.
    """
    try:
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
    except Exception:
        # If table doesn't exist or error, return empty list
        return []


def has_column(table_name, column_name):
    """
    Check if a table has a specific column.
    Returns True if column exists, False otherwise.
    """
    try:
        with current_app.app_context():
            with db.engine.begin() as conn:
                columns = get_table_columns(conn, table_name)
                return column_name in columns
    except Exception:
        return False


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
                # Note: We only add the column, not the foreign key constraint
                # The foreign key is already defined in the model, SQLAlchemy will handle it
                # Adding constraints manually can fail due to PostgreSQL reserved words
                if 'user_id' not in product_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE product ADD COLUMN user_id INTEGER"))
                    except Exception as e:
                        current_app.logger.warning(f'Could not add user_id to product: {str(e)}')
                        pass  # Column might already exist
                
                homemade_columns = get_table_columns(conn, 'homemade_ingredient')
                if 'user_id' not in homemade_columns:
                    try:
                        conn.execute(db.text("ALTER TABLE homemade_ingredient ADD COLUMN user_id INTEGER"))
                    except Exception as e:
                        current_app.logger.warning(f'Could not add user_id to homemade_ingredient: {str(e)}')
                        pass  # Column might already exist
                
                # Store homemade_columns for later use in constraint updates
                homemade_columns_for_constraints = get_table_columns(conn, 'homemade_ingredient')
                
                # Drop old global unique constraints and replace with user-scoped constraints
                db_url = str(db.engine.url)
                if 'postgresql' in db_url or 'postgres' in db_url:
                    try:
                        # Drop old global unique constraint on unique_item_number if it exists
                        # Check both table_constraints and pg_constraint for comprehensive detection
                        constraint_check = conn.execute(db.text(
                            "SELECT 1 FROM information_schema.table_constraints "
                            "WHERE table_name = 'product' AND constraint_name = 'product_unique_item_number_key' "
                            "UNION ALL "
                            "SELECT 1 FROM pg_constraint WHERE conname = 'product_unique_item_number_key'"
                        ))
                        if constraint_check.fetchone():
                            try:
                                conn.execute(db.text("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_unique_item_number_key"))
                                current_app.logger.info('Dropped old global unique constraint on unique_item_number')
                            except Exception as drop_e:
                                current_app.logger.warning(f'Could not drop unique_item_number constraint: {str(drop_e)}')
                        
                        # Drop old global unique constraint on barbuddy_code if it exists
                        # Check both table_constraints and pg_constraint for comprehensive detection
                        barbuddy_constraint_check = conn.execute(db.text(
                            "SELECT 1 FROM information_schema.table_constraints "
                            "WHERE table_name = 'product' AND constraint_name = 'product_barbuddy_code_key' "
                            "UNION ALL "
                            "SELECT 1 FROM pg_constraint WHERE conname = 'product_barbuddy_code_key'"
                        ))
                        if barbuddy_constraint_check.fetchone():
                            try:
                                conn.execute(db.text("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_barbuddy_code_key"))
                                current_app.logger.info('Dropped old global unique constraint on barbuddy_code')
                            except Exception as drop_e:
                                current_app.logger.warning(f'Could not drop barbuddy_code constraint: {str(drop_e)}')
                        
                        # Also check for and drop any unique indexes that might be enforcing uniqueness
                        # Sometimes PostgreSQL creates unique indexes instead of constraints
                        unique_index_check = conn.execute(db.text(
                            "SELECT indexname FROM pg_indexes "
                            "WHERE tablename = 'product' AND indexname IN ('product_unique_item_number_key', 'product_barbuddy_code_key')"
                        ))
                        for row in unique_index_check:
                            index_name = row[0]
                            try:
                                conn.execute(db.text(f"DROP INDEX IF EXISTS {index_name}"))
                                current_app.logger.info(f'Dropped old unique index: {index_name}')
                            except Exception as drop_e:
                                current_app.logger.warning(f'Could not drop index {index_name}: {str(drop_e)}')
                        
                        # Drop old global unique constraint on homemade_ingredient.unique_code if it exists
                        homemade_constraint_check = conn.execute(db.text(
                            "SELECT 1 FROM information_schema.table_constraints "
                            "WHERE table_name = 'homemade_ingredient' AND constraint_name = 'homemade_ingredient_unique_code_key' "
                            "UNION ALL "
                            "SELECT 1 FROM pg_constraint WHERE conname = 'homemade_ingredient_unique_code_key'"
                        ))
                        if homemade_constraint_check.fetchone():
                            try:
                                conn.execute(db.text("ALTER TABLE homemade_ingredient DROP CONSTRAINT IF EXISTS homemade_ingredient_unique_code_key"))
                                current_app.logger.info('Dropped old global unique constraint on homemade_ingredient.unique_code')
                            except Exception as drop_e:
                                current_app.logger.warning(f'Could not drop homemade_ingredient unique_code constraint: {str(drop_e)}')
                        
                        # Also check for unique indexes on homemade_ingredient.unique_code
                        homemade_index_check = conn.execute(db.text(
                            "SELECT indexname FROM pg_indexes "
                            "WHERE tablename = 'homemade_ingredient' AND indexname = 'homemade_ingredient_unique_code_key'"
                        ))
                        for row in homemade_index_check:
                            index_name = row[0]
                            try:
                                conn.execute(db.text(f"DROP INDEX IF EXISTS {index_name}"))
                                current_app.logger.info(f'Dropped old unique index: {index_name}')
                            except Exception as drop_e:
                                current_app.logger.warning(f'Could not drop index {index_name}: {str(drop_e)}')
                        
                        # Add new user-scoped unique constraints (only if user_id column exists)
                        if 'user_id' in product_columns:
                            try:
                                # Check if new constraint for unique_item_number already exists
                                new_constraint_check = conn.execute(db.text(
                                    "SELECT indexname FROM pg_indexes "
                                    "WHERE tablename = 'product' AND indexname = 'product_user_unique_item_number_key'"
                                ))
                                if not new_constraint_check.fetchone():
                                    # Create unique constraint on (user_id, unique_item_number)
                                    conn.execute(db.text(
                                        "CREATE UNIQUE INDEX IF NOT EXISTS product_user_unique_item_number_key "
                                        "ON product (user_id, unique_item_number) "
                                        "WHERE user_id IS NOT NULL AND unique_item_number IS NOT NULL"
                                    ))
                                    current_app.logger.info('Created user-scoped unique constraint on (user_id, unique_item_number)')
                                
                                # Check if new constraint for barbuddy_code already exists
                                barbuddy_index_check = conn.execute(db.text(
                                    "SELECT indexname FROM pg_indexes "
                                    "WHERE tablename = 'product' AND indexname = 'product_user_barbuddy_code_key'"
                                ))
                                if not barbuddy_index_check.fetchone():
                                    # Create unique constraint on (user_id, barbuddy_code)
                                    conn.execute(db.text(
                                        "CREATE UNIQUE INDEX IF NOT EXISTS product_user_barbuddy_code_key "
                                        "ON product (user_id, barbuddy_code) "
                                        "WHERE user_id IS NOT NULL AND barbuddy_code IS NOT NULL"
                                    ))
                                    current_app.logger.info('Created user-scoped unique constraint on (user_id, barbuddy_code)')
                            except Exception as e:
                                current_app.logger.warning(f'Could not create user-scoped constraints: {str(e)}')
                        
                        # Add new user-scoped unique constraint for homemade_ingredient.unique_code
                        if 'user_id' in homemade_columns_for_constraints:
                            try:
                                # Check if new constraint for unique_code already exists
                                homemade_unique_check = conn.execute(db.text(
                                    "SELECT indexname FROM pg_indexes "
                                    "WHERE tablename = 'homemade_ingredient' AND indexname = 'homemade_ingredient_user_unique_code_key'"
                                ))
                                if not homemade_unique_check.fetchone():
                                    # Create unique constraint on (user_id, unique_code)
                                    conn.execute(db.text(
                                        "CREATE UNIQUE INDEX IF NOT EXISTS homemade_ingredient_user_unique_code_key "
                                        "ON homemade_ingredient (user_id, unique_code) "
                                        "WHERE user_id IS NOT NULL AND unique_code IS NOT NULL"
                                    ))
                                    current_app.logger.info('Created user-scoped unique constraint on (user_id, unique_code) for homemade_ingredient')
                            except Exception as e:
                                current_app.logger.warning(f'Could not create user-scoped constraint for homemade_ingredient: {str(e)}')
                    except Exception as e:
                        current_app.logger.warning(f'Could not update unique constraints: {str(e)}')
                        # Try to drop constraints directly as fallback
                        try:
                            conn.execute(db.text("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_unique_item_number_key"))
                            conn.execute(db.text("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_barbuddy_code_key"))
                            conn.execute(db.text("ALTER TABLE homemade_ingredient DROP CONSTRAINT IF EXISTS homemade_ingredient_unique_code_key"))
                            current_app.logger.info('Attempted to drop old constraints as fallback')
                        except Exception:
                            pass
    except Exception as e:
        # Log error but don't crash - schema updates are best effort
        current_app.logger.warning(f'Schema update warning: {str(e)}')

