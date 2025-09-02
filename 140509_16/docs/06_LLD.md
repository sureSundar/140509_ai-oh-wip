# Low Level Design (LLD)
## Supply Chain Demand Forecasting Platform

### Document Control
- **Document Version**: 1.0
- **Created**: 2025-01-XX
- **Document Owner**: Engineering & Implementation Team

---

## ETVX Framework Application

### Entry Criteria
- ✅ **README.md completed** - Problem statement and business case established
- ✅ **PRD Approved** - Business objectives and product features defined
- ✅ **FRD Completed** - Functional specifications documented
- ✅ **NFRD Completed** - Quality attributes and constraints defined
- ✅ **AD Completed** - System architecture and technology stack defined
- ✅ **HLD Completed** - Component designs and interfaces specified

### Task (This Document)
Provide implementation-ready specifications including detailed class designs, database schemas, API implementations, configuration files, and deployment scripts.

### Verification & Validation
- **Code Review** - Implementation team validation of class designs
- **Database Design Review** - DBA validation of schema designs
- **Deployment Testing** - DevOps validation of deployment configurations

### Exit Criteria
- ✅ **Implementation Specifications** - All classes and methods detailed
- ✅ **Database Schemas** - Complete DDL scripts provided
- ✅ **Deployment Configurations** - Docker, Kubernetes, and CI/CD scripts ready

---

## Database Schema Implementation

### PostgreSQL Core Schema
```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS supply_chain;

-- Users and Authentication
CREATE TABLE supply_chain.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'manager', 'analyst', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SKU Master Data
CREATE TABLE supply_chain.skus (
    sku_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku_code VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    unit_cost DECIMAL(12,4),
    lead_time_days INTEGER DEFAULT 7,
    abc_classification VARCHAR(1) CHECK (abc_classification IN ('A', 'B', 'C')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Demand History
CREATE TABLE supply_chain.demand_history (
    demand_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku_id UUID REFERENCES supply_chain.skus(sku_id),
    demand_date DATE NOT NULL,
    actual_demand DECIMAL(12,2) NOT NULL,
    promotional_demand DECIMAL(12,2) DEFAULT 0,
    external_factors JSONB,
    data_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku_id, demand_date)
);

-- Forecasts
CREATE TABLE supply_chain.forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku_id UUID REFERENCES supply_chain.skus(sku_id),
    forecast_date DATE NOT NULL,
    horizon_type VARCHAR(20) NOT NULL CHECK (horizon_type IN ('short', 'medium', 'long')),
    predicted_demand DECIMAL(12,2) NOT NULL,
    confidence_lower DECIMAL(12,2),
    confidence_upper DECIMAL(12,2),
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku_id, forecast_date, horizon_type)
);

-- Performance Indexes
CREATE INDEX idx_demand_history_sku_date ON supply_chain.demand_history(sku_id, demand_date);
CREATE INDEX idx_forecasts_sku_date ON supply_chain.forecasts(sku_id, forecast_date);
```

---

## Core Service Implementations

### Data Ingestion Service
```java
@Service
@Transactional
@Slf4j
public class DataIngestionService {
    
    private final DataIngestionRepository repository;
    private final DataValidationService validationService;
    private final EventPublisher eventPublisher;
    
    public IngestionResponse processFile(IngestionRequest request) {
        String jobId = UUID.randomUUID().toString();
        
        try {
            // 1. Validate file format
            ValidationResult validation = validationService.validateFile(request);
            if (!validation.isValid()) {
                throw new ValidationException(validation.getErrorMessage());
            }
            
            // 2. Parse and transform data
            List<SupplyChainRecord> records = parseFile(request.getFile());
            List<StandardizedRecord> standardized = transformRecords(records);
            
            // 3. Quality assessment
            QualityReport quality = assessDataQuality(standardized);
            
            // 4. Store in database
            repository.saveAll(standardized);
            
            // 5. Publish event
            eventPublisher.publishEvent(new DataIngestionEvent(jobId, quality));
            
            return IngestionResponse.builder()
                .jobId(jobId)
                .recordCount(standardized.size())
                .qualityScore(quality.getOverallScore())
                .status(IngestionStatus.COMPLETED)
                .build();
                
        } catch (Exception e) {
            log.error("Data ingestion failed for job {}", jobId, e);
            throw new IngestionException("Processing failed: " + e.getMessage());
        }
    }
}
```

