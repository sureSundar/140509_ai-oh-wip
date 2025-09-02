#!/usr/bin/env python3
"""
Inventory Management Service - Port 8002
Real-time inventory tracking with predictive stock management
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
    title="RetailAI Inventory Management",
    description="Real-time inventory tracking and predictive stock management for 140509_01",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inventory data with realistic product information
PRODUCTS = [
    {"id": "PROD_001", "name": "Wireless Bluetooth Headphones", "category": "Electronics", "price": 79.99, "supplier": "TechCorp"},
    {"id": "PROD_002", "name": "Smart Fitness Tracker", "category": "Electronics", "price": 149.99, "supplier": "FitTech"},
    {"id": "PROD_003", "name": "USB-C Cable 6ft", "category": "Accessories", "price": 12.99, "supplier": "CableCo"},
    {"id": "PROD_004", "name": "Portable Phone Charger", "category": "Accessories", "price": 25.99, "supplier": "PowerTech"},
    {"id": "PROD_005", "name": "Wireless Mouse", "category": "Electronics", "price": 34.99, "supplier": "InputTech"},
]

def generate_inventory_data():
    """Generate realistic inventory data with seasonal variations"""
    inventory = []
    for product in PRODUCTS:
        base_stock = random.randint(50, 500)
        # Simulate seasonal demand patterns
        seasonal_factor = 1.2 if datetime.now().month in [11, 12] else 0.8
        current_stock = int(base_stock * seasonal_factor * random.uniform(0.3, 1.0))
        reorder_point = int(base_stock * 0.2)
        
        days_of_supply = max(1, current_stock // random.randint(5, 15))
        velocity = random.choice(['Fast', 'Medium', 'Slow'])
        
        inventory.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "category": product["category"],
            "current_stock": current_stock,
            "reorder_point": reorder_point,
            "max_stock": base_stock,
            "unit_price": product["price"],
            "supplier": product["supplier"],
            "days_of_supply": days_of_supply,
            "velocity": velocity,
            "last_restock": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "next_delivery": (datetime.now() + timedelta(days=random.randint(5, 14))).isoformat(),
            "stock_status": "Critical" if current_stock <= reorder_point else "Low" if current_stock <= reorder_point * 2 else "Optimal",
            "turnover_rate": round(random.uniform(4.2, 12.8), 1),
            "forecasted_demand": random.randint(20, 100)
        })
    return inventory

class InventoryUpdate(BaseModel):
    product_id: str
    quantity_change: int
    reason: str

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "inventory-management",
        "version": "2.0.0",
        "project": "140509_01",
        "timestamp": datetime.now().isoformat(),
        "port": 8002
    }

@app.get("/api/inventory")
async def get_inventory():
    """Get current inventory status for all products"""
    inventory = generate_inventory_data()
    
    # Calculate summary statistics
    total_products = len(inventory)
    critical_items = len([item for item in inventory if item["stock_status"] == "Critical"])
    low_stock_items = len([item for item in inventory if item["stock_status"] == "Low"])
    total_value = sum(item["current_stock"] * item["unit_price"] for item in inventory)
    
    return {
        "inventory": inventory,
        "summary": {
            "total_products": total_products,
            "critical_stock": critical_items,
            "low_stock": low_stock_items,
            "optimal_stock": total_products - critical_items - low_stock_items,
            "total_inventory_value": round(total_value, 2),
            "avg_days_of_supply": round(sum(item["days_of_supply"] for item in inventory) / total_products, 1)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "inventory-service:8002"
    }

@app.get("/api/inventory/{product_id}")
async def get_product_inventory(product_id: str):
    """Get detailed inventory information for a specific product"""
    inventory = generate_inventory_data()
    product = next((item for item in inventory if item["product_id"] == product_id), None)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Add movement history
    product["movement_history"] = [
        {"date": (datetime.now() - timedelta(days=i)).isoformat(), 
         "change": random.randint(-20, 30), 
         "reason": random.choice(["Sale", "Restock", "Return", "Adjustment"])}
        for i in range(7)
    ]
    
    return {
        "product": product,
        "source": "inventory-service:8002",
        "retrieved_at": datetime.now().isoformat()
    }

@app.post("/api/inventory/update")
async def update_inventory(update: InventoryUpdate):
    """Update inventory levels for a product"""
    logger.info(f"Inventory update: {update.product_id} by {update.quantity_change} - {update.reason}")
    
    return {
        "success": True,
        "product_id": update.product_id,
        "quantity_changed": update.quantity_change,
        "reason": update.reason,
        "updated_at": datetime.now().isoformat(),
        "source": "inventory-service:8002"
    }

@app.get("/api/inventory/alerts")
async def get_inventory_alerts():
    """Get critical inventory alerts requiring immediate attention"""
    inventory = generate_inventory_data()
    
    alerts = []
    for item in inventory:
        if item["stock_status"] == "Critical":
            alerts.append({
                "alert_id": f"INV_{item['product_id']}_{datetime.now().strftime('%Y%m%d')}",
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "current_stock": item["current_stock"],
                "reorder_point": item["reorder_point"],
                "severity": "HIGH",
                "days_until_stockout": max(1, item["days_of_supply"]),
                "recommended_action": "Immediate reorder required",
                "estimated_impact": f"${item['unit_price'] * item['forecasted_demand']:.2f} lost sales risk"
            })
    
    return {
        "alerts": alerts,
        "total_critical_alerts": len(alerts),
        "generated_at": datetime.now().isoformat(),
        "source": "inventory-service:8002"
    }

@app.get("/api/inventory/reorder-recommendations")
async def get_reorder_recommendations():
    """Get AI-powered reorder recommendations"""
    inventory = generate_inventory_data()
    
    recommendations = []
    for item in inventory:
        if item["current_stock"] <= item["reorder_point"] * 1.5:  # Include near-critical items
            optimal_order = max(item["max_stock"] - item["current_stock"], item["forecasted_demand"])
            recommendations.append({
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "current_stock": item["current_stock"],
                "recommended_order": optimal_order,
                "supplier": item["supplier"],
                "priority": "High" if item["stock_status"] == "Critical" else "Medium",
                "cost_estimate": round(optimal_order * item["unit_price"], 2),
                "expected_delivery": item["next_delivery"],
                "business_impact": f"Prevent ${item['unit_price'] * item['forecasted_demand']:.2f} lost sales"
            })
    
    total_cost = sum(rec["cost_estimate"] for rec in recommendations)
    
    return {
        "recommendations": recommendations,
        "summary": {
            "total_products_to_reorder": len(recommendations),
            "total_investment_required": round(total_cost, 2),
            "estimated_sales_protection": round(total_cost * 2.5, 2)  # Assume 250% markup
        },
        "generated_at": datetime.now().isoformat(),
        "source": "inventory-service:8002"
    }

if __name__ == "__main__":
    logger.info("🏭 Starting Inventory Management Service on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")