#!/usr/bin/env python3
"""
External Data Integration API Server
FastAPI interface for weather and events data integration
"""

import sys
import os
sys.path.append('/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/services/external-data')

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import psycopg2
import redis
import asyncio
import logging
from datetime import datetime, timedelta
import uvicorn

from weather_service import WeatherService, WeatherData, WeatherForecast
from events_service import EventsService, EventData, DemographicData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RetailAI External Data Integration API",
    description="Weather, events, and demographic data integration for enhanced forecasting",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
weather_service = None
events_service = None
redis_client = None

# Pydantic models
class WeatherResponse(BaseModel):
    location: str
    timestamp: datetime
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float
    weather_condition: str
    impact_score: Optional[float] = None

class EventResponse(BaseModel):
    event_id: str
    name: str
    event_type: str
    location: str
    start_date: datetime
    end_date: datetime
    expected_attendance: Optional[int]
    impact_radius_km: Optional[float]
    demand_impact_score: float
    categories: Optional[List[str]]
    venue: Optional[str]

class DemographicResponse(BaseModel):
    location: str
    population: int
    median_age: float
    median_income: float
    education_level: str
    employment_rate: float
    urban_density: str
    lifestyle_segments: List[str]
    shopping_preferences: Dict[str, float]

class ExternalDataFeatures(BaseModel):
    store_id: str
    weather_features: Dict[str, Any]
    event_features: Dict[str, Any]
    demographic_features: Dict[str, Any]
    combined_multipliers: Dict[str, float]

