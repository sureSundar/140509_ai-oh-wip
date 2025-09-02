"""Initialize the project by setting up the environment and database."""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command: str, cwd: str = None) -> bool:
    """Run a shell command and return True if successful."""
    try:
        print(f"Running: {command}")
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}", file=sys.stderr)
        return False

def setup_virtual_environment() -> bool:
    """Set up Python virtual environment."""
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print("Creating virtual environment...")
        if not run_command("python -m venv venv"):
            return False
    else:
        print("Virtual environment already exists.")
    return True

def install_dependencies() -> bool:
    """Install Python dependencies."""
    # Activate virtual environment
    activate_script = "venv/bin/activate"
    if not os.path.exists(activate_script):
        print("Error: Virtual environment not found.")
        return False
    
    # Upgrade pip
    if not run_command("./venv/bin/pip install --upgrade pip"):
        return False
    
    # Install requirements
    if not run_command("./venv/bin/pip install -r requirements.txt"):
        return False
    
    # Install in development mode
    if not run_command("./venv/bin/pip install -e ."):
        return False
    
    return True

def setup_pre_commit() -> bool:
    """Set up pre-commit hooks."""
    if not run_command("./venv/bin/pre-commit install"):
        return False
    return True

def setup_database() -> bool:
    """Set up the database."""
    # Run the database setup script
    if not run_command("./venv/bin/python scripts/setup.py"):
        return False
    return True

def main():
    """Main function to set up the project."""
    print("=== Setting up Manufacturing Quality Control AI Project ===\n")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Generate .env file if it doesn't exist
    if not Path(".env").exists() and Path(".env.example").exists():
        print("Generating .env file...")
        if not run_command("cp .env.example .env"):
            print("Please create a .env file manually from .env.example")
    
    # Set up virtual environment
    if not setup_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    print("\n=== Installing Dependencies ===")
    if not install_dependencies():
        sys.exit(1)
    
    # Set up pre-commit hooks
    print("\n=== Setting up pre-commit hooks ===")
    if not setup_pre_commit():
        print("Warning: Failed to set up pre-commit hooks")
    
    # Create necessary directories
    print("\n=== Creating necessary directories ===")
    if not run_command("./venv/bin/python scripts/create_dirs.py"):
        sys.exit(1)
    
    # Set up database
    print("\n=== Setting up database ===")
    if not setup_database():
        print("Error: Failed to set up database")
        sys.exit(1)
    
    print("\n=== Setup completed successfully! ===")
    print("\nTo activate the virtual environment, run:")
    print("  source venv/bin/activate")
    print("\nTo start the development server, run:")
    print("  uvicorn src.api.main:app --reload")
    print("\nThen open http://localhost:8000 in your browser")

if __name__ == "__main__":
    main()
