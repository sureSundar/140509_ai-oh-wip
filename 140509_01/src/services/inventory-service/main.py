"""
Inventory Service - AI-Powered Retail Inventory Optimization
Core inventory management and optimization algorithms.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta

from .models import (
    InventoryOptimizationRequest, InventoryRecommendation, 
    StockLevel, ReorderRecommendation, SafetyStockCalculation,
    InventoryAlert, PromotionalImpactAnalysis
)
from .services.optimization_service import OptimizationService
from .services.reorder_service import ReorderService
from .services.safety_stock_service import SafetyStockService
from .services.alert_service import AlertService
from .services.scenario_service import ScenarioService
from .config import settings
from .database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RetailAI Inventory Service",
    description="Inventory optimization and management service",
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
optimization_service = OptimizationService()
reorder_service = ReorderService()
safety_stock_service = SafetyStockService()
alert_service = AlertService()
scenario_service = ScenarioService()

@app.on_event("startup")
async def startup_event():
    """Initialize inventory services on startup."""
    try:
        logger.info("Initializing Inventory Service...")
        await optimization_service.initialize()
        await alert_service.initialize()
        
        # Start background optimization tasks
        import asyncio
        asyncio.create_task(optimization_service.scheduled_optimization())
        asyncio.create_task(alert_service.monitor_inventory_levels())
        
        logger.info("Inventory Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Inventory Service: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "inventory-service",
        "version": "1.0.0"
    }

@app.post("/api/v1/optimize", response_model=List[InventoryRecommendation])
async def optimize_inventory(
    request: InventoryOptimizationRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Optimize inventory levels for specified products and stores."""
    try:
        logger.info(f"Starting inventory optimization for {len(request.product_ids)} products")
        
        recommendations = await optimization_service.optimize_inventory(
            product_ids=request.product_ids,
            store_ids=request.store_ids,
            optimization_objective=request.objective,
            constraints=request.constraints,
            db=db
        )
        
        # Save recommendations in background
        background_tasks.add_task(
            optimization_service.save_recommendations,
            recommendations,
            db
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Inventory optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/inventory/current")
async def get_current_inventory(
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    category_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Get current inventory levels."""
    try:
        inventory = await optimization_service.get_current_inventory(
            store_id=store_id,
            product_id=product_id,
            category_id=category_id,
            db=db
        )
        
        return inventory
        
    except Exception as e:
        logger.error(f"Get current inventory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/reorder/recommendations", response_model=List[ReorderRecommendation])
async def generate_reorder_recommendations(
    store_ids: Optional[List[str]] = None,
    product_ids: Optional[List[str]] = None,
    urgency_level: Optional[str] = "medium",
    db=Depends(get_db)
):
    """Generate reorder recommendations based on current stock and forecasts."""
    try:
        recommendations = await reorder_service.generate_recommendations(
            store_ids=store_ids,
            product_ids=product_ids,
            urgency_level=urgency_level,
            db=db
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Generate reorder recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reorder/recommendations/{recommendation_id}")
async def get_reorder_recommendation(
    recommendation_id: str,
    db=Depends(get_db)
):
    """Get specific reorder recommendation details."""
    try:
        recommendation = await reorder_service.get_recommendation(recommendation_id, db)
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return recommendation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get reorder recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/reorder/approve/{recommendation_id}")
async def approve_reorder_recommendation(
    recommendation_id: str,
    approved_quantity: Optional[int] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db=Depends(get_db)
):
    """Approve a reorder recommendation."""
    try:
        result = await reorder_service.approve_recommendation(
            recommendation_id=recommendation_id,
            approved_quantity=approved_quantity,
            db=db
        )
        
        # Trigger actual ordering process in background
        background_tasks.add_task(
            reorder_service.process_approved_order,
            recommendation_id,
            db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Approve reorder recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/safety-stock/calculate")
async def calculate_safety_stock(
    product_ids: List[str],
    store_ids: Optional[List[str]] = None,
    service_level: float = 0.98,
    db=Depends(get_db)
):
    """Calculate optimal safety stock levels."""
    try:
        calculations = await safety_stock_service.calculate_safety_stock(
            product_ids=product_ids,
            store_ids=store_ids,
            service_level=service_level,
            db=db
        )
        
        return calculations
        
    except Exception as e:
        logger.error(f"Calculate safety stock failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/alerts", response_model=List[InventoryAlert])
async def get_inventory_alerts(
    severity: Optional[str] = None,
    is_resolved: Optional[bool] = False,
    limit: int = 100,
    db=Depends(get_db)
):
    """Get current inventory alerts."""
    try:
        alerts = await alert_service.get_alerts(
            severity=severity,
            is_resolved=is_resolved,
            limit=limit,
            db=db
        )
        
        return alerts
        
    except Exception as e:
        logger.error(f"Get inventory alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_notes: Optional[str] = None,
    db=Depends(get_db)
):
    """Resolve an inventory alert."""
    try:
        result = await alert_service.resolve_alert(
            alert_id=alert_id,
            resolution_notes=resolution_notes,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Resolve alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scenario/promotional-impact")
async def analyze_promotional_impact(
    product_ids: List[str],
    promotion_start_date: date,
    promotion_end_date: date,
    expected_demand_increase: float,
    store_ids: Optional[List[str]] = None,
    db=Depends(get_db)
):
    """Analyze the impact of a promotional campaign on inventory."""
    try:
        analysis = await scenario_service.analyze_promotional_impact(
            product_ids=product_ids,
            promotion_start_date=promotion_start_date,
            promotion_end_date=promotion_end_date,
            expected_demand_increase=expected_demand_increase,
            store_ids=store_ids,
            db=db
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"Promotional impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scenario/seasonal-adjustment")
async def analyze_seasonal_adjustment(
    product_ids: List[str],
    season_start_date: date,
    season_end_date: date,
    seasonal_factor: float,
    store_ids: Optional[List[str]] = None,
    db=Depends(get_db)
):
    """Analyze seasonal inventory adjustments."""
    try:
        analysis = await scenario_service.analyze_seasonal_adjustment(
            product_ids=product_ids,
            season_start_date=season_start_date,
            season_end_date=season_end_date,
            seasonal_factor=seasonal_factor,
            store_ids=store_ids,
            db=db
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"Seasonal adjustment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/turnover")
async def get_inventory_turnover(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store_id: Optional[str] = None,
    category_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Get inventory turnover analytics."""
    try:
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()
            
        turnover_data = await optimization_service.calculate_inventory_turnover(
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            category_id=category_id,
            db=db
        )
        
        return turnover_data
        
    except Exception as e:
        logger.error(f"Get inventory turnover failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/stockout-risk")
async def get_stockout_risk(
    days_ahead: int = 7,
    store_id: Optional[str] = None,
    category_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Get stockout risk analysis."""
    try:
        risk_analysis = await optimization_service.analyze_stockout_risk(
            days_ahead=days_ahead,
            store_id=store_id,
            category_id=category_id,
            db=db
        )
        
        return risk_analysis
        
    except Exception as e:
        logger.error(f"Get stockout risk failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/carrying-costs")
async def get_carrying_costs(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Get inventory carrying cost analysis."""
    try:
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        carrying_costs = await optimization_service.calculate_carrying_costs(
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            db=db
        )
        
        return carrying_costs
        
    except Exception as e:
        logger.error(f"Get carrying costs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/optimization/batch")
async def start_batch_optimization(
    store_ids: Optional[List[str]] = None,
    category_ids: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db=Depends(get_db)
):
    """Start batch optimization for all products in specified stores/categories."""
    try:
        task_id = f"optimization_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            optimization_service.batch_optimization,
            store_ids,
            category_ids,
            task_id,
            db
        )
        
        return {
            "status": "started",
            "task_id": task_id,
            "message": "Batch optimization started",
            "estimated_completion": "45 minutes"
        }
        
    except Exception as e:
        logger.error(f"Batch optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/optimization/status/{task_id}")
async def get_optimization_status(task_id: str, db=Depends(get_db)):
    """Get status of a batch optimization task."""
    try:
        status = await optimization_service.get_optimization_status(task_id, db)
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get optimization status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kpis")
async def get_inventory_kpis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Get key inventory performance indicators."""
    try:
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        kpis = await optimization_service.calculate_kpis(
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            db=db
        )
        
        return kpis
        
    except Exception as e:
        logger.error(f"Get inventory KPIs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )