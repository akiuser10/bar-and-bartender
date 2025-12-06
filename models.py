from flask_login import UserMixin
from datetime import datetime

# Import db from extensions (will be initialized in app factory)
from extensions import db

# -------------------------
# USER MODEL
# -------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


# -------------------------
# VERIFICATION CODE MODEL
# -------------------------
class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

# -------------------------
# PRODUCT MODEL
# -------------------------
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='products')
    unique_item_number = db.Column(db.String(50))
    supplier = db.Column(db.String(120))
    barbuddy_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    sub_category = db.Column(db.String(50))
    item_level = db.Column(db.String(20), default='Primary')
    ml_in_bottle = db.Column(db.Float)
    abv = db.Column(db.Float)
    selling_unit = db.Column(db.String(20), default="ml")
    cost_per_unit = db.Column(db.Float, nullable=False)
    supplier_product_code = db.Column(db.String(50))
    purchase_type = db.Column(db.String(10), default="each")
    bottles_per_case = db.Column(db.Integer, default=1)
    case_cost = db.Column(db.Float, default=0.0)
    image_path = db.Column(db.String(255))
    
    # Add unique constraint on user_id + barbuddy_code combination
    __table_args__ = (db.UniqueConstraint('user_id', 'barbuddy_code', name='_user_barbuddy_code_uc'),)

    def calculate_case_cost(self):
        if self.purchase_type == "case":
            return round(self.cost_per_unit * self.bottles_per_case, 2)
        return self.cost_per_unit

# -------------------------
# HOMEMADE INGREDIENTS (Secondary Ingredients)
# -------------------------
class HomemadeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='homemade_ingredients')
    name = db.Column(db.String(150), nullable=False)
    unique_code = db.Column(db.String(50))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Keep for backward compatibility
    creator = db.relationship('User', foreign_keys=[created_by])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_volume_ml = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default="ml")
    method = db.Column(db.Text)
    ingredients = db.relationship('HomemadeIngredientItem', backref='homemade', cascade='all, delete-orphan')
    
    # Add unique constraint on user_id + unique_code combination
    __table_args__ = (db.UniqueConstraint('user_id', 'unique_code', name='_user_unique_code_uc'),)

    def calculate_cost(self):
        return round(sum(i.calculate_cost() for i in self.ingredients), 2)
    
    def calculate_cost_per_unit(self):
        """Calculate cost per unit (ml, gram, etc.)"""
        if self.total_volume_ml > 0:
            return round(self.calculate_cost() / self.total_volume_ml, 4)
        return 0.0

class HomemadeIngredientItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    homemade_id = db.Column(db.Integer, db.ForeignKey('homemade_ingredient.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_ml = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), default="ml")
    product = db.relationship('Product')

    def calculate_cost(self):
        """Calculate cost based on product's unit and quantity"""
        prod = self.product
        qty = self.quantity

        if not prod:
            return 0.0

        # If cost_per_unit is None or 0, return 0
        if prod.cost_per_unit is None or prod.cost_per_unit == 0:
            return 0.0

        # Calculate cost per unit based on product's selling unit
        if prod.selling_unit == "ml":
            # For ml, cost_per_unit is already per ml
            cost_per_unit = prod.cost_per_unit
        elif prod.selling_unit == "grams":
            # For grams, cost_per_unit is per gram
            cost_per_unit = prod.cost_per_unit
        elif prod.selling_unit == "pieces":
            # For pieces, cost_per_unit is per piece
            cost_per_unit = prod.cost_per_unit
        else:
            # For other units or if ml_in_bottle is set, calculate per ml
            if prod.ml_in_bottle and prod.ml_in_bottle > 0:
                # cost_per_unit is typically the cost of the whole bottle
                # So cost per ml = cost_per_unit / ml_in_bottle
                cost_per_unit = prod.cost_per_unit / prod.ml_in_bottle
            else:
                # Fallback to cost_per_unit as-is
                cost_per_unit = prod.cost_per_unit

        # Calculate total cost: cost per unit * quantity
        total_cost = cost_per_unit * qty
        return round(total_cost, 2)

# -------------------------
# RECIPE MODEL
# -------------------------
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_code = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(150), nullable=False)
    method = db.Column(db.Text)
    recipe_type = db.Column(db.String(20))
    type = db.Column(db.String(20))
    item_level = db.Column(db.String(20), default='Primary')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref='recipes')
    ingredients = db.relationship('RecipeIngredient', backref='recipe', cascade='all, delete-orphan')
    image_path = db.Column(db.String(255))
    selling_price = db.Column(db.Float, default=0.0)
    vat_percentage = db.Column(db.Float, default=0.0)
    service_charge_percentage = db.Column(db.Float, default=0.0)
    government_fees_percentage = db.Column(db.Float, default=0.0)
    garnish = db.Column(db.Text)

    def calculate_total_cost(self):
        """Calculate total cost including nested recipes"""
        try:
            total = 0.0
            for i in self.ingredients:
                cost = i.calculate_cost()
                total += cost
            return round(total, 2)
        except Exception as e:
            import logging
            logging.error(f"Error calculating total cost for Recipe {self.id}: {str(e)}")
            return 0.0

    def cost_percentage(self):
        total_cost = self.calculate_total_cost()
        # Selling price is inclusive of VAT, Service Charge, and Government Fees
        # Calculate base selling price by deducting fees
        if self.selling_price and self.selling_price > 0:
            vat = self.vat_percentage or 0.0
            service_charge = self.service_charge_percentage or 0.0
            govt_fees = self.government_fees_percentage or 0.0
            total_fees_percentage = vat + service_charge + govt_fees
            
            # Calculate base selling price (before fees)
            # SP_inclusive = Base_SP × (1 + fees/100)
            # Base_SP = SP_inclusive / (1 + fees/100)
            if total_fees_percentage > 0:
                base_selling_price = self.selling_price / (1 + total_fees_percentage / 100)
            else:
                base_selling_price = self.selling_price
            
            return round((total_cost / base_selling_price) * 100, 2)
        return None
    
    def total_selling_price_with_fees(self):
        """Calculate total selling price including all fees"""
        if not self.selling_price or self.selling_price <= 0:
            return 0.0
        vat = self.vat_percentage or 0.0
        service_charge = self.service_charge_percentage or 0.0
        govt_fees = self.government_fees_percentage or 0.0
        total_fees_percentage = vat + service_charge + govt_fees
        return round(self.selling_price * (1 + total_fees_percentage / 100), 2)

    def selling_price_value(self):
        return round(self.selling_price or 0.0, 2)

    def batch_summary(self):
        try:
            summary = {"Alcohol":0,"Syrups & Purees":0,"Juices":0,"Fruits":0,"Vegetables":0,"Dairy":0,"Non-Alcohol":0,"Other":0}
            for i in self.ingredients:
                try:
                    prod = i.get_product()
                    if not prod:
                        continue
                        
                    category = "Other"
                    if isinstance(prod, Product):
                        sub_cat = prod.sub_category or ""
                        if sub_cat == "Alcohol":
                            category = "Alcohol"
                        elif sub_cat in ["Syrup", "Puree", "Syrups & Purees"]:
                            category = "Syrups & Purees"
                        elif sub_cat == "Juice":
                            category = "Juices"
                        elif sub_cat == "Fruits":
                            category = "Fruits"
                        elif sub_cat == "Vegetables":
                            category = "Vegetables"
                        elif sub_cat == "Dairy":
                            category = "Dairy"
                        elif sub_cat == "Non-Alcohol":
                            category = "Non-Alcohol"
                    elif isinstance(prod, HomemadeIngredient):
                        category = "Syrups & Purees"
                    elif isinstance(prod, Recipe):
                        category = "Other"
                    
                    qty = i.get_quantity()
                    if qty is None or qty <= 0:
                        continue
                    summary[category] += qty
                except Exception as e:
                    import logging
                    logging.error(f"Error processing ingredient in batch_summary: {str(e)}")
                    continue
            return summary
        except Exception as e:
            import logging
            logging.error(f"Error in batch_summary for Recipe {self.id}: {str(e)}")
            return {"Alcohol":0,"Syrups & Purees":0,"Juices":0,"Fruits":0,"Vegetables":0,"Dairy":0,"Non-Alcohol":0,"Other":0}

