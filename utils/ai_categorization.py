"""
AI-powered product categorization utility
Uses AI to automatically identify category and sub-category from product descriptions
"""
import os
import json
from flask import current_app

# Try to import requests, but don't fail if it's not installed
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# List of valid categories
VALID_CATEGORIES = ['Beverage', 'Food']

# List of valid sub-categories
VALID_SUB_CATEGORIES = [
    'Alcohol', 'Vodka', 'Gin', 'Rum', 'American Whiskey', 'Scotch Whisky', 
    'Single Malt', 'Rye Whiskey', 'Irish Whiskey', 'Japanese Whiskey', 
    'Amaro / Vermouth', 'Brandy', 'Cognac', 'Red Wine', 'White Wine', 
    'Rose Wine', 'Sparkling Wine', 'Generic Liqueur', 'Branded Liqueur', 
    'Tequila', 'Non Alcohol', 'Non-Alcohol', 'Non-Alcoholic Spirit', 
    'Non Alcoholic Beer', 'Non-Alcoholic Wine', 'Water', 'Soft Drink', 
    'Tea', 'Coffee', 'Fruits', 'Fresh Berries', 'Frozen Berries', 
    'Vegetables', 'Herbs', 'Spice', 'Edible Flowers', 'Dairy', 
    'Plant Based Milk', 'Syrups & Purees', 'Syrup', 'Puree', 
    'Frozen Puree', 'Juice', 'Packet Juice', 'Other'
]


def categorize_product_ai(description, supplier=None):
    """
    Use AI to categorize a product based on its description.
    
    Args:
        description: Product description/name
        supplier: Optional supplier name for context
    
    Returns:
        tuple: (category, sub_category) or (None, None) if categorization fails
    """
    # Check if requests library is available
    if not REQUESTS_AVAILABLE:
        try:
            current_app.logger.warning('requests library not available, skipping AI categorization')
        except:
            pass  # If current_app is not available, just skip
        return None, None
    
    # Check if AI API is configured
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        try:
            current_app.logger.debug('OpenAI API key not configured, skipping AI categorization')
        except:
            pass  # If current_app is not available, just skip
        return None, None
    
    try:
        # Prepare the prompt
        prompt = f"""Analyze this product and determine its category and sub-category for a bar/restaurant inventory system.

Product Description: {description}
{f'Supplier: {supplier}' if supplier and supplier != 'N/A' else ''}

Categories available: {', '.join(VALID_CATEGORIES)}
Sub-categories available: {', '.join(VALID_SUB_CATEGORIES)}

Based on the product description, identify:
1. The most appropriate category (must be one of: {', '.join(VALID_CATEGORIES)})
2. The most specific sub-category from the list above

Respond ONLY with a JSON object in this exact format:
{{"category": "Beverage or Food", "sub_category": "exact match from the list"}}

If you cannot determine with confidence, use "Other" for sub-category.
Do not include any explanation, only the JSON object."""

        # Call OpenAI API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant that categorizes products for bar and restaurant inventory management. Always respond with valid JSON only.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 150
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Parse JSON response
            # Sometimes the response might have markdown code blocks
            if content.startswith('```'):
                # Extract JSON from code block
                lines = content.split('\n')
                json_start = False
                json_lines = []
                for line in lines:
                    if line.strip().startswith('{'):
                        json_start = True
                    if json_start:
                        json_lines.append(line)
                    if json_start and line.strip().endswith('}'):
                        break
                content = '\n'.join(json_lines)
            
            # Remove markdown code block markers if present
            content = content.replace('```json', '').replace('```', '').strip()
            
            categorization = json.loads(content)
            
            category = categorization.get('category', '').strip()
            sub_category = categorization.get('sub_category', '').strip()
            
            # Validate category
            if category not in VALID_CATEGORIES:
                current_app.logger.warning(f'AI returned invalid category: {category}, defaulting to Beverage')
                category = 'Beverage'
            
            # Validate sub_category
            if sub_category not in VALID_SUB_CATEGORIES:
                current_app.logger.warning(f'AI returned invalid sub_category: {sub_category}, defaulting to Other')
                sub_category = 'Other'
            
            return category, sub_category
        else:
            current_app.logger.warning(f'OpenAI API error: {response.status_code} - {response.text}')
            return None, None
            
    except json.JSONDecodeError as e:
        current_app.logger.warning(f'Failed to parse AI response as JSON: {str(e)}')
        return None, None
    except requests.exceptions.Timeout:
        current_app.logger.warning('OpenAI API request timed out')
        return None, None
    except requests.exceptions.RequestException as e:
        current_app.logger.warning(f'OpenAI API request failed: {str(e)}')
        return None, None
    except Exception as e:
        current_app.logger.warning(f'AI categorization error: {str(e)}')
        return None, None


def should_use_ai_categorization(category, sub_category):
    """
    Determine if AI categorization should be used for this product.
    
    Args:
        category: Current category value
        sub_category: Current sub_category value
    
    Returns:
        bool: True if AI should be used (category is missing/Other or sub_category is missing/Other)
    """
    # Use AI if category is missing, empty, or "Other"
    category_needs_ai = not category or category.strip() == '' or category.strip() == 'Other'
    
    # Use AI if sub_category is missing, empty, or "Other"
    sub_category_needs_ai = not sub_category or sub_category.strip() == '' or sub_category.strip() == 'Other'
    
    return category_needs_ai or sub_category_needs_ai
