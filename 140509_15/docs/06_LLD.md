# Low Level Design (LLD)
## Healthcare Patient Risk Stratification Platform

### Document Control
- **Document Version**: 1.0
- **Created**: 2025-01-XX
- **Document Owner**: Development Team

---

## ETVX Framework Application

### Entry Criteria
- ✅ **PRD Approved** - Business objectives and product features defined
- ✅ **FRD Completed** - Functional specifications documented
- ✅ **NFRD Validated** - Quality attributes and constraints established
- ✅ **AD Approved** - System architecture and component design finalized
- ✅ **HLD Completed** - Component designs and API specifications detailed

### Task (This Document)
Define implementation-ready specifications including class structures, database schemas, API implementations, configuration files, and deployment scripts.

### Verification & Validation
- **Code Review** - Development team validation of implementation specifications
- **Database Review** - DBA team validation of schema designs and performance
- **Security Review** - Security team validation of implementation security controls

### Exit Criteria
- ✅ **Implementation Specs Complete** - All code structures and schemas defined
- ✅ **Configuration Ready** - Deployment and runtime configurations specified
- ✅ **Development Ready** - Teams can begin implementation with clear specifications

---

## Implementation Overview

Building upon the PRD business objectives, FRD functional specifications, NFRD quality attributes, AD system architecture, and HLD component designs, this LLD provides implementation-ready specifications for immediate development.

---

## 1. Database Schema Implementation

### PostgreSQL Schema (Clinical Data)
```sql
-- Database: healthcare_risk_platform
-- Version: PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Patients table with comprehensive indexing
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mrn VARCHAR(50) UNIQUE NOT NULL,
    external_id VARCHAR(100),
    demographics JSONB NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    CONSTRAINT valid_demographics CHECK (
        demographics ? 'name' AND 
        demographics ? 'birthDate' AND
        demographics ? 'gender'
    )
);

-- Optimized indexes for patient queries
CREATE INDEX CONCURRENTLY idx_patients_mrn ON patients(mrn) WHERE active = true;
CREATE INDEX CONCURRENTLY idx_patients_demographics_gin ON patients USING gin(demographics);
CREATE INDEX CONCURRENTLY idx_patients_updated_at ON patients(updated_at DESC);

-- Clinical data with partitioning by date
CREATE TABLE clinical_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    data_type VARCHAR(50) NOT NULL,
    data_payload JSONB NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    source_system VARCHAR(100) NOT NULL,
    quality_score DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_quality_score CHECK (quality_score >= 0.0 AND quality_score <= 1.0)
) PARTITION BY RANGE (effective_date);

-- Create partitions for current and future years
CREATE TABLE clinical_data_2024 PARTITION OF clinical_data
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE clinical_data_2025 PARTITION OF clinical_data
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Risk scores table
CREATE TABLE risk_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    condition_type VARCHAR(50) NOT NULL,
    risk_score DECIMAL(5,4) NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    contributing_factors JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT valid_risk_score CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

CREATE INDEX idx_risk_scores_patient_condition 
ON risk_scores(patient_id, condition_type, calculated_at DESC);
```

---

## 2. FastAPI Implementation

