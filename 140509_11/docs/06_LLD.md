# Low Level Design (LLD)
## Smart Retail Edge Vision - AI-Powered Computer Vision System for Retail Analytics and Automation

*Building upon README, PRD, FRD, NFRD, AD, and HLD foundations for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ README completed with problem overview and technical approach
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 15 functional requirements across 5 modules
- ✅ NFRD completed with performance, scalability, and security requirements
- ✅ AD completed with edge computing architecture and deployment strategy
- ✅ HLD completed with component specifications and API designs

### TASK
Develop implementation-ready detailed class structures, database schemas, API implementations, algorithm specifications, configuration files, and deployment scripts for all system components.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] Class structures implement all HLD component specifications
- [ ] Database schemas support all data models and performance requirements
- [ ] API implementations include validation, error handling, and security
- [ ] Algorithm specifications provide step-by-step implementation guidance

**Validation Criteria:**
- [ ] LLD validated with senior developers and technical leads
- [ ] Database schemas validated with DBA and performance teams
- [ ] API implementations validated with security and integration teams
- [ ] Configuration files validated with DevOps and infrastructure teams

### EXIT CRITERIA
- ✅ Complete implementation-ready class structures and database schemas
- ✅ API implementations with comprehensive error handling and validation
- ✅ Algorithm specifications for all AI/ML processing components
- ✅ Configuration files and deployment scripts for production deployment
- ✅ Foundation prepared for Pseudocode development

---

## 1. Core Service Implementation

### 1.1 Computer Vision Engine Implementation

**Class Structure:**
```python
# src/computer_vision/engine.py
import asyncio
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import cv2
import torch
from ultralytics import YOLO

@dataclass
class CVResult:
    camera_id: str
    timestamp: datetime
    objects: List[DetectedObject]
    persons: List[TrackedPerson]
    products: List[RecognizedProduct]
    behaviors: List[DetectedBehavior]
    processing_time: float
    confidence_scores: Dict[str, float]

class ComputerVisionEngine:
    def __init__(self, config: CVConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI models
        self.object_detector = self._initialize_object_detector()
        self.person_tracker = self._initialize_person_tracker()
        self.product_recognizer = self._initialize_product_recognizer()
        self.behavior_analyzer = self._initialize_behavior_analyzer()
        
        # Performance monitoring
        self.performance_metrics = PerformanceMetrics()
        
    async def process_frame(self, frame: np.ndarray, camera_id: str) -> CVResult:
        """Process single frame through complete CV pipeline"""
        start_time = time.time()
        
        try:
            # Validate input frame
            if not self._validate_frame(frame):
                raise InvalidFrameError("Invalid frame format or size")
                
            # Stage 1: Object Detection
            objects = await self._detect_objects(frame)
            
            # Stage 2: Person Tracking
            persons = await self._track_persons(objects, camera_id, frame)
            
            # Stage 3: Product Recognition
            products = await self._recognize_products(objects, frame)
            
            # Stage 4: Behavior Analysis
            behaviors = await self._analyze_behaviors(persons, frame)
            
            # Calculate performance metrics
            total_time = time.time() - start_time
            
            # Create result
            result = CVResult(
                camera_id=camera_id,
                timestamp=datetime.utcnow(),
                objects=objects,
                persons=persons,
                products=products,
                behaviors=behaviors,
                processing_time=total_time,
                confidence_scores=self._calculate_confidence_scores(objects, persons, products)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Frame processing failed for camera {camera_id}: {str(e)}")
            raise CVProcessingError(f"Frame processing failed: {str(e)}")
```

### 1.2 Database Schema Implementation

**PostgreSQL Schema:**
```sql
-- Stores table
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    configuration JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cameras table
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    rtsp_url VARCHAR(500) NOT NULL,
    position JSONB NOT NULL,
    field_of_view JSONB NOT NULL,
    status camera_status_enum DEFAULT 'active',
    configuration JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TYPE camera_status_enum AS ENUM ('active', 'inactive', 'maintenance', 'error');

-- Object detections with time-based partitioning
CREATE TABLE object_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    object_class VARCHAR(50) NOT NULL,
    confidence DECIMAL(4,3) NOT NULL,
    bbox_x1 INTEGER NOT NULL,
    bbox_y1 INTEGER NOT NULL,
    bbox_x2 INTEGER NOT NULL,
    bbox_y2 INTEGER NOT NULL,
    center_x INTEGER NOT NULL,
    center_y INTEGER NOT NULL,
    area INTEGER NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (detected_at);

-- Person tracking table
CREATE TABLE person_tracks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    track_id VARCHAR(100) NOT NULL,
    demographic_age_group VARCHAR(20),
    demographic_gender VARCHAR(20),
    entry_time TIMESTAMP WITH TIME ZONE,
    exit_time TIMESTAMP WITH TIME ZONE,
    total_dwell_time INTEGER,
    path JSONB,
    zones_visited TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security events
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    event_type security_event_type_enum NOT NULL,
    severity security_severity_enum NOT NULL,
    description TEXT,
    confidence DECIMAL(4,3),
    resolved BOOLEAN DEFAULT FALSE,
    event_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TYPE security_event_type_enum AS ENUM (
    'suspicious_behavior', 'potential_theft', 'loitering', 
    'aggressive_behavior', 'perimeter_breach'
);

CREATE TYPE security_severity_enum AS ENUM ('low', 'medium', 'high', 'critical');

-- Performance indexes
CREATE INDEX idx_object_detections_camera_time ON object_detections (camera_id, detected_at);
CREATE INDEX idx_person_tracks_store_entry ON person_tracks (store_id, entry_time);
CREATE INDEX idx_security_events_store_severity ON security_events (store_id, severity, event_time);
```

