"""Application configuration settings."""
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseSettings, Field, PostgresDsn, validator, HttpUrl


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "Manufacturing AI Vision"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    API_V1_STR: str = "/api/v1"

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_RELOAD: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_MIN: int = Field(1, env="DATABASE_POOL_MIN")
    DATABASE_POOL_MAX: int = Field(10, env="DATABASE_POOL_MAX")
    DATABASE_ECHO: bool = Field(False, env="DATABASE_ECHO")
    
    # First superuser
    FIRST_SUPERUSER: str = Field(..., env="FIRST_SUPERUSER")
    FIRST_SUPERUSER_EMAIL: str = Field(..., env="FIRST_SUPERUSER_EMAIL")
    FIRST_SUPERUSER_PASSWORD: str = Field(..., env="FIRST_SUPERUSER_PASSWORD")
    
    @property
    def DATABASE_URI(self) -> str:
        """Get database URI."""
        return self.DATABASE_URL

    # Model
    MODEL_PATH: str = Field("./data/models/best_model.pt", env="MODEL_PATH")
    CONFIDENCE_THRESHOLD: float = Field(0.8, env="CONFIDENCE_THRESHOLD")
    
    # File Storage
    UPLOAD_FOLDER: str = Field("./data/uploads", env="UPLOAD_FOLDER")
    PROCESSED_FOLDER: str = Field("./data/processed", env="PROCESSED_FOLDER")
    MAX_UPLOAD_SIZE: int = Field(16 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 16MB
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "bmp"}

    # Authentication
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(1440, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")  # 24 hours

    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    LOG_FILE: str = Field("./logs/app.log", env="LOG_FILE")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        ["http://localhost", "http://localhost:3000"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    @validator('BACKEND_CORS_ORIGINS', pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from string to list if needed."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        """Pydantic config."""

        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()

# Create necessary directories
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(settings.PROCESSED_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
os.makedirs(settings.PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
