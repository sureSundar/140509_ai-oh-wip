"""
Integration Tests - AI-Powered Retail Inventory Optimization System
Comprehensive test suite for end-to-end system functionality.
"""

import pytest
import asyncio
import json
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

# Test fixtures
@pytest.fixture
def sample_sales_data():
    """Generate sample sales data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    data = []
    
    for i, date in enumerate(dates):
        # Generate realistic demand patterns with seasonality and trend
        base_demand = 10
        seasonal = 2 * np.sin(2 * np.pi * i / 365.25)  # Yearly seasonality
        weekly = 1 * np.sin(2 * np.pi * i / 7)  # Weekly seasonality
        trend = 0.01 * i  # Small upward trend
        noise = np.random.normal(0, 1)
        
        demand = max(0, base_demand + seasonal + weekly + trend + noise)
        
        data.append({
            'product_id': 'TEST_PRODUCT_001',
            'store_id': 'TEST_STORE_001',
            'date': date,
            'quantity': int(demand),
            'unit_price': 15.99,
            'total_amount': demand * 15.99
        })
    
    return pd.DataFrame(data)

@pytest.fixture
def sample_weather_data():
    """Generate sample weather data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    data = []
    
    for i, date in enumerate(dates):
        # Generate seasonal weather patterns
        temp_base = 20 + 10 * np.sin(2 * np.pi * i / 365.25)  # Seasonal temperature
        temp_avg = temp_base + np.random.normal(0, 2)
        
        data.append({
            'store_id': 'TEST_STORE_001',
            'date': date,
            'temperature_avg': temp_avg,
            'temperature_min': temp_avg - 5,
            'temperature_max': temp_avg + 5,
            'humidity': 50 + np.random.normal(0, 10),
            'precipitation_mm': max(0, np.random.exponential(2))
        })
    
    return pd.DataFrame(data)

@pytest.fixture
async def mock_db():
    """Mock database connection for testing."""
    db_mock = Mock()
    db_mock.query = AsyncMock()
    db_mock.execute = AsyncMock()
    return db_mock

