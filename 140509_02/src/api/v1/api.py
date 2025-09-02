"""Main API router for version 1 of the API."""
from fastapi import APIRouter

from api.v1.endpoints import auth, defects, health, models, predictions

# Create API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
api_router.include_router(defects.router, prefix="/defects", tags=["Defects"])
