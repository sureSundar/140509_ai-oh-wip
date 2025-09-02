"""Initialize the database and create tables."""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def init_db():
    """Initialize the database by creating all tables."""
    from db.session import engine, Base
    from sqlalchemy_utils import database_exists, create_database
    
    # Create database if it doesn't exist
    if not database_exists(engine.url):
        print(f"Creating database: {engine.url}")
        create_database(engine.url)
    
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
