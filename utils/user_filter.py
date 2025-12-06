"""
Helper functions for user-based filtering
Handles cases where user_id column might not exist yet
"""
from flask import current_app
from extensions import db
from sqlalchemy import inspect


def has_user_id_column(model_class):
    """Check if the model has a user_id column in the database"""
    try:
        inspector = inspect(db.engine)
        table_name = model_class.__tablename__
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return 'user_id' in columns
    except Exception:
        return False


def filter_by_user(query, model_class, user_id):
    """
    Filter query by user_id if column exists, otherwise return empty query result
    """
    try:
        if has_user_id_column(model_class):
            return query.filter(model_class.user_id == user_id)
        else:
            # Column doesn't exist yet - return empty result
            current_app.logger.warning(f'user_id column does not exist in {model_class.__name__} table yet')
            return query.filter(False)  # Return empty result
    except Exception as e:
        current_app.logger.error(f'Error filtering by user: {str(e)}')
        return query.filter(False)  # Return empty result on error
