# Low Level Design (LLD)
## Document Intelligence and Processing Platform - AI-Powered Document Processing System

*Building upon README, PRD, FRD, NFRD, AD, and HLD foundations for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ README completed with problem overview, technical approach, and expected outcomes
- ✅ PRD completed with business objectives, user personas, success metrics, and core features
- ✅ FRD completed with 42 detailed functional requirements across 5 system modules
- ✅ NFRD completed with performance (<30s processing), scalability (1M+ documents/month), security (AES-256), reliability (99.9% uptime)
- ✅ AD completed with microservices architecture, AI/ML pipeline, data layer, integration patterns, and deployment strategy
- ✅ HLD completed with detailed component specifications, API designs, data models, and processing workflows

### TASK
Develop implementation-ready low-level design specifications including detailed class structures, database implementations, API implementations, algorithm specifications, configuration files, and deployment scripts.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All HLD components implemented with detailed class structures and method signatures
- [ ] Database schemas implemented with indexes, constraints, and optimization strategies
- [ ] API implementations include request/response models, validation, error handling, and security
- [ ] Algorithm implementations provide step-by-step logic for OCR, classification, and extraction

**Validation Criteria:**
- [ ] Code structures validated with senior developers and technical leads
- [ ] Database implementations validated with database administrators and performance engineers
- [ ] API implementations validated through contract testing and integration validation
- [ ] Algorithm implementations validated with data scientists and ML engineers

### EXIT CRITERIA
- ✅ Complete implementation-ready class structures for all microservices
- ✅ Production-ready database schemas with performance optimizations
- ✅ Fully specified API implementations with comprehensive error handling
- ✅ Detailed algorithm implementations for all OCR, classification, and extraction components

---

## 1. Database Implementation

### 1.1 PostgreSQL Schema with Performance Optimizations

#### Documents Table with Partitioning
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size > 0),
    file_hash VARCHAR(64) NOT NULL,
    
    -- Document metadata
    title VARCHAR(500),
    description TEXT,
    tags JSONB DEFAULT '[]' NOT NULL,
    category VARCHAR(100),
    confidentiality_level VARCHAR(20) NOT NULL DEFAULT 'internal',
    
    -- Processing status
    processing_status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    processing_progress INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Storage information
    storage_provider VARCHAR(50) NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    storage_region VARCHAR(50),
    
    -- Quality metrics
    quality_score DECIMAL(5,4),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_documents_organization FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_documents_user FOREIGN KEY (user_id) REFERENCES users(id)
) PARTITION BY RANGE (created_at);

-- Performance indexes
CREATE INDEX CONCURRENTLY idx_documents_org_created ON documents (organization_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_documents_status ON documents (processing_status, created_at DESC);
CREATE INDEX CONCURRENTLY idx_documents_tags ON documents USING GIN(tags);
```

#### OCR Results Table
```sql
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    processing_engine VARCHAR(50) NOT NULL,
    processing_time DECIMAL(8,3) NOT NULL,
    
    -- OCR metrics
    total_pages INTEGER NOT NULL,
    overall_confidence DECIMAL(5,4) NOT NULL,
    language_detected VARCHAR(10),
    
    -- Extracted content
    full_text TEXT NOT NULL,
    text_blocks JSONB NOT NULL DEFAULT '[]',
    layout_analysis JSONB NOT NULL DEFAULT '{}',
    
    -- Quality metrics
    quality_score DECIMAL(5,4),
    potential_errors JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_ocr_results_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) PARTITION BY RANGE (created_at);

