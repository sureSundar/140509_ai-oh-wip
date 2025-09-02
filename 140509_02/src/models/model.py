"""Model for tracking machine learning models."""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, Session

from models.base import BaseModel

class Model(BaseModel):
    """Model for tracking machine learning models."""
    
    __tablename__ = "models"
    
    # Model identification
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    # Model configuration
    framework = Column(String(50), nullable=False, comment="e.g., tensorflow, pytorch, onnx")
    architecture = Column(String(100), nullable=True, comment="e.g., resnet50, efficientnet-b0")
    input_shape = Column(String(100), nullable=True, comment="e.g., (224, 224, 3)")
    
    # Model files
    path = Column(String(500), nullable=True, comment="Path to the model file")
    config_path = Column(String(500), nullable=True, comment="Path to the model config file")
    label_map_path = Column(String(500), nullable=True, comment="Path to the label map file")
    
    # Performance metrics
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    
    # Training information
    dataset_version = Column(String(100), nullable=True)
    training_metrics = Column(JSON, nullable=True, comment="Additional training metrics")
    
    # Status
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    is_production = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="model")
    
    def __repr__(self) -> str:
        return f"<Model {self.name} v{self.version}>"
    
    @classmethod
    def get_active_model(cls, db: Session) -> Optional['Model']:
        """Get the currently active model."""
        return db.query(cls).filter(cls.is_active == True).first()
    
    @classmethod
    def get_production_model(cls, db: Session) -> Optional['Model']:
        """Get the production model."""
        return db.query(cls).filter(cls.is_production == True).first()
    
    @classmethod
    def get_latest_version(cls, db: Session, name: str) -> Optional['Model']:
        """Get the latest version of a model by name."""
        return (
            db.query(cls)
            .filter(cls.name == name)
            .order_by(cls.version.desc())
            .first()
        )
    
    def activate(self, db: Session) -> None:
        """Activate this model and deactivate others."""
        # Deactivate all other models
        db.query(Model).update({Model.is_active: False})
        
        # Activate this model
        self.is_active = True
        db.add(self)
        db.commit()
    
    def set_as_production(self, db: Session) -> None:
        """Set this model as production and unset others."""
        # Unset other production models
        db.query(Model).update({Model.is_production: False})
        
        # Set this model as production
        self.is_production = True
        db.add(self)
        db.commit()
    
    def update_metrics(
        self,
        db: Session,
        accuracy: Optional[float] = None,
        precision: Optional[float] = None,
        recall: Optional[float] = None,
        f1_score: Optional[float] = None,
        **kwargs
    ) -> None:
        """Update model metrics."""
        if accuracy is not None:
            self.accuracy = accuracy
        if precision is not None:
            self.precision = precision
        if recall is not None:
            self.recall = recall
        if f1_score is not None:
            self.f1_score = f1_score
        
        # Update any additional metrics
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        db.add(self)
        db.commit()
        db.refresh(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary with additional computed fields."""
        result = super().to_dict()
        
        # Add human-readable timestamps
        result["created_at"] = self.created_at.isoformat() if self.created_at else None
        result["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        
        return result