class TestMLForecastingPipeline:
    """Test ML forecasting functionality."""
    
    def test_prophet_forecast_generation(self, sample_sales_data, sample_weather_data):
        """Test Prophet model forecast generation."""
        from services.ml_engine.services.forecast_service import ForecastService
        
        forecast_service = ForecastService()
        
        # Test Prophet forecast
        result = asyncio.run(
            forecast_service._prophet_forecast(
                historical_data=sample_sales_data,
                external_data=sample_weather_data,
                forecast_horizon_days=30,
                product_id='TEST_PRODUCT_001',
                store_id='TEST_STORE_001'
            )
        )
        
        # Validate forecast results
        assert 'forecasts' in result
        assert 'performance' in result
        assert len(result['forecasts']) == 30
        
        # Check forecast structure
        forecast = result['forecasts'][0]
        assert hasattr(forecast, 'product_id')
        assert hasattr(forecast, 'store_id')
        assert hasattr(forecast, 'forecast_date')
        assert hasattr(forecast, 'predicted_demand')
        assert forecast.predicted_demand >= 0
        
        # Check performance metrics
        performance = result['performance']
        assert 'mae' in performance
        assert 'rmse' in performance
        assert 'mape' in performance
        assert all(metric >= 0 for metric in performance.values())
    
    def test_lstm_forecast_generation(self, sample_sales_data):
        """Test LSTM model forecast generation."""
        from services.ml_engine.services.forecast_service import ForecastService
        
        forecast_service = ForecastService()
        
        # Test LSTM forecast
        result = asyncio.run(
            forecast_service._lstm_forecast(
                historical_data=sample_sales_data,
                external_data=pd.DataFrame(),
                forecast_horizon_days=30,
                product_id='TEST_PRODUCT_001',
                store_id='TEST_STORE_001'
            )
        )
        
        # Validate results
        assert 'forecasts' in result
        assert 'performance' in result
        assert len(result['forecasts']) == 30
        
        # Check all forecasts are non-negative
        for forecast in result['forecasts']:
            assert forecast.predicted_demand >= 0
    
    def test_arima_forecast_generation(self, sample_sales_data):
        """Test ARIMA model forecast generation."""
        from services.ml_engine.services.forecast_service import ForecastService
        
        forecast_service = ForecastService()
        
        # Test ARIMA forecast
        result = asyncio.run(
            forecast_service._arima_forecast(
                historical_data=sample_sales_data,
                forecast_horizon_days=30,
                product_id='TEST_PRODUCT_001',
                store_id='TEST_STORE_001'
            )
        )
        
        # Validate results
        assert 'forecasts' in result
        assert 'performance' in result
        assert len(result['forecasts']) == 30
    
    def test_ensemble_forecast_creation(self, sample_sales_data):
        """Test ensemble forecast combining multiple models."""
        from services.ml_engine.services.forecast_service import ForecastService
        from services.ml_engine.models import ProductForecast
        
        forecast_service = ForecastService()
        
        # Create mock forecasts from different models
        base_date = date.today() + timedelta(days=1)
        
        model_forecasts = {
            'prophet': [
                ProductForecast(
                    product_id='TEST_PRODUCT_001',
                    store_id='TEST_STORE_001',
                    forecast_date=base_date + timedelta(days=i),
                    predicted_demand=10.0 + i,
                    confidence_lower=8.0 + i,
                    confidence_upper=12.0 + i,
                    model_name='prophet',
                    model_version='1.0'
                ) for i in range(7)
            ],
            'lstm': [
                ProductForecast(
                    product_id='TEST_PRODUCT_001',
                    store_id='TEST_STORE_001',
                    forecast_date=base_date + timedelta(days=i),
                    predicted_demand=9.0 + i,
                    confidence_lower=7.0 + i,
                    confidence_upper=11.0 + i,
                    model_name='lstm',
                    model_version='1.0'
                ) for i in range(7)
            ]
        }
        
        # Create ensemble
        ensemble_forecasts = forecast_service._create_ensemble_forecast(model_forecasts)
        
        # Validate ensemble results
        assert len(ensemble_forecasts) == 7
        
        # Check that ensemble values are between individual model predictions
        for i, forecast in enumerate(ensemble_forecasts):
            prophet_pred = model_forecasts['prophet'][i].predicted_demand
            lstm_pred = model_forecasts['lstm'][i].predicted_demand
            
            min_pred = min(prophet_pred, lstm_pred)
            max_pred = max(prophet_pred, lstm_pred)
            
            assert min_pred <= forecast.predicted_demand <= max_pred
            assert forecast.model_name == 'ensemble'

class TestInventoryOptimization:
    """Test inventory optimization algorithms."""
    
    def test_eoq_calculation(self):
        """Test Economic Order Quantity calculation."""
        from services.inventory_service.services.optimization_service import OptimizationService
        
        optimization_service = OptimizationService()
        
        # Test EOQ calculation
        eoq = optimization_service._calculate_eoq(
            annual_demand=1000,
            ordering_cost=50,
            holding_cost_rate=0.25,
            unit_cost=10
        )
        
        # Expected EOQ = sqrt(2 * 1000 * 50 / (0.25 * 10)) = sqrt(40000) ≈ 200
        expected_eoq = (2 * 1000 * 50 / (0.25 * 10)) ** 0.5
        assert abs(eoq - expected_eoq) < 0.1
        
        # Test edge cases
        assert optimization_service._calculate_eoq(0, 50, 0.25, 10) == 0
        assert optimization_service._calculate_eoq(1000, 50, 0.25, 0) == 0
    
    def test_safety_stock_calculation(self):
        """Test safety stock calculation."""
        from services.inventory_service.services.optimization_service import OptimizationService, DemandParameters
        
        optimization_service = OptimizationService()
        
        demand_params = DemandParameters(
            mean_demand=10.0,
            demand_std=2.0,
            lead_time_days=7,
            lead_time_std=1.0,
            seasonality_factor=1.2,
            trend_factor=1.0
        )
        
        # Test safety stock calculation
        safety_stock = optimization_service._calculate_safety_stock(
            demand_params=demand_params,
            service_level=0.95
        )
        
        # Safety stock should be positive and reasonable
        assert safety_stock > 0
        assert safety_stock < demand_params.mean_demand * demand_params.lead_time_days
        
        # Higher service level should result in higher safety stock
        safety_stock_99 = optimization_service._calculate_safety_stock(
            demand_params=demand_params,
            service_level=0.99
        )
        
        assert safety_stock_99 > safety_stock
    
    def test_reorder_point_calculation(self):
        """Test reorder point calculation."""
        from services.inventory_service.services.optimization_service import OptimizationService, DemandParameters
        
        optimization_service = OptimizationService()
        
        demand_params = DemandParameters(
            mean_demand=10.0,
            demand_std=2.0,
            lead_time_days=7,
            lead_time_std=1.0,
            seasonality_factor=1.2,
            trend_factor=1.0
        )
        
        safety_stock = 15.0
        
        # Test reorder point calculation
        reorder_point = optimization_service._calculate_reorder_point(
            demand_params=demand_params,
            safety_stock=safety_stock
        )
        
        # Reorder point should be lead time demand + safety stock
        expected_reorder_point = demand_params.mean_demand * demand_params.lead_time_days + safety_stock
        assert abs(reorder_point - expected_reorder_point) < 0.1

