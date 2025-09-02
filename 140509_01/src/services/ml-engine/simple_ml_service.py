"""
Simplified ML Service for Real-Time Demo
Provides actual forecasting functionality without heavy ML dependencies
"""

import numpy as np
import pandas as pd
import json
import os
import redis
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from dataclasses import dataclass
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ForecastResult:
    product_id: str
    product_name: str
    current_demand: int
    forecasted_demand: int
    confidence: float
    trend: str
    recommendation: str

class SimpleForecastEngine:
    def __init__(self):
        self.redis_client = None
        self.db_connection = None
        self.connect_to_services()
    
    def connect_to_services(self):
        """Connect to Redis and PostgreSQL"""
        try:
            # Prefer REDIS_URL, then REDIS_* vars, fallback to service name
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                redis_host = os.getenv("REDIS_HOST", "redis")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_db = int(os.getenv("REDIS_DB", "0"))
                redis_password = os.getenv("REDIS_PASSWORD")
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                )
            self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
        
        try:
            # Prefer DATABASE_URL, else POSTGRES_* vars, else fallback
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                self.db_connection = psycopg2.connect(db_url)
            else:
                db_host = os.getenv("POSTGRES_HOST", "postgres")
                db_name = os.getenv("POSTGRES_DB", "retailai")
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
                db_port = int(os.getenv("POSTGRES_PORT", "5432"))
                self.db_connection = psycopg2.connect(
                    host=db_host,
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_pass,
                )
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
    
    def generate_realistic_forecast(self, product_id: str, product_name: str, historical_data: List[int]) -> ForecastResult:
        """Generate realistic forecasts using simple statistical methods"""
        if not historical_data:
            historical_data = [100, 120, 95, 110, 130]  # Default data
        
        # Calculate moving average and trend
        current_demand = historical_data[-1] if historical_data else 100
        moving_avg = sum(historical_data[-3:]) / min(3, len(historical_data))
        
        # Simple trend calculation
        if len(historical_data) >= 2:
            trend_slope = (historical_data[-1] - historical_data[-2]) / historical_data[-2]
        else:
            trend_slope = 0.1
        
        # Apply seasonal and random factors
        seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * datetime.now().timetuple().tm_yday / 365)
        noise = np.random.normal(0, 0.05)
        
        # Calculate forecast
        base_forecast = moving_avg * (1 + trend_slope)
        forecasted_demand = int(base_forecast * seasonal_factor * (1 + noise))
        
        # Calculate confidence based on data variance
        if len(historical_data) > 1:
            variance = np.var(historical_data)
            confidence = max(0.7, min(0.98, 1 - variance / (moving_avg * 100)))
        else:
            confidence = 0.85
        
        # Determine trend and recommendation
        change_pct = (forecasted_demand - current_demand) / current_demand * 100
        
        if change_pct > 10:
            trend = "up"
            recommendation = f"Increase stock by {int(change_pct)}%"
        elif change_pct < -10:
            trend = "down"
            recommendation = f"Reduce orders by {int(abs(change_pct))}%"
        else:
            trend = "stable"
            recommendation = "Maintain current levels"
        
        return ForecastResult(
            product_id=product_id,
            product_name=product_name,
            current_demand=current_demand,
            forecasted_demand=forecasted_demand,
            confidence=round(confidence, 3),
            trend=trend,
            recommendation=recommendation
        )
    
    def get_live_kpis(self) -> Dict[str, Any]:
        """Generate live KPIs based on current data"""
        try:
            # Try to get cached KPIs from Redis
            cached_kpis = self.redis_client.get("live_kpis") if self.redis_client else None
            if cached_kpis:
                return json.loads(cached_kpis)
        except Exception:
            pass
        
        # Generate realistic KPIs
        base_time = datetime.now()
        
        # Simulate some variance based on time of day
        time_factor = 1 + 0.1 * np.sin(2 * np.pi * base_time.hour / 24)
        
        kpis = {
            "cost_reduction": {
                "value": round(18.7 * time_factor, 1),
                "change": f"+{round(2.3 * time_factor, 1)}% vs last month",
                "trend": "up"
            },
            "service_level": {
                "value": round(97.2 + np.random.normal(0, 0.5), 1),
                "change": f"+{round(1.8 + np.random.normal(0, 0.3), 1)}% improvement",
                "trend": "up"
            },
            "inventory_turnover": {
                "value": f"{round(12.4 + np.random.normal(0, 0.2), 1)}x",
                "change": f"+{round(15 + np.random.normal(0, 2), 0)}% increase",
                "trend": "up"
            },
            "active_stores": {
                "value": "10",
                "change": "All operational",
                "trend": "stable"
            },
            "forecast_accuracy": {
                "arima": round(87.2 + np.random.normal(0, 1), 1),
                "lstm": round(91.4 + np.random.normal(0, 1), 1),
                "prophet": round(89.8 + np.random.normal(0, 1), 1),
                "ensemble": round(93.1 + np.random.normal(0, 0.5), 1)
            },
            "timestamp": base_time.isoformat(),
            "data_freshness": "Live",
            "system_status": "operational"
        }
        
        # Cache KPIs for 30 seconds
        try:
            if self.redis_client:
                self.redis_client.setex("live_kpis", 30, json.dumps(kpis))
        except Exception:
            pass
        
        return kpis

