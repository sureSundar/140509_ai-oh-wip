"""Feedback model for user feedback on predictions."""
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import relationship

from models.base import BaseModel

class Feedback(BaseModel):
    """Feedback model for user feedback on predictions."""
    
    __tablename__ = "feedback"
    
    # Feedback content
    is_correct = Column(Boolean, nullable=False, comment="Whether the prediction was correct")
    comment = Column(Text, nullable=True, comment="User comment")
    
    # Relationships
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False, unique=True)
    prediction = relationship("Prediction", back_populates="feedback")
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="feedback")
    
    defect_id = Column(Integer, ForeignKey("defects.id"), nullable=True)
    defect = relationship("Defect")
    
    def __repr__(self) -> str:
        return f"<Feedback {self.id} for Prediction {self.prediction_id}>"
    
    @classmethod
    def create(
        cls,
        db,
        prediction_id: int,
        user_id: int,
        is_correct: bool,
        defect_id: Optional[int] = None,
        comment: Optional[str] = None
    ) -> 'Feedback':
        """Create a new feedback record."""
        feedback = cls(
            prediction_id=prediction_id,
            user_id=user_id,
            is_correct=is_correct,
            defect_id=defect_id,
            comment=comment
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
    
    def to_dict(self) -> dict:
        """Convert feedback to dictionary with additional computed fields."""
        result = super().to_dict()
        
        # Add related objects
        if self.user:
            result["user"] = {"id": self.user.id, "username": self.user.username}
            
        if self.defect:
            result["defect"] = {"id": self.defect.id, "name": self.defect.name, "code": self.defect.code}
            
        if self.prediction:
            result["prediction"] = {"id": self.prediction.id, "predicted_class": self.prediction.predicted_class}
        
        return result
