#!/usr/bin/env python3
"""
Operations Management Service - Port 8007
Real-time operations monitoring and workforce management
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import random
import logging
import uvicorn
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Operations Management",
    description="Real-time operations monitoring and workforce management for 140509_01",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORES = [
    {"id": "STORE_001", "name": "Manhattan", "city": "New York", "employees": 24},
    {"id": "STORE_002", "name": "Beverly Hills", "city": "Los Angeles", "employees": 22},
    {"id": "STORE_003", "name": "Downtown", "city": "Chicago", "employees": 20},
    {"id": "STORE_004", "name": "Galleria", "city": "Houston", "employees": 18},
    {"id": "STORE_005", "name": "Scottsdale", "city": "Phoenix", "employees": 16}
]

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "operations-management",
        "version": "2.0.0",
        "project": "140509_01",
        "timestamp": datetime.now().isoformat(),
        "port": 8007
    }

@app.get("/api/operations/overview")
async def get_operations_overview():
    """Get comprehensive operations overview"""
    
    # Generate real-time operational metrics
    total_employees = sum(store["employees"] for store in STORES)
    current_hour = datetime.now().hour
    
    # Simulate shift patterns
    if 9 <= current_hour <= 17:  # Business hours
        employees_on_duty = int(total_employees * 0.75)
        customer_traffic = random.randint(450, 680)
    elif 18 <= current_hour <= 21:  # Evening
        employees_on_duty = int(total_employees * 0.60)
        customer_traffic = random.randint(320, 520)
    else:  # Off hours
        employees_on_duty = int(total_employees * 0.25)
        customer_traffic = random.randint(80, 180)
    
    operations_data = {
        "workforce": {
            "total_employees": total_employees,
            "employees_on_duty": employees_on_duty,
            "attendance_rate": round(random.uniform(92, 98), 1),
            "productivity_score": round(random.uniform(85, 95), 1),
            "overtime_hours": random.randint(45, 120)
        },
        "customer_service": {
            "current_customer_count": customer_traffic,
            "avg_wait_time": random.randint(2, 8),
            "service_satisfaction": round(random.uniform(4.1, 4.7), 1),
            "queue_length": random.randint(0, 15),
            "peak_hour_efficiency": round(random.uniform(78, 92), 1)
        },
        "facility_status": {
            "stores_operational": len(STORES),
            "maintenance_alerts": random.randint(1, 5),
            "energy_efficiency": round(random.uniform(82, 94), 1),
            "security_status": "All Clear",
            "hvac_status": "Optimal"
        }
    }
    
    return {
        "operations_overview": operations_data,
        "performance_metrics": {
            "operational_efficiency": round(random.uniform(88, 94), 1),
            "cost_per_transaction": round(random.uniform(2.50, 4.20), 2),
            "staff_utilization": round((employees_on_duty / total_employees) * 100, 1),
            "customer_to_staff_ratio": round(customer_traffic / max(1, employees_on_duty), 1)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "operations-service:8007"
    }

@app.get("/api/operations/workforce")
async def get_workforce_analytics():
    """Get detailed workforce management analytics"""
    
    workforce_data = []
    for store in STORES:
        # Generate shift data
        shifts = ["Morning", "Afternoon", "Evening", "Night"]
        shift_data = {}
        
        for shift in shifts:
            if shift == "Morning":
                staff_count = int(store["employees"] * 0.35)
            elif shift == "Afternoon":
                staff_count = int(store["employees"] * 0.40)
            elif shift == "Evening":
                staff_count = int(store["employees"] * 0.25)
            else:  # Night
                staff_count = max(2, int(store["employees"] * 0.15))
            
            shift_data[shift.lower()] = {
                "scheduled": staff_count,
                "present": staff_count - random.randint(0, 2),
                "productivity": round(random.uniform(78, 95), 1)
            }
        
        workforce_data.append({
            "store_id": store["id"],
            "store_name": store["name"],
            "total_employees": store["employees"],
            "shifts": shift_data,
            "weekly_hours": store["employees"] * random.randint(35, 42),
            "labor_cost": round(store["employees"] * random.uniform(2800, 3500), 2),
            "turnover_rate": round(random.uniform(12, 28), 1),
            "training_completion": round(random.uniform(78, 95), 1)
        })
    
    # Calculate summary metrics
    total_weekly_hours = sum(store["weekly_hours"] for store in workforce_data)
    total_labor_cost = sum(store["labor_cost"] for store in workforce_data)
    avg_turnover = sum(store["turnover_rate"] for store in workforce_data) / len(workforce_data)
    
    return {
        "workforce_analytics": workforce_data,
        "workforce_summary": {
            "total_weekly_hours": total_weekly_hours,
            "total_monthly_labor_cost": round(total_labor_cost * 4.33, 2),
            "average_turnover_rate": round(avg_turnover, 1),
            "staff_satisfaction": round(random.uniform(3.8, 4.5), 1),
            "training_budget_utilization": round(random.uniform(78, 92), 1)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "operations-service:8007"
    }

@app.get("/api/operations/performance")
async def get_performance_metrics():
    """Get detailed operational performance metrics"""
    
    performance_data = []
    for store in STORES:
        # Generate performance metrics
        daily_transactions = random.randint(180, 420)
        avg_transaction_time = round(random.uniform(3.2, 6.8), 1)
        
        performance_data.append({
            "store_id": store["id"],
            "store_name": store["name"],
            "daily_transactions": daily_transactions,
            "avg_transaction_time": avg_transaction_time,
            "customer_satisfaction": round(random.uniform(3.9, 4.8), 1),
            "sales_per_sqft": round(random.uniform(320, 580), 2),
            "inventory_accuracy": round(random.uniform(94, 99), 1),
            "shrinkage_rate": round(random.uniform(0.8, 2.1), 1),
            "energy_usage": random.randint(2800, 4200),
            "maintenance_score": round(random.uniform(85, 96), 1)
        })
    
    # Calculate benchmarks
    avg_satisfaction = sum(store["customer_satisfaction"] for store in performance_data) / len(performance_data)
    total_transactions = sum(store["daily_transactions"] for store in performance_data)
    avg_sales_per_sqft = sum(store["sales_per_sqft"] for store in performance_data) / len(performance_data)
    
    return {
        "store_performance": performance_data,
        "benchmarks": {
            "avg_customer_satisfaction": round(avg_satisfaction, 1),
            "total_daily_transactions": total_transactions,
            "avg_sales_per_sqft": round(avg_sales_per_sqft, 2),
            "best_performing_store": max(performance_data, key=lambda x: x["customer_satisfaction"])["store_name"],
            "efficiency_leader": min(performance_data, key=lambda x: x["avg_transaction_time"])["store_name"]
        },
        "generated_at": datetime.now().isoformat(),
        "source": "operations-service:8007"
    }

@app.get("/api/operations/alerts")
async def get_operational_alerts():
    """Get current operational alerts and issues"""
    
    alert_types = ["Staffing", "Equipment", "Security", "Customer Service", "Inventory"]
    priorities = ["High", "Medium", "Low"]
    
    alerts = []
    for i in range(random.randint(3, 8)):
        store = random.choice(STORES)
        alert_type = random.choice(alert_types)
        priority = random.choice(priorities)
        
        # Generate contextual alert messages
        if alert_type == "Staffing":
            message = f"Staff shortage in {store['name']} - {random.randint(2, 4)} employees called in sick"
        elif alert_type == "Equipment":
            message = f"POS system intermittent issues at {store['name']} - affecting checkout speed"
        elif alert_type == "Security":
            message = f"Security camera malfunction in {store['name']} - Zone 3 monitoring offline"
        elif alert_type == "Customer Service":
            message = f"Queue length exceeding 10 customers at {store['name']} - additional support needed"
        else:  # Inventory
            message = f"Low stock alert for 3 popular items at {store['name']} - restock required"
        
        alerts.append({
            "alert_id": f"OPS_{alert_type[:3].upper()}_{datetime.now().strftime('%m%d')}{i:02d}",
            "type": alert_type,
            "priority": priority,
            "store_id": store["id"],
            "store_name": store["name"],
            "message": message,
            "created_at": (datetime.now() - timedelta(minutes=random.randint(10, 480))).isoformat(),
            "status": random.choice(["Active", "In Progress", "Resolved"]),
            "estimated_resolution": f"{random.randint(15, 120)} minutes"
        })
    
    # Filter and prioritize
    active_alerts = [alert for alert in alerts if alert["status"] == "Active"]
    high_priority = [alert for alert in active_alerts if alert["priority"] == "High"]
    
    return {
        "operational_alerts": alerts,
        "alert_summary": {
            "total_alerts": len(alerts),
            "active_alerts": len(active_alerts),
            "high_priority_alerts": len(high_priority),
            "avg_resolution_time": f"{random.randint(25, 95)} minutes",
            "most_common_type": max(set(alert["type"] for alert in alerts), 
                                  key=lambda x: sum(1 for alert in alerts if alert["type"] == x))
        },
        "generated_at": datetime.now().isoformat(),
        "source": "operations-service:8007"
    }

@app.get("/api/operations/efficiency")
async def get_efficiency_analysis():
    """Get operational efficiency analysis and recommendations"""
    
    efficiency_metrics = {
        "labor_efficiency": {
            "current_score": round(random.uniform(82, 94), 1),
            "benchmark": 88.0,
            "trend": random.choice(["Improving", "Stable", "Declining"]),
            "optimization_potential": round(random.uniform(5, 15), 1)
        },
        "process_efficiency": {
            "checkout_speed": round(random.uniform(3.2, 4.8), 1),
            "inventory_turnover": round(random.uniform(6.2, 8.9), 1),
            "customer_flow": round(random.uniform(78, 92), 1),
            "digital_adoption": round(random.uniform(65, 85), 1)
        },
        "resource_utilization": {
            "space_utilization": round(random.uniform(72, 88), 1),
            "equipment_uptime": round(random.uniform(94, 98), 1),
            "staff_productivity": round(random.uniform(85, 95), 1),
            "energy_efficiency": round(random.uniform(78, 92), 1)
        }
    }
    
    recommendations = [
        {
            "area": "Labor Optimization",
            "recommendation": "Implement dynamic scheduling based on customer traffic patterns",
            "potential_improvement": "12% reduction in labor costs",
            "implementation_effort": "Medium",
            "timeline": "2-3 months"
        },
        {
            "area": "Process Automation",
            "recommendation": "Deploy self-checkout kiosks during peak hours",
            "potential_improvement": "25% improvement in checkout speed",
            "implementation_effort": "High",
            "timeline": "4-6 months"
        },
        {
            "area": "Space Optimization",
            "recommendation": "Redesign store layout based on customer flow analysis",
            "potential_improvement": "18% increase in sales per square foot",
            "implementation_effort": "High",
            "timeline": "3-4 months"
        }
    ]
    
    return {
        "efficiency_analysis": efficiency_metrics,
        "optimization_opportunities": {
            "recommendations": recommendations,
            "total_cost_savings_potential": random.randint(180000, 350000),
            "revenue_increase_potential": random.randint(220000, 420000),
            "payback_period": "8-14 months"
        },
        "generated_at": datetime.now().isoformat(),
        "source": "operations-service:8007"
    }

if __name__ == "__main__":
    logger.info("⚙️ Starting Operations Management Service on port 8007...")
    uvicorn.run(app, host="0.0.0.0", port=8007, log_level="info")