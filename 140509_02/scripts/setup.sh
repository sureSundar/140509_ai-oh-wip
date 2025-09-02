#!/bin/bash
# RetailAI One-Click Setup Script

set -e

echo "🎯 RetailAI Inventory Optimization - One-Click Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[SETUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check system requirements
print_header "Checking system requirements..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi
print_status "✅ Python 3 found"

# Check pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed."
    exit 1
fi
print_status "✅ pip3 found"

# Check Docker (optional)
if command -v docker &> /dev/null; then
    print_status "✅ Docker found"
    DOCKER_AVAILABLE=true
else
    print_warning "Docker not found - containerized deployment will not be available"
    DOCKER_AVAILABLE=false
fi

# Create virtual environment
print_header "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Created virtual environment"
fi

# Activate virtual environment
source venv/bin/activate
print_status "Activated virtual environment"

# Install Python dependencies
print_header "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "✅ Dependencies installed"

# Create necessary directories
print_header "Creating project structure..."
mkdir -p data logs backups
mkdir -p data/models data/processed data/raw
print_status "✅ Directory structure created"

# Initialize real retail dataset
print_header "Initializing real retail dataset..."
python3 data/real_retail_data.py
print_status "✅ Real retail dataset initialized"

# Set up environment variables
print_header "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_status "Created .env file from template"
    print_warning "Please update .env file with your specific configuration"
fi

# Make scripts executable
chmod +x scripts/*.sh
print_status "✅ Made scripts executable"

# Setup complete
print_header "🎉 Setup completed successfully!"
echo ""
echo "Quick Start Options:"
echo ""
echo "1. 🐍 Python Development Mode:"
echo "   source venv/bin/activate"
echo "   python3 src/api/inventory_api.py"
echo "   # Then open UNIFIED_EXECUTIVE_DEMO.html in browser"
echo ""

if [ "$DOCKER_AVAILABLE" = true ]; then
echo "2. 🐳 Docker Mode (Recommended):"
echo "   ./scripts/build.sh"
echo "   ./scripts/deploy.sh local"
echo "   # Access at http://localhost:3000"
echo ""
fi

echo "3. 📊 Demo Only:"
echo "   python3 -m http.server 3000"
echo "   # Open http://localhost:3000/UNIFIED_EXECUTIVE_DEMO.html"
echo ""
echo "Documentation:"
echo "  - README.md - Project overview"
echo "  - CHANGE_REQUESTS.md - All implemented enhancements"
echo "  - docs/ - Detailed technical documentation"
echo ""
echo "Need help? Check the troubleshooting section in README.md"
