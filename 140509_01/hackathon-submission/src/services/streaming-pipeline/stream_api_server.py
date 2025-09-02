#!/usr/bin/env python3
"""
Streaming Pipeline API Server
FastAPI interface for real-time data pipeline management and monitoring
"""

import sys
import os
sys.path.append('/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/services/streaming-pipeline')

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import psycopg2
import redis
import asyncio
import logging
from datetime import datetime
import uvicorn

from kafka_stream_processor import KafkaStreamProcessor, StreamEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RetailAI Streaming Pipeline API",
    description="Real-time data processing pipeline with Kafka streaming",
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

# Global instances
stream_processor = None
redis_client = None

# Pydantic models
class StreamEventRequest(BaseModel):
    event_type: str
    data: Dict[str, Any]
    source: str
    metadata: Optional[Dict] = None

class SalesTransactionEvent(BaseModel):
    transaction_id: str
    product_id: str
    store_id: str
    quantity: int
    unit_price: float
    total_amount: float
    customer_id: Optional[str] = None
    timestamp: Optional[datetime] = None

class InventoryUpdateEvent(BaseModel):
    product_id: str
    store_id: str
    new_stock: int
    update_type: str = "manual"
    reason: Optional[str] = None

class StreamMetrics(BaseModel):
    events_processed: int
    events_failed: int
    success_rate: float
    avg_latency_ms: float
    alerts_generated: int
    active_consumers: int
    throughput_per_minute: int

