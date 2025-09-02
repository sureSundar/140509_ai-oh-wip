# Low Level Design (LLD)
## Finance Spend Analytics and Optimization Platform

*Building upon PRD, FRD, NFRD, AD, and HLD for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 40 functional requirements across 8 modules
- ✅ NFRD completed with 35 non-functional requirements
- ✅ AD completed with microservices architecture and technology stack
- ✅ HLD completed with detailed component specifications, data models, and API designs
- ✅ Component interfaces and processing workflows defined

### TASK
Create implementation-ready low-level design specifications including detailed class structures, database schemas, API implementations, algorithm specifications, configuration files, and deployment scripts that enable direct development of the finance spend analytics platform.

### VERIFICATION & VALIDATION
**Verification**: All HLD components have corresponding LLD implementations with complete class structures and database schemas
**Validation**: LLD specifications reviewed with development teams and validated for direct implementation

### EXIT CRITERIA
- ✅ Complete class diagrams and implementation structures
- ✅ Detailed database schemas with indexes and constraints
- ✅ API implementation specifications with request/response formats
- ✅ Algorithm implementations for ML and analytics components
- ✅ Configuration and deployment specifications
- ✅ Foundation prepared for pseudocode and implementation

---

### Reference to Previous Documents
This LLD builds upon **PRD**, **FRD**, **NFRD**, **AD**, and **HLD** foundations:
- **PRD Success Metrics** → Implementation supporting 15% cost savings, 30% processing reduction, 90% accuracy
- **FRD Functional Requirements** → Implementation classes for all 40 functional requirements
- **NFRD Performance Requirements** → Implementation optimized for <3s response time, 99.9% uptime
- **AD Technology Stack** → Implementation using specified technologies (Node.js, Python, TensorFlow, PostgreSQL)
- **HLD Component Specifications** → Detailed class implementations for all HLD components

## 1. Database Schema Implementation

### 1.1 Core Transaction Tables
```sql
-- Expense transactions with optimized indexes
CREATE TABLE expense_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
    vendor_id UUID NOT NULL REFERENCES vendors(id),
    category_id UUID NOT NULL REFERENCES expense_categories(id),
    department_id UUID NOT NULL REFERENCES departments(id),
    employee_id UUID NOT NULL REFERENCES employees(id),
    description TEXT,
    receipt_url VARCHAR(500),
    receipt_data JSONB,
    status expense_status NOT NULL DEFAULT 'pending',
    policy_violations JSONB DEFAULT '[]',
    approval_workflow JSONB,
    ml_category_confidence DECIMAL(3,2),
    anomaly_score DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    
    -- Performance indexes
    CONSTRAINT valid_amount CHECK (amount > 0 AND amount < 1000000),
    CONSTRAINT valid_confidence CHECK (ml_category_confidence BETWEEN 0 AND 1)
);

-- Optimized indexes for query performance
CREATE INDEX CONCURRENTLY idx_expense_date_dept ON expense_transactions 
    USING btree (transaction_date DESC, department_id);
CREATE INDEX CONCURRENTLY idx_expense_vendor_amount ON expense_transactions 
    USING btree (vendor_id, amount DESC);
CREATE INDEX CONCURRENTLY idx_expense_category_status ON expense_transactions 
    USING btree (category_id, status);
CREATE INDEX CONCURRENTLY idx_expense_employee_date ON expense_transactions 
    USING btree (employee_id, transaction_date DESC);
CREATE INDEX CONCURRENTLY idx_expense_anomaly ON expense_transactions 
    USING btree (anomaly_score DESC) WHERE anomaly_score > 0.7;

-- Partitioning for large datasets
CREATE TABLE expense_transactions_y2024 PARTITION OF expense_transactions
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### 1.2 Analytics Aggregation Tables
```sql
-- Pre-aggregated data for fast analytics
CREATE TABLE spend_analytics_monthly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year_month DATE NOT NULL,
    department_id UUID REFERENCES departments(id),
    category_id UUID REFERENCES expense_categories(id),
    vendor_id UUID REFERENCES vendors(id),
    currency_code VARCHAR(3) NOT NULL,
    transaction_count INTEGER NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    avg_amount DECIMAL(15,2) NOT NULL,
    median_amount DECIMAL(15,2),
    std_deviation DECIMAL(15,2),
    min_amount DECIMAL(15,2) NOT NULL,
    max_amount DECIMAL(15,2) NOT NULL,
    policy_violation_count INTEGER DEFAULT 0,
    anomaly_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(year_month, department_id, category_id, vendor_id, currency_code)
);

