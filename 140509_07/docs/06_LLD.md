# Low Level Design (LLD)
## Sales Performance Analytics and Optimization Platform

*Building upon PRD, FRD, NFRD, AD, and HLD for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ PRD completed with business objectives, success metrics, and market analysis
- ✅ FRD completed with 40 functional requirements across 8 system modules
- ✅ NFRD completed with 30 non-functional requirements for performance, security, compliance
- ✅ AD completed with microservices architecture, technology stack, and integration patterns
- ✅ HLD completed with detailed component specifications, data models, APIs, and processing workflows

### TASK
Develop implementation-ready low-level design specifications including detailed class structures, database implementations, API implementations, algorithm specifications, configuration files, and deployment scripts.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All HLD components implemented with detailed class structures and method signatures
- [ ] Database schemas implemented with indexes, constraints, and optimization strategies
- [ ] API implementations include request/response models, validation, error handling, and security
- [ ] Algorithm implementations provide step-by-step logic for ML models and analytics

**Validation Criteria:**
- [ ] Code structures validated with senior developers and technical leads
- [ ] Database implementations validated with database administrators
- [ ] API implementations validated through contract testing
- [ ] Security implementations validated with cybersecurity experts

### EXIT CRITERIA
- ✅ Complete implementation-ready class structures for all microservices
- ✅ Production-ready database schemas with performance optimizations
- ✅ Fully specified API implementations with comprehensive error handling
- ✅ Detailed algorithm implementations for all ML and analytics components

---

## 1. Database Implementation

### 1.1 PostgreSQL Schema with Optimizations

#### Sales Opportunities Table
```sql
CREATE TABLE sales_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    owner_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
    stage VARCHAR(50) NOT NULL,
    probability INTEGER CHECK (probability BETWEEN 0 AND 100),
    close_date DATE NOT NULL,
    source VARCHAR(100),
    type VARCHAR(50),
    description TEXT,
    competitors JSONB DEFAULT '[]',
    next_steps TEXT,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_date TIMESTAMP WITH TIME ZONE,
    stage_history JSONB DEFAULT '[]',
    custom_fields JSONB DEFAULT '{}',
    created_by UUID NOT NULL,
    updated_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT fk_opportunity_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    CONSTRAINT fk_opportunity_owner FOREIGN KEY (owner_id) REFERENCES users(id)
) PARTITION BY RANGE (close_date);

-- Performance indexes
CREATE INDEX CONCURRENTLY idx_opportunity_owner_stage ON sales_opportunities (owner_id, stage) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY idx_opportunity_close_date ON sales_opportunities (close_date) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY idx_opportunity_amount_stage ON sales_opportunities (amount DESC, stage) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY idx_opportunity_competitors ON sales_opportunities USING GIN (competitors) WHERE deleted_at IS NULL;

-- Quarterly partitions
CREATE TABLE sales_opportunities_2024_q1 PARTITION OF sales_opportunities
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
```

#### Lead Scoring Table
```sql
CREATE TABLE lead_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL,
    composite_score DECIMAL(5,2) NOT NULL CHECK (composite_score BETWEEN 0 AND 100),
    behavioral_score DECIMAL(5,2) NOT NULL CHECK (behavioral_score BETWEEN 0 AND 100),
    demographic_score DECIMAL(5,2) NOT NULL CHECK (demographic_score BETWEEN 0 AND 100),
    engagement_score DECIMAL(5,2) NOT NULL CHECK (engagement_score BETWEEN 0 AND 100),
    intent_score DECIMAL(5,2) NOT NULL CHECK (intent_score BETWEEN 0 AND 100),
    fit_score DECIMAL(5,2) NOT NULL CHECK (fit_score BETWEEN 0 AND 100),
    scoring_factors JSONB NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_accuracy DECIMAL(5,4),
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT fk_lead_score_lead FOREIGN KEY (lead_id) REFERENCES leads(id),
    CONSTRAINT chk_valid_until_future CHECK (valid_until > scored_at)
) PARTITION BY RANGE (scored_at);

CREATE UNIQUE INDEX idx_lead_score_active ON lead_scores (lead_id, scored_at) WHERE valid_until > CURRENT_TIMESTAMP;
CREATE INDEX CONCURRENTLY idx_lead_score_composite ON lead_scores (lead_id, composite_score DESC);
```

## 2. Backend Service Implementation

### 2.1 Sales Performance Service (Node.js/TypeScript)

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Redis } from 'ioredis';

@Injectable()
export class SalesPerformanceService {
  constructor(
    @InjectRepository(SalesOpportunity)
    private opportunityRepository: Repository<SalesOpportunity>,
    private readonly redisClient: Redis
  ) {}