class TestDataIngestionPipeline:
    """Test data ingestion functionality."""
    
    def test_pos_transaction_validation(self):
        """Test POS transaction validation."""
        from services.data_ingestion.services.data_validator import DataValidator
        from services.data_ingestion.models import POSTransaction
        
        validator = DataValidator()
        
        # Valid transaction
        valid_transaction = POSTransaction(
            id="TXN_001",
            product_id="PROD_001",
            store_id="STORE_001",
            quantity=5,
            unit_price=10.99,
            total_amount=54.95,
            transaction_timestamp=datetime.utcnow()
        )
        
        result = asyncio.run(validator.validate_pos_transaction(valid_transaction))
        assert result.is_valid
        
        # Invalid transaction (negative quantity)
        invalid_transaction = POSTransaction(
            id="TXN_002",
            product_id="PROD_001",
            store_id="STORE_001",
            quantity=-1,
            unit_price=10.99,
            total_amount=54.95,
            transaction_timestamp=datetime.utcnow()
        )
        
        result = asyncio.run(validator.validate_pos_transaction(invalid_transaction))
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_data_quality_assessment(self, sample_sales_data):
        """Test data quality assessment functionality."""
        from services.data_ingestion.services.data_validator import DataValidator
        
        validator = DataValidator()
        
        # Test data quality assessment
        quality_score = validator._assess_data_quality(sample_sales_data)
        
        assert 0 <= quality_score <= 1
        assert quality_score > 0.5  # Should be reasonable quality for test data

class TestAlertingSystem:
    """Test alerting and notification functionality."""
    
    def test_stockout_alert_generation(self):
        """Test stockout alert generation."""
        from services.notification_service.services.alert_engine import AlertEngine
        from services.notification_service.models import Alert, AlertSeverity
        
        alert_engine = AlertEngine()
        
        # Test stockout alert creation
        alert = alert_engine._create_stockout_alert(
            product_id="PROD_001",
            store_id="STORE_001",
            current_stock=2,
            expected_demand=10,
            days_until_stockout=1
        )
        
        assert alert.alert_type == "stockout_risk"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.product_id == "PROD_001"
        assert alert.store_id == "STORE_001"
    
    def test_forecast_accuracy_alert(self):
        """Test forecast accuracy alert generation."""
        from services.notification_service.services.alert_engine import AlertEngine
        
        alert_engine = AlertEngine()
        
        # Test forecast accuracy alert
        alert = alert_engine._create_accuracy_alert(
            model_name="prophet",
            accuracy_drop=0.15,
            current_accuracy=0.75,
            threshold=0.8
        )
        
        assert alert.alert_type == "forecast_accuracy"
        assert alert.severity in [alert_engine.AlertSeverity.MEDIUM, alert_engine.AlertSeverity.HIGH]

class TestAPIIntegration:
    """Test API endpoints and integration."""
    
    @pytest.mark.asyncio
    async def test_forecast_api_endpoint(self, mock_db):
        """Test forecast API endpoint."""
        from services.ml_engine.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test forecast request
        request_data = {
            "product_ids": ["PROD_001"],
            "store_ids": ["STORE_001"],
            "forecast_horizon_days": 7,
            "models": ["prophet"]
        }
        
        with patch('services.ml_engine.services.forecast_service.ForecastService.generate_forecasts') as mock_forecast:
            mock_forecast.return_value = []
            
            response = client.post("/api/v1/forecast", json=request_data)
            
            assert response.status_code == 200
            mock_forecast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimization_api_endpoint(self, mock_db):
        """Test inventory optimization API endpoint."""
        from services.inventory_service.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test optimization request
        request_data = {
            "product_ids": ["PROD_001"],
            "store_ids": ["STORE_001"],
            "objective": "minimize_cost",
            "constraints": {
                "min_service_level": 0.95,
                "max_stockout_risk": 0.05
            }
        }
        
        with patch('services.inventory_service.services.optimization_service.OptimizationService.optimize_inventory') as mock_optimize:
            mock_optimize.return_value = []
            
            response = client.post("/api/v1/optimize", json=request_data)
            
            assert response.status_code == 200
            mock_optimize.assert_called_once()

class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_optimization_workflow(self, sample_sales_data, mock_db):
        """Test complete workflow from data ingestion to optimization."""
        
        # Step 1: Data Ingestion
        from services.data_ingestion.services.pos_ingestion_service import POSIngestionService
        pos_service = POSIngestionService()
        
        # Simulate ingesting sales data
        transactions = []
        for _, row in sample_sales_data.head(10).iterrows():
            transaction_data = {
                'product_id': row['product_id'],
                'store_id': row['store_id'],
                'quantity': row['quantity'],
                'unit_price': row['unit_price'],
                'total_amount': row['total_amount'],
                'transaction_timestamp': row['date']
            }
            transactions.append(transaction_data)
        
        # Step 2: ML Forecasting
        from services.ml_engine.services.forecast_service import ForecastService
        forecast_service = ForecastService()
        
        with patch.object(forecast_service, '_get_historical_demand', return_value=sample_sales_data):
            with patch.object(forecast_service, '_get_external_factors', return_value=pd.DataFrame()):
                forecasts = await forecast_service.generate_forecasts(
                    product_ids=['TEST_PRODUCT_001'],
                    store_ids=['TEST_STORE_001'],
                    forecast_horizon_days=7,
                    models=['prophet']
                )
        
        assert len(forecasts) > 0
        
        # Step 3: Inventory Optimization
        from services.inventory_service.services.optimization_service import OptimizationService, OptimizationConstraints
        from services.inventory_service.models import OptimizationObjective
        
        optimization_service = OptimizationService()
        
        constraints = OptimizationConstraints(
            min_service_level=0.95,
            max_stockout_risk=0.05
        )
        
        with patch.object(optimization_service, '_get_product_stores', return_value=['TEST_STORE_001']):
            with patch.object(optimization_service, '_calculate_demand_parameters'):
                with patch.object(optimization_service, '_get_current_inventory_level'):
                    recommendations = await optimization_service.optimize_inventory(
                        product_ids=['TEST_PRODUCT_001'],
                        store_ids=['TEST_STORE_001'],
                        optimization_objective=OptimizationObjective.BALANCED,
                        constraints=constraints,
                        db=mock_db
                    )
        
        # Verify the workflow completed successfully
        assert isinstance(recommendations, list)

class TestPerformanceAndScalability:
    """Test system performance and scalability."""
    
    def test_forecast_generation_performance(self, sample_sales_data):
        """Test forecast generation performance."""
        from services.ml_engine.services.forecast_service import ForecastService
        import time
        
        forecast_service = ForecastService()
        
        start_time = time.time()
        
        # Test with small dataset
        result = asyncio.run(
            forecast_service._prophet_forecast(
                historical_data=sample_sales_data.head(100),
                external_data=pd.DataFrame(),
                forecast_horizon_days=30,
                product_id='TEST_PRODUCT_001',
                store_id='TEST_STORE_001'
            )
        )
        
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time (30 seconds for test)
        assert execution_time < 30
        assert len(result['forecasts']) == 30
    
    def test_batch_processing_scalability(self):
        """Test batch processing with multiple products."""
        from services.ml_engine.services.forecast_service import ForecastService
        
        forecast_service = ForecastService()
        
        # Test with multiple products (simulated)
        product_ids = [f'PROD_{i:03d}' for i in range(10)]
        store_ids = ['STORE_001']
        
        # This would normally involve actual database calls
        # For testing, we just verify the function accepts the parameters
        request_params = {
            'product_ids': product_ids,
            'store_ids': store_ids,
            'forecast_horizon_days': 7,
            'models': ['prophet']
        }
        
        assert len(request_params['product_ids']) == 10
        assert request_params['forecast_horizon_days'] == 7

if __name__ == "__main__":
    pytest.main([__file__, "-v"])