"""Prediction model for tracking defect predictions."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship, Session

from models.base import BaseModel

class Prediction(BaseModel):
    """Prediction model for tracking defect predictions."""
    
    __tablename__ = "predictions"
    
    # Prediction metadata
    image_path = Column(String(500), nullable=False, comment="Path to the original image")
    processed_image_path = Column(String(500), nullable=True, comment="Path to the processed/annotated image")
    model_version = Column(String(100), nullable=False, comment="Model version used for prediction")
    
    # Prediction results
    confidence = Column(Float, nullable=True, comment="Confidence score of the prediction")
    predicted_class = Column(String(100), nullable=True, comment="Predicted class")
    predicted_confidence = Column(Float, nullable=True, comment="Confidence score of the predicted class")
    all_predictions = Column(JSON, nullable=True, comment="All class predictions with confidence scores")
    
    # Bounding box information (if object detection)
    bbox = Column(JSON, nullable=True, comment="Bounding box coordinates [x1, y1, x2, y2]")
    
    # User feedback
    is_correct = Column(Boolean, nullable=True, comment="Whether the prediction was correct (user feedback)")
    feedback_comment = Column(Text, nullable=True, comment="User feedback comment")
    
    # Status
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        comment="Status: pending, processing, completed, failed"
    )
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="predictions")
    
    defect_id = Column(Integer, ForeignKey("defects.id"), nullable=True)
    defect = relationship("Defect", back_populates="predictions")
    
    feedback = relationship("Feedback", back_populates="prediction", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Prediction {self.id}: {self.predicted_class} ({self.confidence:.2f})>"
    
    @classmethod
    def create(
        cls,
        db: Session,
        image_path: str,
        model_version: str,
        user_id: int,
        **kwargs
    ) -> 'Prediction':
        """Create a new prediction record."""
        prediction = cls(
            image_path=image_path,
            model_version=model_version,
            user_id=user_id,
            **kwargs
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction
    
    def update_prediction(
        self,
        db: Session,
        predicted_class: str,
        confidence: float,
        all_predictions: Dict[str, float],
        **kwargs
    ) -> None:
        """Update prediction results."""
        self.predicted_class = predicted_class
        self.predicted_confidence = confidence
        self.all_predictions = all_predictions
        self.status = "completed"
        
        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        db.add(self)
        db.commit()
        db.refresh(self)
    
    def add_feedback(
        self,
        db: Session,
        is_correct: bool,
        defect_id: Optional[int] = None,
        comment: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> 'Feedback':
        """Add feedback to the prediction."""
        from models.feedback import Feedback
        
        feedback = Feedback(
            prediction_id=self.id,
            is_correct=is_correct,
            defect_id=defect_id,
            comment=comment,
            user_id=user_id or self.user_id
        )
        
        db.add(feedback)
        
        # Update prediction with feedback
        self.is_correct = is_correct
        if defect_id:
            self.defect_id = defect_id
        
        db.add(self)
        db.commit()
        db.refresh(feedback)
        
        return feedback
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction to dictionary with additional computed fields."""
        result = super().to_dict()
        
        # Add human-readable timestamps
        result["created_at"] = self.created_at.isoformat() if self.created_at else None
        result["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        
        # Add user and defect information
        if self.user:
            result["user"] = {"id": self.user.id, "username": self.user.username}
        
        if self.defect:
            result["defect"] = {"id": self.defect.id, "name": self.defect.name, "code": self.defect.code}
        
        return result
