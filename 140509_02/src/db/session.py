"""Database session management."""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URI,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_MAX,
    max_overflow=settings.DATABASE_POOL_MAX * 2,
    pool_recycle=3600,
    echo=settings.DATABASE_ECHO,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models to ensure they are registered with SQLAlchemy
from models.base import Base  # noqa: E402


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