# Create FastAPI app
app = FastAPI(title="RetailAI ML Engine", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML engine
ml_engine = SimpleForecastEngine()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "healthy"
    db_status = "healthy"
    
    try:
        if ml_engine.redis_client:
            ml_engine.redis_client.ping()
    except:
        redis_status = "unhealthy"
    
    try:
        if ml_engine.db_connection:
            cursor = ml_engine.db_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "redis": redis_status,
            "database": db_status
        }
    }

@app.get("/api/kpis")
async def get_live_kpis():
    """Get live KPI data"""
    try:
        kpis = ml_engine.get_live_kpis()
        return {"success": True, "data": kpis}
    except Exception as e:
        logger.error(f"Error getting KPIs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch KPIs")

@app.get("/api/forecasts")
async def get_forecasts():
    """Get live forecast data"""
    try:
        # Sample products
        products = [
            ("1", "iPhone 15 Pro"),
            ("2", "Samsung Galaxy S24"),
            ("3", "AirPods Pro"),
            ("4", "MacBook Air M3"),
            ("5", "iPad Pro")
        ]
        
        forecasts = []
        for product_id, product_name in products:
            # Simulate historical data (in production, this would come from database)
            historical_data = [
                int(100 + 50 * np.sin(i/10) + np.random.normal(0, 10))
                for i in range(30)
            ]
            
            forecast = ml_engine.generate_realistic_forecast(product_id, product_name, historical_data)
            forecasts.append({
                "product_id": forecast.product_id,
                "product": forecast.product_name,
                "currentDemand": forecast.current_demand,
                "forecastedDemand": forecast.forecasted_demand,
                "confidence": int(forecast.confidence * 100),
                "trend": forecast.trend,
                "recommendation": forecast.recommendation
            })
        
        return {"success": True, "data": forecasts}
    
    except Exception as e:
        logger.error(f"Error getting forecasts: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate forecasts")

@app.get("/api/analytics/stores")
async def get_store_analytics():
    """Get store performance analytics"""
    stores = [
        {"name": "New York", "revenue": "$485K", "performance": 98, "efficiency": 98},
        {"name": "Los Angeles", "revenue": "$412K", "performance": 96, "efficiency": 96},
        {"name": "Chicago", "revenue": "$378K", "performance": 97, "efficiency": 97},
        {"name": "Houston", "revenue": "$356K", "performance": 95, "efficiency": 95},
        {"name": "Phoenix", "revenue": "$298K", "performance": 99, "efficiency": 99}
    ]
    
    # Add some real-time variance
    for store in stores:
        store["performance"] += np.random.normal(0, 0.5)
        store["efficiency"] += np.random.normal(0, 0.5)
        store["performance"] = max(90, min(100, round(store["performance"], 1)))
        store["efficiency"] = max(90, min(100, round(store["efficiency"], 1)))
    
    return {"success": True, "data": stores}

if __name__ == "__main__":
    logger.info("Starting SimpleForecast ML Service...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
