FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies  
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import psycopg2; conn = psycopg2.connect('postgresql://retailai:retailai123@postgres:5432/retailai'); conn.close()" || exit 1

# Run the application
CMD ["python", "alert_system.py"]