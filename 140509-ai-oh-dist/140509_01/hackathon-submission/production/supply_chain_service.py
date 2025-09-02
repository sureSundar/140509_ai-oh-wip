#!/usr/bin/env python3
"""
Supply Chain Management Service - Port 8005
End-to-end supply chain visibility and optimization
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
    title="RetailAI Supply Chain Management",
    description="End-to-end supply chain visibility and optimization for 140509_01",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPLIERS = [
    {"id": "SUP_001", "name": "TechCorp Electronics", "location": "Shenzhen, China", "rating": 4.5, "lead_time": 14},
    {"id": "SUP_002", "name": "American Components", "location": "Austin, TX", "rating": 4.2, "lead_time": 7},
    {"id": "SUP_003", "name": "European Accessories", "location": "Munich, Germany", "rating": 4.7, "lead_time": 10},
    {"id": "SUP_004", "name": "Pacific Electronics", "location": "Seoul, South Korea", "rating": 4.3, "lead_time": 12},
    {"id": "SUP_005", "name": "Global Manufacturing", "location": "Mumbai, India", "rating": 3.9, "lead_time": 18}
]

def generate_shipment_data():
    """Generate realistic shipment tracking data"""
    statuses = ["In Transit", "Customs", "Delivered", "Delayed", "Processing"]
    shipments = []
    
    for i in range(15):
        shipment_id = f"SH_{datetime.now().strftime('%Y%m')}{i:03d}"
        supplier = random.choice(SUPPLIERS)
        status = random.choice(statuses)
        
        shipments.append({
            "shipment_id": shipment_id,
            "supplier": supplier["name"],
            "supplier_id": supplier["id"],
            "origin": supplier["location"],
            "destination": "Distribution Center - Denver, CO",
            "status": status,
            "items_count": random.randint(50, 500),
            "total_value": round(random.uniform(5000, 50000), 2),
            "shipped_date": (datetime.now() - timedelta(days=random.randint(1, 20))).isoformat(),
            "expected_delivery": (datetime.now() + timedelta(days=random.randint(1, 10))).isoformat(),
            "tracking_number": f"TRK{random.randint(100000, 999999)}",
            "carrier": random.choice(["FedEx", "UPS", "DHL", "Maritime Shipping"]),
            "priority": random.choice(["High", "Medium", "Low"]),
            "temperature_controlled": random.choice([True, False])
        })
    
    return shipments

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "supply-chain-management",
        "version": "2.0.0",
        "project": "140509_01",
        "timestamp": datetime.now().isoformat(),
        "port": 8005
    }

@app.get("/api/supply-chain/overview")
async def get_supply_chain_overview():
    """Get comprehensive supply chain overview"""
    shipments = generate_shipment_data()
    
    # Calculate metrics
    total_shipments = len(shipments)
    in_transit = len([s for s in shipments if s["status"] == "In Transit"])
    delivered = len([s for s in shipments if s["status"] == "Delivered"])
    delayed = len([s for s in shipments if s["status"] == "Delayed"])
    total_value = sum(s["total_value"] for s in shipments)
    
    on_time_rate = round((delivered / max(1, delivered + delayed)) * 100, 1)
    
    return {
        "overview": {
            "total_active_shipments": total_shipments,
            "in_transit": in_transit,
            "delivered_today": delivered,
            "delayed_shipments": delayed,
            "total_shipment_value": round(total_value, 2),
            "on_time_delivery_rate": on_time_rate,
            "avg_lead_time": round(sum(s["lead_time"] for s in SUPPLIERS) / len(SUPPLIERS), 1)
        },
        "performance_metrics": {
            "supplier_count": len(SUPPLIERS),
            "avg_supplier_rating": round(sum(s["rating"] for s in SUPPLIERS) / len(SUPPLIERS), 1),
            "cost_efficiency": 92.3,
            "sustainability_score": 78.5
        },
        "generated_at": datetime.now().isoformat(),
        "source": "supply-chain-service:8005"
    }

@app.get("/api/supply-chain/shipments")
async def get_shipments():
    """Get detailed shipment tracking information"""
    shipments = generate_shipment_data()
    
    return {
        "shipments": shipments,
        "summary": {
            "total_shipments": len(shipments),
            "total_value": round(sum(s["total_value"] for s in shipments), 2),
            "status_distribution": {
                status: len([s for s in shipments if s["status"] == status])
                for status in set(s["status"] for s in shipments)
            }
        },
        "generated_at": datetime.now().isoformat(),
        "source": "supply-chain-service:8005"
    }

@app.get("/api/supply-chain/suppliers")
async def get_suppliers():
    """Get supplier performance and management data"""
    suppliers_data = []
    
    for supplier in SUPPLIERS:
        # Generate performance metrics
        monthly_orders = random.randint(5, 25)
        monthly_value = round(random.uniform(50000, 500000), 2)
        quality_score = round(random.uniform(85, 98), 1)
        delivery_performance = round(random.uniform(75, 95), 1)
        
        suppliers_data.append({
            **supplier,
            "monthly_orders": monthly_orders,
            "monthly_value": monthly_value,
            "quality_score": quality_score,
            "delivery_performance": delivery_performance,
            "contract_status": random.choice(["Active", "Renewal Due", "Under Review"]),
            "risk_level": random.choice(["Low", "Medium", "High"]),
            "payment_terms": random.choice(["Net 30", "Net 45", "Net 60"]),
            "last_audit": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat()
        })
    
    # Calculate summary metrics
    total_monthly_value = sum(s["monthly_value"] for s in suppliers_data)
    avg_quality = sum(s["quality_score"] for s in suppliers_data) / len(suppliers_data)
    avg_delivery = sum(s["delivery_performance"] for s in suppliers_data) / len(suppliers_data)
    
    return {
        "suppliers": suppliers_data,
        "summary": {
            "total_suppliers": len(suppliers_data),
            "total_monthly_spend": round(total_monthly_value, 2),
            "avg_quality_score": round(avg_quality, 1),
            "avg_delivery_performance": round(avg_delivery, 1),
            "high_risk_suppliers": len([s for s in suppliers_data if s["risk_level"] == "High"])
        },
        "generated_at": datetime.now().isoformat(),
        "source": "supply-chain-service:8005"
    }

@app.get("/api/supply-chain/disruptions")
async def get_supply_chain_disruptions():
    """Get current supply chain disruptions and risk alerts"""
    disruptions = [
        {
            "disruption_id": "DIS_001",
            "type": "Weather",
            "description": "Hurricane affecting shipping routes from Asia-Pacific",
            "impact_level": "Medium",
            "affected_suppliers": ["SUP_001", "SUP_004"],
            "estimated_delay": "3-5 days",
            "mitigation_status": "Alternative routes activated",
            "financial_impact": 125000
        },
        {
            "disruption_id": "DIS_002",
            "type": "Port Congestion",
            "description": "Container backup at Long Beach port",
            "impact_level": "High",
            "affected_suppliers": ["SUP_001", "SUP_003"],
            "estimated_delay": "7-10 days",
            "mitigation_status": "Rerouting through Seattle port",
            "financial_impact": 280000
        },
        {
            "disruption_id": "DIS_003",
            "type": "Supplier Issue",
            "description": "Quality control halt at Global Manufacturing",
            "impact_level": "Low",
            "affected_suppliers": ["SUP_005"],
            "estimated_delay": "2-3 days",
            "mitigation_status": "Secondary supplier activated",
            "financial_impact": 45000
        }
    ]
    
    total_impact = sum(d["financial_impact"] for d in disruptions)
    high_impact = len([d for d in disruptions if d["impact_level"] == "High"])
    
    return {
        "disruptions": disruptions,
        "risk_assessment": {
            "total_active_disruptions": len(disruptions),
            "high_impact_events": high_impact,
            "total_financial_impact": total_impact,
            "risk_level": "Elevated" if high_impact > 0 else "Moderate",
            "mitigation_coverage": "87%"
        },
        "generated_at": datetime.now().isoformat(),
        "source": "supply-chain-service:8005"
    }

@app.get("/api/supply-chain/optimization")
async def get_optimization_recommendations():
    """Get AI-powered supply chain optimization recommendations"""
    recommendations = [
        {
            "recommendation_id": "OPT_001",
            "category": "Cost Reduction",
            "title": "Consolidate Asian Suppliers",
            "description": "Combine orders from TechCorp and Pacific Electronics to achieve 12% cost reduction",
            "potential_savings": 156000,
            "implementation_effort": "Medium",
            "timeline": "3 months",
            "risk_level": "Low",
            "confidence": 89.5
        },
        {
            "recommendation_id": "OPT_002",
            "category": "Risk Mitigation",
            "title": "Diversify Critical Component Sources",
            "description": "Add secondary supplier for high-demand electronics to reduce single-point-of-failure risk",
            "potential_savings": 0,
            "risk_reduction": "High",
            "implementation_effort": "High",
            "timeline": "6 months",
            "risk_level": "Low",
            "confidence": 94.2
        },
        {
            "recommendation_id": "OPT_003",
            "category": "Efficiency",
            "title": "Implement Predictive Shipping",
            "description": "Use ML to optimize shipping schedules and reduce inventory holding costs",
            "potential_savings": 89000,
            "implementation_effort": "Low",
            "timeline": "1 month",
            "risk_level": "Low",
            "confidence": 76.8
        }
    ]
    
    total_savings = sum(r.get("potential_savings", 0) for r in recommendations)
    
    return {
        "recommendations": recommendations,
        "impact_summary": {
            "total_recommendations": len(recommendations),
            "total_potential_savings": total_savings,
            "avg_confidence": round(sum(r["confidence"] for r in recommendations) / len(recommendations), 1),
            "quick_wins": len([r for r in recommendations if r["timeline"] == "1 month"]),
            "high_impact": len([r for r in recommendations if r.get("potential_savings", 0) > 100000])
        },
        "generated_at": datetime.now().isoformat(),
        "source": "supply-chain-service:8005"
    }

if __name__ == "__main__":
    logger.info("🚚 Starting Supply Chain Management Service on port 8005...")
    uvicorn.run(app, host="0.0.0.0", port=8005, log_level="info")