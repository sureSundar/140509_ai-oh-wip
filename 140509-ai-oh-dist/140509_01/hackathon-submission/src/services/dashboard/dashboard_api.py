#!/usr/bin/env python3
"""
Dashboard API Server
FastAPI interface for operational dashboard and executive reporting
"""

import sys
import os
sys.path.append('/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/services/dashboard')

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import psycopg2
import redis
import asyncio
import json
import logging
from datetime import datetime, timedelta
import uvicorn

from dashboard_service import DashboardService, KPIMetric, AlertSummary, InventoryInsight, SalesInsight

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RetailAI Dashboard API",
    description="Operational dashboard and executive reporting with real-time updates",
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
dashboard_service = None
redis_client = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Connection closed, remove it
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Pydantic models
class KPIResponse(BaseModel):
    name: str
    value: float
    unit: str
    trend: str
    trend_percentage: float
    target: Optional[float] = None
    status: str
    last_updated: datetime

class DashboardSummary(BaseModel):
    kpis: List[KPIResponse]
    inventory_insights: Dict[str, Any]
    sales_insights: Dict[str, Any]
    alert_summary: Dict[str, Any]
    last_updated: datetime

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
    """Initialize dashboard service on startup."""
    global dashboard_service, redis_client
    
    logger.info("🚀 Initializing Dashboard API Server...")
    
    try:
        # Initialize Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # Initialize dashboard service
        db_conn = get_db_connection()
        dashboard_service = DashboardService(db_conn, redis_client)
        
        # Start real-time update broadcaster
        asyncio.create_task(real_time_broadcaster())
        
        logger.info("✅ Dashboard service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

async def real_time_broadcaster():
    """Broadcast real-time updates to connected WebSocket clients."""
    
    while True:
        try:
            if manager.active_connections:
                # Get latest dashboard data
                kpis = await dashboard_service.get_real_time_kpis(use_cache=True)
                alert_summary = await dashboard_service.get_alert_summary(use_cache=True)
                
                # Prepare update message
                update_message = {
                    "type": "dashboard_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "kpis": [
                            {
                                "name": kpi.name,
                                "value": kpi.value,
                                "unit": kpi.unit,
                                "trend": kpi.trend,
                                "status": kpi.status
                            } for kpi in kpis
                        ],
                        "alerts": {
                            "total": alert_summary.total_alerts,
                            "critical": alert_summary.critical_alerts,
                            "high": alert_summary.high_alerts
                        }
                    }
                }
                
                # Broadcast to all connected clients
                await manager.broadcast(update_message)
            
            # Wait 30 seconds before next update
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Real-time broadcaster error: {e}")
            await asyncio.sleep(60)  # Wait longer on error

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
            "dashboard_service": "initialized" if dashboard_service else "not_initialized",
            "active_websockets": len(manager.active_connections)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/kpis")
