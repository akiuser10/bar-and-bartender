#!/bin/bash
# Bar & Bartender - Development Server Script
# Activates virtual environment and runs Flask development server
cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
fi

export FLASK_APP=app.py
export FLASK_ENV=development
python -m flask run --host=127.0.0.1 --port=5001
