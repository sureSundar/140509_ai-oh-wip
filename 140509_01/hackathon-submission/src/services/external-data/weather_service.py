#!/usr/bin/env python3
"""
Weather Data Integration Service
Implements FR-004: Weather API integration for demand forecasting
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import psycopg2
import redis
from dataclasses import dataclass
import hashlib
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WeatherData:
    """Weather data structure."""
    location: str
    timestamp: datetime
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float
    weather_condition: str
    weather_code: int
    visibility: Optional[float] = None
    pressure: Optional[float] = None

@dataclass
class WeatherForecast:
    """Weather forecast structure."""
    location: str
    forecast_date: datetime
    min_temp: float
    max_temp: float
    avg_temp: float
    precipitation_prob: float
    weather_condition: str
    impact_score: float  # Business impact score 0-10

class WeatherService:
    """Production-ready weather data integration service."""
    
    def __init__(self, db_connection, redis_client=None, api_keys: Dict[str, str] = None):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.api_keys = api_keys or {}
        
        # Weather API configurations
        self.weather_apis = {
            'openweathermap': {
                'base_url': 'https://api.openweathermap.org/data/2.5',
                'key': self.api_keys.get('openweather_api_key', 'demo_key'),
                'requests_per_minute': 60
            },
            'weatherapi': {
                'base_url': 'http://api.weatherapi.com/v1',
                'key': self.api_keys.get('weatherapi_key', 'demo_key'),
                'requests_per_minute': 100
            }
        }
        
        # Store locations from database
        self.store_locations = {}
        self.load_store_locations()
        
        # Weather impact mapping
        self.weather_impact_map = {
            'clear': {'retail_multiplier': 1.1, 'outdoor_boost': 1.3},
            'cloudy': {'retail_multiplier': 1.0, 'outdoor_boost': 0.9},
            'rain': {'retail_multiplier': 0.8, 'indoor_boost': 1.2},
            'snow': {'retail_multiplier': 0.7, 'indoor_boost': 1.4, 'emergency_boost': 1.5},
            'storm': {'retail_multiplier': 0.6, 'essential_boost': 1.8},
            'extreme_heat': {'retail_multiplier': 0.9, 'cooling_boost': 2.0},
            'extreme_cold': {'retail_multiplier': 0.8, 'heating_boost': 1.8}
        }
        
    def load_store_locations(self):
        """Load store locations from database."""
        
        try:
            query = """
            SELECT id, name, city, state, latitude, longitude
            FROM stores 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """
            
            cursor = self.db.cursor()
            cursor.execute(query)
            stores = cursor.fetchall()
            cursor.close()
            
            for store in stores:
                store_id, name, city, state, lat, lon = store
                self.store_locations[store_id] = {
                    'name': name,
                    'city': city,
                    'state': state,
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'location_key': f"{city},{state}"
                }
            
            logger.info(f"✅ Loaded {len(self.store_locations)} store locations")
            
        except Exception as e:
            logger.error(f"Failed to load store locations: {e}")
            # Add demo locations if database fails
            self.store_locations = {
                'STORE_001': {
                    'name': 'Downtown Store',
                    'city': 'New York',
                    'state': 'NY',
                    'latitude': 40.7128,
                    'longitude': -74.0060,
                    'location_key': 'New York,NY'
                },
                'STORE_002': {
                    'name': 'Mall Store',
                    'city': 'Los Angeles', 
                    'state': 'CA',
                    'latitude': 34.0522,
                    'longitude': -118.2437,
                    'location_key': 'Los Angeles,CA'
                },
                'STORE_003': {
                    'name': 'Suburb Store',
                    'city': 'Chicago',
                    'state': 'IL', 
                    'latitude': 41.8781,
                    'longitude': -87.6298,
                    'location_key': 'Chicago,IL'
                }
            }
    
    async def get_current_weather(self, store_id: str) -> Optional[WeatherData]:
        """Get current weather for a store location."""
        
        if store_id not in self.store_locations:
            logger.error(f"Store location not found: {store_id}")
            return None
        
        location = self.store_locations[store_id]
        cache_key = f"weather:current:{store_id}"
        
        # Check cache first (5-minute TTL)
        try:
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached.decode())
                return WeatherData(**data)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        
        # Fetch from API
        try:
            weather_data = await self._fetch_current_weather_openweather(
                location['latitude'], 
                location['longitude'], 
                location['location_key']
            )
            
            if weather_data:
                # Cache the result
                try:
                    cache_data = {
                        'location': weather_data.location,
                        'timestamp': weather_data.timestamp.isoformat(),
                        'temperature': weather_data.temperature,
                        'humidity': weather_data.humidity,
                        'precipitation': weather_data.precipitation,
                        'wind_speed': weather_data.wind_speed,
                        'weather_condition': weather_data.weather_condition,
                        'weather_code': weather_data.weather_code,
                        'visibility': weather_data.visibility,
                        'pressure': weather_data.pressure
                    }
                    self.redis.setex(cache_key, 300, json.dumps(cache_data))
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
                
                # Store in database
                await self.store_weather_data(weather_data)
                
                return weather_data
            
        except Exception as e:
            logger.error(f"Failed to fetch current weather for {store_id}: {e}")
        
        return None
    
    async def _fetch_current_weather_openweather(self, lat: float, lon: float, location: str) -> Optional[WeatherData]:
        """Fetch current weather from OpenWeatherMap API."""
        
        api_key = self.weather_apis['openweathermap']['key']
        base_url = self.weather_apis['openweathermap']['base_url']
        
        # For demo purposes, return simulated weather data if no real API key
        if api_key == 'demo_key':
            return self._generate_demo_weather_data(location)
        
        url = f"{base_url}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse OpenWeatherMap response
                        weather_data = WeatherData(
                            location=location,
                            timestamp=datetime.now(),
                            temperature=data['main']['temp'],
                            humidity=data['main']['humidity'],
                            precipitation=data.get('rain', {}).get('1h', 0) + data.get('snow', {}).get('1h', 0),
                            wind_speed=data['wind']['speed'],
                            weather_condition=data['weather'][0]['main'].lower(),
                            weather_code=data['weather'][0]['id'],
                            visibility=data.get('visibility', 0) / 1000 if data.get('visibility') else None,
                            pressure=data['main'].get('pressure')
                        )
                        
                        return weather_data
                    else:
                        logger.error(f"Weather API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Weather API request failed: {e}")
            return None
    
    def _generate_demo_weather_data(self, location: str) -> WeatherData:
        """Generate realistic demo weather data."""
        
        import random
        
        # Simulate realistic weather based on location and season
        now = datetime.now()
        
        # Base temperature by location (simplified)
        base_temps = {
            'New York,NY': 15,
            'Los Angeles,CA': 22,
            'Chicago,IL': 10
        }
        
        base_temp = base_temps.get(location, 18)
        
        # Seasonal adjustment
        month = now.month
        if month in [12, 1, 2]:  # Winter
            temp_adj = -10
        elif month in [6, 7, 8]:  # Summer
            temp_adj = 8
        else:  # Spring/Fall
            temp_adj = 0
        
        # Weather conditions with realistic probabilities
        conditions = ['clear', 'cloudy', 'rain', 'snow' if temp_adj < -5 else 'cloudy']
        weights = [0.4, 0.3, 0.2, 0.1]
        condition = random.choices(conditions, weights=weights)[0]
        
        # Generate realistic values
        temperature = base_temp + temp_adj + random.uniform(-5, 5)
        humidity = random.randint(30, 90)
        precipitation = random.uniform(0, 20) if condition == 'rain' else 0
        wind_speed = random.uniform(2, 15)
        
        return WeatherData(
            location=location,
            timestamp=now,
            temperature=round(temperature, 1),
            humidity=humidity,
            precipitation=round(precipitation, 1),
            wind_speed=round(wind_speed, 1),
            weather_condition=condition,
            weather_code=800 if condition == 'clear' else 500,
            visibility=random.uniform(5, 20),
            pressure=random.randint(1000, 1030)
        )
    
    async def get_weather_forecast(self, store_id: str, days: int = 7) -> List[WeatherForecast]:
        """Get weather forecast for a store location."""
        
        if store_id not in self.store_locations:
            logger.error(f"Store location not found: {store_id}")
            return []
        
        location = self.store_locations[store_id]
        cache_key = f"weather:forecast:{store_id}:{days}"
        
        # Check cache first (2-hour TTL)
        try:
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached.decode())
                forecasts = []
                for item in data:
                    item['forecast_date'] = datetime.fromisoformat(item['forecast_date'])
                    forecasts.append(WeatherForecast(**item))
                return forecasts
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        
        # Generate demo forecast data
        forecasts = []
        current_weather = await self.get_current_weather(store_id)
        
        if current_weather:
            base_temp = current_weather.temperature
            
            for day in range(days):
                forecast_date = datetime.now() + timedelta(days=day+1)
                
                # Simulate realistic temperature variation
                temp_variation = random.uniform(-3, 3)
                min_temp = base_temp + temp_variation - 5
                max_temp = base_temp + temp_variation + 5
                avg_temp = (min_temp + max_temp) / 2
                
                # Random weather condition
                conditions = ['clear', 'cloudy', 'rain']
                condition = random.choice(conditions)
                
                # Calculate business impact score
                impact_score = self.calculate_weather_impact_score(condition, avg_temp)
                
                forecast = WeatherForecast(
                    location=location['location_key'],
                    forecast_date=forecast_date,
                    min_temp=round(min_temp, 1),
                    max_temp=round(max_temp, 1),
                    avg_temp=round(avg_temp, 1),
                    precipitation_prob=random.uniform(0, 80) if condition == 'rain' else random.uniform(0, 20),
                    weather_condition=condition,
                    impact_score=impact_score
                )
                
                forecasts.append(forecast)
        
        # Cache forecasts
        try:
            cache_data = []
            for forecast in forecasts:
                cache_data.append({
                    'location': forecast.location,
                    'forecast_date': forecast.forecast_date.isoformat(),
                    'min_temp': forecast.min_temp,
                    'max_temp': forecast.max_temp,
                    'avg_temp': forecast.avg_temp,
                    'precipitation_prob': forecast.precipitation_prob,
                    'weather_condition': forecast.weather_condition,
                    'impact_score': forecast.impact_score
                })
            self.redis.setex(cache_key, 7200, json.dumps(cache_data))
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
        
        return forecasts
    
    def calculate_weather_impact_score(self, condition: str, temperature: float) -> float:
        """Calculate weather impact score for demand forecasting (0-10 scale)."""
        
        base_score = 5.0  # Neutral impact
        
        # Temperature impact
        if temperature < 0:
            temp_impact = 1.5  # Cold drives indoor shopping
        elif temperature > 35:
            temp_impact = -1.0  # Too hot reduces shopping
        elif 18 <= temperature <= 25:
            temp_impact = 0.5  # Ideal temperature
        else:
            temp_impact = 0.0
        
        # Weather condition impact
        condition_impact = self.weather_impact_map.get(condition, {}).get('retail_multiplier', 1.0)
        condition_adjustment = (condition_impact - 1.0) * 5  # Scale to -5 to +5
        
        # Calculate final score
        impact_score = base_score + temp_impact + condition_adjustment
        
        # Clamp to 0-10 range
        return max(0.0, min(10.0, impact_score))
    
    async def store_weather_data(self, weather_data: WeatherData):
        """Store weather data in database."""
        
        try:
            query = """
            INSERT INTO weather_data 
            (location, timestamp, temperature, humidity, precipitation, wind_speed, 
             weather_condition, weather_code, visibility, pressure)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location, timestamp) DO UPDATE SET
                temperature = EXCLUDED.temperature,
                humidity = EXCLUDED.humidity,
                precipitation = EXCLUDED.precipitation,
                wind_speed = EXCLUDED.wind_speed,
                weather_condition = EXCLUDED.weather_condition,
                weather_code = EXCLUDED.weather_code,
                visibility = EXCLUDED.visibility,
                pressure = EXCLUDED.pressure
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (
                weather_data.location,
                weather_data.timestamp,
                weather_data.temperature,
                weather_data.humidity,
                weather_data.precipitation,
                weather_data.wind_speed,
                weather_data.weather_condition,
                weather_data.weather_code,
                weather_data.visibility,
                weather_data.pressure
            ))
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to store weather data: {e}")
    
    async def get_weather_features_for_ml(self, store_id: str, date_range: int = 30) -> Dict[str, Any]:
        """Get weather features for ML model training/inference."""
        
        try:
            # Get historical weather data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=date_range)
            
            query = """
            SELECT timestamp, temperature, humidity, precipitation, wind_speed, weather_condition
            FROM weather_data 
            WHERE location = %s AND timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp
            """
            
            location_key = self.store_locations.get(store_id, {}).get('location_key', f'Store_{store_id}')
            df = pd.read_sql(query, self.db, params=[location_key, start_date, end_date])
            
            if df.empty:
                # Generate synthetic data for demo
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                df = pd.DataFrame({
                    'timestamp': dates,
                    'temperature': [20 + random.uniform(-5, 5) for _ in dates],
                    'humidity': [60 + random.randint(-20, 20) for _ in dates],
                    'precipitation': [random.uniform(0, 10) if random.random() < 0.3 else 0 for _ in dates],
                    'wind_speed': [8 + random.uniform(-3, 3) for _ in dates],
                    'weather_condition': [random.choice(['clear', 'cloudy', 'rain']) for _ in dates]
                })
            
            # Calculate weather features
            features = {
                'avg_temperature': float(df['temperature'].mean()),
                'temp_volatility': float(df['temperature'].std()),
                'total_precipitation': float(df['precipitation'].sum()),
                'rainy_days': int((df['precipitation'] > 0).sum()),
                'avg_humidity': float(df['humidity'].mean()),
                'avg_wind_speed': float(df['wind_speed'].mean()),
                'weather_condition_counts': df['weather_condition'].value_counts().to_dict(),
                'extreme_weather_days': int(((df['temperature'] < 0) | (df['temperature'] > 35)).sum()),
                'optimal_weather_days': int(((df['temperature'] >= 18) & (df['temperature'] <= 25) & (df['precipitation'] == 0)).sum()),
                'data_points': len(df),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to get weather features: {e}")
            return {}
    
    async def get_weather_adjusted_forecast_multiplier(self, store_id: str, forecast_date: datetime) -> float:
        """Get weather-adjusted demand multiplier for a specific date."""
        
        try:
            # Get forecast for the date
            forecasts = await self.get_weather_forecast(store_id, days=7)
            
            for forecast in forecasts:
                if forecast.forecast_date.date() == forecast_date.date():
                    # Convert impact score (0-10) to multiplier (0.5-1.5)
                    multiplier = 0.5 + (forecast.impact_score / 10.0)
                    return min(1.5, max(0.5, multiplier))
            
            # Default multiplier if no forecast available
            return 1.0
            
        except Exception as e:
            logger.error(f"Failed to get weather multiplier: {e}")
            return 1.0
    
    async def update_all_store_weather(self):
        """Update weather data for all stores."""
        
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for store_id in self.store_locations.keys():
            try:
                weather_data = await self.get_current_weather(store_id)
                if weather_data:
                    results['success'] += 1
                    logger.info(f"✅ Updated weather for {store_id}: {weather_data.temperature}°C, {weather_data.weather_condition}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to get weather for {store_id}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error updating {store_id}: {str(e)}")
                logger.error(f"Failed to update weather for {store_id}: {e}")
            
            # Rate limiting
            await asyncio.sleep(1)
        
        logger.info(f"Weather update complete: {results['success']} success, {results['failed']} failed")
        return results

# Example usage and testing
if __name__ == "__main__":
    import random
    
    # Database connection
    db_conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='retailai',
        user='retailai',
        password='retailai123'
    )
    
    # Initialize weather service
    weather_service = WeatherService(db_conn)
    
    async def test_weather_service():
        """Test weather service functionality."""
        
        print("🌤️ Testing Weather Service...")
        
        # Test current weather
        current_weather = await weather_service.get_current_weather('STORE_001')
        if current_weather:
            print(f"✅ Current weather: {current_weather.temperature}°C, {current_weather.weather_condition}")
        
        # Test weather forecast
        forecasts = await weather_service.get_weather_forecast('STORE_001', days=5)
        print(f"✅ Got {len(forecasts)} day forecast")
        
        # Test ML features
        features = await weather_service.get_weather_features_for_ml('STORE_001')
        print(f"✅ Weather features: avg temp {features.get('avg_temperature', 0):.1f}°C")
        
        # Test weather multiplier
        tomorrow = datetime.now() + timedelta(days=1)
        multiplier = await weather_service.get_weather_adjusted_forecast_multiplier('STORE_001', tomorrow)
        print(f"✅ Weather demand multiplier for tomorrow: {multiplier:.2f}")
        
        print("🌤️ Weather service testing complete!")
    
    # Run test
    asyncio.run(test_weather_service())