### Risk Assessment Service
```python
# File: risk_assessment_service/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import asyncio
import logging
from datetime import datetime, timedelta

app = FastAPI(
    title="Healthcare Risk Assessment API",
    version="1.0.0",
    description="AI-powered patient risk stratification service"
)

security = HTTPBearer()

# Request/Response Models
class RiskAssessmentRequest(BaseModel):
    patient_id: str = Field(..., description="Unique patient identifier")
    conditions: List[str] = Field(
        default=["sepsis", "readmission", "mortality"],
        description="Conditions to assess risk for"
    )
    time_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Time window for assessment in hours"
    )
    include_explanations: bool = Field(
        default=True,
        description="Include AI explanations in response"
    )

class RiskScore(BaseModel):
    condition: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., regex="^(LOW|MODERATE|HIGH|CRITICAL)$")
    contributing_factors: Optional[List[Dict[str, float]]] = None
    recommendations: Optional[List[str]] = None

class RiskAssessmentResponse(BaseModel):
    patient_id: str
    assessment_timestamp: datetime
    risk_scores: List[RiskScore]
    overall_risk_level: str
    next_assessment_due: datetime
    model_versions: Dict[str, str]

# Main risk assessment endpoint
@app.post("/api/v1/risk/assess", response_model=RiskAssessmentResponse)
async def assess_patient_risk(
    request: RiskAssessmentRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Assess patient risk for specified conditions"""
    try:
        # Validate patient exists and user has access
        patient = await validate_patient_access(request.patient_id, current_user)
        
        # Fetch patient data
        patient_data = await get_patient_clinical_data(
            request.patient_id, 
            request.time_window_hours
        )
        
        # Parallel risk assessment for all conditions
        risk_tasks = [
            assess_condition_risk(condition, patient_data, request.include_explanations)
            for condition in request.conditions
        ]
        
        risk_scores = await asyncio.gather(*risk_tasks)
        
        # Calculate overall risk level
        overall_risk = calculate_overall_risk(risk_scores)
        
        # Schedule next assessment
        next_assessment = calculate_next_assessment_time(risk_scores)
        
        # Log assessment for audit
        background_tasks.add_task(
            log_risk_assessment,
            request.patient_id,
            current_user.id,
            risk_scores
        )
        
        return RiskAssessmentResponse(
            patient_id=request.patient_id,
            assessment_timestamp=datetime.utcnow(),
            risk_scores=risk_scores,
            overall_risk_level=overall_risk,
            next_assessment_due=next_assessment,
            model_versions=get_model_versions()
        )
        
    except Exception as e:
        logger.error(f"Risk assessment failed for patient {request.patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Risk assessment failed")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "models_loaded": len(await get_loaded_models())
    }
```

---

## 3. Docker Configuration

### Docker Compose
```yaml
# File: docker-compose.yml
version: '3.8'

services:
  # API Gateway
  kong:
    image: kong:3.4
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: postgres
      KONG_PG_DATABASE: kong
      KONG_PG_USER: kong
      KONG_PG_PASSWORD: ${KONG_PG_PASSWORD}
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
    ports:
      - "8000:8000"
      - "8001:8001"
    depends_on:
      - postgres
    networks:
      - healthcare-network

  # Risk Assessment Service
  risk-assessment-service:
    build:
      context: ./risk-assessment-service
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/healthcare
      REDIS_URL: redis://redis:6379
      MLFLOW_TRACKING_URI: http://mlflow:5000
      MODEL_REGISTRY_URI: s3://healthcare-models/
    ports:
      - "8002:8000"
    depends_on:
      - postgres
      - redis
      - mlflow
    networks:
      - healthcare-network
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 4G
          cpus: '2.0'

  # Databases
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: healthcare
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - healthcare-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - healthcare-network

volumes:
  postgres_data:
  redis_data:

networks:
  healthcare-network:
    driver: bridge
```

---

## 4. Kubernetes Deployment

### Risk Assessment Deployment
```yaml
# File: k8s/risk-assessment-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: risk-assessment-service
  namespace: healthcare
  labels:
    app: risk-assessment-service
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: risk-assessment-service
  template:
    metadata:
      labels:
        app: risk-assessment-service
        version: v1.0.0
    spec:
      containers:
      - name: risk-assessment
        image: healthcare/risk-assessment:1.0.0
        ports:
        - containerPort: 8000
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
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: risk-assessment-service
  namespace: healthcare
spec:
  selector:
    app: risk-assessment-service
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

---

## 5. Security Implementation

### JWT Token Validation
```python
# File: auth/jwt_validator.py
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from cryptography.hazmat.primitives import serialization

