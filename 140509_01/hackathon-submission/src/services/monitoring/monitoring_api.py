#!/usr/bin/env python3
"""
Performance Monitoring API Server
FastAPI interface for performance metrics and logging
"""

import sys
import os
sys.path.append('/home/vboxuser/Documents/140509_ai-oh-wip/140509_01/src/services/monitoring')

from fastapi import FastAPI, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import psycopg2
import redis
import asyncio
import logging
import time
from datetime import datetime, timedelta
import uvicorn
import json

from performance_monitor import (
    PerformanceMonitor, MetricType, AlertLevel,
    PerformanceMetric, SystemMetrics, ApplicationMetrics, PerformanceAlert
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RetailAI Performance Monitoring API",
    description="Performance metrics, system monitoring, and application logging",
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

# Security
security = HTTPBearer()

# Global services
monitor = None
redis_client = None

# Pydantic models
class CustomMetricRequest(BaseModel):
    name: str
    value: float
    unit: Optional[str] = ""
    tags: Optional[Dict[str, str]] = None
    metric_type: str = "gauge"

class LogEntryRequest(BaseModel):
    level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

class AlertThresholdRequest(BaseModel):
    metric_name: str
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None

class PerformanceMetricResponse(BaseModel):
    metric_id: str
    name: str
    metric_type: str
    value: float
    unit: str
    tags: Dict[str, str]
    timestamp: datetime
    service: str

class PerformanceAlertResponse(BaseModel):
    alert_id: str
    metric_name: str
    threshold_value: float
    actual_value: float
    level: str
    message: str
    service: str
    timestamp: datetime
    resolved_at: Optional[datetime] = None
    is_active: bool

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Mock user authentication for demo purposes."""
    return "demo_user"

# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Middleware to track API request performance."""
    
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Record request metrics
    if monitor:
        monitor.record_request(
            duration_seconds=duration,
            endpoint=str(request.url.path),
            status_code=response.status_code
        )
    
    # Add performance headers
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    response.headers["X-Service-Instance"] = monitor.instance_id if monitor else "unknown"
    
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize performance monitoring service on startup."""
    global monitor, redis_client
    
    logger.info("🚀 Initializing Performance Monitoring API Server...")
    
    try:
        # Initialize Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # Initialize performance monitor
        db_conn = get_db_connection()
        monitor = PerformanceMonitor(db_conn, redis_client, service_name="monitoring_api")
        
        logger.info("✅ Performance monitoring service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if monitor:
        monitor.stop_monitoring()
        logger.info("Performance monitoring stopped")

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
        
        # Get current metrics
        current_metrics = monitor.get_current_metrics() if monitor else {}
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "redis": "connected",
            "monitoring": "active" if monitor and monitor.monitoring_active else "inactive",
            "metrics": current_metrics
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/metrics/current")
async def get_current_metrics(user_id: str = Depends(get_current_user)):
    """Get current real-time metrics."""
    
    try:
        if not monitor:
            raise HTTPException(status_code=500, detail="Performance monitor not initialized")
        
        metrics = monitor.get_current_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get current metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/metrics/summary")
async def get_performance_summary(
    hours: int = 24,
    user_id: str = Depends(get_current_user)
):
    """Get performance summary for specified time period."""
    
    try:
        if not monitor:
            raise HTTPException(status_code=500, detail="Performance monitor not initialized")
        
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
        
        summary = monitor.get_performance_summary(hours=hours)
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitoring/metrics/custom")
async def record_custom_metric(
    metric: CustomMetricRequest,
    user_id: str = Depends(get_current_user)
):
    """Record custom metric."""
    
    try:
        if not monitor:
            raise HTTPException(status_code=500, detail="Performance monitor not initialized")
        
        # Validate metric type
        try:
            metric_type = MetricType(metric.metric_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid metric type: {metric.metric_type}")
        
        monitor.record_custom_metric(
            name=metric.name,
            value=metric.value,
            unit=metric.unit,
            tags=metric.tags,
            metric_type=metric_type
        )
        
        return {
            "success": True,
            "message": "Custom metric recorded successfully",
            "metric_name": metric.name,
            "value": metric.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record custom metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/metrics/history")
async def get_metrics_history(
    metric_name: Optional[str] = None,
    hours: int = 24,
    limit: int = 1000,
    user_id: str = Depends(get_current_user)
) -> List[PerformanceMetricResponse]:
    """Get metrics history."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Build query
        where_conditions = ["timestamp >= %s"]
        params = [start_time]
        
        if metric_name:
            where_conditions.append("name = %s")
            params.append(metric_name)
        
        where_clause = " AND ".join(where_conditions)
        params.append(limit)
        
        query = f"""
            SELECT metric_id, name, metric_type, value, unit, tags, timestamp, service
            FROM performance_metrics
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        cursor.execute(query, params)
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append(PerformanceMetricResponse(
                metric_id=row[0],
                name=row[1],
                metric_type=row[2],
                value=float(row[3]),
                unit=row[4] or "",
                tags=row[5] if row[5] else {},
                timestamp=row[6],
                service=row[7]
            ))
        
        cursor.close()
        db_conn.close()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/alerts/active")
async def get_active_alerts(
    user_id: str = Depends(get_current_user)
) -> List[PerformanceAlertResponse]:
    """Get active performance alerts."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT alert_id, metric_name, threshold_value, actual_value, level,
                   message, service, timestamp, resolved_at, is_active
            FROM performance_alerts
            WHERE is_active = TRUE
            ORDER BY level DESC, timestamp DESC
        """)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append(PerformanceAlertResponse(
                alert_id=row[0],
                metric_name=row[1],
                threshold_value=float(row[2]) if row[2] else 0,
                actual_value=float(row[3]) if row[3] else 0,
                level=row[4],
                message=row[5],
                service=row[6],
                timestamp=row[7],
                resolved_at=row[8],
                is_active=row[9]
            ))
        
        cursor.close()
        db_conn.close()
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/alerts/history")
async def get_alerts_history(
    hours: int = 168,  # 1 week default
    limit: int = 100,
    user_id: str = Depends(get_current_user)
) -> List[PerformanceAlertResponse]:
    """Get alerts history."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT alert_id, metric_name, threshold_value, actual_value, level,
                   message, service, timestamp, resolved_at, is_active
            FROM performance_alerts
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (start_time, limit))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append(PerformanceAlertResponse(
                alert_id=row[0],
                metric_name=row[1],
                threshold_value=float(row[2]) if row[2] else 0,
                actual_value=float(row[3]) if row[3] else 0,
                level=row[4],
                message=row[5],
                service=row[6],
                timestamp=row[7],
                resolved_at=row[8],
                is_active=row[9]
            ))
        
        cursor.close()
        db_conn.close()
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to get alerts history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitoring/alerts/thresholds")
async def update_alert_thresholds(
    threshold: AlertThresholdRequest,
    user_id: str = Depends(get_current_user)
):
    """Update alert thresholds for a metric."""
    
    try:
        if not monitor:
            raise HTTPException(status_code=500, detail="Performance monitor not initialized")
        
        # Update thresholds in monitor
        if threshold.metric_name not in monitor.thresholds:
            monitor.thresholds[threshold.metric_name] = {}
        
        if threshold.warning_threshold is not None:
            monitor.thresholds[threshold.metric_name]['warning'] = threshold.warning_threshold
        
        if threshold.critical_threshold is not None:
            monitor.thresholds[threshold.metric_name]['critical'] = threshold.critical_threshold
        
        return {
            "success": True,
            "message": "Alert thresholds updated successfully",
            "metric_name": threshold.metric_name,
            "thresholds": monitor.thresholds[threshold.metric_name]
        }
        
    except Exception as e:
        logger.error(f"Failed to update alert thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/alerts/thresholds")
