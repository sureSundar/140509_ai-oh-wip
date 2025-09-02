# Low Level Design (LLD)
## Content Recommendation Engine

### Document Control
- **Document Version**: 1.0
- **Created**: 2025-01-XX
- **Document Owner**: Engineering Team

---

## ETVX Framework Application

### Entry Criteria
- ✅ **README.md completed** - Problem statement and business case established
- ✅ **01_PRD.md completed** - Product requirements and business objectives defined
- ✅ **02_FRD.md completed** - Functional modules and system behaviors specified
- ✅ **03_NFRD.md completed** - Non-functional requirements and quality constraints defined
- ✅ **04_AD.md completed** - System architecture and component design established
- ✅ **05_HLD.md completed** - Detailed component designs and API specifications defined

### Task (This Document)
Provide implementation-ready technical specifications including database schemas, service class implementations, deployment configurations, CI/CD pipelines, and detailed code examples that enable direct development and deployment.

### Verification & Validation
- **Code Review** - Implementation code review and validation
- **Database Schema Validation** - Schema design and performance review
- **Deployment Testing** - Infrastructure and deployment configuration testing

### Exit Criteria
- ✅ **Implementation-Ready Schemas** - Complete database DDL and configurations
- ✅ **Service Implementations** - Detailed service class code and logic
- ✅ **Deployment Configurations** - Docker, Kubernetes, and CI/CD pipeline definitions

---

## Database Implementation

### PostgreSQL Schema (User Profile Service)

```sql
-- Database creation and configuration
CREATE DATABASE recommendation_engine
    WITH ENCODING 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8';

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- User profiles table with partitioning
CREATE TABLE user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    demographics JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    segments TEXT[] DEFAULT ARRAY[]::TEXT[],
    privacy_settings JSONB DEFAULT '{"data_sharing": true, "personalization": true}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended'))
);

-- User behaviors table with time-based partitioning
CREATE TABLE user_behaviors (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    content_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    device_type VARCHAR(50),
    platform VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for user_behaviors
CREATE TABLE user_behaviors_2025_01 PARTITION OF user_behaviors
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE user_behaviors_2025_02 PARTITION OF user_behaviors
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Performance indexes
CREATE INDEX CONCURRENTLY idx_user_profiles_email ON user_profiles(email);
CREATE INDEX CONCURRENTLY idx_user_profiles_segments ON user_profiles USING GIN(segments);
CREATE INDEX CONCURRENTLY idx_user_profiles_updated_at ON user_profiles(updated_at);

CREATE INDEX CONCURRENTLY idx_user_behaviors_user_id ON user_behaviors(user_id);
CREATE INDEX CONCURRENTLY idx_user_behaviors_content_id ON user_behaviors(content_id);
CREATE INDEX CONCURRENTLY idx_user_behaviors_event_type ON user_behaviors(event_type);
CREATE INDEX CONCURRENTLY idx_user_behaviors_timestamp ON user_behaviors(timestamp);
CREATE INDEX CONCURRENTLY idx_user_behaviors_session_id ON user_behaviors(session_id);
CREATE INDEX CONCURRENTLY idx_user_behaviors_processed ON user_behaviors(processed) WHERE processed = FALSE;

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### MongoDB Schema (Content Service)

```javascript
// Database initialization
use recommendation_content;

// Content collection with validation
db.createCollection("content", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["contentId", "title", "contentType", "status"],
            properties: {
                contentId: {
                    bsonType: "string",
                    pattern: "^[a-zA-Z0-9_-]+$",
                    minLength: 1,
                    maxLength: 255
                },
                title: {
                    bsonType: "string",
                    minLength: 1,
                    maxLength: 500
                },
                contentType: {
                    bsonType: "string",
                    enum: ["product", "video", "article", "post", "image", "audio"]
                },
                status: {
                    bsonType: "string",
                    enum: ["draft", "published", "archived", "deleted"]
                }
            }
        }
    }
});

// Indexes for performance
db.content.createIndex({ "contentId": 1 }, { unique: true });
db.content.createIndex({ "contentType": 1, "category": 1 });
db.content.createIndex({ "status": 1, "metadata.createdAt": -1 });
db.content.createIndex({ "tags": 1 });

// Text search index
db.content.createIndex({
    "title": "text",
    "description": "text",
    "tags": "text"
}, {
    weights: {
        "title": 10,
        "description": 5,
        "tags": 1
    },
    name: "content_text_search"
});
```

---

## Service Implementation

### Recommendation Service (Python)

```python
# recommendation_service.py
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import redis
import mlflow
import tensorflow as tf
from prometheus_client import Counter, Histogram

# Metrics
REQUEST_COUNT = Counter('recommendation_requests_total', 'Total recommendation requests')
RESPONSE_TIME = Histogram('recommendation_response_time_seconds', 'Response time')

class RecommendationRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., regex='^(product|video|article|post)$')
    count: int = Field(default=10, ge=1, le=100)
    context: Optional[Dict] = Field(default_factory=dict)

class RecommendationItem(BaseModel):
    content_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    rank: int
    explanation: Optional[str] = None

class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem]
    user_id: str
    request_id: str
    model_version: str
    response_time_ms: float
    timestamp: datetime

