# Low Level Design (LLD)
## Meeting Assistant AI - AI-Powered Meeting Management and Intelligence Platform

*Building upon README, PRD, FRD, NFRD, AD, and HLD foundations for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ README completed with problem overview and technical approach
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 15 functional requirements across 5 modules
- ✅ NFRD completed with performance, scalability, and security requirements
- ✅ AD completed with microservices architecture and deployment strategy
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

### Reference to Previous Documents
This LLD builds upon **README**, **PRD**, **FRD**, **NFRD**, **AD**, and **HLD** foundations:
- **HLD Component Specifications** → Detailed class implementations with methods and properties
- **HLD API Designs** → Complete API implementations with validation and error handling
- **HLD Data Models** → Production-ready database schemas with indexing and partitioning
- **AD Architecture Patterns** → Implementation following microservices and security patterns

## 1. Core Service Implementation

### 1.1 Meeting Orchestrator Service Implementation

**Class Structure:**
```typescript
// src/services/meeting-orchestrator/models/Meeting.ts
export class Meeting {
  id: string;
  organizationId: string;
  title: string;
  status: MeetingStatus;
  startTime: Date;
  endTime?: Date;
  participants: Participant[];
  metadata: MeetingMetadata;
  createdAt: Date;
  updatedAt: Date;

  constructor(data: CreateMeetingRequest) {
    this.id = uuidv4();
    this.organizationId = data.organizationId;
    this.title = data.title;
    this.status = MeetingStatus.SCHEDULED;
    this.startTime = data.startTime;
    this.participants = data.participants;
    this.metadata = data.metadata || {};
    this.createdAt = new Date();
    this.updatedAt = new Date();
  }

  public startProcessing(): ProcessingJob {
    this.status = MeetingStatus.PROCESSING;
    this.updatedAt = new Date();
    return new ProcessingJob(this.id);
  }

  public updateStatus(status: MeetingStatus): void {
    this.status = status;
    this.updatedAt = new Date();
  }
}

// src/services/meeting-orchestrator/controllers/MeetingController.ts
@Controller('/api/v1/meetings')
@UseGuards(JwtAuthGuard)
export class MeetingController {
  constructor(
    private readonly meetingService: MeetingService,
    private readonly eventBus: EventBus,
    private readonly logger: Logger
  ) {}

  @Post()
  @UsePipes(ValidationPipe)
  async createMeeting(
    @Body() createMeetingDto: CreateMeetingDto,
    @Request() req: AuthenticatedRequest
  ): Promise<MeetingResponse> {
    try {
      this.logger.log(`Creating meeting: ${createMeetingDto.title}`);
      
      // Validate organization access
      await this.validateOrganizationAccess(req.user.id, createMeetingDto.organizationId);
      
      // Create meeting
      const meeting = await this.meetingService.createMeeting(createMeetingDto);
      
      // Publish event
      await this.eventBus.publish(new MeetingCreatedEvent(meeting));
      
      return new MeetingResponse(meeting);
    } catch (error) {
      this.logger.error(`Failed to create meeting: ${error.message}`);
      throw new BadRequestException('Failed to create meeting');
    }
  }

  @Get(':id')
  async getMeeting(
    @Param('id') id: string,
    @Request() req: AuthenticatedRequest
  ): Promise<MeetingResponse> {
    try {
      const meeting = await this.meetingService.findById(id);
      
      if (!meeting) {
        throw new NotFoundException('Meeting not found');
      }
      
      // Check access permissions
      await this.validateMeetingAccess(req.user.id, meeting);
      
      return new MeetingResponse(meeting);
    } catch (error) {
      this.logger.error(`Failed to get meeting ${id}: ${error.message}`);
      throw error;
    }
  }

  @Put(':id/status')
  async updateMeetingStatus(
    @Param('id') id: string,
    @Body() updateStatusDto: UpdateMeetingStatusDto,
    @Request() req: AuthenticatedRequest
  ): Promise<MeetingResponse> {
    try {
      const meeting = await this.meetingService.updateStatus(id, updateStatusDto.status);
      
      // Publish status change event
      await this.eventBus.publish(new MeetingStatusChangedEvent(meeting));
      
      return new MeetingResponse(meeting);
    } catch (error) {
      this.logger.error(`Failed to update meeting status: ${error.message}`);
      throw new BadRequestException('Failed to update meeting status');
    }
  }

  private async validateOrganizationAccess(userId: string, organizationId: string): Promise<void> {
    const hasAccess = await this.meetingService.checkOrganizationAccess(userId, organizationId);
    if (!hasAccess) {
      throw new ForbiddenException('Insufficient permissions for organization');
    }
  }
}
```

