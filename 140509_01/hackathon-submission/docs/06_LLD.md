# Low Level Design (LLD)
## AI-Powered Retail Inventory Optimization System

*Building upon PRD, FRD, NFRD, Architecture Diagram, and HLD for detailed implementation specifications and code-level design*

## ETVX Framework

### ENTRY CRITERIA
- ✅ HLD completed with detailed component specifications
- ✅ API contracts and database schemas finalized
- ✅ Algorithm designs and performance characteristics defined
- ✅ Development environment and coding standards established
- ✅ Code review and testing processes defined

### TASK
Transform high-level design into implementation-ready code specifications including class definitions, method signatures, data structures, algorithms, error handling, logging, and detailed implementation logic for all system components.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All HLD components have corresponding code implementations
- [ ] Class designs follow SOLID principles and design patterns
- [ ] Method signatures match API contract specifications
- [ ] Data structures optimize for performance requirements
- [ ] Error handling covers all identified failure scenarios
- [ ] Code follows established coding standards and conventions

**Validation Criteria:**
- [ ] Implementation logic satisfies all functional requirements
- [ ] Code structure supports non-functional requirements
- [ ] Algorithm implementations meet performance benchmarks
- [ ] Security implementations follow best practices
- [ ] Code review completed by senior developers
- [ ] Unit test specifications defined for all components

### EXIT CRITERIA
- ✅ Complete code specifications for all system components
- ✅ Implementation-ready class and method definitions
- ✅ Detailed algorithm implementations with complexity analysis
- ✅ Error handling and logging specifications completed
- ✅ Foundation established for pseudocode and actual implementation

---

### Reference to Previous Documents
This LLD provides implementation-ready code specifications based on **ALL** previous requirements:
- **PRD Success Metrics** → Code implementations targeting 98%+ service levels, <3s response times
- **PRD Target Users** → User-specific API endpoints and interface implementations
- **FRD Functional Requirements (FR-001 to FR-032)** → Direct code implementation of each functional requirement
- **NFRD Performance Requirements** → Optimized algorithms, caching implementations, database queries
- **NFRD Security Requirements** → Authentication classes, encryption methods, RBAC implementation
- **Architecture Diagram Technology Stack** → Specific framework implementations (FastAPI, Kafka, PostgreSQL)
- **HLD System Components** → Detailed class structures, method signatures, data flow implementations
- **HLD API Design** → RESTful endpoint implementations with request/response models
- **HLD Database Design** → SQLAlchemy models, repository patterns, query optimizations
- **HLD ML Engine Design** → LSTM/ARIMA/Prophet model implementations with ensemble methods

### 1. Data Ingestion Implementation

#### 1.1 Kafka Producer Implementation
```python
class POSDataProducer:
    def __init__(self, bootstrap_servers, topic_name):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8')
        )
        self.topic = topic_name
    
    def send_transaction(self, transaction_data):
        key = f"{transaction_data['store_id']}_{transaction_data['product_id']}"
        self.producer.send(self.topic, key=key, value=transaction_data)
```

#### 1.2 Stream Processing with Kafka Streams
```python
class SalesDataProcessor:
    def process_sales_stream(self):
        # Real-time aggregation and feature extraction
        sales_stream = self.builder.stream("sales-transactions")
        
        # Windowed aggregations for real-time metrics
        hourly_sales = sales_stream.group_by_key().window_by(
            TimeWindows.of(Duration.of_hours(1))
        ).aggregate(
            initializer=lambda: {"total_quantity": 0, "total_revenue": 0},
            aggregator=self.aggregate_sales
        )
        
        return hourly_sales.to_stream()
```

### 2. ML Model Implementation

#### 2.1 LSTM Demand Forecasting Model
```python
class LSTMForecastModel:
    def __init__(self, sequence_length=30, features=10):
        self.model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(sequence_length, features)),
            Dropout(0.2),
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(1, activation='linear')
        ])
        
    def prepare_sequences(self, data, sequence_length):
        X, y = [], []
        for i in range(len(data) - sequence_length):
            X.append(data[i:(i + sequence_length)])
            y.append(data[i + sequence_length])
        return np.array(X), np.array(y)
    
    def train(self, training_data, validation_data):
        self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        history = self.model.fit(
            training_data[0], training_data[1],
            validation_data=validation_data,
            epochs=100, batch_size=32,
            callbacks=[EarlyStopping(patience=10)]
        )
        return history
```

#### 2.2 Prophet Model Implementation
```python
class ProphetForecastModel:
    def __init__(self):
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        
    def add_external_regressors(self, weather_data, events_data):
        self.model.add_regressor('temperature')
        self.model.add_regressor('precipitation')
        self.model.add_regressor('is_holiday')
        
    def fit_and_predict(self, historical_data, periods=30):
        df = self.prepare_prophet_data(historical_data)
        self.model.fit(df)
        
        future = self.model.make_future_dataframe(periods=periods)
        forecast = self.model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
```

### 3. Inventory Optimization Algorithms

#### 3.1 EOQ Calculation Implementation
```python
class InventoryOptimizer:
    def calculate_eoq(self, annual_demand, ordering_cost, holding_cost):
        """Economic Order Quantity calculation"""
        return math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
    
    def calculate_reorder_point(self, daily_demand, lead_time_days, safety_stock):
        """Reorder point with safety stock"""
        return (daily_demand * lead_time_days) + safety_stock
    
    def calculate_safety_stock(self, demand_std, lead_time_std, service_level=0.98):
        """Safety stock calculation using normal distribution"""
        z_score = norm.ppf(service_level)
        return z_score * math.sqrt(
            (lead_time_std ** 2 * demand_std ** 2) + 
            (demand_std ** 2 * lead_time_std ** 2)
        )
```

