#!/usr/bin/env python3
"""
RetailAI Platform - Alert Engine API Server
FastAPI implementation for the alert system
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import uuid
from enum import Enum
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Alert Engine API",
    description="Business rule-based alerting system for retail operations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    LOW_STOCK = "LOW_STOCK"
    HIGH_DEMAND = "HIGH_DEMAND"
    FORECAST_DEVIATION = "FORECAST_DEVIATION"
    SYSTEM_PERFORMANCE = "SYSTEM_PERFORMANCE"
    INVENTORY_TURNOVER = "INVENTORY_TURNOVER"

class Alert(BaseModel):
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    product_id: Optional[str] = None
    store_id: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    created_at: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    metadata: Dict[str, Any] = {}

class AlertRule(BaseModel):
    rule_id: str
    name: str
    description: Optional[str] = None
    alert_type: AlertType
    severity: AlertSeverity
    conditions: Dict[str, Any]
    notification_channels: List[str] = []
    enabled: bool = True
    created_at: str

class CreateAlertRuleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]
    severity: AlertSeverity
    notification_channels: List[str] = ["email"]

class AcknowledgeAlertRequest(BaseModel):
    acknowledged_by: str
    notes: Optional[str] = None

# In-memory storage
active_alerts: Dict[str, Alert] = {}
alert_rules: Dict[str, AlertRule] = {}
alert_history: List[Alert] = []

def generate_sample_alerts():
    """Generate sample alerts for demo."""
    sample_alerts = [
        Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.HIGH,
            title="Critical Low Stock Alert",
            message="Product PROD_001 at STORE_001 is critically low (2 units remaining)",
            product_id="PROD_001",
            store_id="STORE_001", 
            current_value=2.0,
            threshold_value=15.0,
            created_at=datetime.now().isoformat(),
            metadata={
                "product_name": "Premium Coffee Beans",
                "store_name": "Downtown Store",
                "category": "Beverages"
            }
        ),
        Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.HIGH_DEMAND,
            severity=AlertSeverity.MEDIUM,
            title="Demand Spike Alert", 
            message="Product PROD_007 demand is 180% above forecast",
            product_id="PROD_007",
            store_id="STORE_002",
            current_value=180.0,
            threshold_value=150.0,
            created_at=datetime.now().isoformat(),
            metadata={
                "product_name": "Energy Bars",
                "forecast_demand": 25,
                "actual_demand": 45
            }
        ),
        Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.SYSTEM_PERFORMANCE,
            severity=AlertSeverity.HIGH,
            title="System Performance Alert",
            message="ML Engine API response time exceeding threshold",
            current_value=2800.0,
            threshold_value=2000.0,
            created_at=datetime.now().isoformat(),
            metadata={
                "service": "ML Engine",
                "avg_response_time_ms": 2800,
                "cpu_usage": 85.2
            }
        )
    ]
    
    for alert in sample_alerts:
        active_alerts[alert.alert_id] = alert

def generate_sample_rules():
    """Generate sample alert rules."""
    sample_rules = [
        AlertRule(
            rule_id=str(uuid.uuid4()),
            name="Critical Stock Level",
            description="Alert when stock falls below safety threshold",
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.HIGH,
            conditions={"metric": "stock_level", "operator": "less_than", "threshold": 10},
            notification_channels=["email", "slack"],
            created_at=datetime.now().isoformat()
        ),
        AlertRule(
            rule_id=str(uuid.uuid4()),
            name="Demand Forecast Deviation",
            description="Alert when demand deviates significantly from forecast",
            alert_type=AlertType.FORECAST_DEVIATION,
            severity=AlertSeverity.MEDIUM,
            conditions={"metric": "demand_deviation", "operator": "greater_than", "threshold": 150.0},
            notification_channels=["email"],
            created_at=datetime.now().isoformat()
        )
    ]
    
    for rule in sample_rules:
        alert_rules[rule.rule_id] = rule

@app.on_event("startup")
async def startup_event():
    """Initialize sample data."""
    logger.info("🚀 Starting RetailAI Alert Engine API...")
    generate_sample_alerts()
    generate_sample_rules()
    logger.info(f"✅ Alert Engine initialized with {len(active_alerts)} active alerts")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "alert_engine", 
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "active_alerts": len(active_alerts)
    }

@app.get("/api/alerts/active")
async def get_active_alerts(severity: Optional[AlertSeverity] = None, limit: int = 50):
    """Get active alerts."""
    alerts = list(active_alerts.values())
    
    if severity:
        alerts = [alert for alert in alerts if alert.severity == severity]
    
    alerts = [alert for alert in alerts if not alert.resolved]
    
    # Sort by severity
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    alerts.sort(key=lambda x: severity_order.get(x.severity.value, 0), reverse=True)
    
    alerts = alerts[:limit]
    
    return {
        "alerts": [alert.dict() for alert in alerts],
        "total_count": len(alerts)
    }

@app.post("/api/alerts/rules")
async def create_alert_rule(rule_request: CreateAlertRuleRequest):
    """Create new alert rule."""
    rule_id = str(uuid.uuid4())
    
    rule = AlertRule(
        rule_id=rule_id,
        name=rule_request.name,
        description=rule_request.description,
        alert_type=AlertType.HIGH_DEMAND,
        severity=rule_request.severity,
        conditions=rule_request.conditions,
        notification_channels=rule_request.notification_channels,
        created_at=datetime.now().isoformat()
    )
    
    alert_rules[rule_id] = rule
    
    return {
        "message": "Alert rule created successfully",
        "rule_id": rule_id,
        "rule": rule.dict()
    }

@app.get("/api/alerts/rules")
async def get_alert_rules():
    """Get all alert rules."""
    return {
        "rules": [rule.dict() for rule in alert_rules.values()],
        "total_count": len(alert_rules)
    }

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, request: AcknowledgeAlertRequest):
    """Acknowledge an alert."""
    if alert_id not in active_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = active_alerts[alert_id]
    alert.acknowledged = True
    alert.acknowledged_by = request.acknowledged_by
    
    return {
        "message": "Alert acknowledged successfully",
        "alert_id": alert_id,
        "acknowledged_by": request.acknowledged_by
    }

@app.get("/api/alerts/analytics")
async def get_alert_analytics():
    """Get alert analytics."""
    all_alerts = list(active_alerts.values()) + alert_history
    
    total_alerts = len(all_alerts)
    active_count = len([a for a in all_alerts if not a.resolved])
    resolved_count = len([a for a in all_alerts if a.resolved])
    acknowledged_count = len([a for a in all_alerts if a.acknowledged])
    
    severity_counts = {}
    for severity in AlertSeverity:
        severity_counts[severity.value] = len([a for a in all_alerts if a.severity == severity])
    
    type_counts = {}
    for alert_type in AlertType:
        type_counts[alert_type.value] = len([a for a in all_alerts if a.alert_type == alert_type])
    
    return {
        "summary": {
            "total_alerts": total_alerts,
            "active_alerts": active_count,
            "resolved_alerts": resolved_count,
            "acknowledged_alerts": acknowledged_count,
            "acknowledgement_rate": (acknowledged_count / total_alerts * 100) if total_alerts > 0 else 0
        },
        "severity_breakdown": severity_counts,
        "type_breakdown": type_counts,
        "top_products_with_alerts": [
            {"product_id": "PROD_001", "alert_count": 3},
            {"product_id": "PROD_007", "alert_count": 2}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting RetailAI Alert Engine API Server on port 8003...")
    uvicorn.run(app, host="0.0.0.0", port=8003)