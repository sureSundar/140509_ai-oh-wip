"""Defect model for managing different types of defects."""
from typing import List, Optional

from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.base import BaseModel

class Defect(BaseModel):
    """Defect model for managing different types of defects."""
    
    __tablename__ = "defects"
    
    # Defect identification
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Defect classification
    severity = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="Severity level: critical, high, medium, low, cosmetic"
    )
    
    category = Column(
        String(50),
        nullable=False,
        default="other",
        comment="Defect category: surface, structural, color, dimension, etc."
    )
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="defect")
    
    def __repr__(self) -> str:
        return f"<Defect {self.code}: {self.name}>"
    
    @classmethod
    def get_by_code(cls, db, code: str) -> Optional['Defect']:
        """Get defect by code."""
        return db.query(cls).filter(cls.code == code).first()
    
    @classmethod
    def get_active_defects(cls, db, **filters) -> List['Defect']:
        """Get all active defects with optional filtering."""
        query = db.query(cls).filter(cls.is_active == True)
        
        # Apply additional filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
                
        return query.all()
    
    def get_severity_level(self) -> int:
        """Get severity level as an integer for sorting."""
        severity_levels = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "cosmetic": 1
        }
        return severity_levels.get(self.severity.lower(), 0)
