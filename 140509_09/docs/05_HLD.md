# High Level Design (HLD)
## Document Intelligence and Processing Platform - AI-Powered Document Processing System

*Building upon README, PRD, FRD, NFRD, and AD foundations for detailed component specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ README completed with problem overview, technical approach, and expected outcomes
- ✅ PRD completed with business objectives, user personas, success metrics, and core features
- ✅ FRD completed with 42 detailed functional requirements across 5 system modules
- ✅ NFRD completed with performance (<30s processing), scalability (1M+ documents/month), security (AES-256), reliability (99.9% uptime)
- ✅ AD completed with microservices architecture, AI/ML pipeline, data layer, integration patterns, and deployment strategy

### TASK
Develop detailed high-level design specifications including component interfaces, data models, API specifications, processing workflows, AI/ML model architectures, and system integration patterns that enable implementation of all functional requirements with specified performance and reliability targets.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All AD components detailed with interfaces, dependencies, and data flows
- [ ] API specifications cover all FRD functional requirements with request/response models
- [ ] Data models support all document types and processing workflows
- [ ] AI/ML components designed for 95% accuracy targets and continuous learning
- [ ] Processing workflows handle all document types with <30s processing time
- [ ] Integration patterns support all enterprise systems and cloud platforms

**Validation Criteria:**
- [ ] Component specifications validated with software architects and development teams
- [ ] API designs validated through contract testing and integration scenarios
- [ ] Data models validated with database administrators and data engineers
- [ ] AI/ML architectures validated with data scientists and ML engineers
- [ ] Processing workflows validated with business analysts and domain experts
- [ ] Integration patterns validated with enterprise architects and IT administrators

### EXIT CRITERIA
- ✅ Complete high-level design ready for low-level implementation design
- ✅ Detailed component specifications with interfaces and dependencies
- ✅ Comprehensive API specifications for all service interactions
- ✅ Data models supporting all functional and performance requirements
- ✅ Foundation prepared for detailed implementation design and development

---

### Reference to Previous Documents
This HLD builds upon **README**, **PRD**, **FRD**, **NFRD**, and **AD** foundations:
- **README Technical Approach** → Detailed component design implementing microservices and AI/ML pipeline
- **PRD Success Metrics** → Component specifications supporting 300% ROI and 95% accuracy targets
- **PRD User Personas** → Interface designs tailored for document processors, IT administrators, and business analysts
- **FRD Functional Requirements** → Detailed implementation of all 42 functional requirements across components
- **NFRD Performance Requirements** → Component design meeting <30s processing, 1000+ concurrent users, 99.9% uptime
- **AD System Architecture** → Detailed specification of all architectural components and their interactions

## 1. Component Architecture and Interfaces

### 1.1 Document Ingestion Service

#### 1.1.1 Component Overview
**Technology Stack**: Node.js 18+, Express.js 4.18+, Multer 1.4+, Sharp 0.32+
**Primary Responsibilities**:
- Multi-format document upload handling with validation
- Document preprocessing and optimization
- Metadata extraction and enrichment
- Cloud storage integration and management
- Batch processing coordination and status tracking

#### 1.1.2 Service Interface Specification
```typescript
// Document Ingestion Service API Interface
interface DocumentIngestionAPI {
  // Document upload endpoints
  uploadDocument(request: DocumentUploadRequest): Promise<DocumentUploadResponse>;
  uploadBatch(request: BatchUploadRequest): Promise<BatchUploadResponse>;
  
  // Document management endpoints
  getDocumentStatus(documentId: string): Promise<DocumentStatusResponse>;
  getDocumentMetadata(documentId: string): Promise<DocumentMetadataResponse>;
  deleteDocument(documentId: string): Promise<DeleteDocumentResponse>;
  
  // Preprocessing endpoints
  preprocessDocument(documentId: string, options: PreprocessingOptions): Promise<PreprocessingResponse>;
  getPreprocessingStatus(documentId: string): Promise<PreprocessingStatusResponse>;
}

// Request/Response Models
interface DocumentUploadRequest {
  file: Buffer | Stream;
  filename: string;
  contentType: string;
  metadata?: DocumentMetadata;
  processingOptions?: ProcessingOptions;
  organizationId: string;
  userId: string;
}

interface DocumentUploadResponse {
  documentId: string;
  status: 'uploaded' | 'validating' | 'preprocessing' | 'ready';
  uploadUrl?: string;
  estimatedProcessingTime: number;
  supportedFormats: string[];
}

interface DocumentMetadata {
  title?: string;
  description?: string;
  tags?: string[];
  category?: string;
  confidentialityLevel: 'public' | 'internal' | 'confidential' | 'restricted';
  retentionPeriod?: number;
  customFields?: Record<string, any>;
}
```

