"""
Data Ingestion Service - AI-Powered Retail Inventory Optimization
Real-time data pipeline for POS systems, weather APIs, and external events.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import asyncio
import json

from .models import (
    POSTransaction, WeatherData, EventData, ExternalDataSource,
    DataIngestionStatus, BatchUploadRequest, DataQualityReport
)
from .services.pos_ingestion_service import POSIngestionService
from .services.weather_service import WeatherService
from .services.event_service import EventService
from .services.data_validator import DataValidator
from .services.kafka_producer import KafkaProducer
from .config import settings
from .database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Data Ingestion Service",
    description="Real-time data ingestion pipeline for retail inventory optimization",
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
pos_service = POSIngestionService()
weather_service = WeatherService()
event_service = EventService()
data_validator = DataValidator()
kafka_producer = KafkaProducer()

@app.on_event("startup")
async def startup_event():
    """Initialize data ingestion services on startup."""
    try:
        logger.info("Initializing Data Ingestion Service...")
        await kafka_producer.initialize()
        await pos_service.initialize()
        await weather_service.initialize()
        await event_service.initialize()
        
        # Start background data collection tasks
        asyncio.create_task(weather_service.scheduled_weather_collection())
        asyncio.create_task(event_service.scheduled_event_collection())
        
        logger.info("Data Ingestion Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Data Ingestion Service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("Shutting down Data Ingestion Service...")
    await kafka_producer.close()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "data-ingestion",
        "version": "1.0.0",
        "kafka_status": await kafka_producer.health_check(),
        "external_apis": {
            "weather": await weather_service.health_check(),
            "events": await event_service.health_check()
        }
    }

@app.post("/api/v1/pos/transaction")
async def ingest_pos_transaction(
    transaction: POSTransaction,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Ingest a single POS transaction."""
    try:
        # Validate transaction data
        validation_result = await data_validator.validate_pos_transaction(transaction)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid transaction data: {validation_result.errors}"
            )
        
        # Enrich transaction with additional data
        enriched_transaction = await pos_service.enrich_transaction(transaction, db)
        
        # Send to Kafka for real-time processing
        await kafka_producer.send_message(
            topic="pos-transactions",
            key=f"{transaction.product_id}_{transaction.store_id}",
            value=enriched_transaction.dict()
        )
        
        # Save to database in background
        background_tasks.add_task(
            pos_service.save_transaction,
            enriched_transaction,
            db
        )
        
        return {
            "status": "accepted",
            "transaction_id": enriched_transaction.id,
            "timestamp": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POS transaction ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pos/batch")
async def ingest_pos_batch(
    request: BatchUploadRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Ingest a batch of POS transactions."""
    try:
        logger.info(f"Starting batch ingestion of {len(request.transactions)} transactions")
        
        # Start background batch processing
        task_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            pos_service.process_batch,
            request.transactions,
            task_id,
            db
        )
        
        return {
            "status": "accepted",
            "task_id": task_id,
            "batch_size": len(request.transactions),
            "estimated_completion": "5 minutes"
        }
        
    except Exception as e:
        logger.error(f"Batch ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ingestion/status/{task_id}")
async def get_ingestion_status(task_id: str, db=Depends(get_db)):
    """Get status of a batch ingestion task."""
    try:
        status = await pos_service.get_batch_status(task_id, db)
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get ingestion status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/weather/collect")
async def trigger_weather_collection(
    store_ids: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db=Depends(get_db)
):
    """Trigger weather data collection for specified stores."""
    try:
        background_tasks.add_task(
            weather_service.collect_weather_data,
            store_ids,
            db
        )
        
        return {
            "status": "started",
            "message": "Weather data collection started",
            "stores": len(store_ids) if store_ids else "all"
        }
        
    except Exception as e:
        logger.error(f"Weather collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/events/collect")
async def trigger_event_collection(
    store_ids: Optional[List[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db=Depends(get_db)
):
    """Trigger event data collection."""
    try:
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = start_date + timedelta(days=30)
            
        background_tasks.add_task(
            event_service.collect_events,
            store_ids,
            start_date,
            end_date,
            db
        )
        
        return {
            "status": "started",
            "message": "Event data collection started",
            "date_range": f"{start_date} to {end_date}"
        }
        
    except Exception as e:
        logger.error(f"Event collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data/quality")
async def get_data_quality_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db=Depends(get_db)
):
    """Get data quality report for specified date range."""
    try:
        if not start_date:
            start_date = date.today() - timedelta(days=7)
        if not end_date:
            end_date = date.today()
            
        report = await data_validator.generate_quality_report(
            start_date, end_date, db
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Data quality report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/data/sources")
async def get_data_sources():
    """Get status of all external data sources."""
    try:
        sources = []
        
        # Check weather API status
        weather_status = await weather_service.get_source_status()
        sources.append(ExternalDataSource(
            source_name="Weather API",
            source_type="weather",
            status=weather_status["status"],
            last_update=weather_status["last_update"],
            error_rate=weather_status["error_rate"]
        ))
        
        # Check event API status
        event_status = await event_service.get_source_status()
        sources.append(ExternalDataSource(
            source_name="Event Calendar API",
            source_type="events",
            status=event_status["status"],
            last_update=event_status["last_update"],
            error_rate=event_status["error_rate"]
        ))
        
        return sources
        
    except Exception as e:
        logger.error(f"Get data sources failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/data/cleanup")
async def trigger_data_cleanup(
    days_to_keep: int = 365,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db=Depends(get_db)
):
    """Trigger data cleanup to remove old records."""
    try:
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        background_tasks.add_task(
            pos_service.cleanup_old_data,
            cutoff_date,
            db
        )
        
        return {
            "status": "started",
            "message": "Data cleanup started",
            "cutoff_date": cutoff_date,
            "estimated_completion": "30 minutes"
        }
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics")
async def get_ingestion_metrics(
    hours_back: int = 24,
    db=Depends(get_db)
):
    """Get data ingestion metrics."""
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        metrics = {
            "pos_transactions": await pos_service.get_transaction_count(start_time, db),
            "weather_updates": await weather_service.get_update_count(start_time, db),
            "event_updates": await event_service.get_update_count(start_time, db),
            "kafka_messages": await kafka_producer.get_message_count(start_time),
            "error_count": await data_validator.get_error_count(start_time, db),
            "data_quality_score": await data_validator.get_quality_score(start_time, db)
        }
        
        return {
            "time_period": f"Last {hours_back} hours",
            "metrics": metrics,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Get ingestion metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/stream/start")
async def start_streaming():
    """Start real-time data streaming."""
    try:
        await pos_service.start_streaming()
        await weather_service.start_streaming()
        await event_service.start_streaming()
        
        return {
            "status": "started",
            "message": "Real-time streaming started",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Start streaming failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/stream/stop")
async def stop_streaming():
    """Stop real-time data streaming."""
    try:
        await pos_service.stop_streaming()
        await weather_service.stop_streaming()
        await event_service.stop_streaming()
        
        return {
            "status": "stopped",
            "message": "Real-time streaming stopped",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Stop streaming failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )