"""
Secondary Ingredients Blueprint
Handles all secondary ingredient (homemade ingredient) routes
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, HomemadeIngredient, HomemadeIngredientItem
from utils.db_helpers import ensure_schema_updates
import time

secondary_bp = Blueprint('secondary', __name__)


@secondary_bp.route('/secondary-ingredients', methods=['GET'])
@login_required
def secondary_ingredients():
    ensure_schema_updates()
    try:
        # Eagerly load ingredients and their products to ensure cost calculation works
        from sqlalchemy.orm import joinedload
        from utils.db_helpers import has_column
        try:
            if has_column('homemade_ingredient', 'user_id'):
                secondary_items = HomemadeIngredient.query.filter(HomemadeIngredient.user_id == current_user.id).options(
                    joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
                ).all()
            else:
                current_app.logger.info('user_id column does not exist yet in homemade_ingredient table')
                secondary_items = []
        except Exception as e:
            current_app.logger.error(f'Error loading secondary ingredients: {str(e)}', exc_info=True)
            secondary_items = []
        
        table_rows = []
        for item in secondary_items:
            try:
                # Ensure ingredients are loaded
                _ = item.ingredients
                for ingredient_item in item.ingredients:
                    _ = ingredient_item.product
                
                # Calculate total cost - sum of all ingredient costs
                try:
                    # Debug: Check if ingredients exist
                    if not item.ingredients:
                        current_app.logger.warning(f"Secondary ingredient {item.id} ({item.name}) has no ingredients")
                        total_cost = 0.0
                    else:
                        # Debug: Check each ingredient
                        for ing in item.ingredients:
                            if not ing.product:
                                current_app.logger.warning(f"Ingredient item {ing.id} has no product")
                            elif ing.product.cost_per_unit is None:
                                current_app.logger.warning(f"Product {ing.product.id} ({ing.product.description}) has no cost_per_unit")
                        total_cost = item.calculate_cost()
                        current_app.logger.debug(f"Calculated cost for {item.id} ({item.name}): {total_cost}, ingredients count: {len(item.ingredients)}")
                except Exception as e:
                    current_app.logger.error(f"Error calculating cost for {item.id}: {str(e)}", exc_info=True)
                    total_cost = 0.0
                
                # Calculate cost per unit
                try:
                    if item.total_volume_ml and item.total_volume_ml > 0:
                        unit_cost = item.calculate_cost_per_unit()
                    else:
                        unit_cost = 0.0
                except Exception as e:
                    current_app.logger.error(f"Error calculating unit cost for {item.id}: {str(e)}", exc_info=True)
                    unit_cost = 0.0
                
                table_rows.append({
                    'id': item.id,
                    'code': item.unique_code or f"SEC-{item.id:04d}",
                    'name': item.name or 'Unnamed',
                    'unit': item.unit or 'ml',
                    'total_volume': item.total_volume_ml or 0.0,
                    'total_cost': total_cost,
                    'unit_cost': unit_cost,
                    'item_level': 'Secondary'
                })
            except Exception as e:
                current_app.logger.error(f"Error processing secondary ingredient {item.id}: {str(e)}", exc_info=True)
                table_rows.append({
                    'id': item.id,
                    'code': item.unique_code or f"SEC-{item.id:04d}",
                    'name': item.name or 'Unnamed',
                    'unit': item.unit or 'ml',
                    'total_volume': item.total_volume_ml or 0.0,
                    'total_cost': 0.0,
                    'unit_cost': 0.0,
                    'item_level': 'Secondary'
                })
        return render_template('secondary_ingredients/list.html', secondary_rows=table_rows)
    except Exception as e:
        current_app.logger.error(f"Error in secondary_ingredients route: {str(e)}", exc_info=True)
        flash('An error occurred while loading secondary ingredients.', 'error')
        return render_template('secondary_ingredients/list.html', secondary_rows=[])


@secondary_bp.route('/secondary-ingredients/<int:id>')
@login_required
def view_secondary_ingredient(id):
    ensure_schema_updates()
    try:
        from sqlalchemy.orm import joinedload
        secondary = HomemadeIngredient.query.filter_by(user_id=current_user.id).options(
            joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
        ).first_or_404()
        
        # Ensure ingredients are loaded
        _ = secondary.ingredients
        for item in secondary.ingredients:
            try:
                _ = item.product
            except Exception as e:
                current_app.logger.warning(f"Error loading product for ingredient item {item.id}: {str(e)}")
                continue
        
        return render_template('secondary_ingredients/view.html', secondary=secondary)
    except Exception as e:
        current_app.logger.error(f"Error in view_secondary_ingredient: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'An error occurred while loading the secondary ingredient: {str(e)}', 'error')
        return redirect(url_for('secondary.secondary_ingredients'))


@secondary_bp.route('/secondary-ingredients/add', methods=['GET', 'POST'])
@login_required
def add_secondary_ingredient():
    ensure_schema_updates()
    products = Product.query.filter(Product.user_id == current_user.id).order_by(Product.description).all()
    existing_secondary = HomemadeIngredient.query.filter(HomemadeIngredient.user_id == current_user.id).order_by(HomemadeIngredient.name).all()
    ingredient_options = [
        {
            'label': f"{p.description} ({p.barbuddy_code})",
            'id': p.id,
            'type': 'Product',
            'code': p.barbuddy_code or 'N/A',
            'unit': p.selling_unit or 'ml',
            'cost_per_unit': p.cost_per_unit or 0.0,
            'container_volume': p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0)
        }
        for p in products
    ]
    for sec in existing_secondary:
        if sec.unique_code:
            try:
                cost_per_unit = sec.calculate_cost_per_unit()
            except Exception:
                cost_per_unit = 0.0
            ingredient_options.append({
                'label': f"{sec.name} ({sec.unique_code})",
                'id': sec.id,
                'type': 'Secondary',
                'code': sec.unique_code or 'N/A',
                'unit': sec.unit or 'ml',
                'cost_per_unit': cost_per_unit,
                'container_volume': sec.total_volume_ml or 1
            })

    preset_rows = []

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if not name:
                flash('Name is required.')
                return redirect(url_for('secondary.add_secondary_ingredient'))
            
            try:
                total_volume_ml = float(request.form.get('total_volume_ml', 0) or 0)
            except ValueError:
                total_volume_ml = 0
            unit = request.form.get('unit', 'ml')
            method = request.form.get('method', '')

            if total_volume_ml <= 0:
                flash('Total volume must be greater than zero.')
                return redirect(url_for('secondary.add_secondary_ingredient'))

            # Get max ID for this user only
            max_id = db.session.query(db.func.max(HomemadeIngredient.id)).filter_by(user_id=current_user.id).scalar() or 0
            counter = 1
            while True:
                unique_code = f"SEC-{max_id + counter:04d}"
                existing = HomemadeIngredient.query.filter_by(user_id=current_user.id, unique_code=unique_code).first()
                if not existing:
                    break
                counter += 1
                if counter > 1000:
                    unique_code = f"SEC-{int(time.time())}"
                    break

            homemade = HomemadeIngredient(
                user_id=current_user.id,
                name=name,
                unique_code=unique_code,
                total_volume_ml=total_volume_ml,
                unit=unit,
                method=method,
                created_by=current_user.id
            )
            db.session.add(homemade)
            db.session.flush()

            ingredient_labels = request.form.getlist('ingredient_label')
            ingredient_ids = request.form.getlist('ingredient_id')
            ingredient_types = request.form.getlist('ingredient_type')
            ingredient_quantities = request.form.getlist('ingredient_qty')
            ingredient_units = request.form.getlist('ingredient_unit')

            lookup = {}
            for opt in ingredient_options:
                lookup[opt['label'].lower()] = opt
                simple = opt['label'].split('(')[0].strip().lower()
                lookup.setdefault(simple, opt)

            matched = []
            for idx, label in enumerate(ingredient_labels):
                label_clean = (label or '').strip()
                if not label_clean:
                    continue
                
                option = None
                if idx < len(ingredient_ids) and ingredient_ids[idx]:
                    try:
                        ing_id = int(ingredient_ids[idx])
                        ing_type = ingredient_types[idx] if idx < len(ingredient_types) else None
                        for opt in ingredient_options:
                            if opt['id'] == ing_id and (not ing_type or opt['type'] == ing_type):
                                option = opt
                                break
                    except (ValueError, TypeError):
                        pass
                
                if not option:
                    option = lookup.get(label_clean.lower())
                
                try:
                    qty = float(ingredient_quantities[idx] or 0)
                except (ValueError, IndexError):
                    qty = 0
                unit_item = ingredient_units[idx] if idx < len(ingredient_units) and ingredient_units[idx] else 'ml'
                if not option or qty <= 0:
                    continue
                matched.append((option, qty, unit_item))

            if not matched:
                flash('Please add at least one valid ingredient.')
                db.session.rollback()
                return redirect(url_for('secondary.add_secondary_ingredient'))

            for option, qty, unit_item in matched:
                try:
                    if option['type'] == 'Secondary':
                        source_secondary = HomemadeIngredient.query.filter_by(id=option['id'], user_id=current_user.id).first()
                        if not source_secondary or not source_secondary.total_volume_ml or source_secondary.total_volume_ml <= 0:
                            continue
                        factor = qty / source_secondary.total_volume_ml
                        for component in source_secondary.ingredients:
                            base_qty = component.quantity or 0
                            if base_qty <= 0:
                                continue
                            scaled_qty = base_qty * factor
                            if scaled_qty <= 0:
                                continue
                            if not component.product_id:
                                continue
                            unit_val = component.unit or unit_item
                            quantity_ml_value = scaled_qty
                            item = HomemadeIngredientItem(
                                homemade_id=homemade.id,
                                product_id=component.product_id,
                                quantity=scaled_qty,
                                unit=unit_val,
                                quantity_ml=quantity_ml_value
                            )
                            db.session.add(item)
                    else:
                        product = Product.query.filter_by(id=option['id'], user_id=current_user.id).first()
                        if not product:
                            continue
                        quantity_ml_value = qty
                        item = HomemadeIngredientItem(
                            homemade_id=homemade.id,
                            product_id=option['id'],
                            quantity=qty,
                            unit=unit_item,
                            quantity_ml=quantity_ml_value
                        )
                        db.session.add(item)
                except Exception as e:
                    current_app.logger.error(f"Error adding ingredient item: {str(e)}", exc_info=True)
                    continue

            db.session.commit()
            flash('Secondary ingredient created successfully!')
            return redirect(url_for('secondary.secondary_ingredients'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating secondary ingredient: {str(e)}", exc_info=True)
            flash(f'An error occurred while creating the secondary ingredient: {str(e)}', 'error')
            return redirect(url_for('secondary.add_secondary_ingredient'))

    return render_template(
        'secondary_ingredients/add.html',
        ingredient_options=ingredient_options,
        edit_mode=False,
        secondary=None,
        preset_rows=preset_rows
    )


@secondary_bp.route('/secondary-ingredients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_secondary_ingredient(id):
    ensure_schema_updates()
    try:
        from sqlalchemy.orm import joinedload
        secondary = HomemadeIngredient.query.filter_by(user_id=current_user.id).options(
            joinedload(HomemadeIngredient.ingredients).joinedload(HomemadeIngredientItem.product)
        ).first_or_404()
        
        # Ensure ingredients are loaded
        _ = secondary.ingredients
        for item in secondary.ingredients:
            try:
                _ = item.product
            except Exception as e:
                current_app.logger.warning(f"Error loading product for ingredient item {item.id}: {str(e)}")
                continue
        products = Product.query.filter(Product.user_id == current_user.id).order_by(Product.description).all()
        existing_secondary = HomemadeIngredient.query.filter(HomemadeIngredient.user_id == current_user.id, HomemadeIngredient.id != id).order_by(HomemadeIngredient.name).all()

        ingredient_options = [
        {
            'label': f"{p.description} ({p.barbuddy_code})",
            'id': p.id,
            'type': 'Product',
            'code': p.barbuddy_code or 'N/A',
            'unit': p.selling_unit or 'ml',
            'cost_per_unit': p.cost_per_unit or 0.0,
            'container_volume': p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0)
        }
            for p in products
        ]
        for sec in existing_secondary:
            if sec.unique_code:
                try:
                    cost_per_unit = sec.calculate_cost_per_unit()
                except Exception:
                    cost_per_unit = 0.0
                ingredient_options.append({
                    'label': f"{sec.name} ({sec.unique_code})",
                    'id': sec.id,
                    'type': 'Secondary',
                    'code': sec.unique_code or 'N/A',
                    'unit': sec.unit or 'ml',
                    'cost_per_unit': cost_per_unit,
                    'container_volume': sec.total_volume_ml or 1
                })

        if request.method == 'POST':
            try:
                name = request.form.get('name', '').strip()
                if not name:
                    flash('Name is required.')
                    return redirect(url_for('secondary.edit_secondary_ingredient', id=id))
                
                try:
                    total_volume_ml = float(request.form.get('total_volume_ml', 0) or 0)
                except ValueError:
                    total_volume_ml = 0
                unit = request.form.get('unit', 'ml')
                method = request.form.get('method', '')

                if total_volume_ml <= 0:
                    flash('Total volume must be greater than zero.')
                    return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

                secondary.name = name
                secondary.total_volume_ml = total_volume_ml
                secondary.unit = unit
                secondary.method = method

                for item in secondary.ingredients:
                    db.session.delete(item)
                db.session.flush()

                ingredient_labels = request.form.getlist('ingredient_label')
                ingredient_ids = request.form.getlist('ingredient_id')
                ingredient_types = request.form.getlist('ingredient_type')
                ingredient_quantities = request.form.getlist('ingredient_qty')
                ingredient_units = request.form.getlist('ingredient_unit')

                lookup = {}
                for opt in ingredient_options:
                    lookup[opt['label'].lower()] = opt
                    simple = opt['label'].split('(')[0].strip().lower()
                    lookup.setdefault(simple, opt)

                matched = []
                for idx, label in enumerate(ingredient_labels):
                    label_clean = (label or '').strip()
                    if not label_clean:
                        continue
                    
                    option = None
                    if idx < len(ingredient_ids) and ingredient_ids[idx]:
                        try:
                            ing_id = int(ingredient_ids[idx])
                            ing_type = ingredient_types[idx] if idx < len(ingredient_types) else None
                            for opt in ingredient_options:
                                if opt['id'] == ing_id and (not ing_type or opt['type'] == ing_type):
                                    option = opt
                                    break
                        except (ValueError, TypeError):
                            pass
                    
                    if not option:
                        option = lookup.get(label_clean.lower())
                    
                    try:
                        qty = float(ingredient_quantities[idx] or 0)
                    except (ValueError, IndexError):
                        qty = 0
                    unit_item = ingredient_units[idx] if idx < len(ingredient_units) and ingredient_units[idx] else 'ml'
                    
                    # Validate that we have both a valid option and a positive quantity
                    if not option:
                        current_app.logger.warning(f"Ingredient not found for label: {label_clean}")
                        continue
                    if qty <= 0:
                        current_app.logger.warning(f"Invalid quantity {qty} for ingredient: {label_clean}")
                        continue
                        
                    matched.append((option, qty, unit_item))

                if not matched:
                    flash('Please add at least one valid ingredient with a quantity greater than zero.')
                    db.session.rollback()
                    return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

                items_added = 0
                for option, qty, unit_item in matched:
                    try:
                        if option['type'] == 'Secondary':
                            source_secondary = HomemadeIngredient.query.filter_by(id=option['id'], user_id=current_user.id).first()
                            if not source_secondary or not source_secondary.total_volume_ml or source_secondary.total_volume_ml <= 0:
                                current_app.logger.warning(f"Invalid secondary ingredient source: {option['id']}")
                                continue
                            factor = qty / source_secondary.total_volume_ml
                            for component in source_secondary.ingredients:
                                base_qty = component.quantity or 0
                                if base_qty <= 0:
                                    continue
                                scaled_qty = base_qty * factor
                                if scaled_qty <= 0:
                                    continue
                                if not component.product_id:
                                    continue
                                unit_val = component.unit or unit_item
                                quantity_ml_value = scaled_qty
                                item = HomemadeIngredientItem(
                                    homemade_id=secondary.id,
                                    product_id=component.product_id,
                                    quantity=scaled_qty,
                                    unit=unit_val,
                                    quantity_ml=quantity_ml_value
                                )
                                db.session.add(item)
                                items_added += 1
                        else:
                            product = Product.query.filter_by(id=option['id'], user_id=current_user.id).first()
                            if not product:
                                current_app.logger.warning(f"Product not found: {option['id']}")
                                continue
                            quantity_ml_value = qty
                            item = HomemadeIngredientItem(
                                homemade_id=secondary.id,
                                product_id=option['id'],
                                quantity=qty,
                                unit=unit_item,
                                quantity_ml=quantity_ml_value
                            )
                            db.session.add(item)
                            items_added += 1
                    except Exception as e:
                        current_app.logger.error(f"Error adding ingredient item: {str(e)}", exc_info=True)
                        continue

                if items_added == 0:
                    flash('No valid ingredients were added. Please check that ingredients are selected and quantities are greater than zero.')
                    db.session.rollback()
                    return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

                db.session.commit()
                # Expire and reload the secondary ingredient to ensure ingredients are loaded
                db.session.expire(secondary)
                db.session.refresh(secondary)
                # Force reload of ingredients relationship
                _ = secondary.ingredients
                for item in secondary.ingredients:
                    _ = item.product
                flash(f'Secondary ingredient updated successfully! {items_added} ingredient(s) added.')
                return redirect(url_for('secondary.view_secondary_ingredient', id=secondary.id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating secondary ingredient: {str(e)}", exc_info=True)
                flash(f'An error occurred while updating the secondary ingredient: {str(e)}', 'error')
                return redirect(url_for('secondary.edit_secondary_ingredient', id=id))

        preset_rows = []
        for component in secondary.ingredients:
            try:
                if component.product and component.product_id:
                    # Match the exact label format used in ingredient_options
                    description = component.product.description or ''
                    code = component.product.barbuddy_code or 'N/A'
                    label = f"{description} ({code})"
                    preset_rows.append({
                        'label': label.strip(),
                        'id': component.product_id,
                        'type': 'Product',
                        'qty': float(component.quantity or 0),
                        'unit': component.unit or 'ml',
                        'code': code
                    })
            except Exception as e:
                current_app.logger.warning(f"Error processing ingredient component {component.id} for preset rows: {str(e)}")
                # Skip this component if product is missing or inaccessible
                continue

        return render_template('secondary_ingredients/edit.html', ingredient_options=ingredient_options, secondary=secondary, preset_rows=preset_rows)
    except Exception as e:
        current_app.logger.error(f"Error in edit_secondary_ingredient: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'An error occurred while loading the secondary ingredient: {str(e)}', 'error')
        return redirect(url_for('secondary.secondary_ingredients'))


@secondary_bp.route('/secondary-ingredients/<int:id>/delete', methods=['POST'])
@login_required
def delete_secondary_ingredient(id):
    secondary = HomemadeIngredient.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(secondary)
    db.session.commit()
    flash('Secondary ingredient deleted successfully!')
    return redirect(url_for('secondary.secondary_ingredients'))


@secondary_bp.route('/secondary-ingredients/<int:id>/link-ingredient', methods=['GET', 'POST'])
@login_required
def link_ingredient_to_secondary(id):
    """Link a product/ingredient to a secondary ingredient via web interface"""
    secondary = HomemadeIngredient.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id', type=int)
            quantity = request.form.get('quantity', type=float)
            unit = request.form.get('unit', 'ml')
            
            if not product_id or not quantity or quantity <= 0:
                flash('Please provide a valid product and quantity.')
                return redirect(url_for('secondary.link_ingredient_to_secondary', id=id))
            
            product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
            if not product:
                flash('Product not found.')
                return redirect(url_for('secondary.link_ingredient_to_secondary', id=id))
            
            # Check if link already exists
            existing = HomemadeIngredientItem.query.filter_by(
                homemade_id=id,
                product_id=product_id
            ).first()
            
            if existing:
                existing.quantity = quantity
                existing.unit = unit
                existing.quantity_ml = quantity
                flash(f'Updated link: {product.description} ({quantity} {unit})')
            else:
                item = HomemadeIngredientItem(
                    homemade_id=id,
                    product_id=product_id,
                    quantity=quantity,
                    unit=unit,
                    quantity_ml=quantity
                )
                db.session.add(item)
                flash(f'Successfully linked: {product.description} ({quantity} {unit})')
            
            db.session.commit()
            return redirect(url_for('secondary.view_secondary_ingredient', id=id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error linking ingredient: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('secondary.link_ingredient_to_secondary', id=id))
    
    # GET request - show form
    products = Product.query.filter(Product.user_id == current_user.id).order_by(Product.description).all()
    existing_items = HomemadeIngredientItem.query.filter_by(homemade_id=id).all()
    
    return render_template('secondary_ingredients/link_ingredient.html', 
                         secondary=secondary, 
                         products=products,
                         existing_items=existing_items)


@secondary_bp.route('/secondary-ingredients/item/<int:id>/delete', methods=['POST'])
@login_required
def delete_ingredient_item(id):
    """Delete an individual ingredient item from a secondary ingredient"""
    item = HomemadeIngredientItem.query.get_or_404(id)
    secondary_id = item.homemade_id
    db.session.delete(item)
    db.session.commit()
    flash('Ingredient removed successfully!')
    return redirect(url_for('secondary.link_ingredient_to_secondary', id=secondary_id))

