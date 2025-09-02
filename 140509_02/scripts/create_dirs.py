"""Create necessary directories for the application."""
import os
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories with proper permissions."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Define directories to create
    directories = [
        project_root / "data/uploads",
        project_root / "data/processed",
        project_root / "data/models",
        project_root / "logs",
        project_root / "migrations/versions",
        project_root / "tmp",
    ]
    
    # Create each directory if it doesn't exist
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            # Set permissions (rwxr-xr-x for directories)
            os.chmod(directory, 0o755)
            print(f"Created directory: {directory}")
        except Exception as e:
            print(f"Error creating directory {directory}: {e}", file=sys.stderr)

if __name__ == "__main__":
    create_directories()