#### 3.2 Dynamic Pricing and Promotion Impact
```python
class PromotionOptimizer:
    def calculate_promotion_impact(self, base_demand, discount_rate, price_elasticity):
        """Calculate demand lift from promotional pricing"""
        demand_multiplier = (1 + discount_rate) ** price_elasticity
        return base_demand * demand_multiplier
    
    def optimize_markdown_strategy(self, current_stock, days_remaining, target_margin):
        """Dynamic markdown optimization for slow-moving inventory"""
        daily_markdown = self.calculate_optimal_markdown(
            current_stock, days_remaining, target_margin
        )
        return daily_markdown
```

### 4. API Implementation

#### 4.1 FastAPI Inventory Service
```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

app = FastAPI(title="Inventory Optimization API")

@app.get("/api/v1/inventory/current/{store_id}")
async def get_current_inventory(
    store_id: int, 
    db: Session = Depends(get_db)
):
    inventory = db.query(Inventory).filter(
        Inventory.store_id == store_id
    ).all()
    
    return [InventoryResponse.from_orm(item) for item in inventory]

@app.get("/api/v1/forecasts/{product_id}")
async def get_demand_forecast(
    product_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    forecast_service = ForecastService(db)
    predictions = await forecast_service.get_predictions(product_id, days)
    
    return ForecastResponse(
        product_id=product_id,
        predictions=predictions,
        confidence_interval=predictions.get('confidence_interval')
    )
```

#### 4.2 Real-time Recommendation Engine
```python
class RecommendationEngine:
    def __init__(self, db_session, ml_models):
        self.db = db_session
        self.models = ml_models
        
    async def generate_reorder_recommendations(self, store_id):
        current_inventory = self.get_current_inventory(store_id)
        recommendations = []
        
        for item in current_inventory:
            forecast = await self.models['lstm'].predict(item.product_id)
            optimal_stock = self.calculate_optimal_stock_level(
                item, forecast
            )
            
            if item.current_stock < optimal_stock * 0.8:  # 80% threshold
                recommendation = ReorderRecommendation(
                    product_id=item.product_id,
                    current_stock=item.current_stock,
                    recommended_order=optimal_stock - item.current_stock,
                    urgency_level=self.calculate_urgency(item, forecast)
                )
                recommendations.append(recommendation)
                
        return recommendations
```

### 5. Database Implementation

#### 5.1 SQLAlchemy Models
```python
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    cost = Column(Numeric(10, 2))
    price = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    inventory_items = relationship("Inventory", back_populates="product")

class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    store_id = Column(Integer, ForeignKey("stores.id"))
    current_stock = Column(Integer, default=0)
    reserved_stock = Column(Integer, default=0)
    reorder_point = Column(Integer)
    max_stock_level = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    store = relationship("Store", back_populates="inventory_items")
```

#### 5.2 Repository Pattern Implementation
```python
class InventoryRepository:
    def __init__(self, db_session):
        self.db = db_session
        
    def get_by_store_and_product(self, store_id: int, product_id: int):
        return self.db.query(Inventory).filter(
            Inventory.store_id == store_id,
            Inventory.product_id == product_id
        ).first()
        
    def update_stock_level(self, inventory_id: int, new_stock: int):
        inventory = self.db.query(Inventory).get(inventory_id)
        inventory.current_stock = new_stock
        inventory.last_updated = datetime.utcnow()
        self.db.commit()
        return inventory
        
    def get_low_stock_items(self, store_id: int, threshold_percentage: float = 0.2):
        return self.db.query(Inventory).filter(
            Inventory.store_id == store_id,
            Inventory.current_stock <= (Inventory.reorder_point * threshold_percentage)
        ).all()
```

### 6. Caching Implementation

#### 6.1 Redis Cache Service
```python
class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def get_forecast_cache(self, product_id: int, days: int):
        cache_key = f"forecast:{product_id}:{days}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
        
    async def set_forecast_cache(self, product_id: int, days: int, forecast_data, ttl=3600):
        cache_key = f"forecast:{product_id}:{days}"
        await self.redis.setex(
            cache_key, 
            ttl, 
            json.dumps(forecast_data, default=str)
        )
```

### 7. Background Job Implementation

#### 7.1 Celery Task Implementation
```python
from celery import Celery

app = Celery('inventory_optimizer')

@app.task
def update_demand_forecasts():
    """Daily task to update demand forecasts for all products"""
    db = get_db_session()
    ml_service = MLService()
    
    products = db.query(Product).all()
    
    for product in products:
        try:
            forecast = ml_service.generate_forecast(product.id)
            save_forecast_to_db(product.id, forecast)
        except Exception as e:
            logger.error(f"Failed to update forecast for product {product.id}: {e}")
            
@app.task
def check_reorder_alerts():
    """Hourly task to check for reorder alerts"""
    inventory_service = InventoryService()
    notification_service = NotificationService()
    
    low_stock_items = inventory_service.get_low_stock_items()
    
    for item in low_stock_items:
        alert = create_reorder_alert(item)
        notification_service.send_alert(alert)
```
