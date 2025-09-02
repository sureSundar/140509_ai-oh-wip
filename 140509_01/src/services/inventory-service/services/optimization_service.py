"""
Inventory Optimization Service
Core algorithms for inventory optimization including EOQ, reorder points, and safety stock calculations.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Tuple
from datetime import datetime, date, timedelta
import logging
import asyncio
import math
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass

from ..models import (
    InventoryRecommendation, StockLevel, OptimizationObjective,
    InventoryKPIs, StockoutRisk, CarryingCost
)

logger = logging.getLogger(__name__)

@dataclass
class OptimizationConstraints:
    max_inventory_investment: Optional[float] = None
    max_storage_capacity: Optional[Dict[str, float]] = None
    min_service_level: float = 0.98
    max_stockout_risk: float = 0.02
    supplier_constraints: Optional[Dict[str, Dict]] = None

@dataclass
class DemandParameters:
    mean_demand: float
    demand_std: float
    lead_time_days: int
    lead_time_std: float
    seasonality_factor: float
    trend_factor: float

class OptimizationService:
    def __init__(self):
        self.models = {}
        self.cache = {}
        
    async def initialize(self):
        """Initialize optimization models and parameters."""
        logger.info("Initializing optimization service")
        # Load optimization parameters from configuration
        self.holding_cost_rate = 0.25  # 25% annual holding cost
        self.ordering_cost = 50.0  # Fixed ordering cost per order
        self.stockout_cost_multiplier = 5.0  # Cost multiplier for stockouts
        
    async def optimize_inventory(
        self,
        product_ids: List[str],
        store_ids: Optional[List[str]],
        optimization_objective: OptimizationObjective,
        constraints: OptimizationConstraints,
        db
    ) -> List[InventoryRecommendation]:
        """
        Main inventory optimization function using multi-objective optimization.
        """
        try:
            recommendations = []
            
            # Get current inventory and demand data
            for product_id in product_ids:
                product_stores = store_ids or await self._get_product_stores(product_id, db)
                
                for store_id in product_stores:
                    # Get demand parameters
                    demand_params = await self._calculate_demand_parameters(
                        product_id, store_id, db
                    )
                    
                    if not demand_params:
                        logger.warning(f"No demand data for product {product_id}, store {store_id}")
                        continue
                    
                    # Get current inventory
                    current_inventory = await self._get_current_inventory_level(
                        product_id, store_id, db
                    )
                    
                    # Calculate optimal inventory levels
                    optimal_levels = await self._calculate_optimal_levels(
                        product_id=product_id,
                        store_id=store_id,
                        demand_params=demand_params,
                        current_inventory=current_inventory,
                        objective=optimization_objective,
                        constraints=constraints,
                        db=db
                    )
                    
                    recommendation = InventoryRecommendation(
                        product_id=product_id,
                        store_id=store_id,
                        current_stock=current_inventory.current_stock,
                        recommended_stock=optimal_levels['optimal_stock'],
                        reorder_point=optimal_levels['reorder_point'],
                        safety_stock=optimal_levels['safety_stock'],
                        economic_order_quantity=optimal_levels['eoq'],
                        max_stock_level=optimal_levels['max_stock'],
                        expected_demand=demand_params.mean_demand,
                        confidence_level=0.95,
                        cost_impact=optimal_levels['cost_savings'],
                        service_level_impact=optimal_levels['service_level'],
                        recommendation_reason=optimal_levels['reason'],
                        priority=optimal_levels['priority'],
                        generated_at=datetime.utcnow()
                    )
                    
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Inventory optimization failed: {e}")
            raise
    
    async def _calculate_demand_parameters(
        self, product_id: str, store_id: str, db
    ) -> Optional[DemandParameters]:
        """Calculate demand parameters from historical data and forecasts."""
        try:
            # Get historical sales data (last 6 months)
            historical_data = await self._get_historical_demand(
                product_id, store_id, days_back=180, db=db
            )
            
            if len(historical_data) < 30:  # Need minimum data
                return None
            
            # Calculate demand statistics
            demand_values = historical_data['daily_demand'].values
            mean_demand = np.mean(demand_values)
            demand_std = np.std(demand_values)
            
            # Get supplier lead time
            lead_time_info = await self._get_lead_time_info(product_id, db)
            lead_time_days = lead_time_info.get('lead_time_days', 7)
            lead_time_std = lead_time_info.get('lead_time_std', 1)
            
            # Calculate seasonality and trend
            seasonality_factor = await self._calculate_seasonality_factor(
                historical_data, db
            )
            trend_factor = await self._calculate_trend_factor(
                historical_data, db
            )
            
            return DemandParameters(
                mean_demand=float(mean_demand),
                demand_std=float(demand_std),
                lead_time_days=int(lead_time_days),
                lead_time_std=float(lead_time_std),
                seasonality_factor=float(seasonality_factor),
                trend_factor=float(trend_factor)
            )
            
        except Exception as e:
            logger.error(f"Calculate demand parameters failed: {e}")
            return None
    
    async def _calculate_optimal_levels(
        self,
        product_id: str,
        store_id: str,
        demand_params: DemandParameters,
        current_inventory: StockLevel,
        objective: OptimizationObjective,
        constraints: OptimizationConstraints,
        db
    ) -> Dict:
        """Calculate optimal inventory levels using multi-criteria optimization."""
        
        # Get product cost information
        product_info = await self._get_product_info(product_id, db)
        unit_cost = product_info.get('cost_price', 10.0)
        
        # Calculate Economic Order Quantity (EOQ)
        eoq = self._calculate_eoq(
            annual_demand=demand_params.mean_demand * 365,
            ordering_cost=self.ordering_cost,
            holding_cost_rate=self.holding_cost_rate,
            unit_cost=unit_cost
        )
        
        # Calculate safety stock based on service level
        safety_stock = self._calculate_safety_stock(
            demand_params=demand_params,
            service_level=constraints.min_service_level
        )
        
        # Calculate reorder point
        reorder_point = self._calculate_reorder_point(
            demand_params=demand_params,
            safety_stock=safety_stock
        )
        
        # Calculate maximum stock level
        max_stock = reorder_point + eoq
        
        # Calculate optimal stock level based on objective
        if objective == OptimizationObjective.MINIMIZE_COST:
            optimal_stock = reorder_point + (eoq / 2)  # Average inventory
        elif objective == OptimizationObjective.MAXIMIZE_SERVICE_LEVEL:
            optimal_stock = reorder_point + eoq  # Higher stock for better service
        elif objective == OptimizationObjective.MINIMIZE_STOCKOUTS:
            optimal_stock = max_stock
        else:  # BALANCED
            optimal_stock = self._calculate_balanced_stock_level(
                reorder_point, eoq, safety_stock, demand_params
            )
        
        # Calculate cost impact
        current_cost = self._calculate_total_cost(
            current_inventory.current_stock,
            demand_params,
            unit_cost
        )
        
        optimal_cost = self._calculate_total_cost(
            optimal_stock,
            demand_params,
            unit_cost
        )
        
        cost_savings = current_cost - optimal_cost
        
        # Calculate service level impact
        service_level = self._calculate_service_level(
            safety_stock, demand_params
        )
        
        # Determine priority and reason
        stock_difference = abs(optimal_stock - current_inventory.current_stock)
        if stock_difference > demand_params.mean_demand * 7:  # More than week's demand
            priority = "high"
            reason = f"Significant stock adjustment needed: {stock_difference:.1f} units"
        elif cost_savings > unit_cost * 10:  # Significant cost savings
            priority = "medium"
            reason = f"Cost optimization opportunity: ${cost_savings:.2f} savings"
        else:
            priority = "low"
            reason = "Minor optimization adjustment"
        
        return {
            'optimal_stock': round(optimal_stock),
            'reorder_point': round(reorder_point),
            'safety_stock': round(safety_stock),
            'eoq': round(eoq),
            'max_stock': round(max_stock),
            'cost_savings': cost_savings,
            'service_level': service_level,
            'reason': reason,
            'priority': priority
        }
    
    def _calculate_eoq(
        self,
        annual_demand: float,
        ordering_cost: float,
        holding_cost_rate: float,
        unit_cost: float
    ) -> float:
        """Calculate Economic Order Quantity."""
        if annual_demand <= 0 or unit_cost <= 0:
            return 0
        
        holding_cost = holding_cost_rate * unit_cost
        eoq = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
        return max(1, eoq)
    
    def _calculate_safety_stock(
        self,
        demand_params: DemandParameters,
        service_level: float
    ) -> float:
        """Calculate safety stock based on demand variability and service level."""
        from scipy import stats
        
        # Z-score for service level
        z_score = stats.norm.ppf(service_level)
        
        # Standard deviation of demand during lead time
        lead_time_demand_std = math.sqrt(
            demand_params.lead_time_days * (demand_params.demand_std ** 2) +
            (demand_params.mean_demand ** 2) * (demand_params.lead_time_std ** 2)
        )
        
        safety_stock = z_score * lead_time_demand_std
        return max(0, safety_stock)
    
    def _calculate_reorder_point(
        self,
        demand_params: DemandParameters,
        safety_stock: float
    ) -> float:
        """Calculate reorder point."""
        average_lead_time_demand = (
            demand_params.mean_demand * demand_params.lead_time_days
        )
        reorder_point = average_lead_time_demand + safety_stock
        return max(0, reorder_point)
    
    def _calculate_balanced_stock_level(
        self,
        reorder_point: float,
        eoq: float,
        safety_stock: float,
        demand_params: DemandParameters
    ) -> float:
        """Calculate balanced stock level considering multiple objectives."""
        
        # Weight factors for balanced optimization
        cost_weight = 0.4
        service_weight = 0.4
        risk_weight = 0.2
        
        # Cost-optimal level (minimize holding costs)
        cost_optimal = reorder_point + (eoq / 3)
        
        # Service-optimal level (maximize availability)
        service_optimal = reorder_point + (eoq * 0.8)
        
        # Risk-optimal level (minimize stockout risk)
        risk_optimal = reorder_point + safety_stock + (eoq / 2)
        
        # Weighted combination
        balanced_level = (
            cost_weight * cost_optimal +
            service_weight * service_optimal +
            risk_weight * risk_optimal
        )
        
        return balanced_level
    
    def _calculate_total_cost(
        self,
        stock_level: float,
        demand_params: DemandParameters,
        unit_cost: float
    ) -> float:
        """Calculate total inventory cost including holding, ordering, and stockout costs."""
        
        annual_demand = demand_params.mean_demand * 365
        
        # Holding cost
        holding_cost = stock_level * unit_cost * self.holding_cost_rate
        
        # Ordering cost (assuming optimal order frequency)
        if stock_level > 0:
            order_frequency = annual_demand / stock_level
            ordering_cost = order_frequency * self.ordering_cost
        else:
            ordering_cost = 0
        
        # Stockout cost (simplified model)
        stockout_probability = max(0, 1 - (stock_level / (demand_params.mean_demand * 30)))
        stockout_cost = (
            stockout_probability * annual_demand * unit_cost * self.stockout_cost_multiplier
        )
        
        return holding_cost + ordering_cost + stockout_cost
    
    def _calculate_service_level(
        self,
        safety_stock: float,
        demand_params: DemandParameters
    ) -> float:
        """Calculate expected service level."""
        from scipy import stats
        
        if demand_params.demand_std <= 0:
            return 0.99
        
        # Standard deviation during lead time
        lead_time_std = math.sqrt(demand_params.lead_time_days) * demand_params.demand_std
        
        if lead_time_std <= 0:
            return 0.99
        
        z_score = safety_stock / lead_time_std
        service_level = stats.norm.cdf(z_score)
        
        return min(0.999, max(0.5, service_level))
    
    async def _calculate_seasonality_factor(self, historical_data: pd.DataFrame, db) -> float:
        """Calculate seasonality factor from historical data."""
        try:
            if len(historical_data) < 60:  # Need at least 2 months
                return 1.0
            
            # Simple seasonality calculation based on monthly averages
            historical_data['month'] = pd.to_datetime(historical_data['date']).dt.month
            monthly_avg = historical_data.groupby('month')['daily_demand'].mean()
            
            if len(monthly_avg) < 2:
                return 1.0
            
            # Calculate coefficient of variation for seasonality
            seasonality = monthly_avg.std() / monthly_avg.mean() if monthly_avg.mean() > 0 else 0
            
            return min(2.0, max(0.5, 1.0 + seasonality))
            
        except Exception:
            return 1.0
    
    async def _calculate_trend_factor(self, historical_data: pd.DataFrame, db) -> float:
        """Calculate trend factor from historical data."""
        try:
            if len(historical_data) < 30:
                return 1.0
            
            # Simple linear regression for trend
            historical_data = historical_data.sort_values('date')
            x = np.arange(len(historical_data))
            y = historical_data['daily_demand'].values
            
            # Calculate slope
            slope = np.polyfit(x, y, 1)[0]
            
            # Convert to trend factor (normalized)
            mean_demand = np.mean(y)
            if mean_demand > 0:
                trend_factor = 1.0 + (slope * 30 / mean_demand)  # 30-day trend
                return min(1.5, max(0.5, trend_factor))
            
            return 1.0
            
        except Exception:
            return 1.0
    
    async def calculate_inventory_turnover(
        self,
        start_date: date,
        end_date: date,
        store_id: Optional[str],
        category_id: Optional[str],
        db
    ) -> Dict:
        """Calculate inventory turnover metrics."""
        try:
            # This would query the database for actual calculations
            # Placeholder implementation
            turnover_data = {
                "period": f"{start_date} to {end_date}",
                "average_inventory_turnover": 6.5,
                "best_performers": [
                    {"product_id": "P001", "turnover": 12.3},
                    {"product_id": "P002", "turnover": 10.8}
                ],
                "slow_movers": [
                    {"product_id": "P099", "turnover": 2.1},
                    {"product_id": "P098", "turnover": 1.8}
                ],
                "category_breakdown": {
                    "Electronics": 8.2,
                    "Clothing": 4.5,
                    "Home": 6.1
                }
            }
            
            return turnover_data
            
        except Exception as e:
            logger.error(f"Calculate inventory turnover failed: {e}")
            raise
    
    async def analyze_stockout_risk(
        self,
        days_ahead: int,
        store_id: Optional[str],
        category_id: Optional[str],
        db
    ) -> Dict:
        """Analyze stockout risk for specified time horizon."""
        try:
            # This would use actual forecasts and inventory data
            # Placeholder implementation
            risk_analysis = {
                "analysis_date": datetime.utcnow().isoformat(),
                "forecast_horizon_days": days_ahead,
                "high_risk_products": [
                    {
                        "product_id": "P001",
                        "store_id": "S001",
                        "current_stock": 5,
                        "expected_demand": 8,
                        "stockout_probability": 0.85,
                        "days_until_stockout": 3
                    }
                ],
                "medium_risk_products": [
                    {
                        "product_id": "P002",
                        "store_id": "S001",
                        "current_stock": 15,
                        "expected_demand": 12,
                        "stockout_probability": 0.25,
                        "days_until_stockout": 7
                    }
                ],
                "overall_risk_score": 0.15,
                "recommended_actions": [
                    "Reorder P001 immediately",
                    "Monitor P002 closely"
                ]
            }
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Analyze stockout risk failed: {e}")
            raise
    
    async def calculate_carrying_costs(
        self,
        start_date: date,
        end_date: date,
        store_id: Optional[str],
        db
    ) -> Dict:
        """Calculate inventory carrying costs."""
        try:
            # Placeholder implementation
            carrying_costs = {
                "period": f"{start_date} to {end_date}",
                "total_carrying_cost": 25000.00,
                "cost_breakdown": {
                    "storage_cost": 8000.00,
                    "insurance_cost": 2000.00,
                    "obsolescence_cost": 5000.00,
                    "opportunity_cost": 10000.00
                },
                "cost_per_unit": 2.50,
                "carrying_cost_rate": 0.25,
                "optimization_opportunities": [
                    {
                        "category": "Slow-moving items",
                        "potential_savings": 3000.00,
                        "action": "Reduce stock levels"
                    }
                ]
            }
            
            return carrying_costs
            
        except Exception as e:
            logger.error(f"Calculate carrying costs failed: {e}")
            raise
    
    async def calculate_kpis(
        self,
        start_date: date,
        end_date: date,
        store_id: Optional[str],
        db
    ) -> InventoryKPIs:
        """Calculate key inventory performance indicators."""
        try:
            # Placeholder implementation with realistic values
            kpis = InventoryKPIs(
                period=f"{start_date} to {end_date}",
                inventory_turnover=6.8,
                stockout_rate=0.02,
                service_level=0.98,
                carrying_cost_percentage=0.25,
                inventory_accuracy=0.995,
                obsolete_inventory_percentage=0.03,
                fill_rate=0.97,
                order_cycle_time=2.5,
                inventory_shrinkage=0.01,
                gross_margin_roi=0.35
            )
            
            return kpis
            
        except Exception as e:
            logger.error(f"Calculate KPIs failed: {e}")
            raise
    
    async def scheduled_optimization(self):
        """Scheduled task for regular inventory optimization."""
        while True:
            try:
                logger.info("Starting scheduled inventory optimization")
                
                # This would run optimization for all products
                # Placeholder implementation
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Scheduled optimization failed: {e}")
                await asyncio.sleep(300)  # Retry after 5 minutes
    
    async def batch_optimization(
        self,
        store_ids: Optional[List[str]],
        category_ids: Optional[List[str]],
        task_id: str,
        db
    ):
        """Process batch optimization for multiple products."""
        try:
            logger.info(f"Starting batch optimization task {task_id}")
            
            # This would process optimization in batches
            # Placeholder implementation
            await asyncio.sleep(60)  # Simulate processing time
            
            logger.info(f"Batch optimization task {task_id} completed")
            
        except Exception as e:
            logger.error(f"Batch optimization task {task_id} failed: {e}")
            raise
    
    # Placeholder methods for database operations
    async def _get_product_stores(self, product_id: str, db) -> List[str]:
        return ["store1", "store2", "store3"]
    
    async def _get_current_inventory_level(self, product_id: str, store_id: str, db) -> StockLevel:
        return StockLevel(
            product_id=product_id,
            store_id=store_id,
            current_stock=50,
            reserved_stock=5,
            available_stock=45,
            last_updated=datetime.utcnow()
        )
    
    async def _get_historical_demand(self, product_id: str, store_id: str, days_back: int, db) -> pd.DataFrame:
        # Placeholder - generate sample data
        dates = pd.date_range(end=datetime.now().date(), periods=days_back)
        demand = np.random.poisson(10, days_back)  # Poisson distribution for demand
        return pd.DataFrame({"date": dates, "daily_demand": demand})
    
    async def _get_lead_time_info(self, product_id: str, db) -> Dict:
        return {"lead_time_days": 7, "lead_time_std": 1.5}
    
    async def _get_product_info(self, product_id: str, db) -> Dict:
        return {"cost_price": 15.0, "selling_price": 25.0}
    
    async def get_current_inventory(self, store_id: str, product_id: str, category_id: str, db):
        """Get current inventory levels."""
        # Placeholder implementation
        return [
            {
                "product_id": "P001",
                "store_id": "S001",
                "current_stock": 45,
                "reorder_point": 20,
                "max_stock": 100,
                "status": "normal"
            }
        ]
    
    async def save_recommendations(self, recommendations: List[InventoryRecommendation], db):
        """Save optimization recommendations to database."""
        logger.info(f"Saving {len(recommendations)} recommendations to database")
        # Implementation would save to database
    
    async def get_optimization_status(self, task_id: str, db):
        """Get status of optimization task."""
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "message": "Optimization completed successfully"
        }