#### 1.1.3 Internal Component Architecture
```typescript
// Core Components
class DocumentValidator {
  validateFormat(file: Buffer, contentType: string): ValidationResult;
  validateSize(file: Buffer, maxSize: number): ValidationResult;
  validateIntegrity(file: Buffer): ValidationResult;
  scanForMalware(file: Buffer): Promise<SecurityScanResult>;
}

class DocumentPreprocessor {
  optimizeImage(image: Buffer): Promise<Buffer>;
  correctOrientation(image: Buffer): Promise<Buffer>;
  enhanceQuality(image: Buffer): Promise<Buffer>;
  extractMetadata(file: Buffer): Promise<FileMetadata>;
}

class CloudStorageManager {
  uploadToStorage(file: Buffer, path: string): Promise<StorageResult>;
  generateSignedUrl(path: string, expiration: number): Promise<string>;
  deleteFromStorage(path: string): Promise<boolean>;
  copyBetweenStorages(sourcePath: string, destPath: string): Promise<boolean>;
}
```

#### 1.1.4 Data Flow and Processing Workflow
```yaml
Document Upload Workflow:
  1. Request Validation:
     - Authenticate user and validate permissions
     - Validate file format and size constraints
     - Check organization quotas and limits
     
  2. File Processing:
     - Virus scanning and security validation
     - File integrity verification
     - Metadata extraction and enrichment
     
  3. Preprocessing:
     - Image optimization and enhancement
     - Orientation correction and deskewing
     - Format conversion if required
     
  4. Storage and Indexing:
     - Upload to cloud storage with encryption
     - Create database records with metadata
     - Generate search index entries
     
  5. Event Publication:
     - Publish document.uploaded event
     - Trigger downstream processing workflows
     - Send status notifications to users
```

### 1.2 OCR Processing Service

#### 1.2.1 Component Overview
**Technology Stack**: Python 3.11+, FastAPI 0.104+, Tesseract 5.3+, PaddleOCR 2.7+, TrOCR
**Primary Responsibilities**:
- Advanced optical character recognition with multiple engines
- Multi-language text extraction and recognition
- Layout analysis and document structure detection
- Handwriting recognition and processing
- Quality assessment and confidence scoring

#### 1.2.2 Service Interface Specification
```python
# OCR Processing Service API Interface
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

class OCREngine(str, Enum):
    TESSERACT = "tesseract"
    PADDLEOCR = "paddleocr"
    TROCR = "trocr"
    ENSEMBLE = "ensemble"

class OCRRequest(BaseModel):
    document_id: str = Field(..., description="Document identifier")
    pages: Optional[List[int]] = Field(None, description="Specific pages to process")
    language: str = Field("auto", description="Language code or 'auto' for detection")
    engine: OCREngine = Field(OCREngine.ENSEMBLE, description="OCR engine to use")
    options: Optional[Dict[str, any]] = Field(None, description="Engine-specific options")

class OCRResponse(BaseModel):
    document_id: str
    processing_time: float
    total_pages: int
    pages_processed: int
    overall_confidence: float
    text_blocks: List[TextBlock]
    layout_analysis: LayoutAnalysis
    quality_metrics: QualityMetrics

class TextBlock(BaseModel):
    page_number: int
    block_id: str
    text: str
    confidence: float
    bounding_box: BoundingBox
    language: str
    formatting: TextFormatting

class LayoutAnalysis(BaseModel):
    document_type: str
    reading_order: List[str]
    regions: List[DocumentRegion]
    tables: List[TableStructure]
    images: List[ImageRegion]

# Core OCR Processing Classes
class OCREngineManager:
    def __init__(self):
        self.engines = {
            'tesseract': TesseractEngine(),
            'paddleocr': PaddleOCREngine(),
            'trocr': TrOCREngine()
        }
    
    async def process_document(self, request: OCRRequest) -> OCRResponse:
        # Engine selection and processing logic
        pass
    
    async def ensemble_processing(self, document: bytes, options: Dict) -> OCRResponse:
        # Multi-engine ensemble processing
        pass

class LayoutAnalyzer:
    async def analyze_layout(self, image: bytes) -> LayoutAnalysis:
        # Document layout analysis using LayoutLM
        pass
    
    async def detect_tables(self, image: bytes) -> List[TableStructure]:
        # Table detection and structure analysis
        pass
    
    async def extract_reading_order(self, layout: LayoutAnalysis) -> List[str]:
        # Determine optimal reading order
        pass
```

