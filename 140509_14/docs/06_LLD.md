# Low Level Design (LLD)
## Problem Statement 14: Financial Advisory AI

### ETVX Framework Application

**ENTRY CRITERIA:**
- PRD, FRD, NFRD, AD, and HLD documents completed and approved
- Component designs and API interfaces defined
- Technology stack selections validated

**TASK:**
Provide implementation-ready specifications including class structures, database schemas, API implementations, and deployment configurations.

**VERIFICATION & VALIDATION:**
- Class designs validated against HLD specifications
- Database schemas optimized for performance requirements
- API implementations tested for compliance

**EXIT CRITERIA:**
- Complete implementation-ready specifications
- Database schemas with production-ready indexes
- Configuration files and deployment scripts ready

---

## 1. Core Class Implementations

### 1.1 User Management Classes
```python
# models/user.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    risk_tolerance = Column(Integer, nullable=False)
    annual_income = Column(DECIMAL(12, 2), nullable=False)
    investment_experience = Column(String(50), nullable=False)
    kyc_status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# services/auth_service.py
class AuthenticationService:
    def __init__(self, secret_key: str, redis_client):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.redis_client = redis_client
    
    def create_access_token(self, data: dict) -> str:
        expire = datetime.utcnow() + timedelta(minutes=30)
        to_encode = data.copy()
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return payload
```

### 1.2 Portfolio Optimization
```python
# services/portfolio_optimizer.py
import numpy as np
from scipy.optimize import minimize

class PortfolioOptimizer:
    def optimize_portfolio(self, expected_returns, cov_matrix, risk_tolerance):
        n_assets = len(expected_returns)
        risk_aversion = (11 - risk_tolerance) / 10 * 10
        
        def objective(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -(portfolio_return - (risk_aversion / 2) * portfolio_variance)
        
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        bounds = tuple((0, 1) for _ in range(n_assets))
        x0 = np.array([1/n_assets] * n_assets)
        
        result = minimize(objective, x0, method='SLSQP', 
                         bounds=bounds, constraints=constraints)
        
        return {
            'weights': result.x,
            'expected_return': np.dot(result.x, expected_returns),
            'volatility': np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x))),
            'success': result.success
        }
```

## 2. Database Schema (PostgreSQL)

```sql
-- Core tables with indexes
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    risk_tolerance INTEGER CHECK (risk_tolerance BETWEEN 1 AND 10),
    annual_income DECIMAL(12,2) NOT NULL,
    investment_experience VARCHAR(50) NOT NULL,
    kyc_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_kyc_status ON users(kyc_status);

CREATE TABLE portfolios (
    portfolio_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    portfolio_name VARCHAR(100) NOT NULL,
    target_allocation JSONB NOT NULL,
    total_value DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);

CREATE TABLE holdings (
    holding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES portfolios(portfolio_id),
    symbol VARCHAR(10) NOT NULL,
    quantity DECIMAL(15,6) NOT NULL,
    current_price DECIMAL(10,4),
    market_value DECIMAL(12,2),
    weight DECIMAL(5,4),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_holdings_portfolio_id ON holdings(portfolio_id);
```

## 3. API Implementation (FastAPI)

```python
# api/main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI(title="Financial Advisory AI API")

class UserRegistrationRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    annual_income: float
    investment_experience: str

class RecommendationRequest(BaseModel):
    portfolio_id: uuid.UUID
    constraints: dict = {}

@app.post("/api/v1/auth/register")
async def register_user(request: UserRegistrationRequest):
    # Hash password and create user
    user = User(
        email=request.email,
        password_hash=auth_service.get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        annual_income=request.annual_income,
        investment_experience=request.investment_experience
    )
    
    db_session.add(user)
    db_session.commit()
    
    return {"user_id": str(user.user_id), "status": "registered"}

@app.post("/api/v1/recommendations/generate")
async def generate_recommendation(request: RecommendationRequest):
    # Get portfolio and user data
    portfolio = db_session.query(Portfolio).filter_by(
        portfolio_id=request.portfolio_id
    ).first()
    
    # Generate recommendation using AI engine
    recommendation = recommendation_engine.generate_recommendation(
        portfolio, request.constraints
    )
    
    return {
        "recommendation_id": str(uuid.uuid4()),
        "recommended_allocation": recommendation['allocation'],
        "confidence_score": recommendation['confidence'],
        "rationale": recommendation['explanation']
    }
```

## 4. Configuration Files

### 4.1 Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 Environment Configuration
```yaml
# config/production.yaml
database:
  host: ${DB_HOST}
  port: 5432
  name: financial_advisory
  user: ${DB_USER}
  password: ${DB_PASSWORD}

redis:
  host: ${REDIS_HOST}
  port: 6379
  db: 0

jwt:
  secret_key: ${JWT_SECRET_KEY}
  algorithm: HS256
  access_token_expire_minutes: 30

market_data:
  provider: alpha_vantage
  api_key: ${MARKET_DATA_API_KEY}
  update_frequency: 300  # seconds
```

### 4.3 Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: financial_advisory
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## 5. Deployment Scripts

```bash
#!/bin/bash
# deploy.sh
set -e

echo "Deploying Financial Advisory AI..."

# Build and push Docker images
docker build -t financial-advisory-api:latest .
docker tag financial-advisory-api:latest $REGISTRY/financial-advisory-api:latest
docker push $REGISTRY/financial-advisory-api:latest

# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo "Deployment completed successfully!"
```

---

**Document Approval:**
- Engineering Lead: [Signature Required]
- DevOps Engineer: [Signature Required]
- Security Officer: [Signature Required]

**Version Control:**
- Document Version: 1.0
- Last Updated: [Current Date]
- Next Review Date: [30 days from creation]

This LLD provides implementation-ready specifications for the Financial Advisory AI system, enabling direct development and deployment.
