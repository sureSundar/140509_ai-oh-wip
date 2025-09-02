"""
Forecast Service - Core ML forecasting logic.
Implements ARIMA, LSTM, and Prophet models with ensemble predictions.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Tuple
from datetime import datetime, date, timedelta
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from sklearn.metrics import mean_absolute_error, mean_squared_error
from prophet import Prophet
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from statsmodels.tsa.arima.model import ARIMA
from sklearn.preprocessing import MinMaxScaler
import mlflow
import mlflow.sklearn
import mlflow.tensorflow

from ..models import ForecastResponse, ProductForecast, ForecastAccuracy
from .data_service import DataService

logger = logging.getLogger(__name__)

class ForecastService:
    def __init__(self):
        self.data_service = DataService()
        self.models = {}
        self.scalers = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def initialize_models(self):
        """Initialize and load pre-trained models."""
        try:
            # Load models from MLflow registry
            await self._load_models_from_registry()
            logger.info("Forecast models initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            # Initialize with default parameters if loading fails
            await self._initialize_default_models()
    
    async def _load_models_from_registry(self):
        """Load models from MLflow model registry."""
        try:
            client = mlflow.tracking.MlflowClient()
            
            # Load Prophet models
            prophet_models = client.search_registered_models("name='prophet_demand_forecast'")
            if prophet_models:
                latest_prophet = client.get_latest_versions("prophet_demand_forecast", stages=["Production"])[0]
                self.models['prophet'] = mlflow.prophet.load_model(f"models:/{latest_prophet.name}/{latest_prophet.version}")
            
            # Load LSTM models
            lstm_models = client.search_registered_models("name='lstm_demand_forecast'")
            if lstm_models:
                latest_lstm = client.get_latest_versions("lstm_demand_forecast", stages=["Production"])[0]
                self.models['lstm'] = mlflow.tensorflow.load_model(f"models:/{latest_lstm.name}/{latest_lstm.version}")
                
        except Exception as e:
            logger.warning(f"Could not load models from registry: {e}")
            
    async def _initialize_default_models(self):
        """Initialize models with default parameters."""
        logger.info("Initializing default models")
        # Models will be created on-demand during forecasting
        self.models = {}
    
    async def generate_forecasts(
        self,
        product_ids: List[str],
        store_ids: Optional[List[str]] = None,
        forecast_horizon_days: int = 30,
        models: List[str] = None
    ) -> List[ForecastResponse]:
        """Generate forecasts for specified products and stores."""
        
        if models is None:
            models = ['prophet', 'lstm', 'arima']
            
        forecasts = []
        
        # Process each product-store combination
        for product_id in product_ids:
            # Get historical sales data
            historical_data = await self.data_service.get_sales_history(
                product_id=product_id,
                store_ids=store_ids,
                days_back=365  # Use 1 year of history
            )
            
            if historical_data.empty:
                logger.warning(f"No historical data for product {product_id}")
                continue
                
            # Generate forecasts for each store
            stores_to_forecast = store_ids or historical_data['store_id'].unique()
            
            for store_id in stores_to_forecast:
                store_data = historical_data[historical_data['store_id'] == store_id]
                
                if len(store_data) < 30:  # Need minimum 30 days of data
                    logger.warning(f"Insufficient data for product {product_id}, store {store_id}")
                    continue
                
                # Get external factors
                external_data = await self.data_service.get_external_factors(
                    store_id=store_id,
                    start_date=store_data['date'].min(),
                    end_date=datetime.now().date() + timedelta(days=forecast_horizon_days)
                )
                
                # Generate forecasts using each model
                model_forecasts = {}
                model_performance = {}
                
                for model_type in models:
                    try:
                        forecast_result = await self._generate_single_forecast(
                            model_type=model_type,
                            historical_data=store_data,
                            external_data=external_data,
                            forecast_horizon_days=forecast_horizon_days,
                            product_id=product_id,
                            store_id=store_id
                        )
                        
                        model_forecasts[model_type] = forecast_result['forecasts']
                        model_performance[model_type] = forecast_result['performance']
                        
                    except Exception as e:
                        logger.error(f"Model {model_type} failed for product {product_id}, store {store_id}: {e}")
                        continue
                
                # Create ensemble forecast if multiple models succeeded
                if len(model_forecasts) > 1:
                    ensemble_forecasts = self._create_ensemble_forecast(model_forecasts)
                    model_forecasts['ensemble'] = ensemble_forecasts
                
                # Select best performing model or use ensemble
                best_forecasts = self._select_best_forecast(model_forecasts, model_performance)
                
                response = ForecastResponse(
                    product_id=product_id,
                    store_id=store_id,
                    forecasts=best_forecasts,
                    model_performance=model_performance,
                    generated_at=datetime.utcnow()
                )
                
                forecasts.append(response)
                
        return forecasts
    
    async def _generate_single_forecast(
        self,
        model_type: str,
        historical_data: pd.DataFrame,
        external_data: pd.DataFrame,
        forecast_horizon_days: int,
        product_id: str,
        store_id: str
    ) -> Dict:
        """Generate forecast using a single model type."""
        
        if model_type == 'prophet':
            return await self._prophet_forecast(
                historical_data, external_data, forecast_horizon_days, product_id, store_id
            )
        elif model_type == 'lstm':
            return await self._lstm_forecast(
                historical_data, external_data, forecast_horizon_days, product_id, store_id
            )
        elif model_type == 'arima':
            return await self._arima_forecast(
                historical_data, forecast_horizon_days, product_id, store_id
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    async def _prophet_forecast(
        self,
        historical_data: pd.DataFrame,
        external_data: pd.DataFrame,
        forecast_horizon_days: int,
        product_id: str,
        store_id: str
    ) -> Dict:
        """Generate forecast using Prophet model."""
        
        # Prepare data for Prophet
        prophet_data = historical_data[['date', 'quantity']].rename(columns={
            'date': 'ds',
            'quantity': 'y'
        })
        
        # Add external regressors
        if not external_data.empty:
            prophet_data = prophet_data.merge(external_data, left_on='ds', right_on='date', how='left')
            prophet_data = prophet_data.fillna(method='forward').fillna(method='backward')
        
        # Initialize Prophet model
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.95
        )
        
        # Add external regressors if available
        external_columns = ['temperature_avg', 'precipitation_mm', 'is_holiday']
        for col in external_columns:
            if col in prophet_data.columns:
                model.add_regressor(col)
        
        # Fit model
        model.fit(prophet_data)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=forecast_horizon_days)
        
        # Add future external data
        if not external_data.empty:
            future_external = external_data[external_data['date'] >= future['ds'].max() - timedelta(days=forecast_horizon_days)]
            future = future.merge(future_external, left_on='ds', right_on='date', how='left')
            future = future.fillna(method='forward').fillna(0)
        
        # Generate forecast
        forecast = model.predict(future)
        
        # Extract forecast results
        forecast_results = []
        forecast_start = datetime.now().date() + timedelta(days=1)
        
        for i in range(forecast_horizon_days):
            forecast_date = forecast_start + timedelta(days=i)
            forecast_row = forecast[forecast['ds'].dt.date == forecast_date]
            
            if not forecast_row.empty:
                forecast_results.append(ProductForecast(
                    product_id=product_id,
                    store_id=store_id,
                    forecast_date=forecast_date,
                    predicted_demand=max(0, forecast_row['yhat'].iloc[0]),
                    confidence_lower=max(0, forecast_row['yhat_lower'].iloc[0]),
                    confidence_upper=max(0, forecast_row['yhat_upper'].iloc[0]),
                    model_name='prophet',
                    model_version='1.0'
                ))
        
        # Calculate performance metrics on recent data
        recent_data = prophet_data.tail(30)  # Last 30 days
        recent_pred = model.predict(recent_data)
        
        mae = mean_absolute_error(recent_data['y'], recent_pred['yhat'])
        rmse = np.sqrt(mean_squared_error(recent_data['y'], recent_pred['yhat']))
        mape = np.mean(np.abs((recent_data['y'] - recent_pred['yhat']) / recent_data['y'])) * 100
        
        performance = {
            'mae': float(mae),
            'rmse': float(rmse),
            'mape': float(mape)
        }
        
        return {
            'forecasts': forecast_results,
            'performance': performance
        }
    
    async def _lstm_forecast(
        self,
        historical_data: pd.DataFrame,
        external_data: pd.DataFrame,
        forecast_horizon_days: int,
        product_id: str,
        store_id: str
    ) -> Dict:
        """Generate forecast using LSTM model."""
        
        # Prepare time series data
        data = historical_data.sort_values('date')
        values = data['quantity'].values.astype(float)
        
        # Scale data
        scaler = MinMaxScaler()
        scaled_values = scaler.fit_transform(values.reshape(-1, 1))
        
        # Create sequences for LSTM
        sequence_length = 30  # Use 30 days to predict next day
        X, y = self._create_sequences(scaled_values, sequence_length)
        
        if len(X) < 10:  # Need minimum data for training
            raise ValueError("Insufficient data for LSTM model")
        
        # Split data
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        # Build LSTM model
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(sequence_length, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mean_squared_error')
        
        # Train model
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        history = model.fit(
            X_train, y_train,
            epochs=100,
            batch_size=32,
            validation_data=(X_test, y_test),
            callbacks=[early_stopping],
            verbose=0
        )
        
        # Generate forecasts
        last_sequence = scaled_values[-sequence_length:]
        forecast_results = []
        
        for i in range(forecast_horizon_days):
            # Predict next value
            pred = model.predict(last_sequence.reshape(1, sequence_length, 1), verbose=0)
            
            # Inverse transform
            pred_value = scaler.inverse_transform(pred)[0][0]
            pred_value = max(0, pred_value)  # Ensure non-negative
            
            forecast_date = datetime.now().date() + timedelta(days=i+1)
            
            forecast_results.append(ProductForecast(
                product_id=product_id,
                store_id=store_id,
                forecast_date=forecast_date,
                predicted_demand=float(pred_value),
                confidence_lower=float(pred_value * 0.8),  # Simple confidence interval
                confidence_upper=float(pred_value * 1.2),
                model_name='lstm',
                model_version='1.0'
            ))
            
            # Update sequence for next prediction
            last_sequence = np.append(last_sequence[1:], pred)
        
        # Calculate performance metrics
        test_pred = model.predict(X_test, verbose=0)
        test_pred_scaled = scaler.inverse_transform(test_pred)
        test_actual_scaled = scaler.inverse_transform(y_test)
        
        mae = mean_absolute_error(test_actual_scaled, test_pred_scaled)
        rmse = np.sqrt(mean_squared_error(test_actual_scaled, test_pred_scaled))
        mape = np.mean(np.abs((test_actual_scaled - test_pred_scaled) / test_actual_scaled)) * 100
        
        performance = {
            'mae': float(mae),
            'rmse': float(rmse),
            'mape': float(mape[0])
        }
        
        return {
            'forecasts': forecast_results,
            'performance': performance
        }
    
    async def _arima_forecast(
        self,
        historical_data: pd.DataFrame,
        forecast_horizon_days: int,
        product_id: str,
        store_id: str
    ) -> Dict:
        """Generate forecast using ARIMA model."""
        
        # Prepare time series data
        data = historical_data.sort_values('date')
        values = data['quantity'].values.astype(float)
        
        if len(values) < 50:  # Need minimum data for ARIMA
            raise ValueError("Insufficient data for ARIMA model")
        
        # Auto ARIMA parameters (simplified)
        # In production, use pmdarima.auto_arima for optimal parameters
        order = (2, 1, 2)  # Default ARIMA parameters
        
        try:
            # Fit ARIMA model
            model = ARIMA(values, order=order)
            fitted_model = model.fit()
            
            # Generate forecast
            forecast = fitted_model.forecast(steps=forecast_horizon_days)
            forecast_ci = fitted_model.get_forecast(steps=forecast_horizon_days).conf_int()
            
            # Create forecast results
            forecast_results = []
            forecast_start = datetime.now().date() + timedelta(days=1)
            
            for i in range(forecast_horizon_days):
                forecast_date = forecast_start + timedelta(days=i)
                
                forecast_results.append(ProductForecast(
                    product_id=product_id,
                    store_id=store_id,
                    forecast_date=forecast_date,
                    predicted_demand=max(0, float(forecast[i])),
                    confidence_lower=max(0, float(forecast_ci.iloc[i, 0])),
                    confidence_upper=max(0, float(forecast_ci.iloc[i, 1])),
                    model_name='arima',
                    model_version='1.0'
                ))
            
            # Calculate performance metrics using in-sample fit
            fitted_values = fitted_model.fittedvalues
            residuals = fitted_model.resid
            
            mae = np.mean(np.abs(residuals))
            rmse = np.sqrt(np.mean(residuals**2))
            mape = np.mean(np.abs(residuals / values[1:])) * 100  # Skip first value to avoid division by zero
            
            performance = {
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape)
            }
            
            return {
                'forecasts': forecast_results,
                'performance': performance
            }
            
        except Exception as e:
            logger.error(f"ARIMA model failed: {e}")
            raise
    
    def _create_sequences(self, data, sequence_length):
        """Create sequences for LSTM training."""
        X, y = [], []
        for i in range(sequence_length, len(data)):
            X.append(data[i-sequence_length:i])
            y.append(data[i])
        return np.array(X), np.array(y)
    
    def _create_ensemble_forecast(self, model_forecasts: Dict) -> List[ProductForecast]:
        """Create ensemble forecast by combining multiple models."""
        if not model_forecasts:
            return []
        
        # Get first model's forecasts as template
        first_model = list(model_forecasts.keys())[0]
        template_forecasts = model_forecasts[first_model]
        
        ensemble_forecasts = []
        
        for i, template_forecast in enumerate(template_forecasts):
            # Collect predictions from all models for this date
            predictions = []
            confidence_lowers = []
            confidence_uppers = []
            
            for model_name, forecasts in model_forecasts.items():
                if i < len(forecasts):
                    predictions.append(forecasts[i].predicted_demand)
                    if forecasts[i].confidence_lower:
                        confidence_lowers.append(forecasts[i].confidence_lower)
                    if forecasts[i].confidence_upper:
                        confidence_uppers.append(forecasts[i].confidence_upper)
            
            # Calculate weighted average (equal weights for now)
            ensemble_prediction = np.mean(predictions)
            ensemble_lower = np.mean(confidence_lowers) if confidence_lowers else None
            ensemble_upper = np.mean(confidence_uppers) if confidence_uppers else None
            
            ensemble_forecasts.append(ProductForecast(
                product_id=template_forecast.product_id,
                store_id=template_forecast.store_id,
                forecast_date=template_forecast.forecast_date,
                predicted_demand=float(ensemble_prediction),
                confidence_lower=float(ensemble_lower) if ensemble_lower else None,
                confidence_upper=float(ensemble_upper) if ensemble_upper else None,
                model_name='ensemble',
                model_version='1.0'
            ))
        
        return ensemble_forecasts
    
    def _select_best_forecast(self, model_forecasts: Dict, model_performance: Dict) -> List[ProductForecast]:
        """Select the best performing model's forecast."""
        if 'ensemble' in model_forecasts:
            return model_forecasts['ensemble']
        
        if not model_performance:
            # Return first available forecast
            return list(model_forecasts.values())[0]
        
        # Select model with lowest MAPE
        best_model = min(model_performance.keys(), key=lambda k: model_performance[k].get('mape', float('inf')))
        return model_forecasts[best_model]
    
    async def save_forecasts(self, forecasts: List[ForecastResponse], db):
        """Save forecasts to database."""
        try:
            for forecast_response in forecasts:
                for forecast in forecast_response.forecasts:
                    await self.data_service.save_forecast(forecast, db)
                    
            logger.info(f"Saved {sum(len(f.forecasts) for f in forecasts)} forecasts to database")
            
        except Exception as e:
            logger.error(f"Failed to save forecasts: {e}")
    
    async def get_forecast(self, product_id: str, store_id: str, days: int, db) -> Optional[Dict]:
        """Get latest forecast for a product from database."""
        return await self.data_service.get_latest_forecast(product_id, store_id, days, db)
    
    async def get_forecast_accuracy(self, days_back: int, model_type: Optional[str], db) -> ForecastAccuracy:
        """Calculate forecast accuracy metrics."""
        return await self.data_service.calculate_forecast_accuracy(days_back, model_type, db)
    
    async def batch_forecast(self, products: List[Dict], db):
        """Process batch forecasting for multiple products."""
        try:
            logger.info(f"Starting batch forecast for {len(products)} products")
            
            batch_size = 50  # Process in batches to avoid memory issues
            
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                product_ids = [p['product_id'] for p in batch]
                
                # Generate forecasts for batch
                forecasts = await self.generate_forecasts(
                    product_ids=product_ids,
                    forecast_horizon_days=30,
                    models=['prophet', 'lstm']  # Use faster models for batch processing
                )
                
                # Save to database
                await self.save_forecasts(forecasts, db)
                
                logger.info(f"Completed batch {i//batch_size + 1}/{(len(products)-1)//batch_size + 1}")
                
                # Brief pause to avoid overwhelming the system
                await asyncio.sleep(1)
                
            logger.info("Batch forecast completed successfully")
            
        except Exception as e:
            logger.error(f"Batch forecast failed: {e}")
            raise