-- Materialized view for real-time analytics
CREATE MATERIALIZED VIEW spend_realtime_metrics AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour_bucket,
    department_id,
    COUNT(*) as hourly_transactions,
    SUM(amount) as hourly_spend,
    AVG(amount) as avg_transaction_size,
    COUNT(*) FILTER (WHERE anomaly_score > 0.7) as anomaly_count
FROM expense_transactions
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY hour_bucket, department_id;

-- Auto-refresh materialized view
CREATE OR REPLACE FUNCTION refresh_realtime_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY spend_realtime_metrics;
END;
$$ LANGUAGE plpgsql;

SELECT cron.schedule('refresh-realtime-metrics', '*/5 * * * *', 'SELECT refresh_realtime_metrics();');
```

### 1.3 ML Model Metadata Tables
```sql
-- ML model registry and versioning
CREATE TABLE ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'categorization', 'anomaly', 'forecast'
    version VARCHAR(20) NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    training_data_hash VARCHAR(64),
    hyperparameters JSONB,
    performance_metrics JSONB,
    feature_importance JSONB,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(model_name, version)
);

-- Model training history and experiments
CREATE TABLE model_training_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES ml_models(id),
    training_start TIMESTAMP WITH TIME ZONE NOT NULL,
    training_end TIMESTAMP WITH TIME ZONE,
    training_data_size INTEGER,
    validation_accuracy DECIMAL(5,4),
    test_accuracy DECIMAL(5,4),
    training_loss DECIMAL(10,6),
    validation_loss DECIMAL(10,6),
    training_config JSONB,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    
    INDEX idx_training_model_date (model_id, training_start DESC)
);
```

## 2. Core Service Implementation Classes

### 2.1 Expense Management Service Classes

#### 2.1.1 Receipt OCR Processor Implementation
```python
from typing import Dict, List, Optional, Tuple
import cv2
import pytesseract
import spacy
import numpy as np
from dataclasses import dataclass
from decimal import Decimal
import re
from datetime import datetime

@dataclass
class ExtractedReceiptData:
    vendor_name: Optional[str]
    amount: Optional[Decimal]
    date: Optional[datetime]
    tax_amount: Optional[Decimal]
    line_items: List[Dict]
    confidence_score: float
    raw_text: str

class ReceiptOCRProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.amount_pattern = re.compile(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        self.date_patterns = [
            re.compile(r'(\d{1,2})/(\d{1,2})/(\d{2,4})'),
            re.compile(r'(\d{1,2})-(\d{1,2})-(\d{2,4})'),
            re.compile(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})')
        ]
    
    async def process_receipt(self, image_data: bytes) -> ExtractedReceiptData:
        """Process receipt image and extract structured data"""
        try:
            # Image preprocessing
            enhanced_image = self._enhance_image(image_data)
            
            # OCR text extraction
            raw_text = self._extract_text(enhanced_image)
            
            # NLP-based data extraction
            extracted_data = self._extract_structured_data(raw_text)
            
            # Validate and score confidence
            validated_data = self._validate_and_score(extracted_data, raw_text)
            
            return validated_data
            
        except Exception as e:
            return ExtractedReceiptData(
                vendor_name=None, amount=None, date=None,
                tax_amount=None, line_items=[], confidence_score=0.0,
                raw_text=str(e)
            )
    
    def _enhance_image(self, image_data: bytes) -> np.ndarray:
        """Enhance image quality for better OCR"""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Deskewing
        coords = np.column_stack(np.where(enhanced > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        (h, w) = enhanced.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(enhanced, M, (w, h), 
                                flags=cv2.INTER_CUBIC, 
                                borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def _extract_text(self, image: np.ndarray) -> str:
        """Extract text using Tesseract OCR"""
        config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/$-: '
        text = pytesseract.image_to_string(image, config=config)
        return text.strip()
    
    def _extract_structured_data(self, text: str) -> Dict:
        """Extract structured data using NLP"""
        doc = self.nlp(text)
        
        # Extract vendor name (usually first organization entity)
        vendor_name = None
        for ent in doc.ents:
            if ent.label_ == "ORG":
                vendor_name = ent.text
                break
        
        # Extract amounts
        amounts = []
        for match in self.amount_pattern.finditer(text):
            try:
                amount = Decimal(match.group(1).replace(',', ''))
                amounts.append(amount)
            except:
                continue
        
        # Extract date
        date = None
        for pattern in self.date_patterns:
            match = pattern.search(text)
            if match:
                try:
                    date = self._parse_date(match.groups())
                    break
                except:
                    continue
        
        # Determine total amount (usually the largest amount)
        total_amount = max(amounts) if amounts else None
        
        return {
            'vendor_name': vendor_name,
            'amount': total_amount,
            'date': date,
            'amounts': amounts,
            'raw_text': text
        }
    
    def _validate_and_score(self, data: Dict, raw_text: str) -> ExtractedReceiptData:
        """Validate extracted data and calculate confidence score"""
        confidence_factors = []
        
        # Vendor name confidence
        if data['vendor_name']:
            confidence_factors.append(0.3)
        
        # Amount confidence
        if data['amount'] and data['amount'] > 0:
            confidence_factors.append(0.4)
        
        # Date confidence
        if data['date']:
            confidence_factors.append(0.2)
        
        # Text quality confidence
        text_quality = len([c for c in raw_text if c.isalnum()]) / max(len(raw_text), 1)
        confidence_factors.append(min(text_quality, 0.1))
        
        confidence_score = sum(confidence_factors)
        
        return ExtractedReceiptData(
            vendor_name=data['vendor_name'],
            amount=data['amount'],
            date=data['date'],
            tax_amount=None,  # TODO: Implement tax extraction
            line_items=[],    # TODO: Implement line item extraction
            confidence_score=confidence_score,
            raw_text=raw_text
        )
```

#### 2.1.2 ML Categorization Engine Implementation
```python
import tensorflow as tf
from transformers import AutoTokenizer, TFAutoModel
import numpy as np
from typing import Dict, List, Tuple
import joblib
from sklearn.preprocessing import LabelEncoder
import redis
import json

@dataclass
class CategoryPrediction:
    category_id: str
    category_name: str
    confidence: float
    subcategory: Optional[str] = None

class MLCategorizationEngine:
    def __init__(self, model_path: str, redis_client: redis.Redis):
        self.model_path = model_path
        self.redis_client = redis_client
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.model = None
        self.label_encoder = None
        self.category_mapping = {}
        self._load_model()
    
    def _load_model(self):
        """Load trained categorization model"""
        try:
            # Load TensorFlow model
            self.model = tf.keras.models.load_model(f"{self.model_path}/categorization_model")
            
            # Load label encoder
            self.label_encoder = joblib.load(f"{self.model_path}/label_encoder.pkl")
            
            # Load category mapping
            with open(f"{self.model_path}/category_mapping.json", 'r') as f:
                self.category_mapping = json.load(f)
                
        except Exception as e:
            raise Exception(f"Failed to load categorization model: {str(e)}")
    
    async def categorize_expense(self, expense_data: Dict) -> CategoryPrediction:
        """Categorize expense using ML model"""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(expense_data)
            cached_result = self.redis_client.get(cache_key)
            if cached_result:
                return CategoryPrediction(**json.loads(cached_result))
            
            # Extract features
            features = self._extract_features(expense_data)
            
            # Get BERT embeddings
            embeddings = self._get_bert_embeddings(features['text'])
            
            # Combine with numerical features
            combined_features = np.concatenate([
                embeddings,
                features['numerical']
            ])
            
            # Predict category
            prediction = self.model.predict(combined_features.reshape(1, -1))
            predicted_class = np.argmax(prediction[0])
            confidence = float(np.max(prediction[0]))
            
            # Decode prediction
            category_name = self.label_encoder.inverse_transform([predicted_class])[0]
            category_id = self.category_mapping.get(category_name, 'unknown')
            
            result = CategoryPrediction(
                category_id=category_id,
                category_name=category_name,
                confidence=confidence
            )
            
            # Cache result
            self.redis_client.setex(
                cache_key, 3600,  # 1 hour TTL
                json.dumps(result.__dict__)
            )
            
            return result
            
        except Exception as e:
            # Return default category on error
            return CategoryPrediction(
                category_id='misc',
                category_name='Miscellaneous',
                confidence=0.0
            )
    
    def _extract_features(self, expense_data: Dict) -> Dict:
        """Extract features for ML model"""
        # Text features
        text_parts = []
        if expense_data.get('description'):
            text_parts.append(expense_data['description'])
        if expense_data.get('vendor_name'):
            text_parts.append(expense_data['vendor_name'])
        
        text_feature = ' '.join(text_parts).lower()
        
        # Numerical features
        amount = float(expense_data.get('amount', 0))
        day_of_week = expense_data.get('transaction_date', datetime.now()).weekday()
        hour_of_day = expense_data.get('transaction_date', datetime.now()).hour
        
        # Amount buckets (log scale)
        amount_bucket = int(np.log10(max(amount, 1)))
        
        numerical_features = np.array([
            amount,
            day_of_week,
            hour_of_day,
            amount_bucket
        ])
        
        return {
            'text': text_feature,
            'numerical': numerical_features
        }
    
    def _get_bert_embeddings(self, text: str) -> np.ndarray:
        """Get BERT embeddings for text"""
        # Tokenize text
        tokens = self.tokenizer(
            text,
            max_length=128,
            truncation=True,
            padding='max_length',
            return_tensors='tf'
        )
        
        # Get embeddings from pre-trained BERT
        bert_model = TFAutoModel.from_pretrained('bert-base-uncased')
        outputs = bert_model(tokens)
        
        # Use CLS token embedding
        cls_embedding = outputs.last_hidden_state[:, 0, :].numpy()
        
        return cls_embedding.flatten()
    
    def _generate_cache_key(self, expense_data: Dict) -> str:
        """Generate cache key for expense data"""
        key_parts = [
            expense_data.get('description', ''),
            expense_data.get('vendor_name', ''),
            str(expense_data.get('amount', 0))
        ]
        return f"categorization:{hash('|'.join(key_parts))}"
```

### 2.2 Analytics Service Implementation

#### 2.2.1 Analytics Query Engine
```typescript
import { Pool } from 'pg';
import Redis from 'ioredis';
import { ClickHouse } from 'clickhouse';

interface AnalyticsQuery {
  dimensions: string[];
  metrics: string[];
  filters: QueryFilter[];
  dateRange: DateRange;
  groupBy?: string[];
  orderBy?: OrderBy[];
  limit?: number;
}

interface QueryResult {
  data: any[];
  metadata: QueryMetadata;
  executionTime: number;
  fromCache: boolean;
}

class AnalyticsQueryEngine {
  private pgPool: Pool;
  private redis: Redis;
  private clickhouse: ClickHouse;
  private queryOptimizer: QueryOptimizer;

  constructor(config: DatabaseConfig) {
    this.pgPool = new Pool(config.postgres);
    this.redis = new Redis(config.redis);
    this.clickhouse = new ClickHouse(config.clickhouse);
    this.queryOptimizer = new QueryOptimizer();
  }

  async executeQuery(query: AnalyticsQuery): Promise<QueryResult> {
    const startTime = Date.now();
    
    try {
      // Optimize query
      const optimizedQuery = await this.queryOptimizer.optimize(query);
      
      // Generate cache key
      const cacheKey = this.generateCacheKey(optimizedQuery);
      
      // Check cache first
      const cachedResult = await this.redis.get(cacheKey);
      if (cachedResult) {
        return {
          ...JSON.parse(cachedResult),
          executionTime: Date.now() - startTime,
          fromCache: true
        };
      }
      
      // Execute query based on data size and complexity
      let result;
      if (this.shouldUseClickHouse(optimizedQuery)) {
        result = await this.executeClickHouseQuery(optimizedQuery);
      } else {
        result = await this.executePostgresQuery(optimizedQuery);
      }
      
      // Cache result
      await this.redis.setex(
        cacheKey,
        this.getCacheTTL(optimizedQuery),
        JSON.stringify(result)
      );
      
      return {
        ...result,
        executionTime: Date.now() - startTime,
        fromCache: false
      };
      
    } catch (error) {
      throw new Error(`Query execution failed: ${error.message}`);
    }
  }

  private async executeClickHouseQuery(query: AnalyticsQuery): Promise<any> {
    const sql = this.buildClickHouseSQL(query);
    
    const result = await this.clickhouse.query(sql).toPromise();
    
    return {
      data: result,
      metadata: {
        rowCount: result.length,
        columns: Object.keys(result[0] || {}),
        dataSource: 'clickhouse'
      }
    };
  }

  private buildClickHouseSQL(query: AnalyticsQuery): string {
    const selectClause = [...query.dimensions, ...query.metrics].join(', ');
    const fromClause = 'spend_analytics_daily';
    const whereClause = this.buildWhereClause(query.filters);
    const groupByClause = query.groupBy?.length ? 
      `GROUP BY ${query.groupBy.join(', ')}` : '';
    const orderByClause = query.orderBy?.length ?
      `ORDER BY ${query.orderBy.map(o => `${o.field} ${o.direction}`).join(', ')}` : '';
    const limitClause = query.limit ? `LIMIT ${query.limit}` : '';

    return `
      SELECT ${selectClause}
      FROM ${fromClause}
      ${whereClause}
      ${groupByClause}
      ${orderByClause}
      ${limitClause}
    `.trim();
  }

  private shouldUseClickHouse(query: AnalyticsQuery): boolean {
    // Use ClickHouse for large aggregations and analytical queries
    const hasAggregations = query.metrics.some(m => 
      ['SUM', 'AVG', 'COUNT', 'MAX', 'MIN'].some(agg => m.includes(agg))
    );
    const hasLargeDateRange = this.getDateRangeDays(query.dateRange) > 90;
    
    return hasAggregations || hasLargeDateRange;
  }

  private generateCacheKey(query: AnalyticsQuery): string {
    const queryString = JSON.stringify(query, Object.keys(query).sort());
    return `analytics:${this.hashString(queryString)}`;
  }

  private getCacheTTL(query: AnalyticsQuery): number {
    // Real-time queries: 5 minutes
    // Daily aggregations: 1 hour
    // Historical data: 24 hours
    const dateRangeDays = this.getDateRangeDays(query.dateRange);
    
    if (dateRangeDays <= 1) return 300;      // 5 minutes
    if (dateRangeDays <= 30) return 3600;    // 1 hour
    return 86400;                            // 24 hours
  }
}
```

## 3. Configuration and Deployment

### 3.1 Kubernetes Deployment Configuration
```yaml
# expense-management-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: expense-management-service
  labels:
    app: expense-management
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: expense-management
  template:
    metadata:
      labels:
        app: expense-management
    spec:
      containers:
      - name: expense-service
        image: finance-platform/expense-service:1.0.0
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        - name: ML_MODEL_PATH
          value: "/models/categorization"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: ml-models
          mountPath: /models
          readOnly: true
      volumes:
      - name: ml-models
        persistentVolumeClaim:
          claimName: ml-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: expense-management-service
spec:
  selector:
    app: expense-management
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: expense-management-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: expense-management-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 3.2 Docker Configuration
```dockerfile
# Dockerfile for Expense Management Service
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS runtime

# Install system dependencies for OCR
RUN apk add --no-cache \
    tesseract-ocr \
    tesseract-ocr-data-eng \
    opencv-dev \
    python3 \
    py3-pip

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy application
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Set ownership and permissions
RUN chown -R nodejs:nodejs /app
USER nodejs

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["node", "dist/server.js"]
```

### 3.3 Environment Configuration
```yaml
# config/production.yaml
database:
  postgres:
    host: postgres-cluster.finance-platform.svc.cluster.local
    port: 5432
    database: finance_platform
    pool:
      min: 5
      max: 20
      acquireTimeoutMillis: 30000
      idleTimeoutMillis: 30000
  
  clickhouse:
    host: clickhouse-cluster.finance-platform.svc.cluster.local
    port: 8123
    database: analytics
    
  redis:
    host: redis-cluster.finance-platform.svc.cluster.local
    port: 6379
    db: 0
    keyPrefix: "finance:"

ml:
  models:
    categorization:
      path: "/models/categorization/v1.2.0"
      confidence_threshold: 0.7
      batch_size: 32
    
    anomaly_detection:
      path: "/models/anomaly/v1.1.0"
      threshold: 0.8
      window_size: 100

ocr:
  tesseract:
    config: "--oem 3 --psm 6"
    languages: ["eng"]
  
  preprocessing:
    enhance_contrast: true
    denoise: true
    deskew: true

performance:
  cache:
    ttl:
      analytics: 3600  # 1 hour
      categorization: 1800  # 30 minutes
      user_data: 900  # 15 minutes
  
  rate_limiting:
    api_calls_per_minute: 1000
    ml_requests_per_minute: 500

security:
  jwt:
    secret: ${JWT_SECRET}
    expiration: "24h"
  
  encryption:
    algorithm: "aes-256-gcm"
    key: ${ENCRYPTION_KEY}
```

This LLD provides implementation-ready specifications with complete class structures, database schemas, API implementations, and deployment configurations that build upon all previous documents, enabling direct development of the finance spend analytics platform.
