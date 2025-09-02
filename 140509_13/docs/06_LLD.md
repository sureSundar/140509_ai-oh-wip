# Low Level Design (LLD)
## E-commerce Customer Service AI - AI-Powered Intelligent Customer Service and Support Automation Platform

*Building upon README, PRD, FRD, NFRD, AD, and HLD foundations for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ README completed with problem overview and technical approach
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 21 detailed functional requirements
- ✅ NFRD completed with 24 non-functional requirements
- ✅ AD completed with system architecture design
- ✅ HLD completed with component specifications and API designs

### TASK
Develop implementation-ready specifications including class structures, database schemas, API implementations, algorithm details, configuration files, and deployment scripts.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] Class designs implement HLD component specifications
- [ ] Database schemas support all data models and relationships
- [ ] API implementations meet functional requirements
- [ ] Algorithms achieve performance targets from NFRD

**Validation Criteria:**
- [ ] Implementation specifications validated with development teams
- [ ] Database designs validated with data architects
- [ ] API specifications validated with integration teams
- [ ] Performance algorithms validated with DevOps teams

### EXIT CRITERIA
- ✅ Complete implementation-ready class structures and interfaces
- ✅ Database schemas with indexes and constraints
- ✅ API implementation details with error handling
- ✅ Configuration files and deployment specifications
- ✅ Foundation established for Pseudocode development

---

## 1. Core Service Implementation

### 1.1 Conversation Service Classes

```python
# conversation_service.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

class ConversationStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

@dataclass
class Message:
    id: str
    conversation_id: str
    sender_type: str
    sender_id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    metadata: Dict[str, Any]

class ConversationService:
    def __init__(self, db_client, nlp_service, cache_client):
        self.db = db_client
        self.nlp = nlp_service
        self.cache = cache_client
    
    async def create_conversation(self, customer_id: str, channel: str) -> str:
        conversation_id = str(uuid.uuid4())
        conversation = {
            'id': conversation_id,
            'customer_id': customer_id,
            'channel': channel,
            'status': ConversationStatus.ACTIVE.value,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        await self.db.conversations.insert_one(conversation)
        await self.cache.set(f"conv:{conversation_id}", conversation, ttl=3600)
        return conversation_id
    
    async def add_message(self, conversation_id: str, message: Message) -> Dict:
        # Process message with NLP
        nlp_result = await self.nlp.analyze_text(message.content)
        
        # Store message
        message_doc = {
            'id': message.id,
            'conversation_id': conversation_id,
            'sender_type': message.sender_type,
            'content': message.content,
            'timestamp': message.timestamp,
            'intent': nlp_result.get('intent'),
            'sentiment': nlp_result.get('sentiment'),
            'entities': nlp_result.get('entities')
        }
        
        await self.db.messages.insert_one(message_doc)
        
        # Update conversation context
        await self._update_conversation_context(conversation_id, nlp_result)
        
        return message_doc
    
    async def get_conversation_context(self, conversation_id: str) -> Dict:
        # Check cache first
        cached = await self.cache.get(f"context:{conversation_id}")
        if cached:
            return cached
        
        # Build context from database
        conversation = await self.db.conversations.find_one({'id': conversation_id})
        messages = await self.db.messages.find(
            {'conversation_id': conversation_id}
        ).sort('timestamp', 1).to_list(50)
        
        context = {
            'conversation_id': conversation_id,
            'customer_id': conversation['customer_id'],
            'channel': conversation['channel'],
            'message_count': len(messages),
            'last_intent': messages[-1]['intent'] if messages else None,
            'sentiment_trend': self._calculate_sentiment_trend(messages),
            'entities': self._extract_context_entities(messages)
        }
        
        await self.cache.set(f"context:{conversation_id}", context, ttl=1800)
        return context
```

### 1.2 Knowledge Service Implementation

```python
# knowledge_service.py
from elasticsearch import AsyncElasticsearch
from sentence_transformers import SentenceTransformer
import numpy as np

class KnowledgeService:
    def __init__(self, es_client: AsyncElasticsearch, vector_model: str):
        self.es = es_client
        self.encoder = SentenceTransformer(vector_model)
        self.index_name = "knowledge_base"
    
    async def search_articles(self, query: str, filters: Dict = None, limit: int = 10) -> List[Dict]:
        # Generate query embedding
        query_vector = self.encoder.encode([query])[0].tolist()
        
        # Elasticsearch query with vector similarity and text search
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'content_vector') + 1.0",
                                    "params": {"query_vector": query_vector}
                                }
                            }
                        },
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^2", "content", "tags"],
                                "type": "best_fields"
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "_source": ["id", "title", "content", "category", "tags", "effectiveness_score"]
        }
        
        if filters:
            search_body["query"]["bool"]["filter"] = []
            for key, value in filters.items():
                search_body["query"]["bool"]["filter"].append({"term": {key: value}})
        
        response = await self.es.search(index=self.index_name, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                'article_id': hit['_source']['id'],
                'title': hit['_source']['title'],
                'content': hit['_source']['content'][:500] + "...",
                'relevance_score': hit['_score'],
                'category': hit['_source']['category'],
                'effectiveness_score': hit['_source']['effectiveness_score']
            })
        
        return results
    
    async def get_recommendations(self, conversation_context: Dict) -> List[Dict]:
        # Extract key information from context
        intent = conversation_context.get('last_intent')
        entities = conversation_context.get('entities', [])
        
        # Build recommendation query
        query_parts = []
        if intent:
            query_parts.append(intent)
        
        for entity in entities:
            if entity.get('label') in ['PRODUCT', 'ORDER', 'ISSUE']:
                query_parts.append(entity.get('text'))
        
        query = " ".join(query_parts)
        
        # Get recommendations with higher relevance threshold
        recommendations = await self.search_articles(query, limit=5)
        
        # Filter by relevance score
        filtered_recommendations = [
            rec for rec in recommendations 
            if rec['relevance_score'] > 0.7
        ]
        
        return filtered_recommendations[:3]
```

