"""Seed the database with initial data."""
import sys
from pathlib import Path
from typing import List, Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def seed_defects(db):
    """Seed the database with initial defect types."""
    from models.defect import Defect
    
    # Common defect types for manufacturing
    defect_types = [
        {
            "code": "SCRATCH",
            "name": "Surface Scratch",
            "description": "Minor surface scratches on the product",
            "severity": "low",
            "category": "surface"
        },
        {
            "code": "DENT",
            "name": "Dent",
            "description": "Dent or depression on the product surface",
            "severity": "medium",
            "category": "structural"
        },
        {
            "code": "CRACK",
            "name": "Crack",
            "description": "Hairline or visible crack on the product",
            "severity": "high",
            "category": "structural"
        },
        {
            "code": "DISCOLOR",
            "name": "Discoloration",
            "description": "Inconsistent or incorrect color",
            "severity": "medium",
            "category": "color"
        },
        {
            "code": "MISALIGN",
            "name": "Misalignment",
            "description": "Parts are not properly aligned",
            "severity": "high",
            "category": "assembly"
        },
        {
            "code": "MISSING",
            "name": "Missing Part",
            "description": "Component is missing from the assembly",
            "severity": "critical",
            "category": "assembly"
        },
        {
            "code": "DIM_OFF",
            "name": "Dimensional Inaccuracy",
            "description": "Part dimensions are outside tolerance",
            "severity": "high",
            "category": "dimensional"
        },
        {
            "code": "BURRS",
            "name": "Burrs",
            "description": "Rough edges or excess material",
            "severity": "low",
            "category": "surface"
        },
        {
            "code": "WELD_DEFECT",
            "name": "Weld Defect",
            "description": "Issues with welding such as porosity or undercut",
            "severity": "high",
            "category": "welding"
        },
        {
            "code": "PAINT_DEFECT",
            "name": "Paint Defect",
            "description": "Issues with paint application (runs, sags, orange peel)",
            "severity": "medium",
            "category": "finish"
        }
    ]
    
    # Add defects if they don't exist
    for defect_data in defect_types:
        defect = db.query(Defect).filter(Defect.code == defect_data["code"]).first()
        if not defect:
            defect = Defect(**defect_data)
            db.add(defect)
    
    db.commit()
    print(f"Seeded {len(defect_types)} defect types")

def seed_admin_user(db):
    """Seed the database with an admin user."""
    from models.user import User
    from config.settings import settings
    
    # Check if admin user already exists
    admin = db.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
    
    if not admin and settings.FIRST_SUPERUSER and settings.FIRST_SUPERUSER_PASSWORD:
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
    elif admin:
        print("Admin user already exists")
    else:
        print("Skipping admin user creation - check FIRST_SUPERUSER and FIRST_SUPERUSER_PASSWORD in .env")

def seed_initial_model(db):
    """Seed the database with an initial model entry."""
    from models.model import Model
    
    # Check if initial model exists
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
        print("Created initial model entry")
    else:
        print("Initial model entry already exists")

def seed_database():
    """Seed the database with initial data."""
    from db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        print("Seeding database...")
        seed_defects(db)
        seed_admin_user(db)
        seed_initial_model(db)
        print("Database seeding completed!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
