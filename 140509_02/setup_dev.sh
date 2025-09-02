#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up development environment...${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Install development dependencies
echo -e "${GREEN}Installing development dependencies...${NC}"
pip install -e .

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${GREEN}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update the .env file with your configuration.${NC}"
else
    echo -e "${YELLOW}.env file already exists.${NC}"
fi

# Create necessary directories
echo -e "${GREEN}Creating necessary directories...${NC}"
mkdir -p data/uploads data/processed data/models logs

# Set execute permissions on scripts
chmod +x scripts/*.py

# Install pre-commit hooks
echo -e "${GREEN}Setting up pre-commit hooks...${NC}"
pip install pre-commit
pre-commit install

echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${YELLOW}To activate the virtual environment, run: source venv/bin/activate${NC}"
echo -e "${YELLOW}To set up the database, run: python scripts/setup.py${NC}"
