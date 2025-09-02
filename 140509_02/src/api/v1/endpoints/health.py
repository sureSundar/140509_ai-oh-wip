"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from schemas.health import HealthCheck
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/", response_model=HealthCheck)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        HealthCheck: Status of the API
    """
    return {
        "status": "ok",
        "message": "API is running"
    }

@router.get("/db", response_model=HealthCheck)
async def db_health_check(db: Session = Depends(get_db)):
    """
    Database health check endpoint.
    
    Args:
        db: Database session dependency
        
    Returns:
        HealthCheck: Status of the database connection
    """
    try:
        # Try to execute a simple query
        db.execute("SELECT 1")
        return {
            "status": "ok",
            "message": "Database connection is healthy"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Database connection error: {str(e)}"
        }