async def get_kpis():
    """Get real-time KPIs."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        kpis = await dashboard_service.get_real_time_kpis()
        
        return {
            "kpis": [
                KPIResponse(
                    name=kpi.name,
                    value=kpi.value,
                    unit=kpi.unit,
                    trend=kpi.trend,
                    trend_percentage=kpi.trend_percentage,
                    target=kpi.target,
                    status=kpi.status,
                    last_updated=kpi.last_updated
                ) for kpi in kpis
            ],
            "total_kpis": len(kpis),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"KPIs retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/inventory")
async def get_inventory_insights(store_id: Optional[str] = None):
    """Get inventory insights."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        insights = await dashboard_service.get_inventory_insights(store_id)
        
        return {
            "store_id": store_id,
            "insights": {
                "total_products": insights.total_products,
                "low_stock_items": insights.low_stock_items,
                "overstock_items": insights.overstock_items,
                "out_of_stock_items": insights.out_of_stock_items,
                "inventory_value": insights.inventory_value,
                "turnover_rate": insights.turnover_rate,
                "top_selling_products": insights.top_selling_products,
                "slow_moving_products": insights.slow_moving_products
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Inventory insights retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/sales")
async def get_sales_insights(store_id: Optional[str] = None):
    """Get sales insights."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        insights = await dashboard_service.get_sales_insights(store_id)
        
        return {
            "store_id": store_id,
            "insights": {
                "total_revenue": insights.total_revenue,
                "daily_revenue": insights.daily_revenue,
                "transactions_count": insights.transactions_count,
                "avg_transaction_value": insights.avg_transaction_value,
                "revenue_growth": insights.revenue_growth,
                "top_stores": insights.top_stores,
                "sales_by_hour": insights.sales_by_hour,
                "product_performance": insights.product_performance
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Sales insights retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/alerts")
async def get_alert_summary():
    """Get alert summary."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        summary = await dashboard_service.get_alert_summary()
        
        return {
            "summary": {
                "critical_alerts": summary.critical_alerts,
                "high_alerts": summary.high_alerts,
                "medium_alerts": summary.medium_alerts,
                "total_alerts": summary.total_alerts,
                "recent_alerts": summary.recent_alerts
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Alert summary retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/executive-summary")
async def get_executive_summary():
    """Get executive summary for top-level dashboard."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        summary = await dashboard_service.get_executive_summary()
        
        return summary
        
    except Exception as e:
        logger.error(f"Executive summary retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/drill-down/{metric_name}")
async def get_drill_down_data(
    metric_name: str,
    store_id: Optional[str] = None,
    time_period: int = 30
):
    """Get drill-down data for specific metrics."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        drill_down_data = await dashboard_service.get_drill_down_data(
            metric_name, store_id, time_period
        )
        
        return {
            "metric": metric_name,
            "store_id": store_id,
            "time_period": time_period,
            "data": drill_down_data,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Drill-down data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/summary")
async def get_dashboard_summary(store_id: Optional[str] = None):
    """Get complete dashboard summary."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        # Get all dashboard data in parallel
        kpis, inventory_insights, sales_insights, alert_summary = await asyncio.gather(
            dashboard_service.get_real_time_kpis(),
            dashboard_service.get_inventory_insights(store_id),
            dashboard_service.get_sales_insights(store_id),
            dashboard_service.get_alert_summary()
        )
        
        return DashboardSummary(
            kpis=[
                KPIResponse(
                    name=kpi.name,
                    value=kpi.value,
                    unit=kpi.unit,
                    trend=kpi.trend,
                    trend_percentage=kpi.trend_percentage,
                    target=kpi.target,
                    status=kpi.status,
                    last_updated=kpi.last_updated
                ) for kpi in kpis
            ],
            inventory_insights={
                "total_products": inventory_insights.total_products,
                "low_stock_items": inventory_insights.low_stock_items,
                "overstock_items": inventory_insights.overstock_items,
                "out_of_stock_items": inventory_insights.out_of_stock_items,
                "inventory_value": inventory_insights.inventory_value,
                "turnover_rate": inventory_insights.turnover_rate,
                "top_selling_products": inventory_insights.top_selling_products[:5],
                "slow_moving_products": inventory_insights.slow_moving_products[:5]
            },
            sales_insights={
                "total_revenue": sales_insights.total_revenue,
                "daily_revenue": sales_insights.daily_revenue,
                "transactions_count": sales_insights.transactions_count,
                "avg_transaction_value": sales_insights.avg_transaction_value,
                "revenue_growth": sales_insights.revenue_growth,
                "top_stores": sales_insights.top_stores[:5],
                "sales_by_hour": sales_insights.sales_by_hour,
                "product_performance": sales_insights.product_performance[:5]
            },
            alert_summary={
                "critical_alerts": alert_summary.critical_alerts,
                "high_alerts": alert_summary.high_alerts,
                "medium_alerts": alert_summary.medium_alerts,
                "total_alerts": alert_summary.total_alerts,
                "recent_alerts": alert_summary.recent_alerts[:5]
            },
            last_updated=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Dashboard summary retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/performance")
async def get_performance_metrics():
    """Get dashboard performance and cache metrics."""
    
    try:
        # Get cache hit rates
        cache_stats = {}
        cache_keys = [
            'dashboard:kpis',
            'dashboard:inventory:all',
            'dashboard:sales:all',
            'dashboard:alerts'
        ]
        
        for key in cache_keys:
            exists = redis_client.exists(key)
            ttl = redis_client.ttl(key)
            cache_stats[key] = {
                'exists': bool(exists),
                'ttl': ttl if ttl > 0 else None
            }
        
        # Background worker status
        worker_status = "running" if dashboard_service.refresh_worker_running else "stopped"
        
        return {
            "cache_stats": cache_stats,
            "refresh_worker_status": worker_status,
            "active_websocket_connections": len(manager.active_connections),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/refresh")
async def refresh_dashboard():
    """Manually refresh dashboard cache."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        # Force refresh all cached data
        await dashboard_service.refresh_dashboard_cache()
        
        return {
            "success": True,
            "message": "Dashboard cache refreshed successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/stores")
async def get_store_performance():
    """Get performance comparison across all stores."""
    
    try:
        if not dashboard_service:
            raise HTTPException(status_code=500, detail="Dashboard service not initialized")
        
        # Get list of stores
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT id, name, city, state FROM stores ORDER BY name")
        stores = cursor.fetchall()
        cursor.close()
        db_conn.close()
        
        # Get performance data for each store
        store_performance = []
        
        for store_id, name, city, state in stores:
            try:
                # Get key metrics for this store
                sales_insights = await dashboard_service.get_sales_insights(store_id)
                inventory_insights = await dashboard_service.get_inventory_insights(store_id)
                
                store_performance.append({
                    "store_id": store_id,
                    "name": name,
                    "location": f"{city}, {state}",
                    "revenue_30d": sales_insights.total_revenue,
                    "transactions_30d": sales_insights.transactions_count,
                    "avg_transaction_value": sales_insights.avg_transaction_value,
                    "revenue_growth": sales_insights.revenue_growth,
                    "inventory_value": inventory_insights.inventory_value,
                    "inventory_turnover": inventory_insights.turnover_rate,
                    "out_of_stock_items": inventory_insights.out_of_stock_items
                })
                
            except Exception as e:
                logger.warning(f"Failed to get performance data for store {store_id}: {e}")
                store_performance.append({
                    "store_id": store_id,
                    "name": name,
                    "location": f"{city}, {state}",
                    "error": str(e)
                })
        
        # Sort by revenue
        store_performance.sort(key=lambda x: x.get('revenue_30d', 0), reverse=True)
        
        return {
            "stores": store_performance,
            "total_stores": len(store_performance),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Store performance retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    
    await manager.connect(websocket)
    
    try:
        # Send initial dashboard data
        kpis = await dashboard_service.get_real_time_kpis()
        alert_summary = await dashboard_service.get_alert_summary()
        
        initial_message = {
            "type": "initial_data",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "kpis": [
                    {
                        "name": kpi.name,
                        "value": kpi.value,
                        "unit": kpi.unit,
                        "trend": kpi.trend,
                        "status": kpi.status
                    } for kpi in kpis
                ],
                "alerts": {
                    "total": alert_summary.total_alerts,
                    "critical": alert_summary.critical_alerts,
                    "high": alert_summary.high_alerts
                }
            }
        }
        
        await websocket.send_text(json.dumps(initial_message))
        
        # Keep connection alive
        while True:
            # Wait for client message (ping/pong)
            try:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
            except asyncio.TimeoutError:
                continue
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    print("📊 Starting Dashboard API Server")
    print("🎯 Executive KPIs and operational insights")
    print("📈 Real-time analytics with drill-down capabilities")
    print("🔄 WebSocket support for live updates")
    print("🌐 API available at: http://localhost:8005")
    
    uvicorn.run(app, host="0.0.0.0", port=8005)