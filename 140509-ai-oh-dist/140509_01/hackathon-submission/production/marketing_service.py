#!/usr/bin/env python3
"""
Marketing Analytics Service - Port 8008
Digital marketing performance and campaign optimization
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
    title="RetailAI Marketing Analytics",
    description="Digital marketing performance and campaign optimization for 140509_01",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_campaign_data():
    """Generate realistic marketing campaign data"""
    campaigns = [
        {
            "campaign_id": "CAMP_001",
            "name": "Holiday Electronics Promo",
            "type": "Seasonal",
            "channel": "Multi-channel",
            "status": "Active",
            "budget": 125000,
            "spent": 89750,
            "start_date": "2024-11-01",
            "end_date": "2024-12-31"
        },
        {
            "campaign_id": "CAMP_002",
            "name": "New Customer Acquisition",
            "type": "Acquisition",
            "channel": "Digital",
            "status": "Active",
            "budget": 85000,
            "spent": 62340,
            "start_date": "2024-10-15",
            "end_date": "2025-01-15"
        },
        {
            "campaign_id": "CAMP_003",
            "name": "Mobile App Promotion",
            "type": "Product",
            "channel": "Mobile",
            "status": "Completed",
            "budget": 45000,
            "spent": 43560,
            "start_date": "2024-09-01",
            "end_date": "2024-10-31"
        },
        {
            "campaign_id": "CAMP_004",
            "name": "VIP Customer Retention",
            "type": "Retention",
            "channel": "Email",
            "status": "Active",
            "budget": 35000,
            "spent": 28900,
            "start_date": "2024-11-15",
            "end_date": "2025-02-15"
        }
    ]
    
    # Add performance metrics to each campaign
    for campaign in campaigns:
        impressions = random.randint(45000, 350000)
        clicks = random.randint(int(impressions * 0.02), int(impressions * 0.08))
        conversions = random.randint(int(clicks * 0.05), int(clicks * 0.15))
        
        campaign.update({
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": round((clicks / impressions) * 100, 2),
            "conversion_rate": round((conversions / clicks) * 100, 2),
            "cpc": round(campaign["spent"] / clicks, 2),
            "roas": round(random.uniform(2.8, 6.2), 2),
            "revenue_generated": round(campaign["spent"] * random.uniform(3.2, 5.8), 2)
        })
    
    return campaigns

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "marketing-analytics",
        "version": "2.0.0",
        "project": "140509_01",
        "timestamp": datetime.now().isoformat(),
        "port": 8008
    }

@app.get("/api/marketing/overview")
async def get_marketing_overview():
    """Get comprehensive marketing performance overview"""
    
    campaigns = generate_campaign_data()
    
    # Calculate summary metrics
    total_budget = sum(c["budget"] for c in campaigns)
    total_spent = sum(c["spent"] for c in campaigns)
    total_impressions = sum(c["impressions"] for c in campaigns)
    total_clicks = sum(c["clicks"] for c in campaigns)
    total_conversions = sum(c["conversions"] for c in campaigns)
    total_revenue = sum(c["revenue_generated"] for c in campaigns)
    
    # Channel performance
    channel_performance = {
        "digital": {
            "budget": 180000,
            "spend": 134500,
            "roas": 4.8,
            "conversions": 2340
        },
        "email": {
            "budget": 65000,
            "spend": 52800,
            "roas": 6.2,
            "conversions": 890
        },
        "social_media": {
            "budget": 95000,
            "spend": 78650,
            "roas": 3.4,
            "conversions": 1560
        },
        "mobile": {
            "budget": 75000,
            "spend": 68900,
            "roas": 5.1,
            "conversions": 1240
        }
    }
    
    return {
        "marketing_overview": {
            "total_budget": total_budget,
            "total_spent": total_spent,
            "budget_utilization": round((total_spent / total_budget) * 100, 1),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "overall_ctr": round((total_clicks / total_impressions) * 100, 2),
            "overall_conversion_rate": round((total_conversions / total_clicks) * 100, 2),
            "total_revenue_generated": round(total_revenue, 2),
            "overall_roas": round(total_revenue / total_spent, 2)
        },
        "channel_performance": channel_performance,
        "active_campaigns": len([c for c in campaigns if c["status"] == "Active"]),
        "generated_at": datetime.now().isoformat(),
        "source": "marketing-service:8008"
    }

@app.get("/api/marketing/campaigns")
async def get_campaigns():
    """Get detailed campaign performance data"""
    
    campaigns = generate_campaign_data()
    
    # Add additional performance metrics
    for campaign in campaigns:
        campaign["performance_score"] = round(random.uniform(72, 95), 1)
        campaign["engagement_rate"] = round(random.uniform(2.8, 7.5), 2)
        campaign["audience_reach"] = random.randint(15000, 120000)
        campaign["brand_awareness_lift"] = round(random.uniform(8, 25), 1)
    
    # Campaign insights
    best_roas = max(campaigns, key=lambda x: x["roas"])
    highest_conversion = max(campaigns, key=lambda x: x["conversion_rate"])
    most_efficient = min(campaigns, key=lambda x: x["cpc"])
    
    return {
        "campaigns": campaigns,
        "campaign_insights": {
            "best_roas_campaign": {
                "name": best_roas["name"],
                "roas": best_roas["roas"]
            },
            "highest_conversion_campaign": {
                "name": highest_conversion["name"],
                "conversion_rate": highest_conversion["conversion_rate"]
            },
            "most_cost_efficient": {
                "name": most_efficient["name"],
                "cpc": most_efficient["cpc"]
            },
            "total_active_campaigns": len([c for c in campaigns if c["status"] == "Active"])
        },
        "generated_at": datetime.now().isoformat(),
        "source": "marketing-service:8008"
    }

@app.get("/api/marketing/audience")
async def get_audience_analytics():
    """Get audience segmentation and behavior analytics"""
    
    audience_segments = [
        {
            "segment_id": "AUD_001",
            "name": "Tech Enthusiasts",
            "size": 45620,
            "age_range": "25-40",
            "engagement_rate": 8.7,
            "conversion_rate": 12.3,
            "avg_order_value": 185.40,
            "preferred_channels": ["Digital", "Mobile"],
            "growth_rate": 15.8
        },
        {
            "segment_id": "AUD_002",
            "name": "Budget Conscious",
            "size": 67890,
            "age_range": "35-55",
            "engagement_rate": 5.2,
            "conversion_rate": 8.7,
            "avg_order_value": 95.60,
            "preferred_channels": ["Email", "Social Media"],
            "growth_rate": 4.2
        },
        {
            "segment_id": "AUD_003",
            "name": "Premium Shoppers",
            "size": 23450,
            "age_range": "40-60",
            "engagement_rate": 11.4,
            "conversion_rate": 18.9,
            "avg_order_value": 320.75,
            "preferred_channels": ["Email", "Direct Mail"],
            "growth_rate": 22.1
        },
        {
            "segment_id": "AUD_004",
            "name": "Mobile First",
            "size": 89340,
            "age_range": "18-35",
            "engagement_rate": 9.8,
            "conversion_rate": 10.5,
            "avg_order_value": 125.90,
            "preferred_channels": ["Mobile", "Social Media"],
            "growth_rate": 28.7
        }
    ]
    
    # Demographic breakdown
    demographics = {
        "age_groups": {
            "18-25": 18.5,
            "26-35": 32.8,
            "36-45": 24.7,
            "46-55": 16.3,
            "55+": 7.7
        },
        "gender": {
            "male": 52.3,
            "female": 45.8,
            "other": 1.9
        },
        "income_levels": {
            "under_50k": 22.1,
            "50k_75k": 28.7,
            "75k_100k": 24.9,
            "100k_plus": 24.3
        }
    }
    
    total_audience = sum(seg["size"] for seg in audience_segments)
    avg_engagement = sum(seg["engagement_rate"] for seg in audience_segments) / len(audience_segments)
    
    return {
        "audience_segments": audience_segments,
        "demographics": demographics,
        "audience_insights": {
            "total_audience_size": total_audience,
            "average_engagement_rate": round(avg_engagement, 1),
            "fastest_growing_segment": max(audience_segments, key=lambda x: x["growth_rate"])["name"],
            "highest_value_segment": max(audience_segments, key=lambda x: x["avg_order_value"])["name"],
            "mobile_audience_percentage": round((audience_segments[3]["size"] / total_audience) * 100, 1)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "marketing-service:8008"
    }

@app.get("/api/marketing/attribution")
async def get_attribution_analysis():
    """Get marketing attribution and customer journey analysis"""
    
    attribution_data = {
        "touchpoint_analysis": [
            {"touchpoint": "Paid Search", "first_touch": 28.5, "last_touch": 31.2, "assisted": 45.8},
            {"touchpoint": "Social Media", "first_touch": 22.1, "last_touch": 18.7, "assisted": 52.3},
            {"touchpoint": "Email", "first_touch": 15.8, "last_touch": 24.6, "assisted": 38.9},
            {"touchpoint": "Display Ads", "first_touch": 18.3, "last_touch": 12.8, "assisted": 41.7},
            {"touchpoint": "Direct", "first_touch": 12.6, "last_touch": 35.9, "assisted": 15.2},
            {"touchpoint": "Organic Search", "first_touch": 34.2, "last_touch": 28.4, "assisted": 22.1}
        ],
        "customer_journey": {
            "avg_touchpoints_to_conversion": 4.7,
            "avg_journey_length_days": 12.8,
            "single_touch_conversions": 23.5,
            "multi_touch_conversions": 76.5
        },
        "channel_synergies": [
            {"channels": ["Paid Search", "Email"], "lift": 23.4},
            {"channels": ["Social Media", "Display"], "lift": 18.7},
            {"channels": ["Email", "Direct"], "lift": 31.2}
        ]
    }
    
    # Calculate attribution values
    total_conversions = random.randint(8500, 12500)
    total_revenue = random.uniform(1200000, 1800000)
    
    for touchpoint in attribution_data["touchpoint_analysis"]:
        touchpoint["attributed_conversions"] = int(total_conversions * touchpoint["last_touch"] / 100)
        touchpoint["attributed_revenue"] = round(total_revenue * touchpoint["last_touch"] / 100, 2)
    
    return {
        "attribution_analysis": attribution_data,
        "performance_summary": {
            "total_attributed_conversions": total_conversions,
            "total_attributed_revenue": round(total_revenue, 2),
            "top_performing_touchpoint": max(attribution_data["touchpoint_analysis"], 
                                           key=lambda x: x["last_touch"])["touchpoint"],
            "highest_assist_rate": max(attribution_data["touchpoint_analysis"], 
                                     key=lambda x: x["assisted"])["touchpoint"]
        },
        "generated_at": datetime.now().isoformat(),
        "source": "marketing-service:8008"
    }

@app.get("/api/marketing/optimization")
async def get_optimization_recommendations():
    """Get AI-powered marketing optimization recommendations"""
    
    recommendations = [
        {
            "recommendation_id": "MKT_OPT_001",
            "category": "Budget Allocation",
            "priority": "High",
            "title": "Shift Budget to Mobile Channels",
            "description": "Mobile audience shows 28.7% growth rate with strong conversion potential",
            "current_allocation": "15%",
            "recommended_allocation": "25%",
            "potential_impact": "+18% conversion increase",
            "estimated_roi": 340,
            "implementation_effort": "Low",
            "confidence_score": 87.5
        },
        {
            "recommendation_id": "MKT_OPT_002",
            "category": "Campaign Optimization",
            "priority": "Medium",
            "title": "Optimize Email Campaign Timing",
            "description": "Engagement data shows 34% higher open rates on Tuesday-Thursday 10-11 AM",
            "current_performance": "5.2% engagement",
            "potential_improvement": "7.1% engagement",
            "estimated_revenue_lift": 45000,
            "implementation_effort": "Low",
            "confidence_score": 92.1
        },
        {
            "recommendation_id": "MKT_OPT_003",
            "category": "Audience Targeting",
            "priority": "High",
            "title": "Expand Premium Shopper Segment",
            "description": "Premium shoppers show 320.75 AOV vs 125.90 average - high growth potential",
            "current_segment_size": 23450,
            "target_expansion": "35%",
            "potential_revenue_increase": 280000,
            "implementation_effort": "Medium",
            "confidence_score": 78.9
        },
        {
            "recommendation_id": "MKT_OPT_004",
            "category": "Creative Optimization",
            "priority": "Medium",
            "title": "A/B Test Video Content",
            "description": "Video ads showing 45% higher engagement in tech enthusiast segment",
            "current_engagement": "8.7%",
            "projected_engagement": "12.6%",
            "budget_reallocation": 25000,
            "implementation_effort": "Medium",
            "confidence_score": 68.4
        }
    ]
    
    # Calculate impact summary
    total_revenue_potential = sum(rec.get("potential_revenue_increase", 0) for rec in recommendations)
    total_budget_impact = sum(rec.get("budget_reallocation", 0) for rec in recommendations)
    high_priority_count = len([rec for rec in recommendations if rec["priority"] == "High"])
    
    return {
        "optimization_recommendations": recommendations,
        "impact_summary": {
            "total_recommendations": len(recommendations),
            "high_priority_actions": high_priority_count,
            "total_revenue_potential": total_revenue_potential,
            "total_budget_reallocation": total_budget_impact,
            "average_confidence": round(sum(rec["confidence_score"] for rec in recommendations) / len(recommendations), 1),
            "quick_wins": len([rec for rec in recommendations if rec["implementation_effort"] == "Low"])
        },
        "generated_at": datetime.now().isoformat(),
        "source": "marketing-service:8008"
    }

if __name__ == "__main__":
    logger.info("📢 Starting Marketing Analytics Service on port 8008...")
    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")