def get_db_connection():
    """Get database connection."""
    try:
        return psycopg2.connect(
            host='localhost',
            port=5432,
            database='retailai',
            user='retailai',
            password='retailai123'
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.on_event("startup")
async def startup_event():
    """Initialize streaming pipeline on startup."""
    global stream_processor, redis_client
    
    logger.info("🚀 Initializing Streaming Pipeline API Server...")
    
    try:
        # Initialize Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # Initialize stream processor
        kafka_config = {
            'bootstrap_servers': ['localhost:9092']
        }
        
        db_conn = get_db_connection()
        stream_processor = KafkaStreamProcessor(kafka_config, db_conn, redis_client)
        
        # Start stream processing
        await stream_processor.start_stream_processing()
        
        logger.info("✅ Streaming pipeline initialized successfully")
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
        
        # Check stream processor
        metrics = stream_processor.get_processing_metrics() if stream_processor else {}
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "redis": "connected",
            "stream_processor": "running" if stream_processor and stream_processor.running else "stopped",
            "active_consumers": metrics.get('active_consumers', 0)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stream/metrics", response_model=Dict)
async def get_stream_metrics():
    """Get real-time streaming pipeline metrics."""
    
    try:
        if not stream_processor:
            raise HTTPException(status_code=500, detail="Stream processor not initialized")
        
        metrics = stream_processor.get_processing_metrics()
        
        # Get additional metrics from Redis
        redis_metrics = redis_client.hgetall('streaming_metrics')
        if redis_metrics:
            redis_data = {k.decode(): v.decode() for k, v in redis_metrics.items()}
            metrics.update(redis_data)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream/publish/sales-transaction")
async def publish_sales_transaction(transaction: SalesTransactionEvent):
    """Publish a sales transaction event to the stream."""
    
    try:
        if not stream_processor:
            raise HTTPException(status_code=500, detail="Stream processor not initialized")
        
        # Create stream event
        event = StreamEvent(
            event_id=f"sales_{transaction.transaction_id}_{int(datetime.now().timestamp())}",
            event_type='sales_transaction',
            timestamp=transaction.timestamp or datetime.now(),
            data={
                'transaction_id': transaction.transaction_id,
                'product_id': transaction.product_id,
                'store_id': transaction.store_id,
                'quantity': transaction.quantity,
                'unit_price': transaction.unit_price,
                'total_amount': transaction.total_amount,
                'customer_id': transaction.customer_id
            },
            source='api_server'
        )
        
        # Publish to stream
        success = await stream_processor.publish_event('sales_transactions', event)
        
        if success:
            return {
                "status": "published",
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to publish event")
            
    except Exception as e:
        logger.error(f"Sales transaction publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream/publish/inventory-update")
async def publish_inventory_update(update: InventoryUpdateEvent):
    """Publish an inventory update event to the stream."""
    
    try:
        if not stream_processor:
            raise HTTPException(status_code=500, detail="Stream processor not initialized")
        
        # Create stream event
        event = StreamEvent(
            event_id=f"inventory_{update.product_id}_{update.store_id}_{int(datetime.now().timestamp())}",
            event_type='inventory_update',
            timestamp=datetime.now(),
            data={
                'product_id': update.product_id,
                'store_id': update.store_id,
                'new_stock': update.new_stock,
                'update_type': update.update_type,
                'reason': update.reason
            },
            source='api_server'
        )
        
        # Publish to stream
        success = await stream_processor.publish_event('inventory_updates', event)
        
        if success:
            return {
                "status": "published",
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to publish event")
            
    except Exception as e:
        logger.error(f"Inventory update publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream/publish/custom-event")
async def publish_custom_event(event_request: StreamEventRequest):
    """Publish a custom event to the stream."""
    
    try:
        if not stream_processor:
            raise HTTPException(status_code=500, detail="Stream processor not initialized")
        
        # Create stream event
        event = StreamEvent(
            event_id=f"custom_{event_request.event_type}_{int(datetime.now().timestamp())}",
            event_type=event_request.event_type,
            timestamp=datetime.now(),
            data=event_request.data,
            source=event_request.source,
            metadata=event_request.metadata
        )
        
        # Determine topic based on event type
        topic = 'system_events'  # Default topic
        if 'sales' in event_request.event_type.lower():
            topic = 'sales_transactions'
        elif 'inventory' in event_request.event_type.lower():
            topic = 'inventory_updates'
        elif 'alert' in event_request.event_type.lower():
            topic = 'alerts'
        
        # Publish to stream
        success = await stream_processor.publish_event(topic, event)
        
        if success:
            return {
                "status": "published",
                "event_id": event.event_id,
                "topic": topic,
                "timestamp": event.timestamp.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to publish event")
            
    except Exception as e:
        logger.error(f"Custom event publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stream/recent-events")
async def get_recent_events(limit: int = 50):
    """Get recent processed events from Redis."""
    
    try:
        # Get recent events from Redis
        recent_events = []
        
        # Get recent sales events
        sales_keys = redis_client.keys('analytics:daily:*')
        for key in sales_keys[-limit:]:
            data = redis_client.hgetall(key)
            if data:
                recent_events.append({
                    'type': 'sales_analytics',
                    'key': key.decode(),
                    'data': {k.decode(): v.decode() for k, v in data.items()}
                })
        
        # Get recent alerts
        alerts = redis_client.lrange('recent_alerts', 0, limit-1)
        for alert in alerts:
            try:
                import json
                alert_data = json.loads(alert.decode())
                recent_events.append({
                    'type': 'alert',
                    'data': alert_data
                })
            except:
                continue
        
        # Sort by timestamp if available
        recent_events.sort(
            key=lambda x: x.get('data', {}).get('timestamp', ''),
            reverse=True
        )
        
        return {
            'total_events': len(recent_events),
            'events': recent_events[:limit]
        }
        
    except Exception as e:
        logger.error(f"Recent events retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stream/analytics/realtime")
async def get_realtime_analytics():
    """Get real-time analytics from the streaming pipeline."""
    
    try:
        analytics = {}
        
        # Get today's analytics
        today = datetime.now().date()
        daily_keys = redis_client.keys(f'analytics:daily:*:{today}')
        
        total_sales = 0
        total_transactions = 0
        active_products = len(daily_keys)
        
        for key in daily_keys:
            data = redis_client.hgetall(key)
            if data:
                quantity = int(data.get(b'total_quantity', 0))
                tx_count = int(data.get(b'transaction_count', 0))
                
                total_sales += quantity
                total_transactions += tx_count
        
        # Get hourly data for trends
        current_hour = datetime.now().strftime('%Y-%m-%d-%H')
        hourly_keys = redis_client.keys(f'analytics:hourly:*:{current_hour}')
        
        current_hour_sales = 0
        current_hour_transactions = 0
        
        for key in hourly_keys:
            data = redis_client.hgetall(key)
            if data:
                quantity = int(data.get(b'total_quantity', 0))
                tx_count = int(data.get(b'transaction_count', 0))
                
                current_hour_sales += quantity
                current_hour_transactions += tx_count
        
        analytics = {
            'daily_totals': {
                'total_sales_units': total_sales,
                'total_transactions': total_transactions,
                'active_products': active_products
            },
            'current_hour': {
                'sales_units': current_hour_sales,
                'transactions': current_hour_transactions,
                'active_products': len(hourly_keys)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Real-time analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stream/demo/simulate-traffic")
async def simulate_traffic(num_events: int = 100):
    """Simulate traffic for demonstration purposes."""
    
    try:
        if not stream_processor:
            raise HTTPException(status_code=500, detail="Stream processor not initialized")
        
        import random
        
        # Sample product and store data
        products = ['PROD_0001', 'PROD_0002', 'PROD_0003', 'PROD_0004', 'PROD_0005']
        stores = ['STORE_001', 'STORE_002', 'STORE_003']
        
        events_published = 0
        
        for i in range(num_events):
            # Generate random transaction
            product_id = random.choice(products)
            store_id = random.choice(stores)
            quantity = random.randint(1, 5)
            unit_price = random.uniform(10.0, 100.0)
            
            transaction = SalesTransactionEvent(
                transaction_id=f"SIM_{i:06d}",
                product_id=product_id,
                store_id=store_id,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=quantity * unit_price,
                timestamp=datetime.now()
            )
            
            # Create and publish event
            event = StreamEvent(
                event_id=f"sim_sales_{i}_{int(datetime.now().timestamp())}",
                event_type='sales_transaction',
                timestamp=datetime.now(),
                data=transaction.dict(),
                source='traffic_simulator'
            )
            
            success = await stream_processor.publish_event('sales_transactions', event)
            if success:
                events_published += 1
            
            # Small delay to spread events
            await asyncio.sleep(0.1)
        
        return {
            "status": "completed",
            "events_requested": num_events,
            "events_published": events_published,
            "simulation_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Traffic simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/stream/stop")
async def stop_streaming():
    """Stop the streaming pipeline."""
    
    try:
        if stream_processor:
            stream_processor.stop_stream_processing()
            return {"status": "stopped", "timestamp": datetime.now().isoformat()}
        else:
            return {"status": "not_running", "timestamp": datetime.now().isoformat()}
            
    except Exception as e:
        logger.error(f"Stream stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Starting Real-Time Streaming Pipeline API")
    print("📊 Kafka-based event processing with real-time analytics")
    print("🔄 Processing: Sales, Inventory, Alerts, ML Events")
    print("🌐 API available at: http://localhost:8002")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)