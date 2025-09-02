"""User model for authentication and authorization."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from models.base import BaseModel

class User(BaseModel):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # User authentication information
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # User information
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    is_operator = Column(Boolean(), default=False)
    
    # Timestamps
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.username}>"
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.is_active
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.is_superuser
    
    @classmethod
    def get_by_username(cls, db, username: str) -> Optional['User']:
        """Get user by username."""
        return db.query(cls).filter(cls.username == username).first()
    
    @classmethod
    def get_by_email(cls, db, email: str) -> Optional['User']:
        """Get user by email."""
        return db.query(cls).filter(cls.email == email).first()
    
    def update_last_login(self, db) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        db.add(self)
        db.commit()
    
    def set_password(self, password: str) -> None:
        """Set hashed password."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.hashed_password)