class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    ingredient_type = db.Column(db.String(20))
    ingredient_id = db.Column(db.Integer)
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20), default="ml")
    quantity_ml = db.Column(db.Float)
    product_type = db.Column(db.String(20))
    product_id = db.Column(db.Integer)

    def get_product(self):
        """Get the ingredient (Product, HomemadeIngredient, or Recipe) - filtered by recipe's user"""
        # Get user_id from the recipe this ingredient belongs to
        user_id = self.recipe.user_id if self.recipe else None
        
        if self.ingredient_type:
            if self.ingredient_type == "Product":
                if user_id:
                    return Product.query.filter_by(id=self.ingredient_id, user_id=user_id).first()
                return Product.query.get(self.ingredient_id)
            elif self.ingredient_type == "Homemade":
                if user_id:
                    return HomemadeIngredient.query.filter_by(id=self.ingredient_id, user_id=user_id).first()
                return HomemadeIngredient.query.get(self.ingredient_id)
            elif self.ingredient_type == "Recipe":
                if user_id:
                    return Recipe.query.filter_by(id=self.ingredient_id, user_id=user_id).first()
                return Recipe.query.get(self.ingredient_id)
        elif self.product_type:
            if self.product_type == "Product":
                if user_id:
                    return Product.query.filter_by(id=self.product_id, user_id=user_id).first()
                return Product.query.get(self.product_id)
            else:
                if user_id:
                    return HomemadeIngredient.query.filter_by(id=self.product_id, user_id=user_id).first()
                return HomemadeIngredient.query.get(self.product_id)
        return None
    
    def get_quantity(self):
        """Get quantity, handling both old and new field names"""
        if self.quantity is not None:
            return self.quantity
        elif self.quantity_ml is not None:
            return self.quantity_ml
        return 0.0

    def calculate_cost(self):
        """Calculate cost based on ingredient type"""
        try:
            ingredient = self.get_product()
            if not ingredient:
                return 0.0
            
            qty = self.get_quantity()
            if qty is None or qty <= 0:
                return 0.0
            
            if isinstance(ingredient, Product):
                if not ingredient.cost_per_unit or ingredient.cost_per_unit == 0:
                    return 0.0
                    
                if ingredient.selling_unit == "ml":
                    return round(ingredient.cost_per_unit * qty, 2)
                elif ingredient.selling_unit == "grams":
                    return round(ingredient.cost_per_unit * qty, 2)
                elif ingredient.selling_unit == "pieces":
                    return round(ingredient.cost_per_unit * qty, 2)
                else:
                    if ingredient.ml_in_bottle and ingredient.ml_in_bottle > 0:
                        return round((ingredient.cost_per_unit / ingredient.ml_in_bottle) * qty, 2)
                    return round(ingredient.cost_per_unit * qty, 2)
            
            elif isinstance(ingredient, HomemadeIngredient):
                cost_per_unit = ingredient.calculate_cost_per_unit()
                return round(cost_per_unit * qty, 2)
            
            elif isinstance(ingredient, Recipe):
                recipe_cost = ingredient.calculate_total_cost()
                return round(recipe_cost * qty, 2)
            
            return 0.0
        except Exception as e:
            # Log error but return 0 to prevent template errors
            import logging
            logging.error(f"Error calculating cost for RecipeIngredient {self.id}: {str(e)}")
            return 0.0
