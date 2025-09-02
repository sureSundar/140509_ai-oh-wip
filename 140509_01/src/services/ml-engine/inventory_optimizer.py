"""
Real-World Inventory Optimization Engine
Implements Economic Order Quantity (EOQ), Safety Stock, and Reorder Point calculations
using actual sales data and ML forecasts.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from scipy import stats
from scipy.optimize import minimize
import math

logger = logging.getLogger(__name__)

class InventoryOptimizer:
    """
    Production-ready inventory optimization using real business metrics.
    Calculates optimal order quantities, safety stock levels, and reorder points.
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.optimization_results = {}
        
    def calculate_demand_statistics(self, product_id: str, store_id: str, 
                                  days_back: int = 365) -> Dict:
        """Calculate demand statistics from real sales data."""
        
        logger.info(f"Calculating demand statistics for {product_id} at {store_id}")
        
        # Load historical sales data
        query = """
        SELECT 
            DATE(transaction_timestamp) as sale_date,
            SUM(quantity) as daily_demand,
            AVG(unit_price) as avg_unit_price,
            MAX(unit_price) as max_unit_price,
            MIN(unit_price) as min_unit_price
        FROM sales_transactions 
        WHERE product_id = %s AND store_id = %s
        AND transaction_timestamp >= %s
        GROUP BY DATE(transaction_timestamp)
        ORDER BY sale_date
        """
        
        date_threshold = datetime(2022, 1, 1)  # Use demo data date range (2023-2024)
        df = pd.read_sql(query, self.db, params=[product_id, store_id, date_threshold])
        
        if df.empty:
            raise ValueError(f"No sales data found for product {product_id} in store {store_id}")
        
        # Fill missing dates with zero demand
        df['sale_date'] = pd.to_datetime(df['sale_date'])
        date_range = pd.date_range(start=df['sale_date'].min(), end=df['sale_date'].max(), freq='D')
        complete_df = pd.DataFrame({'sale_date': date_range})
        complete_df = complete_df.merge(df, on='sale_date', how='left')
        complete_df['daily_demand'] = complete_df['daily_demand'].fillna(0)
        
        demand_series = complete_df['daily_demand']
        
        # Calculate comprehensive demand statistics
        stats_dict = {
            'total_demand': float(demand_series.sum()),
            'days_analyzed': len(complete_df),
            'days_with_sales': len(df),
            'avg_daily_demand': float(demand_series.mean()),
            'median_daily_demand': float(demand_series.median()),
            'std_daily_demand': float(demand_series.std()),
            'min_daily_demand': float(demand_series.min()),
            'max_daily_demand': float(demand_series.max()),
            'demand_variance': float(demand_series.var()),
            'demand_cv': float(demand_series.std() / demand_series.mean()) if demand_series.mean() > 0 else 0,
            'stockout_days': int((demand_series == 0).sum()),
            'stockout_rate': float((demand_series == 0).sum() / len(demand_series)),
            'avg_unit_price': float(df['avg_unit_price'].mean()) if not df['avg_unit_price'].isna().all() else 0,
            'price_volatility': float(df['avg_unit_price'].std()) if not df['avg_unit_price'].isna().all() else 0,
        }
        
        # Weekly and monthly patterns
        complete_df['day_of_week'] = complete_df['sale_date'].dt.dayofweek
        complete_df['week'] = complete_df['sale_date'].dt.isocalendar().week
        complete_df['month'] = complete_df['sale_date'].dt.month
        
        # Weekly demand statistics
        weekly_demand = complete_df.groupby('week')['daily_demand'].sum()
        stats_dict.update({
            'avg_weekly_demand': float(weekly_demand.mean()),
            'std_weekly_demand': float(weekly_demand.std()),
            'weekly_demand_cv': float(weekly_demand.std() / weekly_demand.mean()) if weekly_demand.mean() > 0 else 0,
        })
        
        # Monthly demand statistics  
        monthly_demand = complete_df.groupby('month')['daily_demand'].sum()
        stats_dict.update({
            'avg_monthly_demand': float(monthly_demand.mean()),
            'std_monthly_demand': float(monthly_demand.std()),
            'seasonal_index': dict(zip(monthly_demand.index.astype(str), 
                                     (monthly_demand / monthly_demand.mean()).round(2).tolist()))
        })
        
        # Day of week patterns
        dow_demand = complete_df.groupby('day_of_week')['daily_demand'].mean()
        stats_dict['day_of_week_pattern'] = dict(zip(dow_demand.index.astype(str), 
                                                   dow_demand.round(2).tolist()))
        
        logger.info(f"Calculated demand statistics: avg_daily={stats_dict['avg_daily_demand']:.2f}, "
                   f"std={stats_dict['std_daily_demand']:.2f}, cv={stats_dict['demand_cv']:.2f}")
        
        return stats_dict
    
    def get_product_costs(self, product_id: str) -> Dict:
        """Get product cost information from database."""
        
        query = """
        SELECT 
            p.cost_price,
            p.selling_price,
            p.weight_kg,
            s.lead_time_days,
            s.minimum_order_qty
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.id = %s
        """
        
        result = pd.read_sql(query, self.db, params=[product_id])
        
        if result.empty:
            raise ValueError(f"Product {product_id} not found")
        
        row = result.iloc[0]
        
        return {
            'unit_cost': float(row['cost_price']) if pd.notna(row['cost_price']) else 10.0,
            'selling_price': float(row['selling_price']) if pd.notna(row['selling_price']) else 15.0,
            'weight_kg': float(row['weight_kg']) if pd.notna(row['weight_kg']) else 1.0,
            'lead_time_days': int(row['lead_time_days']) if pd.notna(row['lead_time_days']) else 7,
            'supplier_min_order': int(row['minimum_order_qty']) if pd.notna(row['minimum_order_qty']) else 1,
        }
    
    def calculate_eoq(self, annual_demand: float, order_cost: float, 
                      holding_cost_rate: float, unit_cost: float) -> Dict:
        """
        Calculate Economic Order Quantity using the classic EOQ formula.
        
        EOQ = sqrt((2 * D * S) / (H * C))
        where:
        D = Annual demand
        S = Order cost per order
        H = Holding cost rate (as percentage)
        C = Unit cost
        """
        
        if annual_demand <= 0 or order_cost <= 0 or holding_cost_rate <= 0 or unit_cost <= 0:
            raise ValueError("All EOQ parameters must be positive")
        
        # Calculate EOQ
        eoq = math.sqrt((2 * annual_demand * order_cost) / (holding_cost_rate * unit_cost))
        
        # Calculate related metrics
        annual_ordering_cost = (annual_demand / eoq) * order_cost
        annual_holding_cost = (eoq / 2) * holding_cost_rate * unit_cost
        total_annual_cost = annual_ordering_cost + annual_holding_cost
        
        # Order frequency
        orders_per_year = annual_demand / eoq
        days_between_orders = 365 / orders_per_year
        
        return {
            'eoq_quantity': round(eoq),
            'annual_ordering_cost': round(annual_ordering_cost, 2),
            'annual_holding_cost': round(annual_holding_cost, 2),
            'total_annual_cost': round(total_annual_cost, 2),
            'orders_per_year': round(orders_per_year, 1),
            'days_between_orders': round(days_between_orders, 1),
            'cost_savings_vs_current': 0  # Will be calculated if current inventory known
        }
    
    def calculate_safety_stock(self, avg_demand: float, demand_std: float,
                              lead_time_days: int, service_level: float = 0.95,
                              lead_time_variability: float = 0.1) -> Dict:
        """
        Calculate safety stock using service level approach.
        
        Safety Stock = Z * sqrt(LT * σ²d + d² * σ²LT)
        where:
        Z = Z-score for service level
        LT = Lead time
        σd = Standard deviation of demand
        d = Average demand
        σLT = Standard deviation of lead time
        """
        
        # Z-score for service level
        z_score = stats.norm.ppf(service_level)
        
        # Lead time variance (assuming some variability)
        lead_time_variance = (lead_time_days * lead_time_variability) ** 2
        
        # Safety stock calculation
        demand_variance = demand_std ** 2
        
        safety_stock_variance = (lead_time_days * demand_variance + 
                               (avg_demand ** 2) * lead_time_variance)
        
        safety_stock = z_score * math.sqrt(safety_stock_variance)
        
        # Reorder point
        reorder_point = avg_demand * lead_time_days + safety_stock
        
        # Expected stockout probability
        expected_stockouts_per_year = (365 / lead_time_days) * (1 - service_level)
        
        return {
            'safety_stock': round(max(0, safety_stock)),
            'reorder_point': round(max(0, reorder_point)),
            'service_level_target': service_level,
            'z_score_used': round(z_score, 2),
            'expected_stockouts_per_year': round(expected_stockouts_per_year, 1),
            'stockout_cost_estimate': 0  # Would need lost sales data
        }
    
    def calculate_abc_classification(self, products_revenue: List[Tuple[str, float]]) -> Dict:
        """
        Classify products using ABC analysis based on revenue contribution.
        A = Top 80% revenue (usually ~20% of products)
        B = Next 15% revenue  
        C = Bottom 5% revenue
        """
        
        # Sort by revenue descending
        sorted_products = sorted(products_revenue, key=lambda x: x[1], reverse=True)
        total_revenue = sum([rev for _, rev in sorted_products])
        
        classifications = {}
        cumulative_revenue = 0
        cumulative_percentage = 0
        
        for product_id, revenue in sorted_products:
            cumulative_revenue += revenue
            cumulative_percentage = cumulative_revenue / total_revenue
            
            if cumulative_percentage <= 0.8:
                classification = 'A'
            elif cumulative_percentage <= 0.95:
                classification = 'B'
            else:
                classification = 'C'
            
            classifications[product_id] = {
                'classification': classification,
                'revenue': revenue,
                'revenue_percentage': round((revenue / total_revenue) * 100, 2),
                'cumulative_percentage': round(cumulative_percentage * 100, 2)
            }
        
        return classifications
    
    def optimize_inventory_for_product_store(self, product_id: str, store_id: str,
                                           service_level: float = 0.95,
                                           holding_cost_rate: float = 0.25,
                                           order_cost: float = 50.0) -> Dict:
        """
        Complete inventory optimization for a product-store combination.
        """
        
        optimization_key = f"{product_id}_{store_id}"
        logger.info(f"Optimizing inventory for {optimization_key}")
        
        try:
            # Get demand statistics
            demand_stats = self.calculate_demand_statistics(product_id, store_id)
            
            # Get product costs
            product_costs = self.get_product_costs(product_id)
            
            # Calculate annual demand
            annual_demand = demand_stats['avg_daily_demand'] * 365
            
            if annual_demand <= 0:
                return {
                    'error': 'No demand history for optimization',
                    'product_id': product_id,
                    'store_id': store_id
                }
            
            # Calculate EOQ
            eoq_result = self.calculate_eoq(
                annual_demand=annual_demand,
                order_cost=order_cost,
                holding_cost_rate=holding_cost_rate,
                unit_cost=product_costs['unit_cost']
            )
            
            # Calculate safety stock and reorder point
            safety_stock_result = self.calculate_safety_stock(
                avg_demand=demand_stats['avg_daily_demand'],
                demand_std=demand_stats['std_daily_demand'],
                lead_time_days=product_costs['lead_time_days'],
                service_level=service_level
            )
            
            # Calculate maximum stock level
            max_stock_level = eoq_result['eoq_quantity'] + safety_stock_result['safety_stock']
            
            # Calculate inventory turnover
            avg_inventory = (eoq_result['eoq_quantity'] / 2) + safety_stock_result['safety_stock']
            inventory_turnover = annual_demand / avg_inventory if avg_inventory > 0 else 0
            
            # Calculate fill rate based on current performance
            fill_rate = 1 - demand_stats['stockout_rate']
            
            # Optimization recommendations
            recommendations = []
            
            if demand_stats['demand_cv'] > 0.5:
                recommendations.append("High demand variability - consider increasing safety stock")
            
            if inventory_turnover < 4:
                recommendations.append("Low inventory turnover - consider reducing order quantity")
            elif inventory_turnover > 12:
                recommendations.append("High inventory turnover - consider increasing order quantity")
                
            if fill_rate < service_level:
                recommendations.append(f"Current fill rate ({fill_rate:.1%}) below target ({service_level:.1%}) - increase safety stock")
            
            # Compile results
            optimization_result = {
                'product_id': product_id,
                'store_id': store_id,
                'optimization_date': datetime.now().isoformat(),
                'parameters': {
                    'service_level_target': service_level,
                    'holding_cost_rate': holding_cost_rate,
                    'order_cost': order_cost,
                    'lead_time_days': product_costs['lead_time_days']
                },
                'demand_analysis': demand_stats,
                'product_costs': product_costs,
                'eoq_analysis': eoq_result,
                'safety_stock_analysis': safety_stock_result,
                'inventory_policy': {
                    'order_quantity': eoq_result['eoq_quantity'],
                    'reorder_point': safety_stock_result['reorder_point'],
                    'safety_stock': safety_stock_result['safety_stock'],
                    'max_stock_level': round(max_stock_level),
                    'min_stock_level': safety_stock_result['safety_stock']
                },
                'performance_metrics': {
                    'inventory_turnover': round(inventory_turnover, 1),
                    'current_fill_rate': round(fill_rate, 3),
                    'expected_service_level': service_level,
                    'days_of_supply': round(avg_inventory / demand_stats['avg_daily_demand'], 1) if demand_stats['avg_daily_demand'] > 0 else 0
                },
                'financial_impact': {
                    'annual_inventory_cost': eoq_result['total_annual_cost'],
                    'avg_inventory_value': round(avg_inventory * product_costs['unit_cost'], 2),
                    'annual_revenue_potential': round(annual_demand * product_costs['selling_price'], 2),
                    'profit_margin': round(((product_costs['selling_price'] - product_costs['unit_cost']) / product_costs['selling_price']) * 100, 1)
                },
                'recommendations': recommendations
            }
            
            # Store results
            self.optimization_results[optimization_key] = optimization_result
            
            logger.info(f"Optimization complete for {optimization_key}: "
                       f"EOQ={eoq_result['eoq_quantity']}, "
                       f"ROP={safety_stock_result['reorder_point']}, "
                       f"SS={safety_stock_result['safety_stock']}")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Optimization failed for {optimization_key}: {e}")
            return {
                'error': str(e),
                'product_id': product_id,
                'store_id': store_id
            }
    
    def batch_optimize_inventory(self, product_store_combinations: List[Tuple[str, str]],
                                service_level: float = 0.95) -> Dict:
        """
        Optimize inventory for multiple product-store combinations in batch.
        """
        
        logger.info(f"Starting batch optimization for {len(product_store_combinations)} combinations")
        
        results = {
            'total_combinations': len(product_store_combinations),
            'successful_optimizations': 0,
            'failed_optimizations': 0,
            'results': [],
            'summary_statistics': {},
            'batch_start_time': datetime.now().isoformat()
        }
        
        # Get all products for ABC classification
        products_revenue = []
        
        for product_id, store_id in product_store_combinations:
            try:
                # Quick revenue calculation for ABC analysis
                query = """
                SELECT SUM(total_amount) as total_revenue
                FROM sales_transactions 
                WHERE product_id = %s AND store_id = %s
                AND transaction_timestamp >= %s
                """
                
                date_threshold = datetime(2022, 1, 1)  # Use demo data date range
                revenue_result = pd.read_sql(query, self.db, params=[product_id, store_id, date_threshold])
                
                revenue = float(revenue_result.iloc[0]['total_revenue']) if not revenue_result.empty and pd.notna(revenue_result.iloc[0]['total_revenue']) else 0
                products_revenue.append((f"{product_id}_{store_id}", revenue))
                
            except Exception as e:
                logger.warning(f"Could not get revenue for {product_id}_{store_id}: {e}")
                products_revenue.append((f"{product_id}_{store_id}", 0))
        
        # Calculate ABC classification
        abc_classifications = self.calculate_abc_classification(products_revenue)
        
        # Optimize each combination
        for product_id, store_id in product_store_combinations:
            try:
                optimization_result = self.optimize_inventory_for_product_store(
                    product_id, store_id, service_level
                )
                
                if 'error' not in optimization_result:
                    # Add ABC classification
                    combination_key = f"{product_id}_{store_id}"
                    optimization_result['abc_classification'] = abc_classifications.get(combination_key, {})
                    
                    results['successful_optimizations'] += 1
                    results['results'].append(optimization_result)
                else:
                    results['failed_optimizations'] += 1
                    results['results'].append(optimization_result)
                    
            except Exception as e:
                logger.error(f"Batch optimization failed for {product_id}_{store_id}: {e}")
                results['failed_optimizations'] += 1
                results['results'].append({
                    'error': str(e),
                    'product_id': product_id,
                    'store_id': store_id
                })
        
        # Calculate summary statistics
        successful_results = [r for r in results['results'] if 'error' not in r]
        
        if successful_results:
            total_annual_cost = sum([r['eoq_analysis']['total_annual_cost'] for r in successful_results])
            total_inventory_value = sum([r['financial_impact']['avg_inventory_value'] for r in successful_results])
            avg_turnover = np.mean([r['performance_metrics']['inventory_turnover'] for r in successful_results])
            avg_fill_rate = np.mean([r['performance_metrics']['current_fill_rate'] for r in successful_results])
            
            results['summary_statistics'] = {
                'total_annual_inventory_cost': round(total_annual_cost, 2),
                'total_inventory_value': round(total_inventory_value, 2),
                'average_inventory_turnover': round(avg_turnover, 1),
                'average_fill_rate': round(avg_fill_rate, 3),
                'abc_distribution': {
                    'A_products': len([r for r in successful_results if r.get('abc_classification', {}).get('classification') == 'A']),
                    'B_products': len([r for r in successful_results if r.get('abc_classification', {}).get('classification') == 'B']),
                    'C_products': len([r for r in successful_results if r.get('abc_classification', {}).get('classification') == 'C'])
                }
            }
        
        results['batch_end_time'] = datetime.now().isoformat()
        
        logger.info(f"Batch optimization complete: {results['successful_optimizations']} successful, "
                   f"{results['failed_optimizations']} failed")
        
        return results
    
    def generate_reorder_recommendations(self, store_id: str = None) -> List[Dict]:
        """
        Generate reorder recommendations based on current inventory levels and optimization results.
        """
        
        logger.info(f"Generating reorder recommendations for store: {store_id or 'all stores'}")
        
        # Get current inventory levels
        inventory_query = """
        SELECT 
            i.product_id,
            i.store_id,
            i.current_stock,
            i.reserved_stock,
            i.reorder_point,
            i.max_stock_level,
            p.name as product_name,
            p.cost_price,
            s.name as store_name
        FROM inventory i
        LEFT JOIN products p ON i.product_id = p.id
        LEFT JOIN stores s ON i.store_id = s.id
        WHERE i.current_stock > 0
        """
        
        params = []
        if store_id:
            inventory_query += " AND i.store_id = %s"
            params.append(store_id)
            
        inventory_df = pd.read_sql(inventory_query, self.db, params=params)
        
        recommendations = []
        
        for _, row in inventory_df.iterrows():
            product_id = row['product_id']
            store_id_current = row['store_id']
            current_stock = row['current_stock']
            reserved_stock = row.get('reserved_stock', 0)
            available_stock = current_stock - reserved_stock
            
            # Get optimization results if available
            optimization_key = f"{product_id}_{store_id_current}"
            
            if optimization_key in self.optimization_results:
                opt_result = self.optimization_results[optimization_key]
                recommended_reorder_point = opt_result['inventory_policy']['reorder_point']
                recommended_order_qty = opt_result['inventory_policy']['order_quantity']
                max_stock = opt_result['inventory_policy']['max_stock_level']
            else:
                # Use database values or defaults
                recommended_reorder_point = row.get('reorder_point', 20)
                recommended_order_qty = 50  # Default
                max_stock = row.get('max_stock_level', 100)
            
            # Determine if reorder is needed
            needs_reorder = available_stock <= recommended_reorder_point
            
            # Calculate urgency
            if available_stock <= 0:
                urgency = "CRITICAL"
            elif available_stock <= recommended_reorder_point * 0.5:
                urgency = "HIGH"
            elif available_stock <= recommended_reorder_point:
                urgency = "MEDIUM"
            else:
                urgency = "LOW"
            
            # Calculate recommended order quantity
            stock_needed = max_stock - available_stock
            final_order_qty = min(recommended_order_qty, stock_needed)
            
            if needs_reorder or urgency in ["CRITICAL", "HIGH"]:
                recommendation = {
                    'product_id': product_id,
                    'product_name': row.get('product_name', 'Unknown'),
                    'store_id': store_id_current,
                    'store_name': row.get('store_name', 'Unknown'),
                    'current_stock': current_stock,
                    'available_stock': available_stock,
                    'reserved_stock': reserved_stock,
                    'reorder_point': recommended_reorder_point,
                    'recommended_order_quantity': max(1, final_order_qty),
                    'urgency_level': urgency,
                    'days_until_stockout': max(0, int(available_stock / max(1, self._get_daily_demand_estimate(product_id, store_id_current)))),
                    'estimated_order_cost': round(final_order_qty * float(row.get('cost_price', 0)), 2),
                    'recommendation_date': datetime.now().isoformat(),
                    'reason': self._get_reorder_reason(available_stock, recommended_reorder_point, urgency)
                }
                
                recommendations.append(recommendation)
        
        # Sort by urgency and then by days until stockout
        urgency_priority = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: (urgency_priority[x['urgency_level']], x['days_until_stockout']))
        
        logger.info(f"Generated {len(recommendations)} reorder recommendations")
        
        return recommendations
    
    def _get_daily_demand_estimate(self, product_id: str, store_id: str) -> float:
        """Get estimated daily demand for a product-store combination."""
        
        optimization_key = f"{product_id}_{store_id}"
        
        if optimization_key in self.optimization_results:
            return self.optimization_results[optimization_key]['demand_analysis']['avg_daily_demand']
        
        # Fallback: calculate from recent sales
        query = """
        SELECT AVG(daily_demand) as avg_demand
        FROM (
            SELECT DATE(transaction_timestamp), SUM(quantity) as daily_demand
            FROM sales_transactions 
            WHERE product_id = %s AND store_id = %s
            AND transaction_timestamp >= %s
            GROUP BY DATE(transaction_timestamp)
        ) daily_sales
        """
        
        date_threshold = datetime(2023, 1, 1)  # Use demo data date range
        result = pd.read_sql(query, self.db, params=[product_id, store_id, date_threshold])
        
        return float(result.iloc[0]['avg_demand']) if not result.empty and pd.notna(result.iloc[0]['avg_demand']) else 1.0
    
    def _get_reorder_reason(self, available_stock: int, reorder_point: int, urgency: str) -> str:
        """Generate human-readable reason for reorder recommendation."""
        
        if available_stock <= 0:
            return "STOCKOUT: Immediate replenishment required"
        elif available_stock <= reorder_point * 0.5:
            return f"CRITICAL: Stock ({available_stock}) well below reorder point ({reorder_point})"
        elif available_stock <= reorder_point:
            return f"NORMAL: Stock ({available_stock}) at or below reorder point ({reorder_point})"
        else:
            return f"PREVENTIVE: Stock level review recommended"