**Database Schema Implementation:**
```sql
-- Database: meeting_orchestrator
-- Schema: public

-- Meetings table with partitioning by organization
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    status meeting_status_enum DEFAULT 'scheduled',
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    participants JSONB NOT NULL DEFAULT '[]',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY HASH (organization_id);

-- Create partitions for better performance
CREATE TABLE meetings_p0 PARTITION OF meetings FOR VALUES WITH (modulus 4, remainder 0);
CREATE TABLE meetings_p1 PARTITION OF meetings FOR VALUES WITH (modulus 4, remainder 1);
CREATE TABLE meetings_p2 PARTITION OF meetings FOR VALUES WITH (modulus 4, remainder 2);
CREATE TABLE meetings_p3 PARTITION OF meetings FOR VALUES WITH (modulus 4, remainder 3);

-- Indexes for optimal query performance
CREATE INDEX idx_meetings_org_status ON meetings (organization_id, status);
CREATE INDEX idx_meetings_start_time ON meetings (start_time);
CREATE INDEX idx_meetings_participants_gin ON meetings USING GIN (participants);

-- Meeting status enum
CREATE TYPE meeting_status_enum AS ENUM (
    'scheduled',
    'in_progress',
    'processing',
    'completed',
    'cancelled',
    'failed'
);

-- Processing jobs table
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status job_status_enum DEFAULT 'queued',
    priority INTEGER DEFAULT 5,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TYPE job_status_enum AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled');
CREATE INDEX idx_processing_jobs_status_priority ON processing_jobs (status, priority DESC);
```

### 1.2 Speech Recognition Service Implementation

**Class Structure:**
```python
# src/services/speech_recognition/models/transcription.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

@dataclass
class Speaker:
    id: str
    name: Optional[str] = None
    voice_profile: Optional[Dict[str, Any]] = None
    confidence: float = 0.0

@dataclass
class TranscriptionSegment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    speaker_id: str = ""
    text: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 0.0
    language: str = "en"
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TranscriptionSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str = ""
    status: str = "active"
    segments: List[TranscriptionSegment] = field(default_factory=list)
    speakers: List[Speaker] = field(default_factory=list)
    language: str = "auto"
    created_at: datetime = field(default_factory=datetime.utcnow)

# src/services/speech_recognition/services/speech_service.py
import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from fastapi import HTTPException
import torch
import whisper
from transformers import pipeline

class SpeechRecognitionService:
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.whisper_model = whisper.load_model("large-v3")
        self.speaker_pipeline = pipeline("automatic-speech-recognition", 
                                        model="pyannote/speaker-diarization")
        self.active_sessions: Dict[str, TranscriptionSession] = {}
        
    async def start_transcription(self, 
                                meeting_id: str, 
                                audio_stream: AsyncGenerator[bytes, None],
                                language: str = "auto") -> TranscriptionSession:
        """Start real-time transcription session"""
        try:
            session = TranscriptionSession(
                meeting_id=meeting_id,
                language=language,
                status="active"
            )
            
            self.active_sessions[session.id] = session
            
            # Start background processing task
            asyncio.create_task(self._process_audio_stream(session, audio_stream))
            
            self.logger.info(f"Started transcription session {session.id} for meeting {meeting_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to start transcription: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to start transcription")

    async def _process_audio_stream(self, 
                                  session: TranscriptionSession, 
                                  audio_stream: AsyncGenerator[bytes, None]) -> None:
        """Process audio stream in real-time"""
        buffer = bytearray()
        chunk_duration = 5.0  # Process 5-second chunks
        
        try:
            async for audio_chunk in audio_stream:
                buffer.extend(audio_chunk)
                
                # Process when buffer reaches chunk duration
                if len(buffer) >= self._calculate_buffer_size(chunk_duration):
                    audio_data = bytes(buffer[:self._calculate_buffer_size(chunk_duration)])
                    buffer = buffer[self._calculate_buffer_size(chunk_duration):]
                    
                    # Process chunk asynchronously
                    asyncio.create_task(self._process_audio_chunk(session, audio_data))
                    
        except Exception as e:
            self.logger.error(f"Error processing audio stream: {str(e)}")
            session.status = "error"

    async def _process_audio_chunk(self, 
                                 session: TranscriptionSession, 
                                 audio_data: bytes) -> None:
        """Process individual audio chunk"""
        try:
            # Convert audio to numpy array
            audio_array = self._bytes_to_audio_array(audio_data)
            
            # Run Whisper transcription
            result = await self._run_whisper_transcription(audio_array, session.language)
            
            # Perform speaker diarization
            speakers = await self._identify_speakers(audio_array, result)
            
            # Create transcription segments
            segments = self._create_segments(result, speakers, session)
            
            # Add segments to session
            session.segments.extend(segments)
            
            # Publish real-time updates
            await self._publish_transcription_update(session, segments)
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {str(e)}")

    async def _run_whisper_transcription(self, 
                                       audio_array: np.ndarray, 
                                       language: str) -> Dict[str, Any]:
        """Run Whisper model for transcription"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.whisper_model.transcribe, 
                audio_array,
                {"language": language if language != "auto" else None}
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Whisper transcription failed: {str(e)}")
            raise

    def _calculate_buffer_size(self, duration: float) -> int:
        """Calculate buffer size for given duration"""
        sample_rate = self.config.sample_rate
        bytes_per_sample = self.config.bytes_per_sample
        return int(duration * sample_rate * bytes_per_sample)

# src/services/speech_recognition/api/endpoints.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.security import HTTPBearer
import json

router = APIRouter()
security = HTTPBearer()

@router.websocket("/ws/transcription/{meeting_id}")
async def websocket_transcription(
    websocket: WebSocket,
    meeting_id: str,
    speech_service: SpeechRecognitionService = Depends()
):
    """WebSocket endpoint for real-time transcription"""
    await websocket.accept()
    
    try:
        # Start transcription session
        session = await speech_service.start_transcription(
            meeting_id=meeting_id,
            audio_stream=_audio_stream_from_websocket(websocket)
        )
        
        # Send session info
        await websocket.send_text(json.dumps({
            "type": "session_started",
            "session_id": session.id,
            "meeting_id": meeting_id
        }))
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message["type"] == "audio_chunk":
                    # Audio data is handled by the stream processor
                    pass
                elif message["type"] == "stop_transcription":
                    await speech_service.stop_transcription(session.id)
                    break
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
    finally:
        await websocket.close()

async def _audio_stream_from_websocket(websocket: WebSocket):
    """Convert WebSocket messages to audio stream"""
    try:
        while True:
            data = await websocket.receive_bytes()
            yield data
    except WebSocketDisconnect:
        return
```