async def get_alert_thresholds(
    user_id: str = Depends(get_current_user)
):
    """Get current alert thresholds."""
    
    try:
        if not monitor:
            raise HTTPException(status_code=500, detail="Performance monitor not initialized")
        
        return {
            "thresholds": monitor.thresholds,
            "available_metrics": list(monitor.thresholds.keys())
        }
        
    except Exception as e:
        logger.error(f"Failed to get alert thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitoring/logs")
async def create_log_entry(
    log_entry: LogEntryRequest,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """Create centralized log entry."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            INSERT INTO log_entries 
            (level, message, metadata, trace_id, span_id, service, instance_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            log_entry.level.upper(),
            log_entry.message,
            json.dumps(log_entry.metadata or {}),
            log_entry.trace_id,
            log_entry.span_id,
            "api_client",
            request.client.host if request.client else "unknown"
        ))
        
        db_conn.commit()
        cursor.close()
        db_conn.close()
        
        return {
            "success": True,
            "message": "Log entry created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create log entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/logs")
async def get_logs(
    level: Optional[str] = None,
    service: Optional[str] = None,
    hours: int = 24,
    limit: int = 1000,
    user_id: str = Depends(get_current_user)
):
    """Get centralized logs."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Build query
        where_conditions = ["timestamp >= %s"]
        params = [start_time]
        
        if level:
            where_conditions.append("level = %s")
            params.append(level.upper())
        
        if service:
            where_conditions.append("service = %s")
            params.append(service)
        
        where_clause = " AND ".join(where_conditions)
        params.append(limit)
        
        query = f"""
            SELECT level, message, logger_name, service, instance_id, 
                   timestamp, metadata, trace_id, span_id
            FROM log_entries
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        cursor.execute(query, params)
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                "level": row[0],
                "message": row[1],
                "logger_name": row[2],
                "service": row[3],
                "instance_id": row[4],
                "timestamp": row[5].isoformat(),
                "metadata": row[6] if row[6] else {},
                "trace_id": row[7],
                "span_id": row[8]
            })
        
        cursor.close()
        db_conn.close()
        
        return {
            "logs": logs,
            "total": len(logs),
            "period_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/system")
async def get_system_metrics(
    hours: int = 1,
    user_id: str = Depends(get_current_user)
):
    """Get system metrics history."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT cpu_percent, memory_percent, disk_usage_percent,
                   memory_used_mb, disk_free_gb, processes_count, timestamp
            FROM system_metrics
            WHERE timestamp >= %s AND service = %s
            ORDER BY timestamp DESC
            LIMIT 100
        """, (start_time, monitor.service_name if monitor else "unknown"))
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                "cpu_percent": float(row[0]) if row[0] else 0,
                "memory_percent": float(row[1]) if row[1] else 0,
                "disk_usage_percent": float(row[2]) if row[2] else 0,
                "memory_used_mb": float(row[3]) if row[3] else 0,
                "disk_free_gb": float(row[4]) if row[4] else 0,
                "processes_count": row[5] if row[5] else 0,
                "timestamp": row[6].isoformat()
            })
        
        cursor.close()
        db_conn.close()
        
        return {
            "metrics": metrics,
            "period_hours": hours,
            "total_points": len(metrics)
        }
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/application")
async def get_application_metrics(
    hours: int = 1,
    user_id: str = Depends(get_current_user)
):
    """Get application metrics history."""
    
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT requests_per_second, avg_response_time_ms, error_rate_percent,
                   database_connections, cache_hit_rate, memory_usage_mb, timestamp
            FROM application_metrics
            WHERE timestamp >= %s AND service = %s
            ORDER BY timestamp DESC
            LIMIT 100
        """, (start_time, monitor.service_name if monitor else "unknown"))
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                "requests_per_second": float(row[0]) if row[0] else 0,
                "avg_response_time_ms": float(row[1]) if row[1] else 0,
                "error_rate_percent": float(row[2]) if row[2] else 0,
                "database_connections": row[3] if row[3] else 0,
                "cache_hit_rate": float(row[4]) if row[4] else 0,
                "memory_usage_mb": float(row[5]) if row[5] else 0,
                "timestamp": row[6].isoformat()
            })
        
        cursor.close()
        db_conn.close()
        
        return {
            "metrics": metrics,
            "period_hours": hours,
            "total_points": len(metrics)
        }
        
    except Exception as e:
        logger.error(f"Failed to get application metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/dashboard")
