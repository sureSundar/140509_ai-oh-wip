"""
Demo Data Generator - AI-Powered Retail Inventory Optimization
Generates realistic sample data for system demonstration.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import json
import random
import uuid
from faker import Faker
import requests
import time

fake = Faker()

class RetailDataGenerator:
    def __init__(self):
        self.start_date = date(2023, 1, 1)
        self.end_date = date(2024, 1, 31)
        self.stores = []
        self.products = []
        self.suppliers = []
        self.categories = []
        
    def generate_stores(self, num_stores=10):
        """Generate realistic store data."""
        cities = [
            ("New York", "NY", 40.7128, -74.0060, 8000, 75000),
            ("Los Angeles", "CA", 34.0522, -118.2437, 3000, 65000),
            ("Chicago", "IL", 41.8781, -87.6298, 4500, 70000),
            ("Houston", "TX", 29.7604, -95.3698, 2500, 60000),
            ("Phoenix", "AZ", 33.4484, -112.0740, 1800, 58000),
            ("Philadelphia", "PA", 39.9526, -75.1652, 4200, 68000),
            ("San Antonio", "TX", 29.4241, -98.4936, 1600, 55000),
            ("San Diego", "CA", 32.7157, -117.1611, 2200, 72000),
            ("Dallas", "TX", 32.7767, -96.7970, 2100, 62000),
            ("San Jose", "CA", 37.3382, -121.8863, 2800, 95000)
        ]
        
        for i in range(num_stores):
            city_data = cities[i % len(cities)]
            store = {
                "id": f"STORE_{i+1:03d}",
                "name": f"{city_data[0]} - {fake.street_name()} Store",
                "address": fake.street_address(),
                "city": city_data[0],
                "state": city_data[1],
                "zip_code": fake.zipcode(),
                "latitude": city_data[2] + random.uniform(-0.5, 0.5),
                "longitude": city_data[3] + random.uniform(-0.5, 0.5),
                "population_density": city_data[4] + random.randint(-500, 500),
                "avg_income": city_data[5] + random.randint(-5000, 5000),
                "store_size_sqft": random.randint(5000, 15000),
                "opening_date": fake.date_between(start_date='-5y', end_date='-1y')
            }
            self.stores.append(store)
            
        return self.stores
    
    def generate_suppliers(self, num_suppliers=15):
        """Generate supplier data."""
        supplier_types = [
            ("Electronics Corp", "Electronics", 14, 100),
            ("Fashion Wholesale", "Clothing", 7, 50),
            ("Home Goods Dist", "Home & Garden", 10, 75),
            ("Sports Equipment Co", "Sports", 12, 25),
            ("Beauty Supply Inc", "Beauty", 5, 30),
            ("Tech Gadgets Ltd", "Electronics", 21, 200),
            ("Outdoor Gear Co", "Sports", 15, 40),
            ("Kitchen Supply", "Home & Garden", 8, 60),
            ("Fashion Trends", "Clothing", 10, 35),
            ("Health Products", "Health", 7, 25)
        ]
        
        for i in range(num_suppliers):
            supplier_type = supplier_types[i % len(supplier_types)]
            supplier = {
                "id": f"SUPPLIER_{i+1:03d}",
                "name": f"{supplier_type[0]} {i+1}",
                "category_focus": supplier_type[1],
                "contact_email": fake.company_email(),
                "contact_phone": fake.phone_number(),
                "lead_time_days": supplier_type[2] + random.randint(-3, 3),
                "minimum_order_qty": supplier_type[3] + random.randint(-20, 20),
                "reliability_score": random.uniform(0.85, 0.99),
                "quality_score": random.uniform(0.88, 0.98)
            }
            self.suppliers.append(supplier)
            
        return self.suppliers
    
    def generate_categories(self):
        """Generate product categories."""
        categories = [
            {"id": "CAT_001", "name": "Electronics", "seasonality_factor": 1.0},
            {"id": "CAT_002", "name": "Clothing", "seasonality_factor": 1.5},
            {"id": "CAT_003", "name": "Home & Garden", "seasonality_factor": 1.2},
            {"id": "CAT_004", "name": "Sports & Outdoors", "seasonality_factor": 1.3},
            {"id": "CAT_005", "name": "Beauty & Personal Care", "seasonality_factor": 1.1},
            {"id": "CAT_006", "name": "Health & Wellness", "seasonality_factor": 1.0},
            {"id": "CAT_007", "name": "Books & Media", "seasonality_factor": 1.2},
            {"id": "CAT_008", "name": "Toys & Games", "seasonality_factor": 1.8},
            {"id": "CAT_009", "name": "Automotive", "seasonality_factor": 1.1},
            {"id": "CAT_010", "name": "Pet Supplies", "seasonality_factor": 1.0}
        ]
        
        self.categories = categories
        return categories
    
    def generate_products(self, num_products=500):
        """Generate product catalog."""
        if not self.categories:
            self.generate_categories()
        if not self.suppliers:
            self.generate_suppliers()
            
        product_templates = {
            "Electronics": [
                ("Wireless Headphones", 25, 49.99),
                ("Smartphone Case", 5, 19.99),
                ("Bluetooth Speaker", 18, 39.99),
                ("USB Cable", 3, 9.99),
                ("Power Bank", 12, 29.99),
                ("Tablet Stand", 8, 24.99),
                ("Screen Protector", 2, 14.99),
                ("Car Charger", 6, 16.99)
            ],
            "Clothing": [
                ("T-Shirt", 8, 24.99),
                ("Jeans", 20, 59.99),
                ("Hoodie", 15, 44.99),
                ("Sneakers", 35, 89.99),
                ("Jacket", 28, 79.99),
                ("Dress", 22, 49.99),
                ("Shorts", 12, 29.99),
                ("Socks", 3, 12.99)
            ],
            "Home & Garden": [
                ("Coffee Mug", 4, 12.99),
                ("Picture Frame", 7, 18.99),
                ("Throw Pillow", 11, 24.99),
                ("Plant Pot", 8, 16.99),
                ("Candle", 6, 19.99),
                ("Kitchen Towel", 3, 9.99),
                ("Storage Box", 9, 22.99),
                ("Wall Clock", 12, 34.99)
            ]
        }
        
        for i in range(num_products):
            category = random.choice(self.categories)
            # Find suppliers for this category, or fallback to any supplier
            matching_suppliers = [s for s in self.suppliers if s['category_focus'] == category['name']]
            supplier = random.choice(matching_suppliers if matching_suppliers else self.suppliers)
            
            if category['name'] in product_templates:
                template = random.choice(product_templates[category['name']])
                base_name = template[0]
                base_cost = template[1]
                base_price = template[2]
            else:
                base_name = fake.word().title() + " " + fake.word().title()
                base_cost = random.uniform(5, 50)
                base_price = base_cost * random.uniform(1.5, 3.0)
            
            # Add variation to products
            variations = ["Pro", "Plus", "Deluxe", "Classic", "Premium", "Standard"]
            colors = ["Black", "White", "Blue", "Red", "Green", "Gray"]
            
            product_name = f"{base_name}"
            if random.random() > 0.7:
                product_name += f" {random.choice(variations)}"
            if category['name'] in ["Clothing", "Electronics"] and random.random() > 0.6:
                product_name += f" - {random.choice(colors)}"
                
            product = {
                "id": f"PROD_{i+1:04d}",
                "sku": f"SKU{random.randint(100000, 999999)}",
                "name": product_name,
                "category_id": category["id"],
                "category_name": category["name"],
                "supplier_id": supplier["id"],
                "cost_price": round(base_cost * random.uniform(0.8, 1.2), 2),
                "selling_price": round(base_price * random.uniform(0.9, 1.1), 2),
                "weight_kg": round(random.uniform(0.1, 5.0), 2),
                "dimensions_cm": f"{random.randint(5,50)}x{random.randint(5,50)}x{random.randint(2,20)}",
                "is_seasonal": category["seasonality_factor"] > 1.2,
                "launch_date": fake.date_between(start_date='-2y', end_date='-30d')
            }
            
            # Calculate margin
            product["margin_percent"] = round(((product["selling_price"] - product["cost_price"]) / product["selling_price"]) * 100, 1)
            
            self.products.append(product)
            
        return self.products
    
    def generate_sales_data(self, num_days=395):
        """Generate realistic sales transaction data."""
        if not self.stores or not self.products:
            raise ValueError("Must generate stores and products first")
            
        sales_data = []
        
        # Generate date range
        dates = pd.date_range(start=self.start_date, periods=num_days, freq='D')
        
        for date_val in dates:
            day_of_week = date_val.weekday()  # 0 = Monday, 6 = Sunday
            day_of_year = date_val.timetuple().tm_yday
            
            # Store-level patterns
            for store in self.stores:
                store_factor = random.uniform(0.8, 1.2)  # Store performance variation
                
                # Product-level sales
                products_to_sell = random.sample(self.products, random.randint(50, 150))
                
                for product in products_to_sell:
                    # Base demand calculation
                    category = next(c for c in self.categories if c["id"] == product["category_id"])
                    
                    # Factors affecting demand
                    base_demand = random.uniform(1, 15)
                    
                    # Day of week effect (higher on weekends)
                    day_effect = 1.2 if day_of_week >= 5 else 1.0
                    
                    # Seasonal effect
                    seasonal_effect = 1 + 0.3 * np.sin(2 * np.pi * day_of_year / 365) * (category["seasonality_factor"] - 1)
                    
                    # Holiday effects
                    holiday_effect = 1.0
                    if day_of_year > 330 or day_of_year < 10:  # Christmas/New Year
                        holiday_effect = 1.5
                    elif 150 < day_of_year < 170:  # Summer season
                        if category["name"] in ["Sports & Outdoors", "Clothing"]:
                            holiday_effect = 1.3
                    elif 250 < day_of_year < 270:  # Back to school
                        if category["name"] in ["Electronics", "Books & Media"]:
                            holiday_effect = 1.4
                    
                    # Weather effect (simplified)
                    weather_effect = random.uniform(0.9, 1.1)
                    
                    # Calculate final demand
                    final_demand = base_demand * store_factor * day_effect * seasonal_effect * holiday_effect * weather_effect
                    
                    # Convert to discrete sales
                    if final_demand > 0:
                        quantity = max(1, int(np.random.poisson(final_demand)))
                        
                        # Generate individual transactions (sometimes multiple per product per day)
                        num_transactions = random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
                        
                        for _ in range(num_transactions):
                            transaction_qty = max(1, quantity // num_transactions + random.randint(-1, 1))
                            if transaction_qty > 0:
                                # Add some price variation (discounts, promotions)
                                price_variation = random.uniform(0.9, 1.0)
                                unit_price = round(product["selling_price"] * price_variation, 2)
                                
                                transaction = {
                                    "id": str(uuid.uuid4()),
                                    "product_id": product["id"],
                                    "store_id": store["id"],
                                    "quantity": transaction_qty,
                                    "unit_price": unit_price,
                                    "total_amount": round(transaction_qty * unit_price, 2),
                                    "discount_amount": round((product["selling_price"] - unit_price) * transaction_qty, 2),
                                    "transaction_timestamp": date_val.strftime("%Y-%m-%d") + f" {random.randint(9, 21):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
                                    "customer_id": f"CUST_{random.randint(1000, 9999)}",
                                    "payment_method": random.choice(["credit_card", "debit_card", "cash", "mobile_pay"])
                                }
                                
                                sales_data.append(transaction)
        
        return sales_data
    
    def generate_weather_data(self):
        """Generate weather data for each store location."""
        if not self.stores:
            raise ValueError("Must generate stores first")
            
        weather_data = []
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq='D')
        
        for store in self.stores:
            for date_val in dates:
                day_of_year = date_val.timetuple().tm_yday
                
                # Seasonal temperature pattern based on latitude
                base_temp = 20 + 10 * np.sin(2 * np.pi * (day_of_year - 81) / 365)  # Peak around summer
                
                # Add location variation
                latitude_effect = (abs(store["latitude"]) - 30) * 0.5  # Colder at higher latitudes
                temp_avg = base_temp - latitude_effect + np.random.normal(0, 3)
                
                weather = {
                    "store_id": store["id"],
                    "date": date_val.strftime("%Y-%m-%d"),
                    "temperature_avg": round(temp_avg, 1),
                    "temperature_min": round(temp_avg - random.uniform(3, 8), 1),
                    "temperature_max": round(temp_avg + random.uniform(3, 8), 1),
                    "humidity": round(random.uniform(30, 90), 1),
                    "precipitation_mm": max(0, round(np.random.exponential(2), 1)),
                    "weather_condition": random.choice(["sunny", "cloudy", "rainy", "partly_cloudy", "overcast"]),
                    "wind_speed_kmh": round(random.uniform(5, 25), 1)
                }
                
                weather_data.append(weather)
                
        return weather_data
    
    def generate_events_data(self):
        """Generate local events data."""
        if not self.stores:
            raise ValueError("Must generate stores first")
            
        events_data = []
        
        # Define event types and their typical impact
        event_types = [
            ("Holiday Sale", "promotion", 1.5, 3),
            ("Black Friday", "promotion", 2.5, 1),
            ("Back to School", "seasonal", 1.3, 14),
            ("Christmas Season", "seasonal", 1.8, 30),
            ("Summer Festival", "event", 1.2, 3),
            ("Sports Championship", "event", 1.4, 1),
            ("Concert", "event", 1.1, 1),
            ("Trade Show", "business", 0.9, 2),
            ("School Holiday", "seasonal", 1.2, 7),
            ("Weather Emergency", "weather", 0.7, 2)
        ]
        
        for store in self.stores:
            # Generate 20-40 events per store over the year
            num_events = random.randint(20, 40)
            
            for _ in range(num_events):
                event_type = random.choice(event_types)
                start_date = fake.date_between(start_date=self.start_date, end_date=self.end_date)
                duration = event_type[3] + random.randint(-1, 2)
                end_date = start_date + timedelta(days=max(1, duration))
                
                event = {
                    "id": str(uuid.uuid4()),
                    "name": f"{event_type[0]} - {store['city']}",
                    "event_type": event_type[1],
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "store_id": store["id"],
                    "impact_factor": round(event_type[2] + random.uniform(-0.1, 0.1), 2),
                    "description": f"{event_type[0]} event in {store['city']} area",
                    "expected_attendance": random.randint(100, 10000) if event_type[1] == "event" else None
                }
                
                events_data.append(event)
                
        return events_data
    
    def save_data_files(self, output_dir="demo-data"):
        """Save all generated data to JSON files."""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save each dataset
        datasets = {
            "stores.json": self.stores,
            "suppliers.json": self.suppliers,
            "categories.json": self.categories,
            "products.json": self.products,
        }
        
        for filename, data in datasets.items():
            with open(f"{output_dir}/{filename}", 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        # Generate and save transaction data
        print("Generating sales transactions...")
        sales_data = self.generate_sales_data()
        with open(f"{output_dir}/sales_transactions.json", 'w') as f:
            json.dump(sales_data, f, indent=2, default=str)
        
        # Generate and save weather data
        print("Generating weather data...")
        weather_data = self.generate_weather_data()
        with open(f"{output_dir}/weather_data.json", 'w') as f:
            json.dump(weather_data, f, indent=2, default=str)
        
        # Generate and save events data
        print("Generating events data...")
        events_data = self.generate_events_data()
        with open(f"{output_dir}/events_data.json", 'w') as f:
            json.dump(events_data, f, indent=2, default=str)
        
        # Create summary report
        summary = {
            "generation_timestamp": datetime.now().isoformat(),
            "data_summary": {
                "stores": len(self.stores),
                "suppliers": len(self.suppliers),
                "categories": len(self.categories),
                "products": len(self.products),
                "sales_transactions": len(sales_data),
                "weather_records": len(weather_data),
                "events": len(events_data)
            },
            "date_range": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat()
            }
        }
        
        with open(f"{output_dir}/data_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📊 Demo data generated successfully!")
        print(f"📁 Files saved to: {output_dir}/")
        print(f"🏪 Stores: {len(self.stores)}")
        print(f"📦 Products: {len(self.products)}")
        print(f"🛒 Transactions: {len(sales_data):,}")
        print(f"🌤️ Weather Records: {len(weather_data):,}")
        print(f"🎉 Events: {len(events_data)}")
        
        return output_dir

def main():
    """Generate complete demo dataset."""
    print("🔄 Generating RetailAI Demo Data...")
    print("=" * 50)
    
    generator = RetailDataGenerator()
    
    print("🏪 Generating stores...")
    generator.generate_stores(10)
    
    print("🏭 Generating suppliers...")
    generator.generate_suppliers(15)
    
    print("📋 Generating categories...")
    generator.generate_categories()
    
    print("📦 Generating products...")
    generator.generate_products(500)
    
    print("💾 Saving all data files...")
    output_dir = generator.save_data_files()
    
    print(f"\n✅ Demo data generation complete!")
    print(f"📂 Data files available in: {output_dir}/")
    print("\nNext steps:")
    print("1. Run: ./scripts/setup.sh")
    print("2. Run: python demo/load-demo-data.py")
    print("3. Access dashboards at http://localhost:3001")

if __name__ == "__main__":
    main()