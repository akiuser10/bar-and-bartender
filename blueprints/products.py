"""
Products/Ingredients Master List Blueprint
Handles all product and ingredient master list routes
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, HomemadeIngredient
from utils.db_helpers import ensure_schema_updates
from utils.file_upload import save_uploaded_file
from utils.ai_categorization import categorize_product_ai, should_use_ai_categorization
import uuid
import os
import time

products_bp = Blueprint('products', __name__)


@products_bp.route('/products')
@login_required
def products():
    return redirect(url_for('products.ingredients_master'))


@products_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        ensure_schema_updates()
        description = request.form['description']
        supplier = request.form.get('supplier', '').strip() or 'N/A'
        category = request.form['category']
        sub_category = request.form['sub_category']
        item_level = request.form.get('item_level', 'Primary')
        ml_in_bottle = float(request.form.get('ml_in_bottle', 0) or 0)
        abv = float(request.form.get('abv', 0) or 0)
        selling_unit = request.form['selling_unit']
        cost_per_unit = float(request.form['cost_per_unit'])
        purchase_type = request.form['purchase_type']
        bottles_per_case = int(request.form.get('bottles_per_case', 1))
        unique_item_number = (request.form.get('unique_item_number', '') or '').strip()

        if unique_item_number:
            if Product.query.filter(Product.user_id == current_user.id, Product.unique_item_number == unique_item_number).first():
                flash('Unique item number already exists. Please use a different value.')
                return redirect(url_for('products.add_product'))
        else:
            unique_item_number = f"ITEM-{uuid.uuid4().hex[:8].upper()}"

        # Get latest product for this user to generate next code
        latest_product = Product.query.filter(Product.user_id == current_user.id).order_by(Product.id.desc()).first()
        if latest_product and latest_product.barbuddy_code and latest_product.barbuddy_code[2:].isdigit():
            next_number = int(latest_product.barbuddy_code[2:]) + 1
        else:
            next_number = 1
        barbuddy_code = f"BB{next_number:03d}"

        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                image_path = save_uploaded_file(file, 'products')

        product = Product(
            user_id=current_user.id,
            unique_item_number=unique_item_number,
            supplier=supplier,
            barbuddy_code=barbuddy_code,
            description=description,
            category=category,
            sub_category=sub_category,
            item_level=item_level,
            ml_in_bottle=ml_in_bottle,
            abv=abv,
            selling_unit=selling_unit,
            cost_per_unit=cost_per_unit,
            purchase_type=purchase_type,
            bottles_per_case=bottles_per_case,
            image_path=image_path
        )

        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!')
        return redirect(url_for('products.products'))
    return render_template('products/add_product.html')


@products_bp.route('/ingredients', methods=['GET'])
@login_required
def ingredients_master():
    try:
        category_filter = request.args.get('category', '')
        level_filter = request.args.get('level', '')
        # Filter by user_id, excluding NULL user_id records (old data)
        # Handle case where user_id column might not exist yet
        from utils.db_helpers import has_column
        try:
            if has_column('product', 'user_id') and has_column('homemade_ingredient', 'user_id'):
                # Columns exist - filter by user
                products = Product.query.filter(Product.user_id == current_user.id).all()
                secondary_items = HomemadeIngredient.query.filter(HomemadeIngredient.user_id == current_user.id).all()
            else:
                # Columns don't exist yet - return empty lists
                current_app.logger.info('user_id columns do not exist yet - returning empty lists')
                products = []
                secondary_items = []
        except Exception as e:
            # If any error occurs, return empty lists
            current_app.logger.error(f'Error loading ingredients: {str(e)}', exc_info=True)
            products = []
            secondary_items = []

        rows = []
        for p in products:
            rows.append({
                'id': p.id,
                'kind': 'product',
                'image': p.image_path,
                'unique_item_number': p.unique_item_number or 'N/A',
                'code': p.barbuddy_code or 'N/A',
                'description': p.description,
                'supplier': p.supplier or 'N/A',
                'category': p.category or 'Product',
                'sub_category': p.sub_category or 'Other',
                'item_level': p.item_level or 'Primary',
                'quantity': p.ml_in_bottle,
                'cost_per_unit': p.cost_per_unit or 0.0
            })

        for sec in secondary_items:
            rows.append({
                'id': sec.id,
                'kind': 'secondary',
                'image': None,
                'unique_item_number': sec.unique_code or 'N/A',
                'code': sec.unique_code or 'N/A',
                'description': sec.name,
                'supplier': 'In-House',
                'category': 'Secondary',
                'sub_category': 'Secondary Ingredient',
                'item_level': 'Secondary',
                'quantity': sec.total_volume_ml,
                'cost_per_unit': sec.calculate_cost_per_unit()
            })

        if category_filter:
            rows = [r for r in rows if (r['sub_category'] or '').lower() == category_filter.lower()]
        if level_filter:
            rows = [r for r in rows if (r['item_level'] or 'Primary') == level_filter]

        categories = db.session.query(Product.sub_category).filter(Product.user_id == current_user.id).distinct().all()
        categories = [c[0] for c in categories if c[0]]
        default_categories = ['Alcohol', 'Non Alcohol', 'Non-Alcohol', 'Fruits', 'Vegetables', 'Dairy', 'Syrups & Purees', 'Syrup', 'Puree', 'Juice', 'Other', 'Food', 'Beverage', 'Secondary Ingredient']
        categories = sorted(set(categories + default_categories))
        return render_template('master_list/master.html', rows=rows, categories=categories, selected_category=category_filter, selected_level=level_filter)
    except Exception as e:
        flash(f'Error loading ingredients: {str(e)}')
        current_app.logger.error(f'Error in ingredients_master: {str(e)}', exc_info=True)
        return render_template('master_list/master.html', rows=[], categories=[], selected_category='', selected_level='')


@products_bp.route('/ingredients/add', methods=['GET', 'POST'])
@login_required
def add_ingredient():
    if request.method == 'POST':
        ensure_schema_updates()
        unique_item_number = (request.form.get('unique_item_number', '') or '').strip()
        description = request.form['description']
        supplier = request.form.get('supplier', '').strip() or 'N/A'
        category = request.form['category']
        sub_category = request.form['sub_category']
        ml_in_bottle = float(request.form.get('ml_in_bottle', 0) or 0)
        item_level = request.form.get('item_level', 'Primary')
        abv = 0.0
        selling_unit = request.form['selling_unit']
        cost_per_unit = float(request.form['cost_per_unit'])
        purchase_type = request.form.get('purchase_type', 'each')
        bottles_per_case = int(request.form.get('bottles_per_case', 1) or 1)

        if unique_item_number:
            if Product.query.filter(Product.user_id == current_user.id, Product.unique_item_number == unique_item_number).first():
                flash('Unique item number already exists. Please use a different one.')
                return redirect(url_for('products.ingredients_master'))
        else:
            unique_item_number = f"ITEM-{uuid.uuid4().hex[:8].upper()}"

        latest_product = Product.query.filter(Product.user_id == current_user.id).order_by(Product.id.desc()).first()
        if latest_product and latest_product.barbuddy_code and latest_product.barbuddy_code[2:].isdigit():
            next_number = int(latest_product.barbuddy_code[2:]) + 1
        else:
            next_number = 1
        barbuddy_code = f"BB{next_number:03d}"

        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                image_path = save_uploaded_file(file, 'products')

        product = Product(
            user_id=current_user.id,
            unique_item_number=unique_item_number,
            supplier=supplier,
            barbuddy_code=barbuddy_code,
            description=description,
            category=category,
            sub_category=sub_category,
            item_level=item_level,
            ml_in_bottle=ml_in_bottle,
            abv=abv,
            selling_unit=selling_unit,
            cost_per_unit=cost_per_unit,
            purchase_type=purchase_type,
            bottles_per_case=bottles_per_case,
            image_path=image_path
        )

        db.session.add(product)
        db.session.commit()
        flash('Ingredient added successfully!')
        return redirect(url_for('products.ingredients_master'))
    return render_template('master_list/add.html')


@products_bp.route('/ingredients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ingredient(id):
    product = Product.query.filter(Product.id == id, Product.user_id == current_user.id).first_or_404()
    if request.method == 'POST':
        product.unique_item_number = request.form.get('unique_item_number', product.unique_item_number)
        product.description = request.form['description']
        product.supplier = request.form.get('supplier', product.supplier or 'N/A').strip() or 'N/A'
        product.category = request.form['category']
        product.sub_category = request.form['sub_category']
        product.item_level = request.form.get('item_level', product.item_level or 'Primary')
        product.ml_in_bottle = float(request.form.get('ml_in_bottle', 0) or 0)
        product.selling_unit = request.form['selling_unit']
        product.cost_per_unit = float(request.form['cost_per_unit'])
        product.purchase_type = request.form.get('purchase_type', 'each')
        product.bottles_per_case = int(request.form.get('bottles_per_case', 1) or 1)
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                if product.image_path:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], product.image_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                product.image_path = save_uploaded_file(file, 'products')
        
        db.session.commit()
        flash('Ingredient updated successfully!')
        return redirect(url_for('products.ingredients_master'))
    return render_template('master_list/edit.html', product=product)


@products_bp.route('/ingredients/<int:id>/delete', methods=['POST'])
@login_required
def delete_ingredient(id):
    product = Product.query.filter(Product.id == id, Product.user_id == current_user.id).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash('Ingredient deleted successfully!')
    return redirect(url_for('products.ingredients_master'))


@products_bp.route('/ingredients/delete-all', methods=['POST'])
@login_required
def delete_all_ingredients():
    try:
        ensure_schema_updates()
        # Delete all products for this user (not secondary ingredients)
        products = Product.query.filter(Product.user_id == current_user.id).all()
        count = len(products)
        for product in products:
            db.session.delete(product)
        db.session.commit()
        flash(f'Successfully deleted {count} product(s) from the master list.')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting all ingredients: {str(e)}', exc_info=True)
        flash('An error occurred while deleting all products.', 'error')
    return redirect(url_for('products.ingredients_master'))


@products_bp.route('/ingredients/delete-selected', methods=['POST'])
@login_required
def delete_selected_ingredients():
    try:
        ensure_schema_updates()
        selected_ids = request.form.getlist('selected_items')
        if not selected_ids:
            flash('No items selected for deletion.', 'error')
            return redirect(url_for('products.ingredients_master'))
        
        count = 0
        for item_id in selected_ids:
            try:
                product = Product.query.filter(Product.id == int(item_id), Product.user_id == current_user.id).first()
                if product:
                    db.session.delete(product)
                    count += 1
            except (ValueError, TypeError):
                continue
        
        db.session.commit()
        flash(f'Successfully deleted {count} selected product(s) from the master list.')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting selected ingredients: {str(e)}', exc_info=True)
        flash('An error occurred while deleting selected products.', 'error')
    return redirect(url_for('products.ingredients_master'))


@products_bp.route('/ingredients/bulk-upload', methods=['POST'])
@login_required
def bulk_upload_products():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('Please choose an Excel file to upload.')
        return redirect(url_for('products.ingredients_master'))

    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Only .xlsx or .xls files are supported for bulk upload.')
        return redirect(url_for('products.ingredients_master'))

    try:
        import pandas as pd
    except ImportError:
        flash('Pandas is required for bulk upload. Please install it via pip install pandas openpyxl.')
        return redirect(url_for('products.ingredients_master'))

    try:
        df = pd.read_excel(file)
    except Exception as exc:
        flash(f'Failed to read Excel file: {exc}')
        return redirect(url_for('products.ingredients_master'))

    required_columns = ['DESCRIPTION', 'SUPPLIER', 'CATEGORY', 'COST/UNIT (AED)']
    normalized_columns = {str(col).upper().strip(): col for col in df.columns}
    missing = [col for col in required_columns if col not in normalized_columns]
    if missing:
        flash(f'Missing required columns: {", ".join(missing)}')
        return redirect(url_for('products.ingredients_master'))

    def clean_str(value, default=''):
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()

    created = 0
    skipped = 0
    base_count = Product.query.filter(Product.user_id == current_user.id).count()
    
    # Track used codes in this batch to avoid duplicates within the same upload
    used_unique_numbers = set()
    used_barbuddy_codes = set()
    
    # Get existing codes for this user to avoid conflicts
    existing_unique_numbers = {p.unique_item_number for p in Product.query.filter(Product.user_id == current_user.id).all() if p.unique_item_number}
    existing_barbuddy_codes = {p.barbuddy_code for p in Product.query.filter(Product.user_id == current_user.id).all() if p.barbuddy_code}

    for idx, row in df.iterrows():
        try:
            description = clean_str(row[normalized_columns['DESCRIPTION']])
            if not description:
                skipped += 1
                continue

            supplier = clean_str(row[normalized_columns['SUPPLIER']], 'N/A') or 'N/A'
            category = clean_str(row[normalized_columns['CATEGORY']])
            if not category:
                category = 'Other'

            sub_cat_col = normalized_columns.get('SUB CATEGORY')
            # Preserve the exact sub_category from Excel sheet if it exists and is not empty
            if sub_cat_col and row.get(sub_cat_col):
                sub_category_raw = str(row.get(sub_cat_col)).strip()
                sub_category = sub_category_raw if sub_category_raw else 'Other'
            else:
                # Only set to 'Other' if column doesn't exist or is truly empty
                sub_category = 'Other'
            
            # Use AI to categorize ONLY if category or sub_category is truly missing/empty
            # Don't use AI if sub_category is explicitly "Other" from the Excel sheet
            category_missing = not category or category.strip() == '' or category.strip() == 'Other'
            sub_category_missing = (not sub_cat_col or not row.get(sub_cat_col) or 
                                   (sub_category and sub_category.strip() == ''))
            
            if category_missing or sub_category_missing:
                try:
                    ai_category, ai_sub_category = categorize_product_ai(description, supplier)
                    if ai_category and category_missing:
                        category = ai_category
                        current_app.logger.info(f'AI categorized "{description}" as category: {category}')
                    # Only overwrite sub_category if it was truly missing (not explicitly "Other" from sheet)
                    if ai_sub_category and sub_category_missing:
                        sub_category = ai_sub_category
                        current_app.logger.info(f'AI categorized "{description}" as sub_category: {sub_category}')
                except Exception as e:
                    current_app.logger.warning(f'AI categorization failed for "{description}": {str(e)}')
                    # Continue with original values if AI fails

            item_level_col = normalized_columns.get('ITEM LEVEL')
            item_level = clean_str(row.get(item_level_col), 'Primary') if item_level_col else 'Primary'
            if item_level.lower() not in ('primary', 'secondary'):
                item_level = 'Primary'

            unit_col = normalized_columns.get('UNIT')
            unit = clean_str(row.get(unit_col), 'each') if unit_col else 'each'

            cost_per_unit = row[normalized_columns['COST/UNIT (AED)']]
            try:
                cost_per_unit = float(cost_per_unit or 0)
            except (TypeError, ValueError):
                cost_per_unit = 0.0

            unique_col = normalized_columns.get('UNIQUE ITEM #')
            unique_item_number = clean_str(row.get(unique_col)) if unique_col else ''
            # Check if it exists in database OR in this batch
            if unique_item_number:
                if unique_item_number in existing_unique_numbers or unique_item_number in used_unique_numbers:
                    unique_item_number = ''  # Will generate new one
                else:
                    used_unique_numbers.add(unique_item_number)

            code_col = normalized_columns.get('CODE')
            barbuddy_code = clean_str(row.get(code_col)) if code_col else ''
            # Check if it exists in database OR in this batch
            if barbuddy_code:
                if barbuddy_code in existing_barbuddy_codes or barbuddy_code in used_barbuddy_codes:
                    barbuddy_code = ''  # Will generate new one
                else:
                    used_barbuddy_codes.add(barbuddy_code)

            quantity_col = normalized_columns.get('QUANTITY')
            quantity_value = row.get(quantity_col)
            try:
                ml_in_bottle = float(quantity_value) if quantity_value is not None and not pd.isna(quantity_value) else None
            except (TypeError, ValueError):
                ml_in_bottle = None

            # Generate unique codes if not provided or if duplicates found
            if not unique_item_number:
                counter = 1
                while True:
                    candidate = f"ITEM-{base_count + created + counter:06d}"
                    if candidate not in existing_unique_numbers and candidate not in used_unique_numbers:
                        unique_item_number = candidate
                        used_unique_numbers.add(candidate)
                        break
                    counter += 1
                    if counter > 10000:  # Safety limit
                        unique_item_number = f"ITEM-{int(time.time())}{created:04d}"
                        break
            
            if not barbuddy_code:
                counter = 1
                while True:
                    candidate = f"BB{base_count + created + counter:03d}"
                    if candidate not in existing_barbuddy_codes and candidate not in used_barbuddy_codes:
                        barbuddy_code = candidate
                        used_barbuddy_codes.add(candidate)
                        break
                    counter += 1
                    if counter > 10000:  # Safety limit
                        barbuddy_code = f"BB{int(time.time())}{created:04d}"
                        break

            product = Product(
                user_id=current_user.id,
                description=description,
                supplier=supplier,
                category=category,
                sub_category=sub_category,
                selling_unit=unit,
                cost_per_unit=cost_per_unit,
                unique_item_number=unique_item_number,
                barbuddy_code=barbuddy_code,
                item_level=item_level,
                ml_in_bottle=ml_in_bottle,
                image_path=None
            )
            db.session.add(product)
            created += 1
        except Exception as exc:
            skipped += 1
            current_app.logger.error('Failed to import row %s: %s', idx, exc, exc_info=True)
            db.session.rollback()  # Rollback this failed row
            continue

    try:
        db.session.commit()
        flash(f'Imported {created} products successfully. Skipped {skipped} rows.')
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f'Failed to save imported products: {str(exc)}', exc_info=True)
        flash(f'Failed to save imported products: {exc}')

    return redirect(url_for('products.ingredients_master'))

