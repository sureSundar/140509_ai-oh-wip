"""Base model for all database models."""
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session

from db.session import Base

@as_declarative()
class BaseModel(Base):
    """Base model with common fields and methods."""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @declared_attr
    def __tablename__(cls) -> str:
        ""
        Generate table name from class name.
        Converts CamelCase to snake_case.
        """
        return ''.join(['_' + i.lower() if i.isupper() else i for i in cls.__name__]).lstrip('_')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def save(self, db: Session) -> None:
        """Save the model to the database."""
        db.add(self)
        db.commit()
        db.refresh(self)
    
    def delete(self, db: Session) -> None:
        """Delete the model from the database."""
        db.delete(self)
        db.commit()
    
    @classmethod
    def get_by_id(cls, db: Session, id: int) -> Optional['BaseModel']:
        """Get a model by its ID."""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_all(
        cls, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> list['BaseModel']:
        """Get all models with optional filtering and pagination."""
        query = db.query(cls)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        return query.offset(skip).limit(limit).all()