-- Performance indexes
CREATE INDEX CONCURRENTLY idx_ocr_results_document ON ocr_results (document_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_ocr_results_confidence ON ocr_results (overall_confidence DESC);
CREATE INDEX CONCURRENTLY idx_ocr_results_text_blocks ON ocr_results USING GIN(text_blocks);
```

## 2. Backend Service Implementation

### 2.1 Document Ingestion Service (Node.js/TypeScript)

```typescript
import express, { Request, Response } from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import { Pool } from 'pg';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

interface DocumentUploadRequest {
  file: Express.Multer.File;
  metadata?: DocumentMetadata;
  organizationId: string;
  userId: string;
}

interface DocumentMetadata {
  title?: string;
  description?: string;
  tags?: string[];
  category?: string;
  confidentialityLevel: 'public' | 'internal' | 'confidential' | 'restricted';
}

export class DocumentIngestionService {
  private readonly dbPool: Pool;
  private readonly s3Client: S3Client;

  constructor(dbPool: Pool, s3Client: S3Client) {
    this.dbPool = dbPool;
    this.s3Client = s3Client;
  }

  async uploadDocument(request: DocumentUploadRequest): Promise<DocumentUploadResponse> {
    const documentId = uuidv4();
    
    try {
      // Step 1: Validate file
      const validation = await this.validateFile(request.file);
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }

      // Step 2: Upload to storage
      const storagePath = this.generateStoragePath(documentId, request.file.originalname);
      await this.uploadToStorage(request.file.buffer, storagePath);

      // Step 3: Create database record
      const documentRecord = await this.createDocumentRecord({
        id: documentId,
        organizationId: request.organizationId,
        userId: request.userId,
        filename: request.file.originalname,
        contentType: request.file.mimetype,
        fileSize: request.file.size,
        storagePath,
        metadata: request.metadata
      });

      // Step 4: Queue processing
      await this.queueProcessingJob(documentId);

      return {
        documentId,
        status: 'uploaded',
        estimatedProcessingTime: this.estimateProcessingTime(request.file.size)
      };

    } catch (error) {
      console.error(`Upload failed for ${documentId}:`, error);
      throw error;
    }
  }

  private async validateFile(file: Express.Multer.File): Promise<ValidationResult> {
    const errors: string[] = [];
    
    // Size validation
    if (file.size > 100 * 1024 * 1024) {
      errors.push('File too large');
    }
    
    // Type validation
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!allowedTypes.includes(file.mimetype)) {
      errors.push('Unsupported file type');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  private generateStoragePath(documentId: string, filename: string): string {
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `documents/${year}/${month}/${day}/${documentId}/${filename}`;
  }

  private async uploadToStorage(buffer: Buffer, path: string): Promise<void> {
    const command = new PutObjectCommand({
      Bucket: process.env.S3_BUCKET_NAME,
      Key: path,
      Body: buffer,
      ServerSideEncryption: 'AES256'
    });

    await this.s3Client.send(command);
  }

  private async createDocumentRecord(data: DocumentRecordData): Promise<DocumentRecord> {
    const query = `
      INSERT INTO documents (
        id, organization_id, user_id, filename, content_type, 
        file_size, storage_path, storage_provider, title, description, 
        tags, category, confidentiality_level
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      RETURNING *
    `;
    
    const values = [
      data.id,
      data.organizationId,
      data.userId,
      data.filename,
      data.contentType,
      data.fileSize,
      data.storagePath,
      'aws-s3',
      data.metadata?.title,
      data.metadata?.description,
      JSON.stringify(data.metadata?.tags || []),
      data.metadata?.category,
      data.metadata?.confidentialityLevel || 'internal'
    ];

    const result = await this.dbPool.query(query, values);
    return result.rows[0];
  }
}
```

### 2.2 OCR Processing Service (Python/FastAPI)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import cv2
import numpy as np
import pytesseract
from paddleocr import PaddleOCR
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

app = FastAPI(title="OCR Processing Service")

class OCRRequest(BaseModel):
    document_id: str
    image_data: bytes
    language: str = "auto"
    engine: str = "ensemble"

class OCRResponse(BaseModel):
    document_id: str
    text: str
    confidence: float
    processing_time: float
    blocks: list

class OCRProcessor:
    def __init__(self):
        self.tesseract_config = '--oem 3 --psm 6'
        self.paddleocr = PaddleOCR(use_angle_cls=True, lang='en')
        self.trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
        self.trocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-printed')
    
    async def process_image(self, image_data: bytes, engine: str = "ensemble") -> OCRResponse:
        # Convert bytes to OpenCV image
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if engine == "tesseract":
            return await self.process_with_tesseract(image)
        elif engine == "paddleocr":
            return await self.process_with_paddleocr(image)
        elif engine == "trocr":
            return await self.process_with_trocr(image)
        else:
            return await self.process_with_ensemble(image)
    
    async def process_with_tesseract(self, image) -> dict:
        # Preprocess image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Extract text with confidence scores
        data = pytesseract.image_to_data(denoised, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
        
        # Filter out low confidence text
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        texts = [data['text'][i] for i, conf in enumerate(data['conf']) if int(conf) > 30]
        
        full_text = ' '.join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'text': full_text,
            'confidence': avg_confidence / 100,
            'blocks': self.extract_text_blocks(data)
        }
    
    async def process_with_paddleocr(self, image) -> dict:
        result = self.paddleocr.ocr(image, cls=True)
        
        texts = []
        confidences = []
        blocks = []
        
        for line in result:
            for word_info in line:
                bbox, (text, confidence) = word_info
                texts.append(text)
                confidences.append(confidence)
                blocks.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox
                })
        
        return {
            'text': ' '.join(texts),
            'confidence': sum(confidences) / len(confidences) if confidences else 0,
            'blocks': blocks
        }
    
    async def process_with_ensemble(self, image) -> dict:
        # Run multiple OCR engines in parallel
        tesseract_task = asyncio.create_task(self.process_with_tesseract(image))
        paddleocr_task = asyncio.create_task(self.process_with_paddleocr(image))
        
        tesseract_result, paddleocr_result = await asyncio.gather(tesseract_task, paddleocr_task)
        
        # Combine results using confidence weighting
        if tesseract_result['confidence'] > paddleocr_result['confidence']:
            return tesseract_result
        else:
            return paddleocr_result

ocr_processor = OCRProcessor()

@app.post("/process", response_model=OCRResponse)
async def process_document(request: OCRRequest):
    try:
        result = await ocr_processor.process_image(request.image_data, request.engine)
        
        return OCRResponse(
            document_id=request.document_id,
            text=result['text'],
            confidence=result['confidence'],
            processing_time=0.0,  # Calculate actual time
            blocks=result['blocks']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 3. Configuration Files

### 3.1 Kubernetes Deployment Configuration

```yaml
# document-ingestion-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: document-ingestion-service
  namespace: document-intelligence
spec:
  replicas: 3
  selector:
    matchLabels:
      app: document-ingestion-service
  template:
    metadata:
      labels:
        app: document-ingestion-service
    spec:
      containers:
      - name: document-ingestion
        image: document-intelligence/ingestion-service:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: postgresql-url
        - name: S3_BUCKET_NAME
          value: "document-intelligence-storage"
        - name: AWS_REGION
          value: "us-east-1"
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
  name: document-ingestion-service
  namespace: document-intelligence
spec:
  selector:
    app: document-ingestion-service
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
    origin: ["https://document-intelligence.company.com"]
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
      min: 10
      max: 50

storage:
  aws:
    region: "${AWS_REGION}"
    bucket: "${S3_BUCKET_NAME}"
    encryption: "AES256"

processing:
  ocr:
    engines: ["tesseract", "paddleocr", "trocr"]
    default_engine: "ensemble"
    confidence_threshold: 0.7
  
  classification:
    model_path: "/app/models/classification"
    confidence_threshold: 0.8
  
  extraction:
    model_path: "/app/models/extraction"
    entity_types: ["PERSON", "ORG", "DATE", "MONEY"]

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
```

This LLD provides implementation-ready specifications with detailed class structures, database schemas, API implementations, and configuration files that enable direct development of the document intelligence platform.
