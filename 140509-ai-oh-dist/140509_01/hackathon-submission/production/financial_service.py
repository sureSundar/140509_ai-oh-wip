#!/usr/bin/env python3
"""
Financial Analytics Service - Port 8006
Comprehensive financial reporting and business intelligence
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
    title="RetailAI Financial Analytics",
    description="Comprehensive financial reporting and business intelligence for 140509_01",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_financial_data():
    """Generate realistic financial data with seasonal variations"""
    base_revenue = 4200000  # Monthly base
    seasonal_factor = 1.3 if datetime.now().month in [11, 12] else 0.95 if datetime.now().month in [1, 2] else 1.0
    
    return {
        "revenue": {
            "monthly_revenue": round(base_revenue * seasonal_factor * random.uniform(0.95, 1.05), 2),
            "quarterly_revenue": round(base_revenue * 3 * seasonal_factor * random.uniform(0.98, 1.02), 2),
            "annual_revenue": round(base_revenue * 12 * random.uniform(1.08, 1.15), 2),
            "revenue_growth_rate": round(random.uniform(8.5, 15.2), 1),
            "revenue_per_customer": round(random.uniform(125, 185), 2)
        },
        "costs": {
            "cost_of_goods_sold": round(base_revenue * 0.62 * seasonal_factor, 2),
            "operating_expenses": round(base_revenue * 0.28, 2),
            "marketing_costs": round(base_revenue * 0.08, 2),
            "logistics_costs": round(base_revenue * 0.05, 2),
            "total_costs": round(base_revenue * 1.03 * seasonal_factor, 2)
        },
        "profitability": {
            "gross_profit": round(base_revenue * 0.38 * seasonal_factor, 2),
            "operating_profit": round(base_revenue * 0.10 * seasonal_factor, 2),
            "net_profit": round(base_revenue * 0.08 * seasonal_factor, 2),
            "profit_margin": round(8 * seasonal_factor, 1),
            "ebitda": round(base_revenue * 0.12 * seasonal_factor, 2)
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "financial-analytics",
        "version": "2.0.0",
        "project": "140509_01",
        "timestamp": datetime.now().isoformat(),
        "port": 8006
    }

@app.get("/api/finance/overview")
async def get_financial_overview():
    """Get comprehensive financial overview and KPIs"""
    financial_data = generate_financial_data()
    
    # Calculate additional metrics
    roi = round((financial_data["profitability"]["net_profit"] / financial_data["costs"]["total_costs"]) * 100, 1)
    cash_flow = round(financial_data["profitability"]["ebitda"] * random.uniform(0.85, 0.95), 2)
    
    return {
        "financial_summary": financial_data,
        "key_metrics": {
            "return_on_investment": roi,
            "cash_flow": cash_flow,
            "debt_to_equity": 0.35,
            "current_ratio": 2.4,
            "inventory_turnover": 6.8,
            "accounts_receivable_days": 28
        },
        "performance_indicators": {
            "revenue_vs_target": round(random.uniform(98, 112), 1),
            "cost_efficiency": round(random.uniform(88, 96), 1),
            "profit_vs_target": round(random.uniform(95, 108), 1),
            "budget_variance": round(random.uniform(-5, 8), 1)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "financial-service:8006"
    }

@app.get("/api/finance/revenue-analysis")
async def get_revenue_analysis():
    """Get detailed revenue analysis and breakdown"""
    
    # Revenue by channel
    revenue_channels = {
        "online_sales": round(random.uniform(1800000, 2200000), 2),
        "retail_stores": round(random.uniform(1500000, 1900000), 2),
        "mobile_app": round(random.uniform(600000, 900000), 2),
        "wholesale": round(random.uniform(300000, 500000), 2)
    }
    
    # Revenue by product category
    product_categories = {
        "electronics": round(random.uniform(1200000, 1600000), 2),
        "home_garden": round(random.uniform(800000, 1200000), 2),
        "clothing": round(random.uniform(600000, 900000), 2),
        "accessories": round(random.uniform(400000, 700000), 2),
        "seasonal": round(random.uniform(200000, 400000), 2)
    }
    
    # Revenue trends (last 12 months)
    revenue_trends = []
    base_monthly = 4200000
    for i in range(12):
        month_date = datetime.now() - timedelta(days=30*i)
        seasonal = 1.2 if month_date.month in [11, 12] else 0.9 if month_date.month in [1, 2] else 1.0
        revenue = base_monthly * seasonal * random.uniform(0.95, 1.05)
        revenue_trends.append({
            "month": month_date.strftime("%B %Y"),
            "revenue": round(revenue, 2),
            "growth_rate": round(random.uniform(-5, 15), 1)
        })
    
    total_revenue = sum(revenue_channels.values())
    
    return {
        "revenue_analysis": {
            "total_revenue": round(total_revenue, 2),
            "revenue_by_channel": revenue_channels,
            "revenue_by_category": product_categories,
            "monthly_trends": revenue_trends[:6],  # Last 6 months
            "channel_performance": {
                "best_performing": max(revenue_channels.items(), key=lambda x: x[1]),
                "fastest_growing": "mobile_app",
                "market_share_leader": "online_sales"
            }
        },
        "insights": {
            "total_transactions": random.randint(95000, 125000),
            "average_transaction_value": round(total_revenue / random.randint(95000, 125000), 2),
            "repeat_customer_revenue": round(total_revenue * 0.68, 2),
            "new_customer_revenue": round(total_revenue * 0.32, 2)
        },
        "generated_at": datetime.now().isoformat(),
        "source": "financial-service:8006"
    }

@app.get("/api/finance/cost-analysis")
async def get_cost_analysis():
    """Get detailed cost breakdown and optimization opportunities"""
    
    cost_breakdown = {
        "cost_of_goods_sold": {
            "amount": round(random.uniform(2400000, 2800000), 2),
            "percentage": round(random.uniform(58, 65), 1),
            "trend": round(random.uniform(-2, 5), 1)
        },
        "labor_costs": {
            "amount": round(random.uniform(650000, 850000), 2),
            "percentage": round(random.uniform(15, 20), 1),
            "trend": round(random.uniform(2, 8), 1)
        },
        "marketing_advertising": {
            "amount": round(random.uniform(280000, 380000), 2),
            "percentage": round(random.uniform(6, 9), 1),
            "trend": round(random.uniform(-10, 15), 1)
        },
        "rent_utilities": {
            "amount": round(random.uniform(180000, 250000), 2),
            "percentage": round(random.uniform(4, 6), 1),
            "trend": round(random.uniform(1, 4), 1)
        },
        "technology_systems": {
            "amount": round(random.uniform(120000, 180000), 2),
            "percentage": round(random.uniform(3, 4), 1),
            "trend": round(random.uniform(5, 12), 1)
        },
        "logistics_shipping": {
            "amount": round(random.uniform(200000, 280000), 2),
            "percentage": round(random.uniform(4, 7), 1),
            "trend": round(random.uniform(-5, 8), 1)
        }
    }
    
    total_costs = sum(category["amount"] for category in cost_breakdown.values())
    
    # Cost optimization opportunities
    optimization_opportunities = [
        {
            "category": "Supply Chain",
            "opportunity": "Supplier consolidation",
            "potential_savings": 125000,
            "implementation_time": "3 months",
            "risk_level": "Low"
        },
        {
            "category": "Technology",
            "opportunity": "Cloud migration",
            "potential_savings": 48000,
            "implementation_time": "6 months",
            "risk_level": "Medium"
        },
        {
            "category": "Marketing",
            "opportunity": "Digital marketing optimization",
            "potential_savings": 75000,
            "implementation_time": "1 month",
            "risk_level": "Low"
        }
    ]
    
    return {
        "cost_analysis": {
            "total_costs": round(total_costs, 2),
            "cost_breakdown": cost_breakdown,
            "cost_per_transaction": round(total_costs / random.randint(95000, 125000), 2),
            "cost_efficiency_ratio": round(random.uniform(0.85, 0.92), 2)
        },
        "optimization": {
            "opportunities": optimization_opportunities,
            "total_potential_savings": sum(opp["potential_savings"] for opp in optimization_opportunities),
            "quick_wins": len([opp for opp in optimization_opportunities if opp["implementation_time"] == "1 month"])
        },
        "generated_at": datetime.now().isoformat(),
        "source": "financial-service:8006"
    }

@app.get("/api/finance/cashflow")
async def get_cashflow_analysis():
    """Get cash flow analysis and forecasting"""
    
    # Generate cash flow data for last 6 months
    cashflow_data = []
    for i in range(6):
        month_date = datetime.now() - timedelta(days=30*i)
        operating_cash = round(random.uniform(280000, 420000), 2)
        investing_cash = round(random.uniform(-150000, -50000), 2)  # Usually negative (investments)
        financing_cash = round(random.uniform(-80000, 120000), 2)
        
        cashflow_data.append({
            "month": month_date.strftime("%B %Y"),
            "operating_cashflow": operating_cash,
            "investing_cashflow": investing_cash,
            "financing_cashflow": financing_cash,
            "net_cashflow": round(operating_cash + investing_cash + financing_cash, 2),
            "cash_balance": round(random.uniform(1200000, 2800000), 2)
        })
    
    # Cash flow metrics
    avg_operating_cash = sum(cf["operating_cashflow"] for cf in cashflow_data) / len(cashflow_data)
    current_cash_balance = cashflow_data[0]["cash_balance"]
    
    return {
        "cashflow_analysis": {
            "monthly_cashflow": cashflow_data,
            "current_cash_balance": current_cash_balance,
            "avg_monthly_operating_cash": round(avg_operating_cash, 2),
            "cash_conversion_cycle": random.randint(28, 45),
            "days_cash_on_hand": random.randint(45, 90)
        },
        "forecast": {
            "next_month_projection": round(avg_operating_cash * random.uniform(0.95, 1.08), 2),
            "quarterly_projection": round(avg_operating_cash * 3 * random.uniform(1.02, 1.12), 2),
            "cash_flow_trend": random.choice(["Improving", "Stable", "Declining"]),
            "liquidity_status": "Strong" if current_cash_balance > 2000000 else "Adequate"
        },
        "generated_at": datetime.now().isoformat(),
        "source": "financial-service:8006"
    }

@app.get("/api/finance/budget-variance")
async def get_budget_variance():
    """Get budget vs actual performance analysis"""
    
    budget_items = [
        {"category": "Revenue", "budget": 4500000, "actual": 4327500, "variance_pct": -3.8},
        {"category": "COGS", "budget": 2700000, "actual": 2684250, "variance_pct": -0.6},
        {"category": "Marketing", "budget": 360000, "actual": 384750, "variance_pct": 6.9},
        {"category": "Operations", "budget": 480000, "actual": 465200, "variance_pct": -3.1},
        {"category": "Technology", "budget": 150000, "actual": 167800, "variance_pct": 11.9},
        {"category": "Personnel", "budget": 750000, "actual": 738500, "variance_pct": -1.5}
    ]
    
    # Calculate summary metrics
    total_budget = sum(item["budget"] for item in budget_items if item["category"] != "Revenue")
    total_actual = sum(item["actual"] for item in budget_items if item["category"] != "Revenue")
    overall_variance = round(((total_actual - total_budget) / total_budget) * 100, 1)
    
    favorable_variances = len([item for item in budget_items[1:] if item["variance_pct"] < 0])  # Under budget
    unfavorable_variances = len([item for item in budget_items[1:] if item["variance_pct"] > 0])  # Over budget
    
    return {
        "budget_variance": {
            "budget_items": budget_items,
            "overall_variance_pct": overall_variance,
            "total_budget": total_budget,
            "total_actual": total_actual,
            "variance_amount": round(total_actual - total_budget, 2)
        },
        "variance_analysis": {
            "favorable_variances": favorable_variances,
            "unfavorable_variances": unfavorable_variances,
            "largest_overspend": max(budget_items[1:], key=lambda x: x["variance_pct"] if x["variance_pct"] > 0 else 0),
            "largest_savings": min(budget_items[1:], key=lambda x: x["variance_pct"] if x["variance_pct"] < 0 else 0)
        },
        "recommendations": [
            "Review marketing spend efficiency - 6.9% over budget",
            "Technology investments showing 11.9% overspend - evaluate ROI",
            "Operations showing good cost control with 3.1% under budget"
        ],
        "generated_at": datetime.now().isoformat(),
        "source": "financial-service:8006"
    }

if __name__ == "__main__":
    logger.info("💰 Starting Financial Analytics Service on port 8006...")
    uvicorn.run(app, host="0.0.0.0", port=8006, log_level="info")