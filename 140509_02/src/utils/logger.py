"""Logging configuration for the application."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import settings


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    ""
    Configure and return a logger with both file and console handlers.
    
    Args:
        name: Name of the logger. If None, returns the root logger.
        
    Returns:
        Configured logger instance.
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    
    # Prevent adding handlers multiple times in case of module reload
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Create file handler
    os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Configure root logger if this is the root logger
    if name is None:
        logging.basicConfig(
            level=settings.LOG_LEVEL,
            handlers=[console_handler, file_handler]
        )
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    This is a convenience function that wraps setup_logger.
    
    Args:
        name: Name of the logger (usually __name__)
        
    Returns:
        Configured logger instance.
    """
    return setup_logger(name)