async def get_monitoring_dashboard(
    user_id: str = Depends(get_current_user)
):
    """Get comprehensive monitoring dashboard data."""
    
    try:
        if not monitor:
            raise HTTPException(status_code=500, detail="Performance monitor not initialized")
        
        # Get current metrics
        current_metrics = monitor.get_current_metrics()
        
        # Get performance summary
        summary_24h = monitor.get_performance_summary(hours=24)
        
        # Get active alerts
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT level, COUNT(*) as count
            FROM performance_alerts
            WHERE is_active = TRUE
            GROUP BY level
        """)
        
        alert_counts = dict(cursor.fetchall())
        
        # Get recent system metrics
        cursor.execute("""
            SELECT cpu_percent, memory_percent, disk_usage_percent, timestamp
            FROM system_metrics
            WHERE service = %s
            ORDER BY timestamp DESC
            LIMIT 10
        """, (monitor.service_name,))
        
        recent_system = [
            {
                "cpu": float(row[0]) if row[0] else 0,
                "memory": float(row[1]) if row[1] else 0,
                "disk": float(row[2]) if row[2] else 0,
                "timestamp": row[3].isoformat()
            }
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        db_conn.close()
        
        return {
            "current_metrics": current_metrics,
            "performance_summary_24h": summary_24h,
            "alert_counts": alert_counts,
            "recent_system_metrics": recent_system,
            "service_info": {
                "name": monitor.service_name,
                "instance_id": monitor.instance_id,
                "monitoring_active": monitor.monitoring_active,
                "buffer_size": len(monitor.metrics_buffer)
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🔍 Starting Performance Monitoring API Server")
    print("📊 System and application metrics collection")
    print("🚨 Real-time performance alerts")
    print("📝 Centralized logging and tracing")
    print("🌐 API available at: http://localhost:8007")
    
    uvicorn.run(app, host="0.0.0.0", port=8007)