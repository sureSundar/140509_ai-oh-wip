"""
ML Engine Service - AI-Powered Retail Inventory Optimization
Main FastAPI application for machine learning forecasting models.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List, Optional
from datetime import datetime, date
import asyncio

from .models import (
    ForecastRequest, ForecastResponse, ModelTrainingRequest, 
    ModelPerformance, ProductForecast
)
from .services.forecast_service import ForecastService
from .services.model_service import ModelService
from .services.data_service import DataService
from .config import settings
from .database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI ML Engine",
    description="Machine Learning forecasting service for retail inventory optimization",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
forecast_service = ForecastService()
model_service = ModelService()
data_service = DataService()

@app.on_event("startup")
async def startup_event():
    """Initialize ML models and services on startup."""
    try:
        logger.info("Initializing ML Engine...")
        await model_service.initialize_models()
        await data_service.initialize_connections()
        logger.info("ML Engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ML Engine: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("Shutting down ML Engine...")
    await data_service.close_connections()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "ml-engine",
        "version": "1.0.0"
    }

@app.post("/api/v1/forecast", response_model=List[ForecastResponse])
async def generate_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Generate demand forecasts for products."""
    try:
        logger.info(f"Generating forecast for {len(request.product_ids)} products")
        
        # Generate forecasts
        forecasts = await forecast_service.generate_forecasts(
            product_ids=request.product_ids,
            store_ids=request.store_ids,
            forecast_horizon_days=request.forecast_horizon_days,
            models=request.models or ['prophet', 'lstm', 'arima']
        )
        
        # Save forecasts to database in background
        background_tasks.add_task(
            forecast_service.save_forecasts,
            forecasts,
            db
        )
        
        return forecasts
        
    except Exception as e:
        logger.error(f"Forecast generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/forecast/batch")
async def generate_batch_forecast(
    store_ids: Optional[List[str]] = None,
    category_ids: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db=Depends(get_db)
):
    """Generate forecasts for all products in specified stores/categories."""
    try:
        logger.info("Starting batch forecast generation")
        
        # Get products to forecast
        products = await data_service.get_products_for_forecasting(
            store_ids=store_ids,
            category_ids=category_ids
        )
        
        # Start background task for batch processing
        background_tasks.add_task(
            forecast_service.batch_forecast,
            products,
            db
        )
        
        return {
            "message": "Batch forecast started",
            "products_count": len(products),
            "estimated_completion": "30 minutes"
        }
        
    except Exception as e:
        logger.error(f"Batch forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/forecast/{product_id}")
async def get_product_forecast(
    product_id: str,
    store_id: Optional[str] = None,
    days: int = 30,
    db=Depends(get_db)
):
    """Get latest forecast for a specific product."""
    try:
        forecast = await forecast_service.get_forecast(
            product_id=product_id,
            store_id=store_id,
            days=days,
            db=db
        )
        
        if not forecast:
            raise HTTPException(
                status_code=404, 
                detail=f"No forecast found for product {product_id}"
            )
            
        return forecast
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train")
async def train_models(
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Train or retrain ML models."""
    try:
        logger.info(f"Starting model training for {request.model_types}")
        
        # Start background training task
        task_id = f"training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            model_service.train_models,
            request.model_types,
            request.product_ids,
            request.start_date,
            request.end_date,
            task_id,
            db
        )
        
        return {
            "message": "Model training started",
            "task_id": task_id,
            "estimated_completion": "2 hours"
        }
        
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/models/performance")
async def get_model_performance(
    model_type: Optional[str] = None,
    product_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Get model performance metrics."""
    try:
        performance = await model_service.get_model_performance(
            model_type=model_type,
            product_id=product_id,
            db=db
        )
        
        return performance
        
    except Exception as e:
        logger.error(f"Get model performance failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/models/status")
async def get_models_status():
    """Get status of all ML models."""
    try:
        status = await model_service.get_models_status()
        return status
        
    except Exception as e:
        logger.error(f"Get models status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/data/features/extract")
async def extract_features(
    start_date: date,
    end_date: date,
    product_ids: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Extract and preprocess features for ML models."""
    try:
        logger.info("Starting feature extraction")
        
        background_tasks.add_task(
            data_service.extract_features,
            start_date,
            end_date,
            product_ids
        )
        
        return {
            "message": "Feature extraction started",
            "date_range": f"{start_date} to {end_date}",
            "estimated_completion": "30 minutes"
        }
        
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/accuracy")
async def get_forecast_accuracy(
    days_back: int = 30,
    model_type: Optional[str] = None,
    db=Depends(get_db)
):
    """Get forecast accuracy analytics."""
    try:
        accuracy = await forecast_service.get_forecast_accuracy(
            days_back=days_back,
            model_type=model_type,
            db=db
        )
        
        return accuracy
        
    except Exception as e:
        logger.error(f"Get forecast accuracy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )