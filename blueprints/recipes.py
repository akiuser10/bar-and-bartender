"""
Recipes Blueprint
Handles all recipe routes
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, HomemadeIngredient, Recipe, RecipeIngredient
from utils.db_helpers import ensure_schema_updates
from utils.file_upload import save_uploaded_file
from utils.constants import resolve_recipe_category, category_context_from_type, CATEGORY_CONFIG

recipes_bp = Blueprint('recipes', __name__)


@recipes_bp.route('/recipes', methods=['GET'])
@login_required
def recipes_list():
    ensure_schema_updates()
    try:
        from sqlalchemy.orm import joinedload
        # Eagerly load ingredients to avoid N+1 queries and ensure cost calculation works
        from sqlalchemy import and_
        from utils.db_helpers import has_column
        try:
            if has_column('recipe', 'user_id'):
                recipes = Recipe.query.filter(Recipe.user_id == current_user.id).options(
                    joinedload(Recipe.ingredients)
                ).all()
            else:
                current_app.logger.info('user_id column does not exist yet in recipe table')
                recipes = []
        except Exception as e:
            current_app.logger.error(f'Error loading recipes: {str(e)}', exc_info=True)
            recipes = []
        
        recipe_type_filter = request.args.get('type', '')
        category_filter = request.args.get('category', '') or ''
        
        if recipe_type_filter:
            recipes = [r for r in recipes if r.recipe_type == recipe_type_filter]
        if category_filter:
            # Filter by actual category value (food_category or derived category)
            def matches_category(recipe):
                # First check food_category (most specific)
                if recipe.food_category:
                    # Normalize for comparison (handle spaces, case)
                    recipe_cat = recipe.food_category.strip()
                    filter_cat = category_filter.replace('-', ' ').strip()
                    if recipe_cat.lower() == filter_cat.lower():
                        return True
                else:
                    # Use the same logic as template to derive category
                    cat_key = (recipe.type or recipe.recipe_type or '').lower()
                    derived_cat = None
                    if cat_key in ['cocktails','classic']:
                        derived_cat = 'Cocktail'
                    elif cat_key in ['mocktails','signature']:
                        derived_cat = 'Mocktail'
                    elif cat_key in ['beverages','beverage']:
                        derived_cat = 'Beverage'
                    elif cat_key in ['food']:
                        derived_cat = 'Food'
                    
                    if derived_cat:
                        filter_cat = category_filter.replace('-', ' ').strip()
                        if derived_cat.lower() == filter_cat.lower():
                            return True
                return False
            recipes = [r for r in recipes if matches_category(r)]
        
        # Ensure ingredients are loaded for cost calculation
        for recipe in recipes:
            try:
                _ = recipe.ingredients
                for ingredient in recipe.ingredients:
                    try:
                        _ = ingredient.get_product()
                    except Exception as ing_e:
                        current_app.logger.warning(f"Error loading product for ingredient {ingredient.id}: {str(ing_e)}")
            except Exception as recipe_e:
                current_app.logger.warning(f"Error loading ingredients for recipe {recipe.id}: {str(recipe_e)}")
        
        # Collect unique category values from recipes (same logic as in template)
        unique_categories = set()
        for recipe in recipes:
            if recipe.food_category:
                unique_categories.add(recipe.food_category)
            else:
                # Use the same logic as the template to derive category
                cat_key = (recipe.type or recipe.recipe_type or '').lower()
                if cat_key in ['cocktails','classic']:
                    unique_categories.add('Cocktail')
                elif cat_key in ['mocktails','signature']:
                    unique_categories.add('Mocktail')
                elif cat_key in ['beverages','beverage']:
                    unique_categories.add('Beverage')
                elif cat_key in ['food']:
                    unique_categories.add('Food')
        
        # Sort categories for consistent display
        unique_categories = sorted(unique_categories)
        
        return render_template('recipes/list.html', recipes=recipes, selected_type=recipe_type_filter, selected_category=category_filter, unique_categories=unique_categories)
    except Exception as e:
        current_app.logger.error(f"Error in recipes_list: {str(e)}", exc_info=True)
        flash('An error occurred while loading recipes.', 'error')
        return render_template('recipes/list.html', recipes=[], selected_type='', selected_category='')


@recipes_bp.route('/recipes/<category>', methods=['GET'])
@login_required
def recipe_list(category):
    try:
        # Check if this is actually a recipe code (starts with 'REC-')
        # If so, redirect to the recipe code handler
        if category.startswith('REC-'):
            return view_recipe_by_code(category)
        
        canonical, config = resolve_recipe_category(category)
        if not canonical:
            # If category is invalid, redirect to recipes list instead of showing error
            flash(f"Category '{category}' not found. Showing all recipes.")
            return redirect(url_for('recipes.recipes_list'))

        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_, and_
        # Prioritize type field over recipe_type since recipe_type is generic ('Beverage')
        # and type field has specific values ('Beverages', 'Mocktails', 'Cocktails')
        from sqlalchemy import and_, or_
        recipes = Recipe.query.filter(Recipe.user_id == current_user.id).options(
            joinedload(Recipe.ingredients)
        ).filter(
            or_(
                Recipe.type.in_(config['db_labels']),
                and_(
                    or_(Recipe.type.is_(None), Recipe.type == ''),
                    Recipe.recipe_type.in_(config['db_labels'])
                )
            )
        ).all()
        
        # Ensure ingredients are loaded for cost calculation
        for recipe in recipes:
            try:
                _ = recipe.ingredients
                for ingredient in recipe.ingredients:
                    try:
                        _ = ingredient.get_product()
                    except Exception as ing_e:
                        current_app.logger.warning(f"Error loading product for ingredient {ingredient.id}: {str(ing_e)}")
            except Exception as recipe_e:
                current_app.logger.warning(f"Error loading ingredients for recipe {recipe.id}: {str(recipe_e)}")
        
        return render_template(
            'recipes/list.html',
            recipes=recipes,
            selected_type='',
            selected_category=canonical
        )
    except Exception as e:
        current_app.logger.error(f"Error in recipe_list: {str(e)}", exc_info=True)
        flash('An error occurred while loading recipes.', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipes/<code>')
@login_required
def view_recipe_by_code(code):
    try:
        # First check if it looks like a recipe code (starts with REC-)
        # This should take priority over category matching
        if code.startswith('REC-'):
            from sqlalchemy.orm import joinedload
            # First check if this is a valid recipe code
            recipe = Recipe.query.filter(Recipe.user_id == current_user.id, Recipe.recipe_code == code).first()
            if recipe:
                # Reload with eager loading
                recipe = Recipe.query.filter(Recipe.user_id == current_user.id).options(
                    joinedload(Recipe.ingredients)
                ).filter(Recipe.recipe_code == code).first()
                
                if not recipe:
                    # Recipe code exists but query failed
                    flash("Recipe not found")
                    return redirect(url_for('recipes.recipes_list'))
                
                # Ensure ingredients are loaded
                _ = recipe.ingredients
                for ingredient in recipe.ingredients:
                    try:
                        _ = ingredient.get_product()
                    except Exception as e:
                        current_app.logger.warning(f"Error loading product for ingredient {ingredient.id}: {str(e)}")
                        continue
                
                try:
                    batch = recipe.batch_summary()
                except Exception as e:
                    current_app.logger.warning(f"Error in batch_summary for recipe {recipe.id}: {str(e)}")
                    batch = {}
                
                category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or '')
                # Ensure category_slug is always valid
                if not category_slug or category_slug not in ['cocktails', 'mocktails', 'beverages']:
                    category_slug = 'cocktails'
                    category_display = 'Cocktails'
                # Double-check that category_slug is valid before rendering
                canonical_check, _ = resolve_recipe_category(category_slug)
                if not canonical_check:
                    category_slug = 'cocktails'
                    category_display = 'Cocktails'
                return render_template('recipes/view.html', recipe=recipe, batch=batch, category_slug=category_slug, category_display=category_display)
            else:
                # Recipe code not found
                flash("Recipe not found")
                return redirect(url_for('recipes.recipes_list'))
        
        # If not a recipe code, check if it's a category name
        canonical, config = resolve_recipe_category(code)
        if canonical:
            # This is a category, not a recipe code - call the category handler directly
            return recipe_list(canonical)
        
        # Not a recipe code and not a category
        flash("Recipe or category not found")
        return redirect(url_for('recipes.recipes_list'))
    except Exception as e:
        current_app.logger.error(f"Error in view_recipe_by_code: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'An error occurred while loading the recipe: {str(e)}', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipe/add/<category>', methods=['GET', 'POST'])
@login_required
def add_recipe(category):
    try:
        canonical, config = resolve_recipe_category(category)
        if not canonical:
            flash("Invalid recipe category")
            return redirect(url_for('main.index'))

        # Filter products and secondary ingredients by current user
        from utils.db_helpers import has_column
        try:
            if has_column('product', 'user_id'):
                products = Product.query.filter(Product.user_id == current_user.id).order_by(Product.description).all()
            else:
                products = Product.query.order_by(Product.description).all()
        except Exception:
            products = Product.query.order_by(Product.description).all()
        
        try:
            if has_column('homemade_ingredient', 'user_id'):
                secondary_ingredients = HomemadeIngredient.query.filter(HomemadeIngredient.user_id == current_user.id).order_by(HomemadeIngredient.name).all()
            else:
                secondary_ingredients = HomemadeIngredient.query.order_by(HomemadeIngredient.name).all()
        except Exception:
            secondary_ingredients = HomemadeIngredient.query.order_by(HomemadeIngredient.name).all()
        
        # Build ingredient options list, ensuring no duplicates
        ingredient_options = []
        seen_products = set()  # Track products by (description, code) to avoid duplicates
        
        for p in products:
            description = p.description or ''
            code = p.barbuddy_code or ''
            # Use a unique key to detect duplicates
            product_key = (description.lower().strip(), code.lower().strip())
            
            # Skip if we've already added this product
            if product_key in seen_products:
                current_app.logger.warning(f'Skipping duplicate product: {description} ({code})')
                continue
            
            seen_products.add(product_key)
            label = f"{description} ({code})" if code else description
            ingredient_options.append({
                'label': label,
                'description': description,
                'code': code,
                'id': p.id,
                'type': 'Product',
                'unit': p.selling_unit or 'ml',
                'cost_per_unit': p.cost_per_unit or 0.0,
                'container_volume': p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0)
            })
        
        # Add secondary ingredients, also checking for duplicates
        seen_secondary = set()
        for sec in secondary_ingredients:
            if not sec.unique_code:
                continue
            
            # Use a unique key to detect duplicates
            secondary_key = (sec.name.lower().strip() if sec.name else '', sec.unique_code.lower().strip())
            
            # Skip if we've already added this secondary ingredient
            if secondary_key in seen_secondary:
                current_app.logger.warning(f'Skipping duplicate secondary ingredient: {sec.name} ({sec.unique_code})')
                continue
            
            seen_secondary.add(secondary_key)
            try:
                # Ensure ingredients are loaded for cost calculation
                _ = sec.ingredients
                for item in sec.ingredients:
                    try:
                        _ = item.product
                    except Exception:
                        pass
                
                total_cost = sec.calculate_cost()
                cost_per_unit = sec.calculate_cost_per_unit()
                
                if cost_per_unit is None or cost_per_unit <= 0:
                    current_app.logger.warning(
                        f'Secondary ingredient {sec.id} ({sec.unique_code}) has zero or invalid cost_per_unit: {cost_per_unit}. '
                        f'Total cost: {total_cost}, Total volume: {sec.total_volume_ml}, '
                        f'Has ingredients: {len(sec.ingredients) if sec.ingredients else 0}'
                    )
                    cost_per_unit = 0.0
                else:
                    current_app.logger.debug(
                        f'Secondary ingredient {sec.id} ({sec.unique_code}): cost_per_unit={cost_per_unit}, '
                        f'total_cost={total_cost}, total_volume_ml={sec.total_volume_ml}'
                    )
            except Exception as e:
                current_app.logger.error(f'Error calculating cost_per_unit for secondary ingredient {sec.id} ({sec.unique_code}): {str(e)}', exc_info=True)
                cost_per_unit = 0.0
            
            ingredient_options.append({
                'label': f"{sec.name} ({sec.unique_code})",
                'description': sec.name,
                'code': sec.unique_code or '',
                'id': sec.id,
                'type': 'Secondary',
                'unit': sec.unit or 'ml',
                'cost_per_unit': cost_per_unit,
                'container_volume': sec.total_volume_ml or 1
            })

        if request.method == 'POST':
            try:
                title = request.form.get('title', '').strip()
                if not title:
                    flash('Recipe name is required.')
                    return redirect(url_for('recipes.add_recipe', category=canonical))
                
                method = request.form.get('method', '')
                garnish = request.form.get('garnish', '')
                food_category = request.form.get('food_category', '')
                item_level = request.form.get('item_level', 'Primary')
                selling_price = float(request.form.get('selling_price', 0) or 0)
                vat_percentage = float(request.form.get('vat_percentage', 0) or 0)
                service_charge_percentage = float(request.form.get('service_charge_percentage', 0) or 0)
                government_fees_percentage = float(request.form.get('government_fees_percentage', 0) or 0)
                
                # Generate unique recipe code (per user)
                max_attempts = 100
                recipe_code = None
                user_recipe_count = Recipe.query.filter(Recipe.user_id == current_user.id).count()
                for attempt in range(max_attempts):
                    candidate_code = f"REC-{user_recipe_count + attempt + 1:04d}"
                    existing = Recipe.query.filter(Recipe.user_id == current_user.id, Recipe.recipe_code == candidate_code).first()
                    if not existing:
                        recipe_code = candidate_code
                        break
                
                if not recipe_code:
                    # Fallback to timestamp-based code
                    from datetime import datetime
                    recipe_code = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                image_path = None
                if 'image' in request.files:
                    file = request.files['image']
                    if file and file.filename:
                        try:
                            image_path = save_uploaded_file(file, 'recipes')
                        except Exception as e:
                            current_app.logger.warning(f"Error saving image: {str(e)}")
                            # Continue without image if upload fails

                # Determine recipe_type and type based on category and food_category
                if canonical == 'food':
                    recipe_type = 'Food'
                    recipe_type_db = 'Food'
                else:
                    recipe_type = 'Beverage'
                    # For beverages, determine type based on food_category selection
                    if food_category:
                        food_category_lower = food_category.lower()
                        if 'cocktail' in food_category_lower:
                            recipe_type_db = 'Cocktails'
                        elif 'mocktail' in food_category_lower:
                            recipe_type_db = 'Mocktails'
                        else:
                            # For other beverages (wines, spirits, etc.), use Beverages
                            recipe_type_db = 'Beverages'
                    else:
                        # Default to Beverages if no category selected
                        recipe_type_db = config['db_labels'][0] if config else 'Beverages'
                
                recipe = Recipe(
                    recipe_code=recipe_code,
                    title=title,
                    method=method,
                    garnish=garnish,
                    food_category=food_category,
                    recipe_type=recipe_type,
                    type=recipe_type_db,
                    item_level=item_level,
                    user_id=current_user.id,
                    image_path=image_path,
                    selling_price=selling_price,
                    vat_percentage=vat_percentage,
                    service_charge_percentage=service_charge_percentage,
                    government_fees_percentage=government_fees_percentage
                )
                db.session.add(recipe)
                db.session.flush()

                # Parse ingredients from form data
                # The form sends: ingredient_id[], ingredient_type[], ingredient_qty[], ingredient_unit[]
                ingredient_ids = request.form.getlist('ingredient_id')
                ingredient_types = request.form.getlist('ingredient_type')
                ingredient_qtys = request.form.getlist('ingredient_qty')
                ingredient_units = request.form.getlist('ingredient_unit')
                
                current_app.logger.debug(f"Received {len(ingredient_ids)} ingredient IDs")
                current_app.logger.debug(f"Ingredient IDs: {ingredient_ids}")
                current_app.logger.debug(f"Ingredient types: {ingredient_types}")
                current_app.logger.debug(f"Ingredient qtys: {ingredient_qtys}")
                
                items_added = 0
                for idx, ing_id in enumerate(ingredient_ids):
                    if not ing_id or not str(ing_id).strip():
                        current_app.logger.debug(f"Skipping empty ingredient ID at index {idx}")
                        continue
                    
                    try:
                        ing_type = ingredient_types[idx] if idx < len(ingredient_types) else ''
                        qty_str = ingredient_qtys[idx] if idx < len(ingredient_qtys) else '0'
                        unit = ingredient_units[idx] if idx < len(ingredient_units) else 'ml'
                        
                        if not qty_str or not str(qty_str).strip():
                            current_app.logger.debug(f"Skipping ingredient {idx} - no quantity")
                            continue
                        
                        try:
                            qty = float(qty_str)
                        except (ValueError, TypeError):
                            current_app.logger.warning(f"Invalid quantity '{qty_str}' for ingredient {idx}")
                            continue
                        
                        if qty <= 0:
                            current_app.logger.debug(f"Skipping ingredient {idx} - quantity {qty} <= 0")
                            continue
                        
                        try:
                            ing_id_int = int(ing_id)
                        except (ValueError, TypeError):
                            current_app.logger.warning(f"Invalid ingredient ID '{ing_id}' at index {idx}")
                            continue
                        
                        # Determine ingredient_type for RecipeIngredient
                        db_ingredient_type = None
                        db_product_type = None
                        db_product_id = None
                        if ing_type == 'Product':
                            db_ingredient_type = 'Product'
                            db_product_type = 'Product'
                            db_product_id = ing_id_int
                        elif ing_type == 'Secondary':
                            db_ingredient_type = 'Homemade'
                            db_product_type = 'Homemade'
                            db_product_id = ing_id_int
                        else:
                            # Try to determine from ID
                            if Product.query.filter(Product.id == ing_id_int, Product.user_id == current_user.id).first():
                                db_ingredient_type = 'Product'
                                db_product_type = 'Product'
                                db_product_id = ing_id_int
                            elif HomemadeIngredient.query.filter(HomemadeIngredient.id == ing_id_int, HomemadeIngredient.user_id == current_user.id).first():
                                db_ingredient_type = 'Homemade'
                                db_product_type = 'Homemade'
                                db_product_id = ing_id_int
                            else:
                                current_app.logger.warning(f"Unknown ingredient type for ID {ing_id_int}, type was '{ing_type}'")
                                continue
                        
                        if not db_ingredient_type:
                            current_app.logger.warning(f"Could not determine ingredient type for ID {ing_id_int}")
                            continue
                        
                        # Calculate quantity_ml - ensure it's never None
                        quantity_ml = float(qty)  # Default to qty
                        if unit and unit != 'ml':
                            # Try to convert if we have the product info
                            if db_ingredient_type == 'Product':
                                product = Product.query.filter(Product.id == ing_id_int, Product.user_id == current_user.id).first()
                                if product and product.ml_in_bottle and product.ml_in_bottle > 0:
                                    # Assume unit is in bottles/containers
                                    quantity_ml = qty * product.ml_in_bottle
                            elif db_ingredient_type == 'Homemade':
                                # For secondary ingredients, assume ml
                                quantity_ml = qty
                        
                        # Ensure quantity_ml is a valid number
                        if quantity_ml is None or quantity_ml <= 0:
                            quantity_ml = qty
                        
                        item = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_type=db_ingredient_type,
                            ingredient_id=ing_id_int,
                            quantity=float(qty),
                            unit=str(unit) if unit else 'ml',
                            quantity_ml=float(quantity_ml),
                            product_type=db_product_type or db_ingredient_type,
                            product_id=db_product_id or ing_id_int
                        )
                        db.session.add(item)
                        items_added += 1
                        current_app.logger.debug(f"Added ingredient {idx}: type={db_ingredient_type}, id={ing_id_int}, qty={qty}, unit={unit}")
                    except (ValueError, TypeError) as e:
                        current_app.logger.warning(f"Error processing ingredient {idx}: {str(e)}", exc_info=True)
                        continue
                    except Exception as e:
                        current_app.logger.error(f"Unexpected error processing ingredient {idx}: {str(e)}", exc_info=True)
                        continue

                if items_added == 0:
                    flash('Please add at least one ingredient with a quantity greater than zero.')
                    db.session.rollback()
                    return redirect(url_for('recipes.add_recipe', category=canonical))

                db.session.commit()
                flash(f'{config["add_label"]} recipe added successfully!')
                return redirect(url_for('recipes.recipes_list'))
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                current_app.logger.error(f"Error creating recipe: {error_msg}", exc_info=True)
                
                # Provide more specific error messages
                if 'UNIQUE constraint' in error_msg or 'unique' in error_msg.lower():
                    flash('A recipe with this code already exists. Please try again.', 'error')
                elif 'NOT NULL constraint' in error_msg or 'null' in error_msg.lower():
                    flash('Missing required information. Please ensure all required fields are filled.', 'error')
                elif 'ingredient' in error_msg.lower():
                    flash(f'Error with ingredients: {error_msg}. Please check your ingredient selections.', 'error')
                else:
                    flash(f'An error occurred while creating the recipe: {error_msg}. Please try again.', 'error')
                
                return redirect(url_for('recipes.add_recipe', category=canonical))

        return render_template(
            'recipes/add_recipe.html',
            products=products,
            secondary_ingredients=secondary_ingredients,
            category=config['display'],
            add_label=config['add_label'],
            category_slug=canonical,
            ingredient_options=ingredient_options,
            edit_mode=False,
            recipe=None,
            preset_rows=[]
        )
    except Exception as e:
        current_app.logger.error(f"Error in add_recipe: {str(e)}", exc_info=True)
        flash('An error occurred while loading the recipe creation page.', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipe/<int:id>')
@login_required
def view_recipe(id):
    try:
        from sqlalchemy.orm import joinedload
        recipe = Recipe.query.filter(Recipe.id == id, Recipe.user_id == current_user.id).options(
            joinedload(Recipe.ingredients)
        ).first_or_404()
        
        # Ensure ingredients are loaded
        _ = recipe.ingredients
        for ingredient in recipe.ingredients:
            try:
                _ = ingredient.get_product()
            except Exception as e:
                current_app.logger.warning(f"Error loading product for ingredient {ingredient.id}: {str(e)}")
                continue
        
        try:
            batch = recipe.batch_summary()
        except Exception as e:
            current_app.logger.warning(f"Error in batch_summary for recipe {recipe.id}: {str(e)}")
            batch = {}
        
        category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or '')
        # Ensure category_slug is always valid
        if not category_slug or category_slug not in ['cocktails', 'mocktails', 'beverages']:
            category_slug = 'cocktails'
            category_display = 'Cocktails'
        # Double-check that category_slug is valid before rendering
        canonical_check, _ = resolve_recipe_category(category_slug)
        if not canonical_check:
            category_slug = 'cocktails'
            category_display = 'Cocktails'
        return render_template('recipes/view.html', recipe=recipe, batch=batch, category_slug=category_slug, category_display=category_display)
    except Exception as e:
        current_app.logger.error(f"Error in view_recipe: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'An error occurred while loading the recipe: {str(e)}', 'error')
        return redirect(url_for('recipes.recipes_list'))




@recipes_bp.route('/recipes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(id):
    ensure_schema_updates()
    try:
        from sqlalchemy.orm import joinedload
        recipe = Recipe.query.filter(Recipe.id == id, Recipe.user_id == current_user.id).options(
            joinedload(Recipe.ingredients)
        ).first_or_404()
        
        # Ensure ingredients are loaded
        _ = recipe.ingredients
        for ingredient in recipe.ingredients:
            _ = ingredient.get_product()
        
        category_slug, category_display = category_context_from_type(recipe.type or recipe.recipe_type or '')
        if not category_slug:
            category_slug = 'cocktails'
            category_display = 'Cocktails'
        config = CATEGORY_CONFIG.get(category_slug, CATEGORY_CONFIG['cocktails'])
        
        # Filter products and secondary ingredients by current user
        from utils.db_helpers import has_column
        try:
            if has_column('product', 'user_id'):
                products = Product.query.filter(Product.user_id == current_user.id).order_by(Product.description).all()
            else:
                products = Product.query.order_by(Product.description).all()
        except Exception:
            products = Product.query.order_by(Product.description).all()
        
        try:
            if has_column('homemade_ingredient', 'user_id'):
                secondary_ingredients = HomemadeIngredient.query.filter(HomemadeIngredient.user_id == current_user.id).order_by(HomemadeIngredient.name).all()
            else:
                secondary_ingredients = HomemadeIngredient.query.order_by(HomemadeIngredient.name).all()
        except Exception:
            secondary_ingredients = HomemadeIngredient.query.order_by(HomemadeIngredient.name).all()
        
        # Build ingredient options list, ensuring no duplicates
        ingredient_options = []
        seen_products = set()  # Track products by (description, code) to avoid duplicates
        
        for p in products:
            description = p.description or ''
            code = p.barbuddy_code or ''
            # Use a unique key to detect duplicates
            product_key = (description.lower().strip(), code.lower().strip())
            
            # Skip if we've already added this product
            if product_key in seen_products:
                current_app.logger.warning(f'Skipping duplicate product: {description} ({code})')
                continue
            
            seen_products.add(product_key)
            label = f"{description} ({code})" if code else description
            ingredient_options.append({
                'label': label,
                'description': description,
                'code': code,
                'id': int(p.id),
                'type': 'Product',
                'unit': p.selling_unit or 'ml',
                'cost_per_unit': float(p.cost_per_unit or 0.0),
                'container_volume': float(p.ml_in_bottle or (1 if (p.selling_unit or '').lower() == 'ml' else 0))
            })
        
        # Add secondary ingredients, also checking for duplicates
        seen_secondary = set()
        for sec in secondary_ingredients:
            if not sec.unique_code:
                continue
            
            # Use a unique key to detect duplicates
            secondary_key = (sec.name.lower().strip() if sec.name else '', sec.unique_code.lower().strip())
            
            # Skip if we've already added this secondary ingredient
            if secondary_key in seen_secondary:
                current_app.logger.warning(f'Skipping duplicate secondary ingredient: {sec.name} ({sec.unique_code})')
                continue
            
            seen_secondary.add(secondary_key)
            try:
                cost_per_unit = sec.calculate_cost_per_unit()
                if cost_per_unit is None or cost_per_unit <= 0:
                    current_app.logger.warning(f'Secondary ingredient {sec.id} ({sec.unique_code}) has zero or invalid cost_per_unit: {cost_per_unit}. Total cost: {sec.calculate_cost()}, Total volume: {sec.total_volume_ml}')
                    cost_per_unit = 0.0
            except Exception as e:
                current_app.logger.error(f'Error calculating cost_per_unit for secondary ingredient {sec.id} ({sec.unique_code}): {str(e)}', exc_info=True)
                cost_per_unit = 0.0
            
            ingredient_options.append({
                'label': f"{sec.name} ({sec.unique_code})",
                'description': sec.name,
                'code': sec.unique_code or '',
                'id': int(sec.id),
                'type': 'Secondary',
                'unit': sec.unit or 'ml',
                'cost_per_unit': float(cost_per_unit),
                'container_volume': float(sec.total_volume_ml or 1.0)
            })

        if request.method == 'POST':
            try:
                recipe.title = request.form['title']
                recipe.item_level = request.form.get('item_level', recipe.item_level or 'Primary')
                recipe.method = request.form.get('method', '')
                recipe.garnish = request.form.get('garnish', '')
                recipe.food_category = request.form.get('food_category', '')
                recipe.selling_price = float(request.form.get('selling_price', recipe.selling_price or 0))
                recipe.vat_percentage = float(request.form.get('vat_percentage', recipe.vat_percentage or 0))
                recipe.service_charge_percentage = float(request.form.get('service_charge_percentage', recipe.service_charge_percentage or 0))
                recipe.government_fees_percentage = float(request.form.get('government_fees_percentage', recipe.government_fees_percentage or 0))

                if 'image' in request.files:
                    file = request.files['image']
                    if file.filename:
                        recipe.image_path = save_uploaded_file(file, 'recipes')

                RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()

                ingredient_ids = request.form.getlist('ingredient_id')
                ingredient_types = request.form.getlist('ingredient_type')
                ingredient_quantities = request.form.getlist('ingredient_qty')
                ingredient_units = request.form.getlist('ingredient_unit')

                for idx, ing_id in enumerate(ingredient_ids):
                    if not ing_id or idx >= len(ingredient_types) or idx >= len(ingredient_quantities):
                        continue
                    
                    ing_type = (ingredient_types[idx] or '').strip()
                    try:
                        ing_id_int = int(ing_id)
                    except (ValueError, TypeError):
                        continue
                    
                    try:
                        qty = float(ingredient_quantities[idx] or 0)
                    except (ValueError, IndexError, TypeError):
                        qty = 0
                    
                    if qty <= 0:
                        continue
                    
                    unit = ingredient_units[idx] if idx < len(ingredient_units) and ingredient_units[idx] else 'ml'
                    
                    # Normalize type, and also set product_type/id for NOT NULL schema
                    if ing_type == 'Secondary':
                        db_ingredient_type = 'Homemade'
                    elif ing_type in ['Product', 'Homemade', 'Recipe']:
                        db_ingredient_type = ing_type
                    else:
                        # Best-effort detection
                        if Product.query.filter(Product.id == ing_id_int, Product.user_id == current_user.id).first():
                            db_ingredient_type = 'Product'
                        elif HomemadeIngredient.query.filter(HomemadeIngredient.id == ing_id_int, HomemadeIngredient.user_id == current_user.id).first():
                            db_ingredient_type = 'Homemade'
                        else:
                            db_ingredient_type = 'Recipe'
                    
                    db_product_type = db_ingredient_type
                    db_product_id = ing_id_int
                    
                    # Compute quantity_ml; convert if not ml and product has ml_in_bottle
                    quantity_ml = qty
                    if unit and unit != 'ml':
                        if db_ingredient_type == 'Product':
                            prod = Product.query.filter(Product.id == ing_id_int, Product.user_id == current_user.id).first()
                            if prod and prod.ml_in_bottle and prod.ml_in_bottle > 0:
                                quantity_ml = qty * prod.ml_in_bottle
                        # For Homemade/Recipe, treat qty as ml/serving
                    
                    if quantity_ml is None or quantity_ml <= 0:
                        quantity_ml = qty
                    
                    item = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_type=db_ingredient_type,
                        ingredient_id=ing_id_int,
                        quantity=qty,
                        unit=unit,
                        quantity_ml=float(quantity_ml),
                        product_type=db_product_type,
                        product_id=db_product_id
                    )
                    db.session.add(item)

                db.session.commit()
                flash('Recipe updated successfully!')
                return redirect(url_for('recipes.recipes_list'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating recipe: {str(e)}", exc_info=True)
                flash(f'An error occurred while updating the recipe: {str(e)}', 'error')
                return redirect(url_for('recipes.edit_recipe', id=id))

        preset_rows = []
        recipe_ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
        current_app.logger.info(f"Edit recipe {recipe.id}: Found {len(recipe_ingredients)} ingredients")
        for ingredient in recipe_ingredients:
            ing_type = ingredient.ingredient_type
            if ing_type == 'Homemade':
                ing_type = 'Secondary'
            
            label = ''
            description = ''
            code = ''
            if ing_type == 'Product':
                product = Product.query.filter(Product.id == ingredient.ingredient_id, Product.user_id == current_user.id).first()
                if product:
                    description = product.description or ''
                    code = product.barbuddy_code or ''
                    label = f"{description} ({code})" if code else description
            elif ing_type == 'Secondary':
                sec = HomemadeIngredient.query.filter(HomemadeIngredient.id == ingredient.ingredient_id, HomemadeIngredient.user_id == current_user.id).first()
                if sec and sec.unique_code:
                    description = sec.name or ''
                    code = sec.unique_code or ''
                    label = f"{description} ({code})" if code else description
            elif ing_type == 'Recipe':
                rec = Recipe.query.filter(Recipe.id == ingredient.ingredient_id, Recipe.user_id == current_user.id).first()
                if rec and rec.recipe_code:
                    description = rec.title or ''
                    code = rec.recipe_code or ''
                    label = f"{description} ({code})" if code else description
            
            if label:
                preset_rows.append({
                    'label': label,
                    'description': description,
                    'code': code,
                    'id': int(ingredient.ingredient_id),
                    'type': ing_type,
                    'qty': float(ingredient.quantity or 0),
                    'unit': ingredient.unit or 'ml'
                })

        return render_template('recipes/edit.html',
                               products=products,
                               secondary_ingredients=secondary_ingredients,
                               category=category_display,
                               add_label=config['add_label'],
                               category_slug=category_slug,
                               ingredient_options=ingredient_options,
                               recipe=recipe,
                               preset_rows=preset_rows)
    except Exception as e:
        current_app.logger.error(f"Error in edit_recipe: {str(e)}", exc_info=True)
        flash('An error occurred while loading the recipe for editing.', 'error')
        return redirect(url_for('recipes.recipes_list'))


@recipes_bp.route('/recipes/<int:id>/delete', methods=['POST'])
@login_required
def delete_recipe(id):
    recipe = Recipe.query.filter(Recipe.id == id, Recipe.user_id == current_user.id).first_or_404()
    db.session.delete(recipe)
    db.session.commit()
    flash('Recipe deleted successfully!')
    return redirect(url_for('recipes.recipes_list'))

