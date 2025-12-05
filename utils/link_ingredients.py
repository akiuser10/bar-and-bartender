"""
Utility script to link secondary ingredients to products/ingredients
This can be used to manually link ingredients to existing secondary ingredients
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from models import HomemadeIngredient, HomemadeIngredientItem, Product
from app import create_app

def link_ingredient_to_secondary(secondary_id, product_id, quantity, unit='ml'):
    """
    Link a product/ingredient to a secondary ingredient
    
    Args:
        secondary_id: ID of the secondary ingredient (HomemadeIngredient)
        product_id: ID of the product/ingredient to link
        quantity: Quantity of the ingredient
        unit: Unit of measurement (default: 'ml')
    
    Returns:
        True if successful, False otherwise
    """
    try:
        secondary = HomemadeIngredient.query.get(secondary_id)
        if not secondary:
            print(f"Secondary ingredient with ID {secondary_id} not found")
            return False
        
        product = Product.query.get(product_id)
        if not product:
            print(f"Product with ID {product_id} not found")
            return False
        
        # Check if link already exists
        existing = HomemadeIngredientItem.query.filter_by(
            homemade_id=secondary_id,
            product_id=product_id
        ).first()
        
        if existing:
            # Update existing
            existing.quantity = quantity
            existing.unit = unit
            existing.quantity_ml = quantity
            print(f"Updated existing link: {secondary.name} -> {product.description} ({quantity} {unit})")
        else:
            # Create new link
            item = HomemadeIngredientItem(
                homemade_id=secondary_id,
                product_id=product_id,
                quantity=quantity,
                unit=unit,
                quantity_ml=quantity
            )
            db.session.add(item)
            print(f"Created new link: {secondary.name} -> {product.description} ({quantity} {unit})")
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error linking ingredient: {str(e)}")
        return False


def list_secondary_ingredients():
    """List all secondary ingredients with their current ingredient counts"""
    secondaries = HomemadeIngredient.query.all()
    print("\n=== Secondary Ingredients ===")
    for sec in secondaries:
        ingredient_count = HomemadeIngredientItem.query.filter_by(homemade_id=sec.id).count()
        print(f"ID: {sec.id} | Name: {sec.name} | Ingredients: {ingredient_count}")
    print()


def list_products(search_term=None):
    """List all products, optionally filtered by search term"""
    query = Product.query
    if search_term:
        query = query.filter(Product.description.contains(search_term))
    products = query.order_by(Product.description).limit(50).all()
    
    print(f"\n=== Products (showing up to 50) ===")
    for prod in products:
        cost = prod.cost_per_unit or 0
        print(f"ID: {prod.id} | {prod.description} | Cost: {cost} AED/{prod.selling_unit or 'unit'}")
    print()


def show_secondary_ingredient_details(secondary_id):
    """Show details of a secondary ingredient including its linked ingredients"""
    secondary = HomemadeIngredient.query.get(secondary_id)
    if not secondary:
        print(f"Secondary ingredient with ID {secondary_id} not found")
        return
    
    print(f"\n=== {secondary.name} (ID: {secondary.id}) ===")
    print(f"Total Volume: {secondary.total_volume_ml} {secondary.unit}")
    print(f"Method: {secondary.method or 'N/A'}")
    
    items = HomemadeIngredientItem.query.filter_by(homemade_id=secondary_id).all()
    if items:
        print(f"\nLinked Ingredients ({len(items)}):")
        total_cost = 0
        for item in items:
            if item.product:
                cost = item.calculate_cost()
                total_cost += cost
                print(f"  - {item.product.description}: {item.quantity} {item.unit} (Cost: {cost} AED)")
        print(f"\nTotal Cost: {total_cost} AED")
        print(f"Cost per Unit: {secondary.calculate_cost_per_unit()} AED/{secondary.unit}")
    else:
        print("\nNo ingredients linked yet")
    print()


def interactive_link():
    """Interactive function to link ingredients to secondary ingredients"""
    app = create_app()
    with app.app_context():
        while True:
            print("\n=== Link Ingredients to Secondary Ingredient ===")
            print("1. List secondary ingredients")
            print("2. List products")
            print("3. Show secondary ingredient details")
            print("4. Link ingredient to secondary ingredient")
            print("5. Exit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                list_secondary_ingredients()
            elif choice == '2':
                search = input("Search term (or press Enter for all): ").strip() or None
                list_products(search)
            elif choice == '3':
                sec_id = input("Enter secondary ingredient ID: ").strip()
                try:
                    show_secondary_ingredient_details(int(sec_id))
                except ValueError:
                    print("Invalid ID")
            elif choice == '4':
                try:
                    sec_id = int(input("Enter secondary ingredient ID: ").strip())
                    prod_id = int(input("Enter product ID: ").strip())
                    quantity = float(input("Enter quantity: ").strip())
                    unit = input("Enter unit (default: ml): ").strip() or 'ml'
                    
                    if link_ingredient_to_secondary(sec_id, prod_id, quantity, unit):
                        print("✓ Successfully linked!")
                    else:
                        print("✗ Failed to link")
                except ValueError:
                    print("Invalid input")
            elif choice == '5':
                break
            else:
                print("Invalid choice")


if __name__ == '__main__':
    # Example usage:
    # python -m utils.link_ingredients
    
    app = create_app()
    with app.app_context():
        print("Secondary Ingredient Linker Utility")
        print("=" * 50)
        interactive_link()

