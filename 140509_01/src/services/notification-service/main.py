"""
Notification Service - AI-Powered Retail Inventory Optimization
Real-time alerting and automated reordering system.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import asyncio
import json
from enum import Enum

from .models import (
    Alert, AlertRule, NotificationChannel, AutoReorderRule,
    AlertSeverity, AlertStatus, NotificationRequest, AlertResponse
)
from .services.alert_engine import AlertEngine
from .services.notification_dispatcher import NotificationDispatcher
from .services.auto_reorder_service import AutoReorderService
from .services.email_service import EmailService
from .services.sms_service import SMSService
from .services.webhook_service import WebhookService
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Notification Service",
    description="Real-time alerting and automated reordering system",
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
alert_engine = AlertEngine()
notification_dispatcher = NotificationDispatcher()
auto_reorder_service = AutoReorderService()
email_service = EmailService()
sms_service = SMSService()
webhook_service = WebhookService()

@app.on_event("startup")
async def startup_event():
    """Initialize notification services on startup."""
    try:
        logger.info("Initializing Notification Service...")
        
        await alert_engine.initialize()
        await notification_dispatcher.initialize()
        await auto_reorder_service.initialize()
        
        # Start background monitoring tasks
        asyncio.create_task(alert_engine.monitor_inventory_levels())
        asyncio.create_task(alert_engine.monitor_forecast_accuracy())
        asyncio.create_task(auto_reorder_service.process_auto_reorders())
        
        logger.info("Notification Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Notification Service: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "notification-service",
        "version": "1.0.0",
        "active_alerts": await alert_engine.get_active_alert_count(),
        "pending_notifications": await notification_dispatcher.get_queue_size()
    }

@app.post("/api/v1/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: Dict,
    background_tasks: BackgroundTasks
):
    """Create a new alert."""
    try:
        alert = Alert(
            id=f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            alert_type=alert_data.get("alert_type"),
            severity=AlertSeverity(alert_data.get("severity", "medium")),
            title=alert_data.get("title"),
            message=alert_data.get("message"),
            product_id=alert_data.get("product_id"),
            store_id=alert_data.get("store_id"),
            data=alert_data.get("data", {}),
            created_at=datetime.utcnow(),
            status=AlertStatus.ACTIVE
        )
        
        # Save alert
        await alert_engine.save_alert(alert)
        
        # Dispatch notifications in background
        background_tasks.add_task(
            notification_dispatcher.dispatch_alert,
            alert
        )
        
        return AlertResponse(
            id=alert.id,
            status="created",
            message="Alert created and notifications dispatched"
        )
        
    except Exception as e:
        logger.error(f"Create alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/alerts", response_model=List[Alert])
async def get_alerts(
    severity: Optional[AlertSeverity] = None,
    alert_type: Optional[str] = None,
    status: Optional[AlertStatus] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get alerts with optional filtering."""
    try:
        alerts = await alert_engine.get_alerts(
            severity=severity,
            alert_type=alert_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return alerts
        
    except Exception as e:
        logger.error(f"Get alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get specific alert details."""
    try:
        alert = await alert_engine.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str,
    notes: Optional[str] = None
):
    """Acknowledge an alert."""
    try:
        result = await alert_engine.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=acknowledged_by,
            notes=notes
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Acknowledge alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolved_by: str,
    resolution_notes: Optional[str] = None
):
    """Resolve an alert."""
    try:
        result = await alert_engine.resolve_alert(
            alert_id=alert_id,
            resolved_by=resolved_by,
            resolution_notes=resolution_notes
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Resolve alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/alert-rules")
async def create_alert_rule(rule: AlertRule):
    """Create a new alert rule."""
    try:
        rule_id = await alert_engine.create_alert_rule(rule)
        return {
            "id": rule_id,
            "status": "created",
            "message": "Alert rule created successfully"
        }
        
    except Exception as e:
        logger.error(f"Create alert rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/alert-rules")
async def get_alert_rules():
    """Get all alert rules."""
    try:
        rules = await alert_engine.get_alert_rules()
        return rules
        
    except Exception as e:
        logger.error(f"Get alert rules failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/alert-rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule: AlertRule):
    """Update an alert rule."""
    try:
        result = await alert_engine.update_alert_rule(rule_id, rule)
        return result
        
    except Exception as e:
        logger.error(f"Update alert rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule."""
    try:
        result = await alert_engine.delete_alert_rule(rule_id)
        return result
        
    except Exception as e:
        logger.error(f"Delete alert rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/notifications/send")
async def send_notification(
    notification: NotificationRequest,
    background_tasks: BackgroundTasks
):
    """Send a notification through specified channels."""
    try:
        background_tasks.add_task(
            notification_dispatcher.send_notification,
            notification
        )
        
        return {
            "status": "queued",
            "message": "Notification queued for delivery",
            "channels": notification.channels
        }
        
    except Exception as e:
        logger.error(f"Send notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/notifications/channels")
async def get_notification_channels():
    """Get available notification channels."""
    try:
        channels = await notification_dispatcher.get_available_channels()
        return channels
        
    except Exception as e:
        logger.error(f"Get notification channels failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auto-reorder/rules")
async def create_auto_reorder_rule(rule: AutoReorderRule):
    """Create an automated reorder rule."""
    try:
        rule_id = await auto_reorder_service.create_rule(rule)
        return {
            "id": rule_id,
            "status": "created",
            "message": "Auto-reorder rule created successfully"
        }
        
    except Exception as e:
        logger.error(f"Create auto-reorder rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/auto-reorder/rules")
async def get_auto_reorder_rules():
    """Get all auto-reorder rules."""
    try:
        rules = await auto_reorder_service.get_rules()
        return rules
        
    except Exception as e:
        logger.error(f"Get auto-reorder rules failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/auto-reorder/history")
async def get_auto_reorder_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Get auto-reorder execution history."""
    try:
        history = await auto_reorder_service.get_history(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return history
        
    except Exception as e:
        logger.error(f"Get auto-reorder history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auto-reorder/test/{rule_id}")
async def test_auto_reorder_rule(rule_id: str):
    """Test an auto-reorder rule without executing."""
    try:
        result = await auto_reorder_service.test_rule(rule_id)
        return result
        
    except Exception as e:
        logger.error(f"Test auto-reorder rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/webhooks/register")
async def register_webhook(
    url: str,
    events: List[str],
    secret_token: Optional[str] = None
):
    """Register a webhook endpoint for notifications."""
    try:
        webhook_id = await webhook_service.register_webhook(
            url=url,
            events=events,
            secret_token=secret_token
        )
        
        return {
            "id": webhook_id,
            "status": "registered",
            "message": "Webhook registered successfully"
        }
        
    except Exception as e:
        logger.error(f"Register webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/webhooks")
async def get_webhooks():
    """Get all registered webhooks."""
    try:
        webhooks = await webhook_service.get_webhooks()
        return webhooks
        
    except Exception as e:
        logger.error(f"Get webhooks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a registered webhook."""
    try:
        result = await webhook_service.delete_webhook(webhook_id)
        return result
        
    except Exception as e:
        logger.error(f"Delete webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/alert-metrics")
async def get_alert_metrics(
    days_back: int = 30
):
    """Get alert analytics and metrics."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        metrics = await alert_engine.get_alert_metrics(start_date)
        
        return {
            "period": f"Last {days_back} days",
            "metrics": metrics,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Get alert metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/notification-metrics")
async def get_notification_metrics(
    days_back: int = 30
):
    """Get notification delivery metrics."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        metrics = await notification_dispatcher.get_delivery_metrics(start_date)
        
        return {
            "period": f"Last {days_back} days",
            "metrics": metrics,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Get notification metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/maintenance/process-pending")
async def process_pending_notifications(
    background_tasks: BackgroundTasks
):
    """Process pending notifications (maintenance endpoint)."""
    try:
        background_tasks.add_task(
            notification_dispatcher.process_pending_notifications
        )
        
        return {
            "status": "started",
            "message": "Processing pending notifications"
        }
        
    except Exception as e:
        logger.error(f"Process pending notifications failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/maintenance/cleanup-old-alerts")
async def cleanup_old_alerts(
    days_to_keep: int = 90,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Clean up old resolved alerts."""
    try:
        background_tasks.add_task(
            alert_engine.cleanup_old_alerts,
            days_to_keep
        )
        
        return {
            "status": "started",
            "message": f"Cleaning up alerts older than {days_to_keep} days"
        }
        
    except Exception as e:
        logger.error(f"Cleanup old alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )