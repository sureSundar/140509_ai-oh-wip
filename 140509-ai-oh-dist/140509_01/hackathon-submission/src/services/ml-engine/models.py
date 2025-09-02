"""
Pydantic models for ML Engine API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

class ModelType(str, Enum):
    ARIMA = "arima"
    LSTM = "lstm"
    PROPHET = "prophet"
    ENSEMBLE = "ensemble"

class ForecastRequest(BaseModel):
    product_ids: List[str] = Field(..., description="List of product IDs to forecast")
    store_ids: Optional[List[str]] = Field(None, description="List of store IDs, if None forecasts for all stores")
    forecast_horizon_days: int = Field(30, ge=1, le=365, description="Number of days to forecast")
    models: Optional[List[ModelType]] = Field(None, description="Models to use, if None uses all available")
    include_confidence: bool = Field(True, description="Include confidence intervals")
    
class ProductForecast(BaseModel):
    product_id: str
    store_id: str
    forecast_date: date
    predicted_demand: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model_name: str
    model_version: str

class ForecastResponse(BaseModel):
    product_id: str
    store_id: str
    forecasts: List[ProductForecast]
    model_performance: Dict[str, float]
    generated_at: datetime
    
class ModelTrainingRequest(BaseModel):
    model_types: List[ModelType] = Field(..., description="Types of models to train")
    product_ids: Optional[List[str]] = Field(None, description="Specific products to train on")
    start_date: Optional[date] = Field(None, description="Training data start date")
    end_date: Optional[date] = Field(None, description="Training data end date")
    hyperparameter_tuning: bool = Field(True, description="Enable hyperparameter optimization")
    
class ModelPerformance(BaseModel):
    model_type: str
    model_version: str
    mae: float
    rmse: float
    mape: float
    accuracy_score: float
    training_date: datetime
    product_count: int
    
class ModelStatus(BaseModel):
    model_type: str
    status: str
    version: str
    last_trained: Optional[datetime]
    performance: Optional[Dict[str, float]]
    
class FeatureImportance(BaseModel):
    feature_name: str
    importance_score: float
    
class ForecastAccuracy(BaseModel):
    model_type: str
    time_period: str
    actual_vs_predicted: List[Dict[str, float]]
    mae: float
    rmse: float
    mape: float
    
class TrainingMetrics(BaseModel):
    model_type: str
    training_loss: List[float]
    validation_loss: List[float]
    epochs: int
    best_epoch: int
    
class BatchForecastStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    total_products: int
    completed_products: int
    estimated_completion: Optional[datetime]
    
class SeasonalityComponent(BaseModel):
    component_type: str  # 'weekly', 'monthly', 'yearly'
    values: List[float]
    dates: List[date]
    
class TrendComponent(BaseModel):
    values: List[float]
    dates: List[date]
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    
class ForecastDecomposition(BaseModel):
    product_id: str
    store_id: str
    trend: TrendComponent
    seasonality: List[SeasonalityComponent]
    residuals: List[float]
    
class ExternalFactorImpact(BaseModel):
    factor_name: str
    factor_type: str  # 'weather', 'event', 'promotion'
    impact_score: float
    confidence: float
    
class AlertRule(BaseModel):
    rule_id: str
    rule_name: str
    condition: str
    threshold: float
    severity: str
    
class MLAlert(BaseModel):
    alert_id: str
    rule_id: str
    product_id: str
    store_id: str
    message: str
    severity: str
    timestamp: datetime
    is_resolved: bool