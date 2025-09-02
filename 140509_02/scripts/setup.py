"""Database setup and migration script."""
import os
import sys
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_database() -> None:
    """Create the database if it doesn't exist."""
    from sqlalchemy_utils import database_exists, create_database
    from db.session import engine
    from config import settings
    
    if not database_exists(engine.url):
        print(f"Creating database: {settings.DATABASE_URI}")
        create_database(engine.url)
        print("Database created successfully!")
    else:
        print(f"Database already exists at {settings.DATABASE_URI}")

def run_migrations() -> None:
    """Run database migrations."""
    from alembic.config import Config
    from alembic import command
    from config import settings
    
    # Set the database URL for Alembic
    os.environ["DATABASE_URL"] = settings.DATABASE_URI
    
    # Path to the alembic.ini file
    alembic_cfg = Config("alembic.ini")
    
    print("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    print("Migrations completed successfully!")

def seed_database() -> None:
    """Seed the database with initial data."""
    from db.session import SessionLocal
    from models.user import User
    from models.defect import Defect
    from models.model import Model
    from config import settings
    
    db = SessionLocal()
    
    try:
        print("Seeding database...")
        
        # Create admin user if it doesn't exist
        admin = db.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
        if not admin:
            admin = User(
                username=settings.FIRST_SUPERUSER,
                email=settings.FIRST_SUPERUSER_EMAIL,
                full_name="Admin User",
                is_superuser=True,
                is_operator=True,
                is_active=True
            )
            admin.set_password(settings.FIRST_SUPERUSER_PASSWORD)
            db.add(admin)
            db.commit()
            print("Created admin user")
        
        # Seed defect types
        defect_types = [
            {"code": "SCRATCH", "name": "Surface Scratch", "severity": "low", "category": "surface"},
            {"code": "DENT", "name": "Dent", "severity": "medium", "category": "structural"},
            {"code": "CRACK", "name": "Crack", "severity": "high", "category": "structural"},
            {"code": "DISCOLOR", "name": "Discoloration", "severity": "medium", "category": "color"},
            {"code": "MISALIGN", "name": "Misalignment", "severity": "high", "category": "assembly"},
            {"code": "MISSING", "name": "Missing Part", "severity": "critical", "category": "assembly"},
            {"code": "DIM_OFF", "name": "Dimensional Inaccuracy", "severity": "high", "category": "dimensional"},
            {"code": "BURRS", "name": "Burrs", "severity": "low", "category": "surface"},
            {"code": "WELD_DEFECT", "name": "Weld Defect", "severity": "high", "category": "welding"},
            {"code": "PAINT_DEFECT", "name": "Paint Defect", "severity": "medium", "category": "finish"}
        ]
        
        for defect_data in defect_types:
            defect = db.query(Defect).filter(Defect.code == defect_data["code"]).first()
            if not defect:
                defect = Defect(**defect_data)
                db.add(defect)
        
        # Create initial model entry
        model = db.query(Model).filter(Model.name == "initial_model").first()
        if not model:
            model = Model(
                name="initial_model",
                version="1.0.0",
                description="Initial model for defect detection",
                framework="tensorflow",
                architecture="efficientnet_b0",
                input_shape="(224, 224, 3)",
                is_active=True,
                is_production=True
            )
            db.add(model)
        
        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

def main() -> None:
    """Run database setup steps."""
    try:
        create_database()
        run_migrations()
        seed_database()
        print("Database setup completed successfully!")
    except Exception as e:
        print(f"Error during database setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
