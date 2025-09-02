#!/bin/bash

# Exit on error
set -e

# Set Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
else
    echo "Warning: .env file not found. Using default settings."
fi

# Create database if it doesn't exist
python -c "from sqlalchemy_utils import database_exists, create_database; from config.settings import settings; \
    if not database_exists(settings.DATABASE_URI): \
        print(f'Creating database: {settings.DATABASE_URI}'); \
        create_database(settings.DATABASE_URI)"

# Run migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Seed initial data
echo "Seeding database..."
python scripts/seed_db.py

echo "Database setup completed successfully!"
