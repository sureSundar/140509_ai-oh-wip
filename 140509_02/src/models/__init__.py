"""Models package for the application."""
from models.base import BaseModel
from models.defect import Defect
from models.feedback import Feedback
from models.model import Model
from models.prediction import Prediction
from models.user import User

# Import all models here so they are registered with SQLAlchemy's metadata
__all__ = ["BaseModel", "User", "Defect", "Prediction", "Feedback", "Model"]
