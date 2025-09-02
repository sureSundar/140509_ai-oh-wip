#!/bin/bash
# RetailAI Build Script

set -e

echo "🚀 Building RetailAI Inventory Optimization System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build the application
print_status "Building Docker image..."
docker build -t retailai-app:latest --target production .

# Initialize real retail data
print_status "Initializing real retail dataset..."
python3 data/real_retail_data.py

# Run tests if pytest is available
if command -v pytest &> /dev/null; then
    print_status "Running tests..."
    pytest --cov=src --cov-report=term-missing
else
    print_warning "pytest not found, skipping tests"
fi

# Build documentation
print_status "Building documentation..."
if [ -d "docs" ]; then
    cd docs
    if command -v mkdocs &> /dev/null; then
        mkdocs build
    else
        print_warning "mkdocs not found, skipping documentation build"
    fi
    cd ..
fi

print_status "✅ Build completed successfully!"
print_status "To start the application, run: ./scripts/deploy.sh"
