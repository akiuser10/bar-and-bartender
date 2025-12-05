# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# psycopg[binary] includes all needed libraries, no system packages needed
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway sets PORT env var at runtime)
EXPOSE 5000

# Run the application
# Use PORT env var if set, otherwise default to 5000
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000}
