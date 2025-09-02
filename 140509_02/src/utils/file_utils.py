"""Utility functions for file operations."""
import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Union

from fastapi import UploadFile

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

def get_file_hash(file_path: Union[str, Path], block_size: int = 65536) -> str:
    """
    Generate a SHA-256 hash for a file.
    
    Args:
        file_path: Path to the file
        block_size: Size of blocks to read at a time
        
    Returns:
        Hexadecimal string of the file's hash
    """
    file_path = Path(file_path)
    hasher = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        buf = f.read(block_size)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(block_size)
    
    return hasher.hexdigest()

def save_upload_file(upload_file: UploadFile, destination: Union[str, Path]) -> Tuple[bool, str]:
    """
    Save an uploaded file to the specified destination.
    
    Args:
        upload_file: FastAPI UploadFile object
        destination: Directory where the file should be saved
        
    Returns:
        Tuple of (success, message_or_path)
    """
    try:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        
        # Generate a secure filename
        file_extension = Path(upload_file.filename).suffix.lower()
        file_hash = hashlib.md5(upload_file.filename.encode()).hexdigest()
        secure_filename = f"{file_hash}{file_extension}"
        file_path = destination / secure_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        logger.info(f"File saved successfully: {file_path}")
        return True, str(file_path)
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        return False, str(e)

def is_file_allowed(filename: str) -> bool:
    """
    Check if the file has an allowed extension.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if the file extension is allowed, False otherwise
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in settings.ALLOWED_EXTENSIONS
    )

def ensure_directory_exists(directory: Union[str, Path]) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        True if the directory exists or was created, False otherwise
    """
    try:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {str(e)}")
        return False

def get_unique_filename(directory: Union[str, Path], filename: str) -> Path:
    """
    Generate a unique filename in the specified directory.
    
    If a file with the same name exists, appends a number to make it unique.
    
    Args:
        directory: Directory where the file will be saved
        filename: Desired filename
        
    Returns:
        Path object with a unique filename
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    counter = 1
    
    while True:
        new_filename = f"{base_name}_{counter}{extension}" if counter > 1 else filename
        file_path = directory / new_filename
        
        if not file_path.exists():
            return file_path
            
        counter += 1
        
        # Safety check to prevent infinite loops
        if counter > 1000:
            raise RuntimeError("Could not generate a unique filename after 1000 attempts")