## 2. Database Schema Implementation

### 2.1 PostgreSQL Schema

```sql
-- conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    
    INDEX idx_conversations_customer (customer_id),
    INDEX idx_conversations_status (status),
    INDEX idx_conversations_created (created_at)
);

-- messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    sender_type VARCHAR(20) NOT NULL,
    sender_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    intent VARCHAR(100),
    sentiment_score DECIMAL(3,2),
    entities JSONB,
    metadata JSONB,
    
    INDEX idx_messages_conversation (conversation_id),
    INDEX idx_messages_timestamp (timestamp),
    INDEX idx_messages_intent (intent)
);

-- customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_customers_email (email),
    INDEX idx_customers_external_id (external_id)
);

-- agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'ai' or 'human'
    skills TEXT[],
    current_workload INTEGER DEFAULT 0,
    max_capacity INTEGER DEFAULT 10,
    status VARCHAR(20) DEFAULT 'available',
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_agents_type (type),
    INDEX idx_agents_status (status),
    INDEX idx_agents_skills USING GIN (skills)
);
```

### 2.2 MongoDB Schema

```javascript
// knowledge_articles collection
db.knowledge_articles.createIndex({"category": 1, "status": 1})
db.knowledge_articles.createIndex({"tags": 1})
db.knowledge_articles.createIndex({"effectiveness_score": -1})
db.knowledge_articles.createIndex({"updated_at": -1})

// conversation_contexts collection
db.conversation_contexts.createIndex({"conversation_id": 1}, {"unique": true})
db.conversation_contexts.createIndex({"customer_id": 1})
db.conversation_contexts.createIndex({"updated_at": -1})

// Example document structure
{
  "_id": ObjectId("..."),
  "conversation_id": "uuid-string",
  "customer_id": "uuid-string",
  "context_variables": {
    "current_intent": "order_status",
    "entities": [
      {"type": "ORDER_ID", "value": "12345", "confidence": 0.95}
    ],
    "sentiment_history": [0.2, 0.1, -0.3, -0.5],
    "interaction_count": 4
  },
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

## 3. API Implementation Details

### 3.1 FastAPI Application Structure

```python
# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio

app = FastAPI(title="E-commerce Customer Service AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ConversationCreateRequest(BaseModel):
    customer_id: str
    channel: str
    initial_message: Optional[str] = None

class MessageRequest(BaseModel):
    content: str
    sender_type: str
    sender_id: str
    message_type: str = "text"

class ConversationResponse(BaseModel):
    id: str
    customer_id: str
    channel: str
    status: str
    created_at: str

# API Endpoints
@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        conversation_id = await conversation_service.create_conversation(
            request.customer_id, 
            request.channel
        )
        
        conversation = await conversation_service.get_conversation(conversation_id)
        return ConversationResponse(**conversation)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    request: MessageRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_type=request.sender_type,
            sender_id=request.sender_id,
            content=request.content,
            message_type=MessageType(request.message_type),
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        result = await conversation_service.add_message(conversation_id, message)
        
        # Trigger response generation if from customer
        if request.sender_type == "customer":
            asyncio.create_task(
                generate_and_send_response(conversation_id, message)
            )
        
        return {"message_id": result["id"], "status": "processed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 4. Configuration Management

### 4.1 Environment Configuration

```yaml
# config/production.yaml
database:
  postgresql:
    host: ${DB_HOST}
    port: ${DB_PORT:5432}
    database: ${DB_NAME}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    pool_size: 20
    max_overflow: 30
  
  mongodb:
    uri: ${MONGO_URI}
    database: ${MONGO_DB_NAME}
    
  redis:
    host: ${REDIS_HOST}
    port: ${REDIS_PORT:6379}
    password: ${REDIS_PASSWORD}
    db: 0

ai_services:
  nlp:
    model_name: "bert-base-uncased"
    max_sequence_length: 512
    batch_size: 32
    
  response_generation:
    model_name: "gpt-4"
    api_key: ${OPENAI_API_KEY}
    max_tokens: 500
    temperature: 0.7

elasticsearch:
  hosts: 
    - ${ES_HOST}:${ES_PORT:9200}
  username: ${ES_USERNAME}
  password: ${ES_PASSWORD}
  
performance:
  max_concurrent_conversations: 50000
  message_processing_timeout: 30
  response_generation_timeout: 10
  cache_ttl: 3600

security:
  jwt_secret: ${JWT_SECRET}
  encryption_key: ${ENCRYPTION_KEY}
  allowed_origins: ${ALLOWED_ORIGINS}
```

### 4.2 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

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
      - ES_HOST=elasticsearch
    depends_on:
      - postgres
      - redis
      - elasticsearch
    
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: customer_service
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    
  elasticsearch:
    image: elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data

volumes:
  postgres_data:
  es_data:
```

This comprehensive LLD provides implementation-ready specifications that development teams can use to build the e-commerce customer service AI platform with all required functionality, performance characteristics, and security features.