#### 1.2.3 AI/ML Model Integration
```python
# OCR Model Management
class OCRModelManager:
    def __init__(self):
        self.models = {
            'tesseract': self.load_tesseract_models(),
            'paddleocr': self.load_paddleocr_models(),
            'trocr': self.load_trocr_models(),
            'layout_analysis': self.load_layout_models()
        }
    
    def load_tesseract_models(self) -> Dict[str, any]:
        # Load Tesseract language models
        return {
            'eng': tesseract.load_model('eng'),
            'spa': tesseract.load_model('spa'),
            'fra': tesseract.load_model('fra'),
            'deu': tesseract.load_model('deu'),
            'chi_sim': tesseract.load_model('chi_sim'),
            'jpn': tesseract.load_model('jpn'),
            'ara': tesseract.load_model('ara')
        }
    
    def load_trocr_models(self) -> Dict[str, any]:
        # Load TrOCR transformer models
        return {
            'base': transformers.TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed'),
            'large': transformers.TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed'),
            'handwritten': transformers.TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
        }

# Quality Assessment Component
class OCRQualityAssessor:
    def assess_text_quality(self, text: str, confidence_scores: List[float]) -> QualityMetrics:
        # Assess OCR output quality
        return QualityMetrics(
            character_accuracy=self.calculate_character_accuracy(text, confidence_scores),
            word_accuracy=self.calculate_word_accuracy(text, confidence_scores),
            line_accuracy=self.calculate_line_accuracy(text, confidence_scores),
            overall_confidence=statistics.mean(confidence_scores),
            quality_score=self.calculate_quality_score(text, confidence_scores)
        )
    
    def detect_potential_errors(self, text: str, confidence_scores: List[float]) -> List[PotentialError]:
        # Identify likely OCR errors for manual review
        pass
```

### 1.3 Document Classification Service

#### 1.3.1 Component Overview
**Technology Stack**: Python 3.11+, FastAPI 0.104+, Transformers 4.35+, scikit-learn 1.3+
**Primary Responsibilities**:
- Intelligent document type classification using ML models
- Content-based categorization and labeling
- Custom model training and deployment
- Hierarchical classification support
- Classification confidence scoring and validation

#### 1.3.2 Service Interface Specification
```python
# Document Classification Service API
class ClassificationRequest(BaseModel):
    document_id: str = Field(..., description="Document identifier")
    text_content: str = Field(..., description="Extracted text content")
    metadata: Optional[DocumentMetadata] = Field(None, description="Document metadata")
    classification_type: str = Field("standard", description="Classification model type")
    confidence_threshold: float = Field(0.8, description="Minimum confidence threshold")

class ClassificationResponse(BaseModel):
    document_id: str
    predictions: List[ClassificationPrediction]
    processing_time: float
    model_version: str
    confidence_distribution: Dict[str, float]

class ClassificationPrediction(BaseModel):
    category: str
    subcategory: Optional[str]
    confidence: float
    probability_distribution: Dict[str, float]
    explanation: ClassificationExplanation

class ClassificationExplanation(BaseModel):
    key_features: List[str]
    decision_factors: Dict[str, float]
    similar_documents: List[str]
    confidence_factors: List[str]

# Core Classification Components
class DocumentClassifier:
    def __init__(self):
        self.models = {
            'bert_classifier': self.load_bert_model(),
            'roberta_classifier': self.load_roberta_model(),
            'custom_models': self.load_custom_models()
        }
        self.feature_extractor = FeatureExtractor()
        self.ensemble_manager = EnsembleManager()
    
    async def classify_document(self, request: ClassificationRequest) -> ClassificationResponse:
        # Extract features from document content
        features = await self.feature_extractor.extract_features(
            request.text_content, 
            request.metadata
        )
        
        # Run ensemble classification
        predictions = await self.ensemble_manager.predict(features, request.classification_type)
        
        # Generate explanations
        explanations = await self.generate_explanations(features, predictions)
        
        return ClassificationResponse(
            document_id=request.document_id,
            predictions=predictions,
            processing_time=time.time() - start_time,
            model_version=self.get_model_version(),
            confidence_distribution=self.calculate_confidence_distribution(predictions)
        )

class FeatureExtractor:
    def __init__(self):
        self.text_vectorizer = TfidfVectorizer(max_features=10000)
        self.bert_tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.bert_model = AutoModel.from_pretrained('bert-base-uncased')
    
    async def extract_features(self, text: str, metadata: Optional[DocumentMetadata]) -> FeatureVector:
        # Extract comprehensive features for classification
        features = {
            'text_features': self.extract_text_features(text),
            'semantic_features': await self.extract_semantic_features(text),
            'metadata_features': self.extract_metadata_features(metadata),
            'structural_features': self.extract_structural_features(text)
        }
        return FeatureVector(**features)
```

