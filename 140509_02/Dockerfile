# Multi-stage Docker build for RetailAI Inventory Optimization
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development
ENV FLASK_ENV=development
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.api.inventory_api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
ENV FLASK_ENV=production

# Create non-root user
RUN groupadd -r retailai && useradd -r -g retailai retailai

# Copy application code
COPY --chown=retailai:retailai . .

# Initialize database and real retail data
RUN python data/real_retail_data.py

# Set proper permissions
RUN chown -R retailai:retailai /app
USER retailai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/inventory || exit 1

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.api.inventory_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