  async generatePerformanceDashboard(
    userId: string,
    dashboardConfig: DashboardConfig
  ): Promise<PerformanceDashboard> {
    // Check cache first
    const cacheKey = `dashboard:${userId}:${dashboardConfig.id}`;
    const cachedDashboard = await this.redisClient.get(cacheKey);
    
    if (cachedDashboard) {
      return JSON.parse(cachedDashboard);
    }

    // Generate dashboard data
    const [kpiMetrics, pipelineHealth, activityMetrics] = await Promise.all([
      this.generateKPIMetrics(userId, dashboardConfig.timeRange),
      this.assessPipelineHealth(userId, dashboardConfig.timeRange),
      this.analyzeActivityMetrics(userId, dashboardConfig.timeRange)
    ]);

    const dashboard: PerformanceDashboard = {
      id: dashboardConfig.id,
      userId,
      kpiMetrics,
      pipelineHealth,
      activityMetrics,
      generatedAt: new Date(),
      refreshInterval: dashboardConfig.refreshInterval || 300000
    };

    // Cache the dashboard
    await this.redisClient.setex(
      cacheKey,
      Math.floor(dashboard.refreshInterval / 1000),
      JSON.stringify(dashboard)
    );

    return dashboard;
  }

  private async generateKPIMetrics(userId: string, timeRange: TimeRange): Promise<KPIMetrics> {
    const query = this.opportunityRepository
      .createQueryBuilder('opp')
      .select([
        'COUNT(*) as total_opportunities',
        'SUM(CASE WHEN opp.stage = \'Closed Won\' THEN 1 ELSE 0 END) as won_opportunities',
        'SUM(CASE WHEN opp.stage = \'Closed Won\' THEN opp.amount ELSE 0 END) as won_amount',
        'SUM(opp.amount) as total_pipeline_value'
      ])
      .where('opp.owner_id = :userId', { userId })
      .andWhere('opp.created_date BETWEEN :startDate AND :endDate', {
        startDate: timeRange.startDate,
        endDate: timeRange.endDate
      })
      .andWhere('opp.deleted_at IS NULL');

    const result = await query.getRawOne();
    const winRate = result.total_opportunities > 0 
      ? (result.won_opportunities / result.total_opportunities) * 100 
      : 0;

    return {
      totalOpportunities: parseInt(result.total_opportunities),
      wonOpportunities: parseInt(result.won_opportunities),
      winRate: Math.round(winRate * 100) / 100,
      totalPipelineValue: parseFloat(result.total_pipeline_value) || 0,
      wonAmount: parseFloat(result.won_amount) || 0
    };
  }
}
```

### 2.2 Lead Scoring Service (Python/FastAPI)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import asyncio
import redis.asyncio as redis
from datetime import datetime, timedelta
import joblib
import numpy as np

app = FastAPI(title="Lead Scoring Service")

class LeadScoringRequest(BaseModel):
    lead_id: str = Field(..., description="Unique lead identifier")
    lead_data: Dict[str, Any] = Field(..., description="Lead profile and behavioral data")
    scoring_model: Optional[str] = Field("default", description="Scoring model version")

class LeadScore(BaseModel):
    lead_id: str
    composite_score: float = Field(..., ge=0, le=100)
    behavioral_score: float = Field(..., ge=0, le=100)
    demographic_score: float = Field(..., ge=0, le=100)
    engagement_score: float = Field(..., ge=0, le=100)
    intent_score: float = Field(..., ge=0, le=100)
    fit_score: float = Field(..., ge=0, le=100)
    scoring_factors: Dict[str, Any]
    model_version: str
    confidence: float = Field(..., ge=0, le=1)
    scored_at: datetime
    valid_until: datetime

class LeadScoringService:
    def __init__(self):
        self.redis_client = None
        self.ml_models = {}
        self.load_models()
    
    def load_models(self):
        """Load pre-trained ML models for lead scoring"""
        try:
            self.ml_models['composite'] = joblib.load('models/lead_scoring_xgboost_v1.pkl')
            self.ml_models['behavioral'] = joblib.load('models/behavioral_scoring_v1.pkl')
            self.ml_models['demographic'] = joblib.load('models/demographic_scoring_v1.pkl')
            self.ml_models['engagement'] = joblib.load('models/engagement_scoring_v1.pkl')
            self.ml_models['intent'] = joblib.load('models/intent_scoring_v1.pkl')
            self.ml_models['fit'] = joblib.load('models/fit_scoring_v1.pkl')
        except Exception as e:
            print(f"Error loading ML models: {e}")

    async def score_lead(self, request: LeadScoringRequest) -> LeadScore:
        """Score a lead using ML models and business rules"""
        start_time = datetime.now()
        
        try:
            # Check cache for recent score
            cached_score = await self.get_cached_score(request.lead_id)
            if cached_score and self.is_score_valid(cached_score):
                return cached_score
            
            # Extract features from lead data
            features = await self.extract_lead_features(request.lead_data)
            
            # Calculate individual score components
            scores = await self.calculate_component_scores(features, request.scoring_model)
            
            # Calculate composite score
            composite_score = await self.calculate_composite_score(scores, features)
            
            # Create lead score object
            lead_score = LeadScore(
                lead_id=request.lead_id,
                composite_score=round(composite_score, 2),
                behavioral_score=round(scores['behavioral'], 2),
                demographic_score=round(scores['demographic'], 2),
                engagement_score=round(scores['engagement'], 2),
                intent_score=round(scores['intent'], 2),
                fit_score=round(scores['fit'], 2),
                scoring_factors=self.identify_scoring_factors(features, scores),
                model_version=request.scoring_model or "default",
                confidence=self.calculate_confidence(features, scores),
                scored_at=start_time,
                valid_until=start_time + timedelta(hours=1)
            )
            
            # Cache the score
            await self.cache_score(lead_score)
            
            return lead_score
            
        except Exception as e:
            print(f"Error scoring lead {request.lead_id}: {e}")
            raise HTTPException(status_code=500, detail="Lead scoring failed")

    async def extract_lead_features(self, lead_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract numerical features from lead data for ML models"""
        features = {}
        
        # Demographic features
        features['company_size'] = self.normalize_company_size(
            lead_data.get('company', {}).get('employee_count', 0)
        )
        features['industry_score'] = self.get_industry_score(
            lead_data.get('company', {}).get('industry', '')
        )
        features['title_seniority'] = self.calculate_title_seniority(
            lead_data.get('title', '')
        )
        
        # Behavioral features
        web_activity = lead_data.get('web_activity', {})
        features['page_views'] = min(web_activity.get('page_views', 0), 100)
        features['time_on_site'] = min(web_activity.get('total_time_minutes', 0), 1440)
        features['pages_per_session'] = min(web_activity.get('avg_pages_per_session', 0), 20)
        
        # Engagement features
        email_activity = lead_data.get('email_activity', {})
        features['email_opens'] = min(email_activity.get('opens', 0), 50)
        features['email_clicks'] = min(email_activity.get('clicks', 0), 20)
        features['email_replies'] = min(email_activity.get('replies', 0), 10)
        
        # Intent features
        features['pricing_page_visits'] = min(web_activity.get('pricing_visits', 0), 20)
        features['demo_requests'] = min(lead_data.get('demo_requests', 0), 5)
        features['contact_form_submissions'] = min(lead_data.get('form_submissions', 0), 10)
        
        # Recency features
        last_activity = lead_data.get('last_activity_date')
        if last_activity:
            days_since_activity = (datetime.now() - datetime.fromisoformat(last_activity)).days
            features['days_since_last_activity'] = min(days_since_activity, 365)
        else:
            features['days_since_last_activity'] = 365
        
        return features

    def normalize_company_size(self, employee_count: int) -> float:
        """Normalize company size to 0-1 scale"""
        if employee_count <= 0:
            return 0.0
        elif employee_count <= 50:
            return 0.2
        elif employee_count <= 200:
            return 0.4
        elif employee_count <= 1000:
            return 0.6
        elif employee_count <= 5000:
            return 0.8
        else:
            return 1.0
```