### 1.4 Information Extraction Service

#### 1.4.1 Component Overview
**Technology Stack**: Python 3.11+, FastAPI 0.104+, spaCy 3.7+, Transformers 4.35+
**Primary Responsibilities**:
- Named entity recognition and extraction
- Table and form data extraction
- Custom entity extraction and training
- Data validation and quality assessment
- Structured output generation and formatting

#### 1.4.2 Service Interface Specification
```python
# Information Extraction Service API
class ExtractionRequest(BaseModel):
    document_id: str = Field(..., description="Document identifier")
    text_content: str = Field(..., description="OCR extracted text")
    document_type: str = Field(..., description="Classified document type")
    layout_analysis: LayoutAnalysis = Field(..., description="Document layout information")
    extraction_config: ExtractionConfig = Field(..., description="Extraction configuration")

class ExtractionResponse(BaseModel):
    document_id: str
    extracted_entities: List[ExtractedEntity]
    extracted_tables: List[ExtractedTable]
    extracted_forms: List[ExtractedForm]
    validation_results: ValidationResults
    processing_time: float
    confidence_metrics: ConfidenceMetrics

class ExtractedEntity(BaseModel):
    entity_type: str
    entity_value: str
    confidence: float
    location: BoundingBox
    context: str
    validation_status: str
    normalized_value: Optional[str]

class ExtractedTable(BaseModel):
    table_id: str
    headers: List[str]
    rows: List[List[str]]
    confidence: float
    location: BoundingBox
    table_type: str
    validation_status: str

# Core Extraction Components
class EntityExtractor:
    def __init__(self):
        self.nlp_models = {
            'en': spacy.load('en_core_web_lg'),
            'es': spacy.load('es_core_news_lg'),
            'fr': spacy.load('fr_core_news_lg'),
            'de': spacy.load('de_core_news_lg')
        }
        self.custom_models = self.load_custom_models()
        self.transformers_pipeline = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')
    
    async def extract_entities(self, text: str, document_type: str, language: str = 'en') -> List[ExtractedEntity]:
        # Multi-model entity extraction
        spacy_entities = self.extract_with_spacy(text, language)
        transformer_entities = self.extract_with_transformers(text)
        custom_entities = await self.extract_custom_entities(text, document_type)
        
        # Merge and deduplicate entities
        merged_entities = self.merge_entity_results(
            spacy_entities, 
            transformer_entities, 
            custom_entities
        )
        
        return merged_entities

class TableExtractor:
    def __init__(self):
        self.table_detection_model = self.load_table_detection_model()
        self.table_structure_model = self.load_table_structure_model()
    
    async def extract_tables(self, image: bytes, layout_analysis: LayoutAnalysis) -> List[ExtractedTable]:
        # Detect table regions
        table_regions = await self.detect_table_regions(image, layout_analysis)
        
        extracted_tables = []
        for region in table_regions:
            # Extract table structure and content
            table_structure = await self.extract_table_structure(region)
            table_content = await self.extract_table_content(region, table_structure)
            
            extracted_table = ExtractedTable(
                table_id=self.generate_table_id(),
                headers=table_structure.headers,
                rows=table_content.rows,
                confidence=table_structure.confidence,
                location=region.bounding_box,
                table_type=self.classify_table_type(table_structure),
                validation_status='pending'
            )
            
            extracted_tables.append(extracted_table)
        
        return extracted_tables
```

## 2. API Specifications

### 2.1 RESTful API Design Standards

