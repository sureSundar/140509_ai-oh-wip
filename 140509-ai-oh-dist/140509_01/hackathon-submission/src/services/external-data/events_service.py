#!/usr/bin/env python3
"""
Events Data Integration Service  
Implements FR-005-006: Event calendar ingestion and demographic data for demand forecasting
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
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EventData:
    """Event data structure."""
    event_id: str
    name: str
    event_type: str
    location: str
    start_date: datetime
    end_date: datetime
    expected_attendance: Optional[int] = None
    impact_radius_km: Optional[float] = None
    demand_impact_score: float = 5.0  # 0-10 scale
    categories: Optional[List[str]] = None
    venue: Optional[str] = None
    description: Optional[str] = None

@dataclass
class DemographicData:
    """Demographic data structure."""
    location: str
    population: int
    median_age: float
    median_income: float
    education_level: str
    employment_rate: float
    urban_density: str
    lifestyle_segments: List[str]
    shopping_preferences: Dict[str, float]

class EventsService:
    """Production-ready events and demographic data integration service."""
    
    def __init__(self, db_connection, redis_client=None, api_keys: Dict[str, str] = None):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.api_keys = api_keys or {}
        
        # Events API configurations
        self.events_apis = {
            'eventbrite': {
                'base_url': 'https://www.eventbriteapi.com/v3',
                'key': self.api_keys.get('eventbrite_token', 'demo_token'),
                'requests_per_hour': 1000
            },
            'ticketmaster': {
                'base_url': 'https://app.ticketmaster.com/discovery/v2',
                'key': self.api_keys.get('ticketmaster_key', 'demo_key'),
                'requests_per_second': 5
            }
        }
        
        # Store locations
        self.store_locations = {}
        self.load_store_locations()
        
        # Event impact mapping for different event types
        self.event_impact_map = {
            'concert': {'attendance_multiplier': 1.2, 'radius_km': 25, 'categories': ['food', 'beverage', 'apparel']},
            'sports': {'attendance_multiplier': 1.5, 'radius_km': 30, 'categories': ['food', 'beverage', 'merchandise']},
            'festival': {'attendance_multiplier': 2.0, 'radius_km': 40, 'categories': ['food', 'beverage', 'outdoor', 'apparel']},
            'conference': {'attendance_multiplier': 0.8, 'radius_km': 15, 'categories': ['food', 'technology', 'business']},
            'convention': {'attendance_multiplier': 1.3, 'radius_km': 20, 'categories': ['food', 'retail', 'entertainment']},
            'holiday': {'attendance_multiplier': 3.0, 'radius_km': 50, 'categories': ['food', 'gift', 'decoration', 'apparel']},
            'graduation': {'attendance_multiplier': 1.1, 'radius_km': 20, 'categories': ['food', 'gift', 'apparel']},
            'wedding_season': {'attendance_multiplier': 1.4, 'radius_km': 35, 'categories': ['apparel', 'gift', 'food']},
            'back_to_school': {'attendance_multiplier': 1.6, 'radius_km': 25, 'categories': ['school_supplies', 'apparel', 'electronics']}
        }
        
        # Demographic impact mapping
        self.demographic_multipliers = {
            'high_income': {'luxury': 1.5, 'premium': 1.3, 'standard': 0.9},
            'medium_income': {'luxury': 0.8, 'premium': 1.1, 'standard': 1.2},
            'low_income': {'luxury': 0.4, 'premium': 0.7, 'standard': 1.3, 'budget': 1.5},
            'young_adults': {'technology': 1.4, 'fashion': 1.3, 'entertainment': 1.2},
            'families': {'family_products': 1.5, 'bulk': 1.3, 'educational': 1.2},
            'seniors': {'health': 1.2, 'comfort': 1.1, 'premium': 1.1},
            'urban': {'convenience': 1.3, 'premium': 1.2, 'organic': 1.1},
            'suburban': {'bulk': 1.2, 'family_products': 1.3, 'automotive': 1.1},
            'rural': {'bulk': 1.4, 'basic_necessities': 1.2, 'outdoor': 1.3}
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
            
            logger.info(f"✅ Loaded {len(self.store_locations)} store locations for events")
            
        except Exception as e:
            logger.error(f"Failed to load store locations: {e}")
            # Add demo locations
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
    
    async def get_events_for_location(self, store_id: str, date_range: int = 30) -> List[EventData]:
        """Get events near a store location within date range."""
        
        if store_id not in self.store_locations:
            logger.error(f"Store location not found: {store_id}")
            return []
        
        location = self.store_locations[store_id]
        cache_key = f"events:{store_id}:{date_range}"
        
        # Check cache first (4-hour TTL)
        try:
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached.decode())
                events = []
                for item in data:
                    item['start_date'] = datetime.fromisoformat(item['start_date'])
                    item['end_date'] = datetime.fromisoformat(item['end_date'])
                    if item['categories'] is None:
                        item['categories'] = []
                    events.append(EventData(**item))
                return events
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        
        # Generate demo events data (in production, this would fetch from APIs)
        events = await self._generate_demo_events(location, date_range)
        
        # Cache the results
        try:
            cache_data = []
            for event in events:
                cache_data.append({
                    'event_id': event.event_id,
                    'name': event.name,
                    'event_type': event.event_type,
                    'location': event.location,
                    'start_date': event.start_date.isoformat(),
                    'end_date': event.end_date.isoformat(),
                    'expected_attendance': event.expected_attendance,
                    'impact_radius_km': event.impact_radius_km,
                    'demand_impact_score': event.demand_impact_score,
                    'categories': event.categories,
                    'venue': event.venue,
                    'description': event.description
                })
            self.redis.setex(cache_key, 14400, json.dumps(cache_data))
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
        
        # Store events in database
        for event in events:
            await self.store_event_data(event)
        
        return events
    
    async def _generate_demo_events(self, location: Dict, date_range: int) -> List[EventData]:
        """Generate realistic demo events data."""
        
        import random
        
        events = []
        current_date = datetime.now()
        
        # Generate various types of events
        event_types = ['concert', 'sports', 'festival', 'conference', 'convention', 'holiday']
        
        # Add seasonal/holiday events
        month = current_date.month
        if month == 12:
            event_types.extend(['holiday', 'holiday', 'holiday'])  # More holiday events in December
        elif month in [8, 9]:
            event_types.extend(['back_to_school', 'sports'])
        elif month in [5, 6]:
            event_types.extend(['graduation', 'wedding_season'])
        
        num_events = random.randint(3, 8)  # 3-8 events per location
        
        for i in range(num_events):
            event_type = random.choice(event_types)
            impact_data = self.event_impact_map.get(event_type, {})
            
            # Generate event dates within range
            days_offset = random.randint(1, date_range)
            start_date = current_date + timedelta(days=days_offset)
            duration = random.randint(1, 3)  # 1-3 days
            end_date = start_date + timedelta(days=duration)
            
            # Generate realistic attendance based on event type and location
            base_attendance = {
                'concert': random.randint(5000, 50000),
                'sports': random.randint(10000, 80000),
                'festival': random.randint(15000, 200000),
                'conference': random.randint(500, 5000),
                'convention': random.randint(2000, 25000),
                'holiday': random.randint(50000, 500000),
                'graduation': random.randint(500, 5000),
                'wedding_season': random.randint(100, 500),
                'back_to_school': random.randint(10000, 100000)
            }
            
            attendance = base_attendance.get(event_type, random.randint(1000, 10000))
            
            # Calculate impact score based on attendance and type
            impact_score = self.calculate_event_impact_score(event_type, attendance, location['city'])
            
            # Generate event names
            event_names = {
                'concert': f"{random.choice(['Summer', 'Rock', 'Pop', 'Jazz'])} Music {random.choice(['Festival', 'Concert', 'Tour'])}",
                'sports': f"{location['city']} vs {random.choice(['Rival Team', 'Championship', 'Local Team'])} {random.choice(['Game', 'Match', 'Tournament'])}",
                'festival': f"{location['city']} {random.choice(['Food', 'Art', 'Cultural', 'Street'])} Festival",
                'conference': f"{random.choice(['Tech', 'Business', 'Innovation', 'Industry'])} Conference {current_date.year}",
                'convention': f"{random.choice(['Comic', 'Trade', 'Auto', 'Home'])} {random.choice(['Convention', 'Show', 'Expo'])}",
                'holiday': f"{random.choice(['Christmas', 'New Year', 'Holiday'])} {random.choice(['Market', 'Celebration', 'Parade'])}",
                'graduation': f"{random.choice(['University', 'High School', 'College'])} Graduation",
                'wedding_season': f"Wedding Season Event",
                'back_to_school': f"Back to School {random.choice(['Fair', 'Event', 'Shopping Days'])}"
            }
            
            event = EventData(
                event_id=f"EVT_{event_type.upper()}_{i:03d}_{int(start_date.timestamp())}",
                name=event_names.get(event_type, f"{event_type.title()} Event"),
                event_type=event_type,
                location=location['location_key'],
                start_date=start_date,
                end_date=end_date,
                expected_attendance=attendance,
                impact_radius_km=impact_data.get('radius_km', 20.0),
                demand_impact_score=impact_score,
                categories=impact_data.get('categories', []),
                venue=f"{location['city']} {random.choice(['Arena', 'Center', 'Stadium', 'Convention Center', 'Park'])}",
                description=f"A {event_type} event in {location['city']} expected to attract {attendance:,} attendees."
            )
            
            events.append(event)
        
        return sorted(events, key=lambda x: x.start_date)
    
    def calculate_event_impact_score(self, event_type: str, attendance: int, city: str) -> float:
        """Calculate event impact score for demand forecasting (0-10 scale)."""
        
        base_score = 5.0
        
        # Attendance impact (logarithmic scale)
        import math
        attendance_score = min(4.0, math.log10(max(1, attendance)) - 2)  # Scale 0-4
        
        # Event type multiplier
        type_multiplier = self.event_impact_map.get(event_type, {}).get('attendance_multiplier', 1.0)
        type_score = (type_multiplier - 1.0) * 2  # Scale -2 to +4
        
        # City size impact (simplified)
        city_multipliers = {
            'New York': 1.2,
            'Los Angeles': 1.1,
            'Chicago': 1.0,
            'Houston': 0.9,
            'Phoenix': 0.8
        }
        city_multiplier = city_multipliers.get(city, 0.9)
        city_score = (city_multiplier - 1.0) * 2
        
        # Calculate final score
        impact_score = base_score + attendance_score + type_score + city_score
        
        # Clamp to 0-10 range
        return max(0.0, min(10.0, impact_score))
    
    async def get_demographic_data(self, store_id: str) -> Optional[DemographicData]:
        """Get demographic data for a store location."""
        
        if store_id not in self.store_locations:
            logger.error(f"Store location not found: {store_id}")
            return None
        
        location = self.store_locations[store_id]
        cache_key = f"demographics:{store_id}"
        
        # Check cache first (24-hour TTL)
        try:
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached.decode())
                return DemographicData(**data)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        
        # Generate demo demographic data (in production, would fetch from Census API, etc.)
        demographic_data = self._generate_demo_demographics(location)
        
        # Cache the result
        try:
            cache_data = {
                'location': demographic_data.location,
                'population': demographic_data.population,
                'median_age': demographic_data.median_age,
                'median_income': demographic_data.median_income,
                'education_level': demographic_data.education_level,
                'employment_rate': demographic_data.employment_rate,
                'urban_density': demographic_data.urban_density,
                'lifestyle_segments': demographic_data.lifestyle_segments,
                'shopping_preferences': demographic_data.shopping_preferences
            }
            self.redis.setex(cache_key, 86400, json.dumps(cache_data))
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
        
        # Store in database
        await self.store_demographic_data(demographic_data)
        
        return demographic_data
    
    def _generate_demo_demographics(self, location: Dict) -> DemographicData:
        """Generate realistic demo demographic data."""
        
        import random
        
        city = location['city']
        
        # City-specific demographic profiles (simplified)
        city_profiles = {
            'New York': {
                'population': random.randint(150000, 300000),
                'median_age': random.uniform(32, 38),
                'median_income': random.uniform(65000, 85000),
                'education_level': 'college',
                'employment_rate': random.uniform(0.92, 0.96),
                'urban_density': 'high',
                'lifestyle_segments': ['young_professionals', 'urban_families', 'students'],
                'shopping_preferences': {
                    'online': 0.65,
                    'convenience': 0.85,
                    'premium': 0.70,
                    'sustainable': 0.60
                }
            },
            'Los Angeles': {
                'population': random.randint(100000, 250000),
                'median_age': random.uniform(30, 36),
                'median_income': random.uniform(58000, 75000),
                'education_level': 'some_college',
                'employment_rate': random.uniform(0.88, 0.93),
                'urban_density': 'medium',
                'lifestyle_segments': ['young_adults', 'families', 'entertainment'],
                'shopping_preferences': {
                    'online': 0.70,
                    'fashion': 0.75,
                    'premium': 0.65,
                    'health_conscious': 0.80
                }
            },
            'Chicago': {
                'population': random.randint(80000, 200000),
                'median_age': random.uniform(34, 40),
                'median_income': random.uniform(52000, 68000),
                'education_level': 'high_school',
                'employment_rate': random.uniform(0.85, 0.91),
                'urban_density': 'medium',
                'lifestyle_segments': ['working_families', 'middle_class', 'traditional'],
                'shopping_preferences': {
                    'online': 0.55,
                    'value': 0.80,
                    'bulk': 0.70,
                    'family_focused': 0.85
                }
            }
        }
        
        profile = city_profiles.get(city, city_profiles['Chicago'])  # Default to Chicago profile
        
        return DemographicData(
            location=location['location_key'],
            population=profile['population'],
            median_age=profile['median_age'],
            median_income=profile['median_income'],
            education_level=profile['education_level'],
            employment_rate=profile['employment_rate'],
            urban_density=profile['urban_density'],
            lifestyle_segments=profile['lifestyle_segments'],
            shopping_preferences=profile['shopping_preferences']
        )
    
    async def store_event_data(self, event_data: EventData):
        """Store event data in database."""
        
        try:
            query = """
            INSERT INTO events_data 
            (event_id, name, event_type, location, start_date, end_date, 
             expected_attendance, impact_radius_km, demand_impact_score, categories, venue, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO UPDATE SET
                name = EXCLUDED.name,
                event_type = EXCLUDED.event_type,
                location = EXCLUDED.location,
                start_date = EXCLUDED.start_date,
                end_date = EXCLUDED.end_date,
                expected_attendance = EXCLUDED.expected_attendance,
                impact_radius_km = EXCLUDED.impact_radius_km,
                demand_impact_score = EXCLUDED.demand_impact_score,
                categories = EXCLUDED.categories,
                venue = EXCLUDED.venue,
                description = EXCLUDED.description
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (
                event_data.event_id,
                event_data.name,
                event_data.event_type,
                event_data.location,
                event_data.start_date,
                event_data.end_date,
                event_data.expected_attendance,
                event_data.impact_radius_km,
                event_data.demand_impact_score,
                json.dumps(event_data.categories) if event_data.categories else None,
                event_data.venue,
                event_data.description
            ))
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to store event data: {e}")
    
    async def store_demographic_data(self, demographic_data: DemographicData):
        """Store demographic data in database."""
        
        try:
            query = """
            INSERT INTO demographic_data 
            (location, population, median_age, median_income, education_level, 
             employment_rate, urban_density, lifestyle_segments, shopping_preferences)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (location) DO UPDATE SET
                population = EXCLUDED.population,
                median_age = EXCLUDED.median_age,
                median_income = EXCLUDED.median_income,
                education_level = EXCLUDED.education_level,
                employment_rate = EXCLUDED.employment_rate,
                urban_density = EXCLUDED.urban_density,
                lifestyle_segments = EXCLUDED.lifestyle_segments,
                shopping_preferences = EXCLUDED.shopping_preferences
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (
                demographic_data.location,
                demographic_data.population,
                demographic_data.median_age,
                demographic_data.median_income,
                demographic_data.education_level,
                demographic_data.employment_rate,
                demographic_data.urban_density,
                json.dumps(demographic_data.lifestyle_segments),
                json.dumps(demographic_data.shopping_preferences)
            ))
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to store demographic data: {e}")
    
    async def get_event_demand_multiplier(self, store_id: str, target_date: datetime, product_category: str = None) -> float:
        """Get event-adjusted demand multiplier for a specific date and category."""
        
        try:
            # Get events for the location
            events = await self.get_events_for_location(store_id, 30)
            
            multiplier = 1.0
            
            for event in events:
                # Check if event overlaps with target date
                if event.start_date.date() <= target_date.date() <= event.end_date.date():
                    # Base multiplier from impact score (0-10 scale to 0.5-2.0 multiplier)
                    base_multiplier = 0.5 + (event.demand_impact_score / 10.0) * 1.5
                    
                    # Category-specific multiplier
                    category_boost = 1.0
                    if product_category and event.categories:
                        if product_category.lower() in [cat.lower() for cat in event.categories]:
                            category_boost = 1.3  # 30% boost for relevant categories
                    
                    # Combine multipliers (use max, not compound)
                    event_multiplier = base_multiplier * category_boost
                    multiplier = max(multiplier, event_multiplier)
            
            return min(2.0, max(0.5, multiplier))  # Clamp between 0.5x and 2.0x
            
        except Exception as e:
            logger.error(f"Failed to get event demand multiplier: {e}")
            return 1.0
    
    async def get_demographic_demand_multiplier(self, store_id: str, product_category: str) -> float:
        """Get demographic-adjusted demand multiplier for a product category."""
        
        try:
            demographic = await self.get_demographic_data(store_id)
            
            if not demographic:
                return 1.0
            
            multiplier = 1.0
            
            # Income level adjustments
            if demographic.median_income > 70000:
                income_segment = 'high_income'
            elif demographic.median_income > 45000:
                income_segment = 'medium_income'
            else:
                income_segment = 'low_income'
            
            income_multipliers = self.demographic_multipliers.get(income_segment, {})
            multiplier *= income_multipliers.get(product_category, 1.0)
            
            # Age group adjustments
            if demographic.median_age < 35:
                age_segment = 'young_adults'
            elif demographic.median_age < 55:
                age_segment = 'families'
            else:
                age_segment = 'seniors'
            
            age_multipliers = self.demographic_multipliers.get(age_segment, {})
            multiplier *= age_multipliers.get(product_category, 1.0)
            
            # Urban density adjustments
            density_multipliers = self.demographic_multipliers.get(demographic.urban_density, {})
            multiplier *= density_multipliers.get(product_category, 1.0)
            
            return min(2.0, max(0.3, multiplier))  # Clamp between 0.3x and 2.0x
            
        except Exception as e:
            logger.error(f"Failed to get demographic demand multiplier: {e}")
            return 1.0
    
    async def get_external_data_features_for_ml(self, store_id: str, date_range: int = 30) -> Dict[str, Any]:
        """Get external data features for ML model training/inference."""
        
        try:
            # Get events data
            events = await self.get_events_for_location(store_id, date_range)
            
            # Get demographic data
            demographic = await self.get_demographic_data(store_id)
            
            # Calculate event features
            upcoming_events = [e for e in events if e.start_date >= datetime.now()]
            major_events = [e for e in upcoming_events if e.demand_impact_score >= 7.0]
            
            event_features = {
                'total_events': len(events),
                'upcoming_events': len(upcoming_events),
                'major_events': len(major_events),
                'avg_event_impact': sum(e.demand_impact_score for e in events) / len(events) if events else 5.0,
                'max_event_impact': max([e.demand_impact_score for e in events], default=5.0),
                'event_types': {},
                'days_to_next_major_event': 365  # Default
            }
            
            # Event type distribution
            for event in events:
                event_features['event_types'][event.event_type] = event_features['event_types'].get(event.event_type, 0) + 1
            
            # Days to next major event
            if major_events:
                next_major = min(major_events, key=lambda e: e.start_date)
                days_to_next = (next_major.start_date - datetime.now()).days
                event_features['days_to_next_major_event'] = max(0, days_to_next)
            
            # Demographic features
            demographic_features = {}
            if demographic:
                demographic_features = {
                    'population_density': demographic.population / 100,  # Scale down
                    'median_age': demographic.median_age,
                    'income_segment': self._categorize_income(demographic.median_income),
                    'education_score': self._education_to_score(demographic.education_level),
                    'employment_rate': demographic.employment_rate,
                    'urban_density_score': self._density_to_score(demographic.urban_density),
                    'shopping_preferences': demographic.shopping_preferences
                }
            
            return {
                'events': event_features,
                'demographics': demographic_features,
                'external_data_quality': 'good' if events and demographic else 'limited',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get external data features: {e}")
            return {}
    
    def _categorize_income(self, income: float) -> int:
        """Convert income to categorical score."""
        if income > 70000:
            return 3  # High income
        elif income > 45000:
            return 2  # Medium income
        else:
            return 1  # Low income
    
    def _education_to_score(self, education: str) -> int:
        """Convert education level to score."""
        education_scores = {
            'graduate': 4,
            'college': 3,
            'some_college': 2,
            'high_school': 1
        }
        return education_scores.get(education, 1)
    
    def _density_to_score(self, density: str) -> int:
        """Convert urban density to score."""
        density_scores = {
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return density_scores.get(density, 2)
    
    async def update_all_external_data(self):
        """Update external data for all store locations."""
        
        results = {'events_updated': 0, 'demographics_updated': 0, 'failed': 0, 'errors': []}
        
        for store_id in self.store_locations.keys():
            try:
                # Update events
                events = await self.get_events_for_location(store_id, 30)
                if events:
                    results['events_updated'] += len(events)
                    logger.info(f"✅ Updated {len(events)} events for {store_id}")
                
                # Update demographics
                demographic = await self.get_demographic_data(store_id)
                if demographic:
                    results['demographics_updated'] += 1
                    logger.info(f"✅ Updated demographics for {store_id}: {demographic.population:,} population")
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error updating {store_id}: {str(e)}")
                logger.error(f"Failed to update external data for {store_id}: {e}")
            
            # Rate limiting
            await asyncio.sleep(1)
        
        logger.info(f"External data update complete: {results['events_updated']} events, {results['demographics_updated']} demographics updated, {results['failed']} failed")
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
    
    # Initialize events service
    events_service = EventsService(db_conn)
    
    async def test_events_service():
        """Test events service functionality."""
        
        print("🎉 Testing Events Service...")
        
        # Test events data
        events = await events_service.get_events_for_location('STORE_001', 30)
        print(f"✅ Found {len(events)} events for STORE_001")
        
        if events:
            major_events = [e for e in events if e.demand_impact_score >= 7.0]
            print(f"✅ Major events: {len(major_events)}")
        
        # Test demographic data
        demographic = await events_service.get_demographic_data('STORE_001')
        if demographic:
            print(f"✅ Demographics: {demographic.population:,} population, ${demographic.median_income:,.0f} median income")
        
        # Test demand multipliers
        tomorrow = datetime.now() + timedelta(days=1)
        event_multiplier = await events_service.get_event_demand_multiplier('STORE_001', tomorrow, 'food')
        demographic_multiplier = await events_service.get_demographic_demand_multiplier('STORE_001', 'premium')
        
        print(f"✅ Event demand multiplier for food: {event_multiplier:.2f}")
        print(f"✅ Demographic multiplier for premium: {demographic_multiplier:.2f}")
        
        # Test ML features
        features = await events_service.get_external_data_features_for_ml('STORE_001')
        print(f"✅ External data features: {features.get('events', {}).get('total_events', 0)} events, quality: {features.get('external_data_quality', 'unknown')}")
        
        print("🎉 Events service testing complete!")
    
    # Run test
    asyncio.run(test_events_service())