def get_db_connection():
    """Get database connection."""
    try:
        return psycopg2.connect(
            host='localhost',
            port=5432,
            database='retailai',
            user='postgres',
            password='postgres'
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.on_event("startup")
async def startup_event():
    """Initialize external data services on startup."""
    global weather_service, events_service, redis_client
    
    logger.info("🚀 Initializing External Data Integration API Server...")
    
    try:
        # Initialize Redis (with auth if set)
        redis_client = get_redis_client()
        
        # Initialize services
        db_conn = get_db_connection()
        
        # API keys (in production, load from environment variables)
        api_keys = {
            'openweather_api_key': 'demo_key',
            'weatherapi_key': 'demo_key',
            'eventbrite_token': 'demo_token',
            'ticketmaster_key': 'demo_key'
        }
        
        weather_service = WeatherService(db_conn, redis_client, api_keys)
        events_service = EventsService(db_conn, redis_client, api_keys)
        
        logger.info("✅ External data services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    try:
        # Check database
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db_conn.close()
        
        # Check Redis
        redis_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "redis": "connected",
            "weather_service": "initialized" if weather_service else "not_initialized",
            "events_service": "initialized" if events_service else "not_initialized"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/weather/current/{store_id}", response_model=WeatherResponse)
async def get_current_weather(store_id: str):
    """Get current weather for a store location."""
    
    try:
        if not weather_service:
            raise HTTPException(status_code=500, detail="Weather service not initialized")
        
        weather_data = await weather_service.get_current_weather(store_id)
        
        if not weather_data:
            raise HTTPException(status_code=404, detail=f"Weather data not found for store {store_id}")
        
        return WeatherResponse(
            location=weather_data.location,
            timestamp=weather_data.timestamp,
            temperature=weather_data.temperature,
            humidity=weather_data.humidity,
            precipitation=weather_data.precipitation,
            wind_speed=weather_data.wind_speed,
            weather_condition=weather_data.weather_condition,
            impact_score=weather_service.calculate_weather_impact_score(
                weather_data.weather_condition, 
                weather_data.temperature
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Current weather retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/weather/forecast/{store_id}")
async def get_weather_forecast(store_id: str, days: int = Query(7, ge=1, le=14)):
    """Get weather forecast for a store location."""
    
    try:
        if not weather_service:
            raise HTTPException(status_code=500, detail="Weather service not initialized")
        
        forecasts = await weather_service.get_weather_forecast(store_id, days)
        
        if not forecasts:
            raise HTTPException(status_code=404, detail=f"Weather forecast not found for store {store_id}")
        
        return {
            "store_id": store_id,
            "forecast_days": len(forecasts),
            "forecasts": [
                {
                    "date": forecast.forecast_date.isoformat(),
                    "min_temp": forecast.min_temp,
                    "max_temp": forecast.max_temp,
                    "avg_temp": forecast.avg_temp,
                    "precipitation_prob": forecast.precipitation_prob,
                    "weather_condition": forecast.weather_condition,
                    "impact_score": forecast.impact_score
                }
                for forecast in forecasts
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Weather forecast retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/weather/ml-features/{store_id}")
async def get_weather_ml_features(store_id: str, date_range: int = Query(30, ge=7, le=90)):
    """Get weather features for ML model training/inference."""
    
    try:
        if not weather_service:
            raise HTTPException(status_code=500, detail="Weather service not initialized")
        
        features = await weather_service.get_weather_features_for_ml(store_id, date_range)
        
        if not features:
            raise HTTPException(status_code=404, detail=f"Weather features not found for store {store_id}")
        
        return {
            "store_id": store_id,
            "date_range_days": date_range,
            "features": features
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Weather ML features retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events/{store_id}")
async def get_events_for_location(store_id: str, date_range: int = Query(30, ge=7, le=90)):
    """Get events near a store location."""
    
    try:
        if not events_service:
            raise HTTPException(status_code=500, detail="Events service not initialized")
        
        events = await events_service.get_events_for_location(store_id, date_range)
        
        return {
            "store_id": store_id,
            "date_range_days": date_range,
            "total_events": len(events),
            "major_events": len([e for e in events if e.demand_impact_score >= 7.0]),
            "events": [
                EventResponse(
                    event_id=event.event_id,
                    name=event.name,
                    event_type=event.event_type,
                    location=event.location,
                    start_date=event.start_date,
                    end_date=event.end_date,
                    expected_attendance=event.expected_attendance,
                    impact_radius_km=event.impact_radius_km,
                    demand_impact_score=event.demand_impact_score,
                    categories=event.categories,
                    venue=event.venue
                )
                for event in events
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Events retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demographics/{store_id}", response_model=DemographicResponse)
async def get_demographic_data(store_id: str):
    """Get demographic data for a store location."""
    
    try:
        if not events_service:
            raise HTTPException(status_code=500, detail="Events service not initialized")
        
        demographic = await events_service.get_demographic_data(store_id)
        
        if not demographic:
            raise HTTPException(status_code=404, detail=f"Demographic data not found for store {store_id}")
        
        return DemographicResponse(
            location=demographic.location,
            population=demographic.population,
            median_age=demographic.median_age,
            median_income=demographic.median_income,
            education_level=demographic.education_level,
            employment_rate=demographic.employment_rate,
            urban_density=demographic.urban_density,
            lifestyle_segments=demographic.lifestyle_segments,
            shopping_preferences=demographic.shopping_preferences
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demographic data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demand-multipliers/{store_id}")
async def get_demand_multipliers(
    store_id: str, 
    target_date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    product_category: Optional[str] = Query(None, description="Product category for specific adjustments")
):
    """Get combined demand multipliers from weather, events, and demographics."""
    
    try:
        if not weather_service or not events_service:
            raise HTTPException(status_code=500, detail="External data services not initialized")
        
        # Parse target date
        try:
            target_datetime = datetime.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get weather multiplier
        weather_multiplier = await weather_service.get_weather_adjusted_forecast_multiplier(
            store_id, target_datetime
        )
        
        # Get event multiplier
        event_multiplier = await events_service.get_event_demand_multiplier(
            store_id, target_datetime, product_category
        )
        
        # Get demographic multiplier
        demographic_multiplier = 1.0
        if product_category:
            demographic_multiplier = await events_service.get_demographic_demand_multiplier(
                store_id, product_category
            )
        
        # Combined multiplier (geometric mean to avoid extreme values)
        combined_multiplier = (weather_multiplier * event_multiplier * demographic_multiplier) ** (1/3)
        
        return {
            "store_id": store_id,
            "target_date": target_date,
            "product_category": product_category,
            "multipliers": {
                "weather": round(weather_multiplier, 3),
                "events": round(event_multiplier, 3),
                "demographic": round(demographic_multiplier, 3),
                "combined": round(combined_multiplier, 3)
            },
            "interpretation": {
                "weather_impact": "positive" if weather_multiplier > 1.0 else "negative" if weather_multiplier < 1.0 else "neutral",
                "events_impact": "positive" if event_multiplier > 1.0 else "negative" if event_multiplier < 1.0 else "neutral",
                "demographic_fit": "positive" if demographic_multiplier > 1.0 else "negative" if demographic_multiplier < 1.0 else "neutral",
                "overall_adjustment": round((combined_multiplier - 1.0) * 100, 1)  # Percentage change
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demand multipliers calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ml-features/{store_id}")
async def get_external_ml_features(store_id: str, date_range: int = Query(30, ge=7, le=90)):
    """Get comprehensive external data features for ML model enhancement."""
    
    try:
        if not weather_service or not events_service:
            raise HTTPException(status_code=500, detail="External data services not initialized")
        
        # Get weather features
        weather_features = await weather_service.get_weather_features_for_ml(store_id, date_range)
        
        # Get events and demographic features
        external_features = await events_service.get_external_data_features_for_ml(store_id, date_range)
        
        # Calculate combined multipliers for major categories
        common_categories = ['food', 'apparel', 'electronics', 'premium', 'budget']
        tomorrow = datetime.now() + timedelta(days=1)
        
        combined_multipliers = {}
        for category in common_categories:
            weather_mult = await weather_service.get_weather_adjusted_forecast_multiplier(store_id, tomorrow)
            event_mult = await events_service.get_event_demand_multiplier(store_id, tomorrow, category)
            demo_mult = await events_service.get_demographic_demand_multiplier(store_id, category)
            
            combined_multipliers[category] = round((weather_mult * event_mult * demo_mult) ** (1/3), 3)
        
        return ExternalDataFeatures(
            store_id=store_id,
            weather_features=weather_features,
            event_features=external_features.get('events', {}),
            demographic_features=external_features.get('demographics', {}),
            combined_multipliers=combined_multipliers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"External ML features retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh-data/{store_id}")
async def refresh_external_data(store_id: str, background_tasks: BackgroundTasks):
    """Refresh external data for a specific store."""
    
    try:
        if not weather_service or not events_service:
            raise HTTPException(status_code=500, detail="External data services not initialized")
        
        async def refresh_data():
            """Background task to refresh data."""
            try:
                # Refresh weather data
                weather_data = await weather_service.get_current_weather(store_id)
                
                # Refresh events data  
                events = await events_service.get_events_for_location(store_id, 30)
                
                # Refresh demographic data
                demographic = await events_service.get_demographic_data(store_id)
                
                logger.info(f"✅ Refreshed external data for {store_id}: weather, {len(events)} events, demographics")
                
            except Exception as e:
                logger.error(f"Background data refresh failed for {store_id}: {e}")
        
        # Add to background tasks
        background_tasks.add_task(refresh_data)
        
        return {
            "store_id": store_id,
            "status": "refresh_started",
            "message": "External data refresh initiated in background",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data refresh initiation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh-all-data")
async def refresh_all_external_data(background_tasks: BackgroundTasks):
    """Refresh external data for all store locations."""
    
    try:
        if not weather_service or not events_service:
            raise HTTPException(status_code=500, detail="External data services not initialized")
        
        async def refresh_all_data():
            """Background task to refresh all external data."""
            try:
                # Update weather for all stores
                weather_results = await weather_service.update_all_store_weather()
                
                # Update events and demographics for all stores
                external_results = await events_service.update_all_external_data()
                
                logger.info(f"✅ Refreshed all external data: weather {weather_results['success']}/{weather_results['success'] + weather_results['failed']}, events {external_results['events_updated']}, demographics {external_results['demographics_updated']}")
                
            except Exception as e:
                logger.error(f"Background full data refresh failed: {e}")
        
        # Add to background tasks
        background_tasks.add_task(refresh_all_data)
        
        return {
            "status": "full_refresh_started",
            "message": "Full external data refresh initiated in background",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full data refresh initiation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/summary")
async def get_external_data_summary():
    """Get summary of external data across all stores."""
    
    try:
        if not weather_service or not events_service:
            raise HTTPException(status_code=500, detail="External data services not initialized")
        
        # Get store locations
        store_locations = weather_service.store_locations
        
        summary = {
            "total_stores": len(store_locations),
            "weather_data_available": 0,
            "total_events": 0,
            "major_events": 0,
            "demographic_data_available": 0,
            "store_details": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Check data availability for each store
        for store_id, location in store_locations.items():
            try:
                # Check weather
                weather = await weather_service.get_current_weather(store_id)
                weather_available = weather is not None
                if weather_available:
                    summary["weather_data_available"] += 1
                
                # Check events
                events = await events_service.get_events_for_location(store_id, 30)
                events_count = len(events)
                major_events_count = len([e for e in events if e.demand_impact_score >= 7.0])
                
                summary["total_events"] += events_count
                summary["major_events"] += major_events_count
                
                # Check demographics
                demographic = await events_service.get_demographic_data(store_id)
                demographic_available = demographic is not None
                if demographic_available:
                    summary["demographic_data_available"] += 1
                
                summary["store_details"].append({
                    "store_id": store_id,
                    "location": location["location_key"],
                    "weather_available": weather_available,
                    "events_count": events_count,
                    "major_events": major_events_count,
                    "demographic_available": demographic_available
                })
                
            except Exception as e:
                logger.warning(f"Failed to get summary data for {store_id}: {e}")
                summary["store_details"].append({
                    "store_id": store_id,
                    "location": location["location_key"],
                    "error": str(e)
                })
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"External data summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🌤️ Starting External Data Integration API")
    print("📊 Integrating: Weather • Events • Demographics")
    print("🤖 Enhanced ML forecasting with external factors")
    print("🌐 API available at: http://localhost:8002")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
def get_redis_client() -> redis.Redis:
    """Create Redis client using REDIS_URL or host/password envs."""
    url = os.getenv("REDIS_URL")
    if url:
        try:
            return redis.from_url(url)
        except Exception:
            pass
    password = os.getenv("REDIS_PASSWORD")
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, password=password)
