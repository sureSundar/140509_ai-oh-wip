#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Manufacturing Quality Control AI Setup ===${NC}\n"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 is required but not installed. Please install Python 3.8+ and try again.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
if [[ "$PYTHON_VERSION" < "3.8" ]]; then
    echo -e "${YELLOW}Python 3.8 or higher is required. Found Python ${PYTHON_VERSION}.${NC}"
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "\n${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "\n${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "\n${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Install in development mode
echo -e "\n${GREEN}Installing in development mode...${NC}"
pip install -e .

# Generate .env file if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo -e "\n${GREEN}Generating .env file...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update the .env file with your configuration.${NC}"
else
    echo -e "\n${YELLOW}.env file already exists.${NC}"
fi

# Create necessary directories
echo -e "\n${GREEN}Creating necessary directories...${NC}"
python scripts/create_dirs.py

# Set up pre-commit hooks
echo -e "\n${GREEN}Setting up pre-commit hooks...${NC}"
pip install pre-commit
pre-commit install

# Set up database
echo -e "\n${GREEN}Setting up database...${NC}"
python scripts/setup.py

echo -e "\n${GREEN}=== Setup completed successfully! ===${NC}"
echo -e "\nTo activate the virtual environment, run:"
echo -e "  source venv/bin/activate"
echo -e "\nTo start the development server, run:"
echo -e "  uvicorn src.api.main:app --reload"
echo -e "\nThen open http://localhost:8000 in your browser"

# Make setup script executable
chmod +x setup.sh
