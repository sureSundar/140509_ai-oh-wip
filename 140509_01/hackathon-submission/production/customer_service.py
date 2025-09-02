#!/usr/bin/env python3
"""
Customer Analytics Service - Port 8003
Customer behavior analytics and segmentation for business intelligence
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
    title="RetailAI Customer Analytics",
    description="Customer behavior analytics and segmentation for 140509_01",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_customer_segments():
    """Generate realistic customer segmentation data"""
    segments = [
        {
            "segment_id": "VIP_PREMIUM",
            "name": "VIP Premium Customers",
            "customer_count": 2156,
            "avg_order_value": 245.80,
            "purchase_frequency": 8.2,
            "lifetime_value": 2015.60,
            "retention_rate": 94.5,
            "preferred_categories": ["Electronics", "Premium Accessories"],
            "growth_trend": 12.3
        },
        {
            "segment_id": "FREQUENT_BUYERS",
            "name": "Frequent Buyers",
            "customer_count": 8934,
            "avg_order_value": 125.40,
            "purchase_frequency": 5.7,
            "lifetime_value": 715.28,
            "retention_rate": 78.2,
            "preferred_categories": ["Electronics", "Home & Garden"],
            "growth_trend": 8.7
        },
        {
            "segment_id": "SEASONAL_SHOPPERS",
            "name": "Seasonal Shoppers",
            "customer_count": 15672,
            "avg_order_value": 87.60,
            "purchase_frequency": 2.8,
            "lifetime_value": 245.28,
            "retention_rate": 45.3,
            "preferred_categories": ["Seasonal", "Gifts"],
            "growth_trend": -2.1
        },
        {
            "segment_id": "NEW_CUSTOMERS",
            "name": "New Customers",
            "customer_count": 4521,
            "avg_order_value": 68.90,
            "purchase_frequency": 1.2,
            "lifetime_value": 82.68,
            "retention_rate": 23.8,
            "preferred_categories": ["Electronics", "Accessories"],
            "growth_trend": 34.5
        }
    ]
    return segments

def generate_customer_behavior():
    """Generate customer behavior analytics"""
    return {
        "peak_shopping_hours": [
            {"hour": 10, "activity_score": 65},
            {"hour": 12, "activity_score": 78},
            {"hour": 14, "activity_score": 82},
            {"hour": 16, "activity_score": 89},
            {"hour": 18, "activity_score": 95},
            {"hour": 20, "activity_score": 88},
            {"hour": 22, "activity_score": 45}
        ],
        "channel_preferences": {
            "online": 67.8,
            "mobile": 45.2,
            "in_store": 78.5,
            "phone": 12.3
        },
        "payment_methods": {
            "credit_card": 56.7,
            "debit_card": 23.4,
            "digital_wallet": 15.8,
            "cash": 4.1
        },
        "satisfaction_metrics": {
            "overall_satisfaction": 4.2,
            "product_quality": 4.4,
            "service_quality": 4.1,
            "price_satisfaction": 3.8,
            "delivery_satisfaction": 4.3
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "customer-analytics",
        "version": "2.0.0",
        "project": "140509_01",
        "timestamp": datetime.now().isoformat(),
        "port": 8003
    }

@app.get("/api/customers/segments")
async def get_customer_segments():
    """Get detailed customer segmentation analysis"""
    segments = generate_customer_segments()
    
    total_customers = sum(seg["customer_count"] for seg in segments)
    total_revenue = sum(seg["customer_count"] * seg["lifetime_value"] for seg in segments)
    
    return {
        "segments": segments,
        "overview": {
            "total_customers": total_customers,
            "total_lifetime_value": round(total_revenue, 2),
            "avg_customer_value": round(total_revenue / total_customers, 2),
            "segments_count": len(segments)
        },
        "insights": {
            "highest_value_segment": max(segments, key=lambda x: x["lifetime_value"])["name"],
            "fastest_growing_segment": max(segments, key=lambda x: x["growth_trend"])["name"],
            "largest_segment": max(segments, key=lambda x: x["customer_count"])["name"]
        },
        "generated_at": datetime.now().isoformat(),
        "source": "customer-service:8003"
    }

@app.get("/api/customers/behavior")
async def get_customer_behavior():
    """Get comprehensive customer behavior analytics"""
    behavior = generate_customer_behavior()
    
    # Calculate additional metrics
    peak_hour = max(behavior["peak_shopping_hours"], key=lambda x: x["activity_score"])
    preferred_channel = max(behavior["channel_preferences"].items(), key=lambda x: x[1])
    
    return {
        "behavior_data": behavior,
        "key_insights": {
            "peak_shopping_hour": f"{peak_hour['hour']}:00 ({peak_hour['activity_score']}% activity)",
            "preferred_channel": f"{preferred_channel[0].title()} ({preferred_channel[1]}%)",
            "avg_satisfaction": behavior["satisfaction_metrics"]["overall_satisfaction"],
            "mobile_adoption": behavior["channel_preferences"]["mobile"]
        },
        "generated_at": datetime.now().isoformat(),
        "source": "customer-service:8003"
    }

@app.get("/api/customers/loyalty")
async def get_loyalty_analytics():
    """Get customer loyalty and retention analytics"""
    loyalty_data = {
        "loyalty_tiers": [
            {"tier": "Diamond", "customers": 1256, "min_spending": 2000, "benefits": "25% discount + free shipping", "retention": 96.8},
            {"tier": "Gold", "customers": 3847, "min_spending": 1000, "benefits": "15% discount + priority support", "retention": 87.2},
            {"tier": "Silver", "customers": 8934, "min_spending": 500, "benefits": "10% discount", "retention": 72.5},
            {"tier": "Bronze", "customers": 15672, "min_spending": 100, "benefits": "5% discount", "retention": 45.8}
        ],
        "retention_trends": {
            "month_1": 78.5,
            "month_3": 65.2,
            "month_6": 54.8,
            "month_12": 42.3
        },
        "churn_risk": {
            "high_risk": 2341,
            "medium_risk": 5678,
            "low_risk": 21934
        }
    }
    
    total_loyal_customers = sum(tier["customers"] for tier in loyalty_data["loyalty_tiers"])
    avg_retention = sum(tier["retention"] for tier in loyalty_data["loyalty_tiers"]) / len(loyalty_data["loyalty_tiers"])
    
    return {
        "loyalty_program": loyalty_data,
        "summary": {
            "total_loyalty_members": total_loyal_customers,
            "average_retention_rate": round(avg_retention, 1),
            "churn_risk_total": sum(loyalty_data["churn_risk"].values()),
            "year_1_retention": loyalty_data["retention_trends"]["month_12"]
        },
        "generated_at": datetime.now().isoformat(),
        "source": "customer-service:8003"
    }

@app.get("/api/customers/insights")
async def get_customer_insights():
    """Get AI-powered customer insights and recommendations"""
    insights = [
        {
            "insight_id": "CUST_001",
            "type": "Opportunity",
            "title": "VIP Customer Upselling Potential",
            "description": "2,156 VIP customers show 34% higher engagement with premium electronics",
            "recommended_action": "Launch targeted premium product campaign",
            "potential_impact": "$425,600 additional revenue",
            "confidence": 87.5
        },
        {
            "insight_id": "CUST_002", 
            "type": "Risk",
            "title": "Seasonal Customer Retention Drop",
            "description": "15,672 seasonal shoppers showing 45.3% retention rate decline",
            "recommended_action": "Implement off-season engagement program",
            "potential_impact": "Retain 2,350 customers worth $205,000",
            "confidence": 92.1
        },
        {
            "insight_id": "CUST_003",
            "type": "Growth",
            "title": "Mobile Shopping Surge",
            "description": "Mobile channel growth of 45.2% with higher conversion rates",
            "recommended_action": "Optimize mobile experience and exclusive offers",
            "potential_impact": "$180,000 mobile revenue increase",
            "confidence": 78.9
        }
    ]
    
    return {
        "insights": insights,
        "summary": {
            "total_insights": len(insights),
            "opportunities": len([i for i in insights if i["type"] == "Opportunity"]),
            "risks": len([i for i in insights if i["type"] == "Risk"]),
            "growth_potential": len([i for i in insights if i["type"] == "Growth"]),
            "avg_confidence": round(sum(i["confidence"] for i in insights) / len(insights), 1)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "customer-service:8003"
    }

@app.get("/api/customers/{customer_id}")
async def get_customer_profile(customer_id: str):
    """Get detailed profile for a specific customer"""
    # Generate realistic customer profile
    profile = {
        "customer_id": customer_id,
        "name": f"Customer {customer_id[-4:]}",
        "segment": random.choice(["VIP_PREMIUM", "FREQUENT_BUYERS", "SEASONAL_SHOPPERS", "NEW_CUSTOMERS"]),
        "total_orders": random.randint(1, 25),
        "total_spent": round(random.uniform(50, 2000), 2),
        "avg_order_value": round(random.uniform(40, 300), 2),
        "last_purchase": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
        "preferred_categories": random.sample(["Electronics", "Home & Garden", "Clothing", "Accessories"], 2),
        "satisfaction_score": round(random.uniform(3.0, 5.0), 1),
        "loyalty_tier": random.choice(["Bronze", "Silver", "Gold", "Diamond"]),
        "churn_risk": random.choice(["Low", "Medium", "High"])
    }
    
    return {
        "customer": profile,
        "generated_at": datetime.now().isoformat(),
        "source": "customer-service:8003"
    }

if __name__ == "__main__":
    logger.info("👥 Starting Customer Analytics Service on port 8003...")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")