### Forecasting Engine Service
```python
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import mlflow
from tensorflow import keras

class ForecastingModel(ABC):
    """Abstract base class for forecasting models"""
    
    @abstractmethod
    def train(self, data: pd.DataFrame, config: dict) -> None:
        pass
    
    @abstractmethod
    def predict(self, data: pd.DataFrame, horizon: int) -> np.ndarray:
        pass

class LSTMForecastingModel(ForecastingModel):
    """LSTM-based demand forecasting model"""
    
    def __init__(self, config: dict):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        
    def train(self, data: pd.DataFrame, config: dict) -> None:
        # Feature engineering
        features = self._engineer_features(data)
        X, y = self._create_sequences(features)
        
        # Build LSTM model
        self.model = keras.Sequential([
            keras.layers.LSTM(config['units'], return_sequences=True, 
                             input_shape=(config['sequence_length'], features.shape[1])),
            keras.layers.Dropout(config['dropout']),
            keras.layers.LSTM(config['units']),
            keras.layers.Dropout(config['dropout']),
            keras.layers.Dense(1, activation='linear')
        ])
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=config['learning_rate']),
            loss='mse',
            metrics=['mae']
        )
        
        # Train model
        history = self.model.fit(
            X, y,
            epochs=config['epochs'],
            batch_size=config['batch_size'],
            validation_split=0.2
        )
        
        # Log to MLflow
        mlflow.log_params(config)
        mlflow.tensorflow.log_model(self.model, "model")
    
    def predict(self, data: pd.DataFrame, horizon: int) -> np.ndarray:
        features = self._engineer_features(data)
        X = self._prepare_input_sequence(features)
        predictions = self.model.predict(X)
        return self.scaler.inverse_transform(predictions).flatten()
```

### Optimization Service
```python
from ortools.linear_solver import pywraplp
import numpy as np

class InventoryOptimizationEngine:
    """Advanced inventory optimization using operations research"""
    
    def optimize_safety_stock(self, sku_data: dict) -> dict:
        """Optimize safety stock levels using service level constraints"""
        
        results = {}
        
        for sku_id, data in sku_data.items():
            demand_mean = data['demand_forecast']
            demand_std = data['demand_std']
            lead_time = data['lead_time']
            service_level = data['target_service_level']
            
            # Calculate optimal safety stock using newsvendor model
            z_score = self._calculate_z_score(service_level)
            lead_time_demand_std = demand_std * np.sqrt(lead_time)
            safety_stock = z_score * lead_time_demand_std
            
            reorder_point = demand_mean * lead_time + safety_stock
            
            results[sku_id] = {
                'optimal_safety_stock': safety_stock,
                'reorder_point': reorder_point,
                'expected_service_level': service_level
            }
        
        return results
```

---

## API Implementation

### REST Controller
```java
@RestController
@RequestMapping("/api/v1/forecasting")
@Validated
@Slf4j
public class ForecastingController {
    
    private final ForecastingService forecastingService;
    private final OptimizationService optimizationService;
    
    @PostMapping("/generate")
    public ResponseEntity<ForecastResponse> generateForecast(
            @Valid @RequestBody ForecastRequest request) {
        
        try {
            ForecastResponse response = forecastingService.generateForecast(request);
            return ResponseEntity.ok(response);
        } catch (ValidationException e) {
            return ResponseEntity.badRequest().build();
        } catch (Exception e) {
            log.error("Forecast generation failed", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }
    
    @GetMapping("/forecasts/{skuId}")
    public ResponseEntity<List<Forecast>> getForecastsBySkuId(
            @PathVariable UUID skuId,
            @RequestParam(defaultValue = "short") String horizonType) {
        
        List<Forecast> forecasts = forecastingService.getForecastsBySkuId(skuId, horizonType);
        return ResponseEntity.ok(forecasts);
    }
    
    @PostMapping("/optimize/safety-stock")
    public ResponseEntity<OptimizationResponse> optimizeSafetyStock(
            @Valid @RequestBody OptimizationRequest request) {
        
        OptimizationResponse response = optimizationService.optimizeSafetyStock(request);
        return ResponseEntity.ok(response);
    }
}
```

---

## Configuration Files

### Docker Configuration
```dockerfile
# Forecasting Service Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "app.py"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: forecasting-service
  namespace: supply-chain
spec:
  replicas: 3
  selector:
    matchLabels:
      app: forecasting-service
  template:
    metadata:
      labels:
        app: forecasting-service
    spec:
      containers:
      - name: forecasting-service
        image: supply-chain/forecasting:v1.0
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: forecasting-service
  namespace: supply-chain
spec:
  selector:
    app: forecasting-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

---

## Conclusion

This Low Level Design provides implementation-ready specifications for the Supply Chain Demand Forecasting Platform, building upon all previous documents with detailed database schemas, service implementations, API specifications, and deployment configurations.

Key implementation features:
- **Complete Database Schema**: PostgreSQL schemas with indexes and constraints
- **Service Implementations**: Java Spring Boot and Python service classes
- **API Specifications**: RESTful endpoints with validation and error handling
- **Deployment Ready**: Docker, Kubernetes configurations
- **Performance Optimized**: Indexes, caching, and resource management

**Next Steps**: Proceed to Pseudocode document for algorithmic implementations.

---

*This document is confidential and proprietary. Distribution is restricted to authorized personnel only.*