### 1.3 Database Schema Implementation

**PostgreSQL Schema with Optimization:**
```sql
-- Speech Recognition Service Database Schema

-- Transcription sessions table
CREATE TABLE transcription_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    language VARCHAR(10) DEFAULT 'auto',
    total_duration DECIMAL(10,3) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transcription segments with time-based partitioning
CREATE TABLE transcription_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES transcription_sessions(id) ON DELETE CASCADE,
    speaker_id VARCHAR(100),
    text TEXT NOT NULL,
    start_time DECIMAL(10,3) NOT NULL,
    end_time DECIMAL(10,3) NOT NULL,
    confidence DECIMAL(3,2),
    language VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for transcription segments
CREATE TABLE transcription_segments_2024_01 PARTITION OF transcription_segments
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE transcription_segments_2024_02 PARTITION OF transcription_segments
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- Continue for other months...

-- Speakers table
CREATE TABLE speakers (
    id VARCHAR(100) PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES transcription_sessions(id) ON DELETE CASCADE,
    name VARCHAR(255),
    voice_profile JSONB,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX idx_transcription_sessions_meeting ON transcription_sessions (meeting_id);
CREATE INDEX idx_transcription_segments_session_time ON transcription_segments (session_id, start_time);
CREATE INDEX idx_transcription_segments_text_gin ON transcription_segments USING GIN (to_tsvector('english', text));
CREATE INDEX idx_speakers_session ON speakers (session_id);

-- Full-text search configuration
CREATE INDEX idx_transcription_segments_fts ON transcription_segments 
    USING GIN (to_tsvector('english', text));
```

### 1.4 Configuration Files

**Kubernetes Deployment Configuration:**
```yaml
# k8s/speech-recognition-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: speech-recognition-service
  namespace: meeting-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: speech-recognition-service
  template:
    metadata:
      labels:
        app: speech-recognition-service
    spec:
      containers:
      - name: speech-recognition
        image: meeting-assistant/speech-recognition:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: speech-recognition-db-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secrets
              key: redis-url
        - name: WHISPER_MODEL_PATH
          value: "/models/whisper-large-v3"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
            nvidia.com/gpu: 1
          limits:
            memory: "4Gi"
            cpu: "2000m"
            nvidia.com/gpu: 1
        volumeMounts:
        - name: model-storage
          mountPath: /models
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
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: model-storage-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: speech-recognition-service
  namespace: meeting-assistant
spec:
  selector:
    app: speech-recognition-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

**Environment Configuration:**
```yaml
# config/production.yaml
database:
  host: ${DATABASE_HOST}
  port: ${DATABASE_PORT:5432}
  name: ${DATABASE_NAME}
  username: ${DATABASE_USERNAME}
  password: ${DATABASE_PASSWORD}
  ssl: true
  pool_size: 20
  max_overflow: 30

redis:
  url: ${REDIS_URL}
  max_connections: 50
  retry_on_timeout: true

speech_recognition:
  whisper_model: "large-v3"
  sample_rate: 16000
  chunk_duration: 5.0
  max_concurrent_sessions: 1000
  gpu_enabled: true

logging:
  level: INFO
  format: json
  handlers:
    - console
    - file
  file_path: /var/log/speech-recognition.log

monitoring:
  prometheus:
    enabled: true
    port: 9090
  health_check:
    enabled: true
    endpoint: /health
```

This comprehensive LLD provides implementation-ready specifications with detailed class structures, database schemas, API implementations, and configuration files that development teams can use to build the Meeting Assistant AI platform directly.