class JWTValidator:
    def __init__(self, public_key_path: str, algorithm: str = "RS256"):
        with open(public_key_path, 'rb') as key_file:
            self.public_key = serialization.load_pem_public_key(key_file.read())
        self.algorithm = algorithm
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token and return user claims"""
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True, "verify_aud": True}
            )
            
            # Additional validation
            if not self._validate_claims(payload):
                return None
            
            # Check if user is active
            if not await self._is_user_active(payload.get('sub')):
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def _validate_claims(self, payload: Dict) -> bool:
        """Validate required claims"""
        required_claims = ['sub', 'iat', 'exp', 'aud', 'roles']
        return all(claim in payload for claim in required_claims)
```

### Data Encryption Service
```python
# File: security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance with derived key"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_pii(self, data: str) -> str:
        """Encrypt personally identifiable information"""
        encrypted_data = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_pii(self, encrypted_data: str) -> str:
        """Decrypt personally identifiable information"""
        decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.fernet.decrypt(decoded_data)
        return decrypted_data.decode()
```

---

## 6. ML Model Implementation

### Sepsis Risk Model
```python
# File: models/sepsis_model.py
import tensorflow as tf
import numpy as np
from typing import Dict, List, Tuple

class SepsisRiskModel:
    def __init__(self, model_path: str):
        self.model = tf.keras.models.load_model(model_path)
        self.feature_columns = self._load_feature_columns()
        self.scaler = self._load_scaler()
    
    def predict_risk(self, patient_data: Dict) -> Dict:
        """Predict sepsis risk for a patient"""
        # Extract and normalize features
        features = self._extract_features(patient_data)
        normalized_features = self.scaler.transform([features])
        
        # Model prediction
        prediction = self.model.predict(normalized_features)
        risk_score = float(prediction[0][0])
        
        # Calculate confidence
        confidence = self._calculate_confidence(normalized_features, prediction)
        
        # Generate explanations
        explanations = self._generate_explanations(features, prediction)
        
        return {
            'risk_score': risk_score,
            'confidence': confidence,
            'contributing_factors': explanations,
            'risk_level': self._categorize_risk(risk_score)
        }
    
    def _extract_features(self, patient_data: Dict) -> List[float]:
        """Extract features from patient data"""
        features = []
        
        # Vital signs features
        vitals = patient_data.get('vitals', {})
        features.extend([
            vitals.get('heart_rate', 0),
            vitals.get('systolic_bp', 0),
            vitals.get('diastolic_bp', 0),
            vitals.get('temperature', 0),
            vitals.get('respiratory_rate', 0),
            vitals.get('oxygen_saturation', 0)
        ])
        
        # Lab values features
        labs = patient_data.get('labs', {})
        features.extend([
            labs.get('white_blood_cell_count', 0),
            labs.get('lactate', 0),
            labs.get('procalcitonin', 0),
            labs.get('creatinine', 0)
        ])
        
        # Demographics
        demographics = patient_data.get('demographics', {})
        features.extend([
            demographics.get('age', 0),
            1 if demographics.get('gender') == 'M' else 0
        ])
        
        return features
    
    def _calculate_confidence(self, features: np.ndarray, prediction: np.ndarray) -> float:
        """Calculate prediction confidence"""
        # Use model uncertainty estimation
        predictions = []
        for _ in range(100):
            pred = self.model.predict(features, training=True)
            predictions.append(pred[0][0])
        
        std = np.std(predictions)
        confidence = max(0.0, min(1.0, 1.0 - (std * 2)))
        return float(confidence)
    
    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score into levels"""
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.3:
            return "MODERATE"
        else:
            return "LOW"
```

---

## Conclusion

This Low Level Design provides comprehensive implementation-ready specifications for the Healthcare Patient Risk Stratification Platform. The detailed database schemas, API implementations, configuration files, and security controls enable immediate development while ensuring enterprise-grade quality and compliance.

Building upon all previous documents (PRD, FRD, NFRD, AD, HLD), this LLD completes the technical foundation for a production-ready healthcare AI system.

**Next Steps**: Proceed to Pseudocode development to define executable algorithms and implementation logic.

---

*This document is confidential and proprietary. Distribution is restricted to authorized personnel only.*
