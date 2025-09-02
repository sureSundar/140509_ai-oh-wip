"""Run database migrations."""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_migrations():
    """Run database migrations using Alembic."""
    from alembic.config import Config
    from alembic import command
    from config.settings import settings
    
    # Set the database URL for Alembic
    os.environ["DATABASE_URL"] = settings.DATABASE_URI
    
    # Get the directory of this script
    script_dir = Path(__file__).parent
    
    # Path to the alembic.ini file
    alembic_cfg = Config(script_dir.parent / "alembic.ini")
    
    print("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    print("Migrations completed successfully!")

if __name__ == "__main__":
    run_migrations()