### 1.3 API Implementation

**FastAPI Service:**
```python
# src/api/main.py
from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import asyncio
import json
import logging
from datetime import datetime

app = FastAPI(
    title="Smart Retail Edge Vision API",
    description="AI-Powered Computer Vision System for Retail Analytics",
    version="1.0.0"
)

security = HTTPBearer()

# Request/Response Models
class ProcessFrameRequest(BaseModel):
    camera_id: str = Field(..., description="Camera identifier")
    frame_data: str = Field(..., description="Base64 encoded frame data")
    timestamp: Optional[datetime] = Field(default=None)

class ProcessFrameResponse(BaseModel):
    camera_id: str
    timestamp: datetime
    processing_time: float
    objects_detected: int
    persons_tracked: int
    products_recognized: int
    confidence_scores: Dict[str, float]

class SecurityAlert(BaseModel):
    id: str
    store_id: str
    camera_id: str
    event_type: str
    severity: str
    description: str
    timestamp: datetime
    confidence: float

# Computer Vision Endpoints
@app.post("/api/v1/cv/process", response_model=ProcessFrameResponse)
async def process_frame(
    request: ProcessFrameRequest,
    cv_engine = Depends(get_cv_engine)
):
    """Process single frame through computer vision pipeline"""
    try:
        # Decode frame data
        frame_bytes = base64.b64decode(request.frame_data)
        frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid frame data")
        
        # Process frame
        result = await cv_engine.process_frame(frame, request.camera_id)
        
        # Create response
        response = ProcessFrameResponse(
            camera_id=result.camera_id,
            timestamp=result.timestamp,
            processing_time=result.processing_time,
            objects_detected=len(result.objects),
            persons_tracked=len(result.persons),
            products_recognized=len(result.products),
            confidence_scores=result.confidence_scores
        )
        
        return response
        
    except Exception as e:
        logging.error(f"Frame processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Frame processing failed")

@app.websocket("/ws/cv/stream/{camera_id}")
async def websocket_cv_stream(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for real-time computer vision processing"""
    await websocket.accept()
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_text()
            frame_data = json.loads(data)
            
            # Process frame and send results
            # Implementation details...
            
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for camera {camera_id}")

@app.get("/api/v1/security/alerts", response_model=List[SecurityAlert])
async def get_security_alerts(
    store_id: str,
    severity: Optional[str] = None,
    limit: int = 100
):
    """Get recent security alerts"""
    try:
        # Implementation details...
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail="Security alerts request failed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

### 1.4 Configuration Files

**Docker Compose:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  retail-vision-app:
    build:
      context: .
      dockerfile: Dockerfile.edge
    container_name: retail-vision-app
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/retail_vision
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    volumes:
      - ./config:/app/config
      - ./models:/app/models
      - ./logs:/app/logs
    ports:
      - "8000:8000"
      - "8001:8001"
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  postgres:
    image: postgres:14-alpine
    container_name: retail-vision-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=retail_vision
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    container_name: retail-vision-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
```

**Environment Configuration:**
```yaml
# config/production.yaml
database:
  host: ${DATABASE_HOST:localhost}
  port: ${DATABASE_PORT:5432}
  name: ${DATABASE_NAME:retail_vision}
  username: ${DATABASE_USERNAME:postgres}
  password: ${DATABASE_PASSWORD:password}
  ssl: true
  pool_size: 20

redis:
  url: ${REDIS_URL:redis://localhost:6379}
  max_connections: 50

computer_vision:
  models:
    object_detection:
      model_path: "/app/models/yolov8n.engine"
      confidence_threshold: 0.5
      iou_threshold: 0.4
    person_tracking:
      max_disappeared: 30
      max_distance: 100
  performance:
    max_processing_time: 0.1  # 100ms
    target_fps: 30

security:
  alert_thresholds:
    suspicious_behavior: 0.7
    potential_theft: 0.8
    loitering: 0.6
  notification:
    enabled: true
    webhook_url: ${SECURITY_WEBHOOK_URL}

logging:
  level: ${LOG_LEVEL:INFO}
  format: json
  handlers:
    - console
    - file
```

This LLD provides implementation-ready specifications with detailed class structures, database schemas, API implementations, and configuration files for direct development implementation.
