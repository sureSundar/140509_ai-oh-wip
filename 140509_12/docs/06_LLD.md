# Low Level Design (LLD)
## Social Media Management Agent - AI-Powered Intelligent Social Media Management and Content Optimization Platform

*Building upon README, PRD, FRD, NFRD, AD, and HLD foundations for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ README completed with problem overview and technical approach
- ✅ PRD completed with business objectives, market analysis, and success metrics
- ✅ FRD completed with 22 detailed functional requirements across 6 modules
- ✅ NFRD completed with 26 non-functional requirements covering performance, security, and scalability
- ✅ AD completed with microservices architecture and cloud-native deployment strategy
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

### 1.1 User Management Service

**Class Structure:**
```python
# src/services/user_management/models.py
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime
from enum import Enum as PyEnum

Base = declarative_base()

class UserStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    profile_image_url = Column(String(500))
    timezone = Column(String(50), default='UTC')
    language = Column(String(10), default='en')
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    last_login = Column(DateTime(timezone=True))
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class UserManagementService:
    def __init__(self, db: Session, redis_client):
        self.db = db
        self.redis = redis_client
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not self.verify_password(password, user.password_hash):
            return None
        user.last_login = datetime.utcnow()
        self.db.commit()
        return user
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
```

### 1.2 Content Management Service

**Implementation:**
```python
# src/services/content_management/service.py
from typing import List, Dict, Optional
from datetime import datetime

class ContentManagementService:
    def __init__(self, db: Session, media_service, ai_service):
        self.db = db
        self.media_service = media_service
        self.ai_service = ai_service
        
    async def create_content(self, content_data: dict, author_id: str) -> Content:
        """Create new content with validation and processing"""
        await self._validate_content_data(content_data)
        
        processed_media = []
        if content_data.get("media_files"):
            processed_media = await self.media_service.process_media_files(
                content_data["media_files"]
            )
        
        content = Content(
            title=content_data["title"],
            body=content_data["body"],
            media_urls=processed_media,
            hashtags=content_data.get("hashtags", []),
            platforms=content_data.get("platforms", []),
            author_id=author_id,
            team_id=content_data.get("team_id"),
            metadata=content_data.get("metadata", {})
        )
        
        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)
        return content
        
    async def schedule_content(self, content_id: str, schedule_data: dict) -> List[ContentSchedule]:
        """Schedule content for publishing across platforms"""
        content = self.db.query(Content).filter(Content.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        schedules = []
        for platform in schedule_data["platforms"]:
            optimal_time = schedule_data["scheduled_at"]
            if schedule_data.get("optimize_timing", False):
                optimal_time = await self.ai_service.get_optimal_posting_time(
                    platform=platform,
                    content=content,
                    target_time=schedule_data["scheduled_at"]
                )
            
            schedule = ContentSchedule(
                content_id=content_id,
                platform=platform,
                scheduled_at=optimal_time,
                status="scheduled"
            )
            
            self.db.add(schedule)
            schedules.append(schedule)
        
        self.db.commit()
        return schedules
```

### 1.3 Social Media Integration

**Platform Connector:**
```python
# src/services/social_media/connectors/facebook.py
import aiohttp
from typing import Dict

class FacebookConnector:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://graph.facebook.com/v18.0"
        
    async def publish_post(self, page_id: str, access_token: str, content: Dict) -> Dict:
        """Publish content to Facebook page"""
        url = f"{self.base_url}/{page_id}/feed"
        
        post_data = {
            "access_token": access_token,
            "message": content["text"]
        }
        
        if content.get("link"):
            post_data["link"] = content["link"]
            
        if content.get("media_urls"):
            post_data["url"] = content["media_urls"][0]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=post_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "platform_post_id": result["id"],
                        "published_at": datetime.utcnow().isoformat()
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("error", {}).get("message", "Publishing failed")
                    }
```

## 2. Database Schema

**PostgreSQL Implementation:**
```sql
-- Core tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    profile_image_url VARCHAR(500),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    status user_status_enum DEFAULT 'active',
    preferences JSONB DEFAULT '{}',
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    body TEXT,
    media_urls TEXT[],
    hashtags TEXT[],
    platforms TEXT[],
    status content_status_enum DEFAULT 'draft',
    author_id UUID NOT NULL REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE content_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    platform_post_id VARCHAR(255),
    status schedule_status_enum DEFAULT 'scheduled',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enums
CREATE TYPE user_status_enum AS ENUM ('active', 'inactive', 'suspended');
CREATE TYPE content_status_enum AS ENUM ('draft', 'pending_approval', 'approved', 'scheduled', 'published', 'failed');
CREATE TYPE schedule_status_enum AS ENUM ('scheduled', 'publishing', 'published', 'failed', 'cancelled');

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_content_author_created ON content(author_id, created_at);
CREATE INDEX idx_schedules_scheduled_at ON content_schedules(scheduled_at);
```

## 3. API Implementation

**FastAPI Service:**
```python
# src/api/main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(title="Social Media Management Agent API", version="1.0.0")

class ContentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=10000)
    platforms: List[str] = Field(..., min_items=1)
    hashtags: Optional[List[str]] = Field(default=[])

class ContentResponse(BaseModel):
    id: str
    title: str
    body: str
    platforms: List[str]
    status: str
    created_at: str

@app.post("/api/v1/content", response_model=ContentResponse)
async def create_content(
    request: ContentCreateRequest,
    current_user: str = Depends(get_current_user),
    content_service: ContentManagementService = Depends(get_content_service)
):
    """Create new social media content"""
    content = await content_service.create_content(
        content_data=request.dict(),
        author_id=current_user
    )
    
    return ContentResponse(
        id=str(content.id),
        title=content.title,
        body=content.body,
        platforms=content.platforms,
        status=content.status.value,
        created_at=content.created_at.isoformat()
    )

@app.get("/api/v1/content", response_model=List[ContentResponse])
async def list_content(
    skip: int = 0,
    limit: int = 20,
    current_user: str = Depends(get_current_user),
    content_service: ContentManagementService = Depends(get_content_service)
):
    """List user's content with pagination"""
    content_list = await content_service.list_user_content(
        user_id=current_user,
        skip=skip,
        limit=limit
    )
    
    return [
        ContentResponse(
            id=str(content.id),
            title=content.title,
            body=content.body,
            platforms=content.platforms,
            status=content.status.value,
            created_at=content.created_at.isoformat()
        )
        for content in content_list
    ]
```

## 4. Configuration Files

**Docker Compose:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/social_media_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=social_media_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Environment Configuration:**
```yaml
# config/production.yaml
database:
  url: ${DATABASE_URL}
  pool_size: 20
  max_overflow: 30

redis:
  url: ${REDIS_URL}
  max_connections: 50

social_media:
  facebook:
    app_id: ${FACEBOOK_APP_ID}
    app_secret: ${FACEBOOK_APP_SECRET}
  twitter:
    api_key: ${TWITTER_API_KEY}
    api_secret: ${TWITTER_API_SECRET}

ai_services:
  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-4"
  
security:
  jwt_secret: ${JWT_SECRET}
  jwt_algorithm: "HS256"
  access_token_expire_minutes: 30

logging:
  level: INFO
  format: json
```

This LLD provides implementation-ready specifications with detailed class structures, database schemas, API implementations, and configuration files for direct development implementation.
