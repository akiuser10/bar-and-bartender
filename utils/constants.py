"""
Application constants
"""
CATEGORY_CONFIG = {
    'cocktails': {
        'display': 'Cocktails',
        'db_labels': ['Cocktails', 'Classic'],
        'template': 'recipes/recipes_classic.html',
        'add_label': 'Cocktail'
    },
    'mocktails': {
        'display': 'Mocktails',
        'db_labels': ['Mocktails', 'Signature'],
        'template': 'recipes/recipes_mocktail.html',
        'add_label': 'Mocktail'
    },
    'beverages': {
        'display': 'Beverages',
        'db_labels': ['Beverages', 'Beverage'],
        'template': 'recipes/recipes_beverages.html',
        'add_label': 'Beverage'
    },
    'food': {
        'display': 'Food',
        'db_labels': ['Food'],
        'template': 'recipes/add_recipe.html',
        'add_label': 'Food'
    }
}

CATEGORY_ALIASES = {
    'cocktails': 'cocktails',
    'classic': 'cocktails',
    'mocktails': 'mocktails',
    'signature': 'mocktails',
    'beverages': 'beverages',
    'beverage': 'beverages',
    'food': 'food'
}

TYPE_TO_CATEGORY = {
    'cocktails': 'cocktails',
    'classic': 'cocktails',
    'mocktails': 'mocktails',
    'signature': 'mocktails',
    'beverages': 'beverages',
    'beverage': 'beverages',
    'food': 'food',
    '': 'cocktails'  # Default empty type to Cocktails
}


def resolve_recipe_category(category: str):
    key = (category or '').lower()
    canonical = CATEGORY_ALIASES.get(key)
    if not canonical:
        return None, None
    return canonical, CATEGORY_CONFIG[canonical]


def category_context_from_type(recipe_type: str):
    key = (recipe_type or '').lower().strip()
    canonical = TYPE_TO_CATEGORY.get(key)
    if not canonical:
        # Default to cocktails if type doesn't match
        canonical = 'cocktails'
    info = CATEGORY_CONFIG[canonical]
    return canonical, info['display']