#### 2.1.1 API Gateway Configuration
```yaml
# Kong API Gateway Configuration
api_gateway:
  version: "3.4"
  services:
    - name: document-ingestion
      url: http://document-ingestion-service:3000
      routes:
        - name: document-upload
          paths: ["/api/v1/documents"]
          methods: ["POST", "GET", "DELETE"]
        - name: batch-upload
          paths: ["/api/v1/documents/batch"]
          methods: ["POST"]
    
    - name: ocr-processing
      url: http://ocr-processing-service:8000
      routes:
        - name: ocr-process
          paths: ["/api/v1/ocr"]
          methods: ["POST"]
    
    - name: classification
      url: http://classification-service:8000
      routes:
        - name: classify
          paths: ["/api/v1/classification"]
          methods: ["POST"]
    
    - name: extraction
      url: http://extraction-service:8000
      routes:
        - name: extract
          paths: ["/api/v1/extraction"]
          methods: ["POST"]

  plugins:
    - name: rate-limiting
      config:
        minute: 100
        hour: 1000
        day: 10000
    
    - name: authentication
      config:
        type: oauth2
        scopes: ["read", "write", "admin"]
    
    - name: cors
      config:
        origins: ["*"]
        methods: ["GET", "POST", "PUT", "DELETE"]
        headers: ["Accept", "Content-Type", "Authorization"]
```

#### 2.1.2 API Response Standards
```typescript
// Standard API Response Format
interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: APIError;
  metadata: ResponseMetadata;
}

interface APIError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
  request_id: string;
}

interface ResponseMetadata {
  request_id: string;
  timestamp: string;
  processing_time: number;
  api_version: string;
  rate_limit: RateLimitInfo;
}

// Error Handling Standards
enum ErrorCodes {
  VALIDATION_ERROR = "VALIDATION_ERROR",
  AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR",
  AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR",
  PROCESSING_ERROR = "PROCESSING_ERROR",
  SYSTEM_ERROR = "SYSTEM_ERROR",
  RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
}
```

## 3. Data Models and Schema Design

### 3.1 Core Data Models

#### 3.1.1 Document Data Model
```sql
-- PostgreSQL Schema for Document Management
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Document metadata
    title VARCHAR(500),
    description TEXT,
    tags JSONB DEFAULT '[]',
    category VARCHAR(100),
    confidentiality_level VARCHAR(20) NOT NULL DEFAULT 'internal',
    retention_period INTEGER,
    custom_fields JSONB DEFAULT '{}',
    
    -- Processing status
    processing_status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    processing_progress INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Storage information
    storage_provider VARCHAR(50) NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    storage_region VARCHAR(50),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT fk_documents_organization FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT fk_documents_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT chk_confidentiality_level CHECK (confidentiality_level IN ('public', 'internal', 'confidential', 'restricted')),
    CONSTRAINT chk_processing_status CHECK (processing_status IN ('uploaded', 'preprocessing', 'processing', 'completed', 'failed'))
);

-- Indexes for performance
CREATE INDEX idx_documents_organization ON documents(organization_id, created_at DESC);
CREATE INDEX idx_documents_user ON documents(user_id, created_at DESC);
CREATE INDEX idx_documents_status ON documents(processing_status, created_at DESC);
CREATE INDEX idx_documents_category ON documents(category, created_at DESC);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_custom_fields ON documents USING GIN(custom_fields);
```

#### 3.1.2 Processing Results Data Model
```sql
-- OCR Results Table
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    processing_engine VARCHAR(50) NOT NULL,
    processing_time DECIMAL(8,3) NOT NULL,
    
    -- OCR metrics
    total_pages INTEGER NOT NULL,
    pages_processed INTEGER NOT NULL,
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
);

-- Classification Results Table
CREATE TABLE classification_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    processing_time DECIMAL(8,3) NOT NULL,
    
    -- Classification results
    primary_category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    confidence DECIMAL(5,4) NOT NULL,
    probability_distribution JSONB NOT NULL,
    
    -- Explanation data
    key_features JSONB DEFAULT '[]',
    decision_factors JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_classification_results_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Extraction Results Table
CREATE TABLE extraction_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    extraction_type VARCHAR(50) NOT NULL, -- 'entities', 'tables', 'forms'
    
    -- Extracted data
    extracted_data JSONB NOT NULL,
    confidence_scores JSONB NOT NULL,
    validation_results JSONB DEFAULT '{}',
    
    -- Processing metadata
    processing_time DECIMAL(8,3) NOT NULL,
    model_versions JSONB NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_extraction_results_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

This HLD provides comprehensive component specifications, API designs, and data models that enable implementation of all functional requirements while meeting performance and reliability targets specified in previous documents.