## 3. Configuration Files

### 3.1 Kubernetes Deployment Configuration

```yaml
# sales-performance-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sales-performance-service
  namespace: sales-analytics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sales-performance-service
  template:
    metadata:
      labels:
        app: sales-performance-service
    spec:
      containers:
      - name: sales-performance-service
        image: sales-analytics/performance-service:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: postgresql-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: cache-secrets
              key: redis-url
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
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: sales-performance-service
  namespace: sales-analytics
spec:
  selector:
    app: sales-performance-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: ClusterIP
```

### 3.2 Environment Configuration

```yaml
# config/production.yaml
server:
  port: 3000
  host: "0.0.0.0"
  cors:
    origin: ["https://sales-analytics.company.com"]
    credentials: true

database:
  postgresql:
    host: "${DATABASE_HOST}"
    port: 5432
    database: "${DATABASE_NAME}"
    username: "${DATABASE_USER}"
    password: "${DATABASE_PASSWORD}"
    ssl: true
    pool:
      min: 5
      max: 20
      acquireTimeoutMillis: 30000
      idleTimeoutMillis: 600000

cache:
  redis:
    host: "${REDIS_HOST}"
    port: 6379
    password: "${REDIS_PASSWORD}"
    db: 0
    keyPrefix: "sales-analytics:"
    ttl: 3600

security:
  jwt:
    secret: "${JWT_SECRET}"
    expiresIn: "24h"
  encryption:
    algorithm: "aes-256-gcm"
    key: "${ENCRYPTION_KEY}"

monitoring:
  prometheus:
    enabled: true
    path: "/metrics"
  logging:
    level: "info"
    format: "json"

ml:
  models:
    path: "/app/models"
    version: "v1.0.0"
  inference:
    timeout: 5000
    batchSize: 100
```

This LLD provides implementation-ready specifications building upon all previous documents, enabling direct development of the sales performance analytics platform.