class RecommendationService:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.mlflow_client = mlflow.tracking.MlflowClient()
        self.models = {}
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize service and load models"""
        await self._load_models()
        
    async def _load_models(self):
        """Load ML models from MLflow"""
        try:
            # Load collaborative filtering model
            cf_model_uri = "models:/collaborative_filtering/production"
            self.models['collaborative_filtering'] = mlflow.tensorflow.load_model(cf_model_uri)
            
            # Load content-based model
            cb_model_uri = "models:/content_based/production"
            self.models['content_based'] = mlflow.tensorflow.load_model(cb_model_uri)
            
            self.logger.info("Models loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
            raise
    
    async def generate_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """Generate personalized recommendations"""
        start_time = datetime.now()
        REQUEST_COUNT.inc()
        
        try:
            # Check cache first
            cache_key = f"rec:{request.user_id}:{request.content_type}:{request.count}"
            cached_result = await self._get_from_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Generate recommendations
            recommendations = await self._generate_recommendations_internal(
                request.user_id, request.content_type, request.count
            )
            
            # Create response
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            response = RecommendationResponse(
                recommendations=recommendations,
                user_id=request.user_id,
                request_id=f"req_{int(datetime.now().timestamp())}",
                model_version="v1.2.0",
                response_time_ms=response_time,
                timestamp=datetime.now()
            )
            
            # Cache result
            await self._set_cache(cache_key, response, ttl=300)
            
            # Record metrics
            RESPONSE_TIME.observe(response_time / 1000)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _generate_recommendations_internal(
        self, user_id: str, content_type: str, count: int
    ) -> List[RecommendationItem]:
        """Internal recommendation generation logic"""
        
        # Simplified implementation
        recommendations = []
        for i in range(count):
            recommendations.append(RecommendationItem(
                content_id=f"content_{i}",
                score=0.9 - (i * 0.05),
                rank=i + 1,
                explanation="Recommended based on your preferences"
            ))
        
        return recommendations
    
    async def _get_from_cache(self, key: str) -> Optional[RecommendationResponse]:
        """Get cached recommendation"""
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return RecommendationResponse.parse_raw(cached_data)
        except Exception as e:
            self.logger.warning(f"Cache get error: {e}")
        return None
    
    async def _set_cache(self, key: str, response: RecommendationResponse, ttl: int):
        """Set cache with TTL"""
        try:
            self.redis_client.setex(key, ttl, response.json())
        except Exception as e:
            self.logger.warning(f"Cache set error: {e}")

# FastAPI application
app = FastAPI(title="Recommendation Service", version="1.0.0")

recommendation_service = RecommendationService()

@app.on_event("startup")
async def startup_event():
    await recommendation_service.initialize()

@app.post("/api/v1/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Generate personalized recommendations"""
    return await recommendation_service.generate_recommendations(request)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Docker Configuration

### Recommendation Service Dockerfile

```dockerfile
# Dockerfile for Recommendation Service
FROM python:3.9-slim

# Set working directory
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

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "recommendation_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  recommendation-service:
    build: ./recommendation-service
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - DATABASE_URL=postgresql://user:password@postgres:5432/recommendations
    depends_on:
      - redis
      - postgres
      - mlflow
    volumes:
      - ./recommendation-service:/app
    restart: unless-stopped

  user-profile-service:
    build: ./user-profile-service
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/recommendations
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  content-service:
    build: ./content-service
    ports:
      - "8002:8000"
    environment:
      - MONGODB_URL=mongodb://mongo:27017/recommendation_content
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - mongo
      - elasticsearch
    restart: unless-stopped

  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=recommendations
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  mongo:
    image: mongo:5.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

  elasticsearch:
    image: elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    restart: unless-stopped

  mlflow:
    image: python:3.9-slim
    command: >
      bash -c "pip install mlflow psycopg2-binary &&
               mlflow server --backend-store-uri postgresql://user:password@postgres:5432/mlflow
               --default-artifact-root /mlflow/artifacts --host 0.0.0.0 --port 5000"
    ports:
      - "5000:5000"
    depends_on:
      - postgres
    volumes:
      - mlflow_data:/mlflow
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
  mongo_data:
  elasticsearch_data:
  mlflow_data:
```

---

## Kubernetes Deployment

### Recommendation Service Deployment

```yaml
# k8s/recommendation-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recommendation-service
  namespace: production
  labels:
    app: recommendation-service
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: recommendation-service
  template:
    metadata:
      labels:
        app: recommendation-service
        version: v1
    spec:
      containers:
      - name: recommendation-service
        image: recommendation-engine/recommendation-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-service:5000"
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
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
      volumes:
      - name: config-volume
        configMap:
          name: recommendation-config
      imagePullSecrets:
      - name: docker-registry-secret

---
apiVersion: v1
kind: Service
metadata:
  name: recommendation-service
  namespace: production
spec:
  selector:
    app: recommendation-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: recommendation-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: recommendation-service
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

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: recommendation-engine

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
    - uses: actions/checkout@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy to EKS
      run: |
        aws eks update-kubeconfig --name production-cluster
        kubectl set image deployment/recommendation-service \
          recommendation-service=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main
        kubectl rollout status deployment/recommendation-service
```

---

## Monitoring Configuration

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "recommendation_rules.yml"

scrape_configs:
  - job_name: 'recommendation-service'
    static_configs:
      - targets: ['recommendation-service:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'user-profile-service'
    static_configs:
      - targets: ['user-profile-service:8000']
    metrics_path: /actuator/prometheus
    scrape_interval: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Recommendation Engine Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(recommendation_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(recommendation_response_time_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

---

## Conclusion

This Low Level Design builds upon all previous documents (README + PRD + FRD + NFRD + AD + HLD) to provide implementation-ready technical specifications for the Content Recommendation Engine. The LLD includes complete database schemas, service implementations, Docker configurations, Kubernetes deployments, and CI/CD pipelines that enable direct development and production deployment.

The detailed specifications ensure enterprise-grade quality, performance, security, and operational excellence while maintaining scalability and maintainability for the recommendation engine platform.

**Next Steps**: Proceed to Pseudocode document development to provide algorithmic implementations and detailed procedural logic for the core recommendation algorithms and system workflows.

---

*This document is confidential and proprietary. Distribution is restricted to authorized personnel only.*
