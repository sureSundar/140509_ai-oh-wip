# Low Level Design (LLD)
## Banking Fraud Detection Real-Time Analytics System

*Building upon PRD, FRD, NFRD, Architecture Diagram, and HLD for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 114 functional requirements (FR-001 to FR-114)
- ✅ NFRD completed with 138 non-functional requirements (NFR-001 to NFR-138)
- ✅ Architecture Diagram completed with technology stack and system architecture
- ✅ HLD completed with detailed component specifications and interfaces
- ✅ Technology stack validated and approved for banking environment

### TASK
Create implementation-ready low-level design specifications including detailed class diagrams, database schemas, API specifications, algorithm implementations, configuration parameters, and deployment scripts that enable direct development of the fraud detection system.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All classes and methods have detailed specifications with parameters and return types
- [ ] Database schemas support all data requirements from HLD components
- [ ] API specifications include request/response formats, error codes, and authentication
- [ ] Algorithm implementations satisfy performance requirements (<100ms processing)
- [ ] Configuration parameters support all operational requirements
- [ ] Code structure follows banking industry security and quality standards

**Validation Criteria:**
- [ ] Implementation specifications reviewed with development team for feasibility
- [ ] Database design validated with DBA team for performance and scalability
- [ ] API specifications validated with integration team and external partners
- [ ] Security implementations reviewed with cybersecurity team for compliance
- [ ] Performance specifications validated with load testing requirements
- [ ] Code quality standards confirmed with architecture review board

### EXIT CRITERIA
- ✅ Complete implementation specifications ready for development team
- ✅ Database schemas, API specs, and class diagrams documented
- ✅ Algorithm implementations with performance optimizations specified
- ✅ Configuration management and deployment procedures defined
- ✅ Foundation established for pseudocode and implementation phase

---

### Reference to Previous Documents
This LLD provides implementation-ready specifications based on **ALL** previous documents:
- **PRD Success Metrics** → Implementation targets for >99% detection accuracy, <100ms processing, 99.99% uptime
- **FRD Functional Requirements (FR-001-114)** → Detailed method implementations for all system functions
- **NFRD Performance Requirements (NFR-001-138)** → Optimized algorithms and data structures for performance targets
- **Architecture Diagram** → Technology stack implementation with specific versions and configurations
- **HLD Component Design** → Detailed class structures, database schemas, and API implementations

## 1. Transaction Ingestion Service Implementation

### 1.1 Class Structure
```java
@RestController
@RequestMapping("/api/v1/transactions")
public class TransactionIngestionController {
    
    @Autowired
    private TransactionValidationService validationService;
    
    @Autowired
    private TransactionEnrichmentService enrichmentService;
    
    @Autowired
    private KafkaTransactionProducer kafkaProducer;
    
    @Autowired
    private RedisTransactionCache redisCache;
    
    @PostMapping
    @ResponseTime(maxMillis = 10)
    public ResponseEntity<TransactionResponse> ingestTransaction(
            @Valid @RequestBody TransactionRequest request) {
        
        // Validate transaction format (ISO 8583)
        ValidationResult validation = validationService.validate(request);
        if (!validation.isValid()) {
            return ResponseEntity.badRequest()
                .body(new TransactionResponse(validation.getErrors()));
        }
        
        // Enrich with customer profile data
        EnrichedTransaction enriched = enrichmentService.enrich(request);
        
        // Cache in Redis for fast access
        redisCache.store(enriched.getTransactionId(), enriched);
        
        // Publish to Kafka topic
        kafkaProducer.send("fraud-detection-transactions", enriched);
        
        return ResponseEntity.ok(new TransactionResponse(
            enriched.getTransactionId(), 
            "ACCEPTED", 
            System.currentTimeMillis()
        ));
    }
}
```

### 1.2 Data Models
```java
@Entity
@Table(name = "transactions", indexes = {
    @Index(name = "idx_customer_id", columnList = "customerId"),
    @Index(name = "idx_timestamp", columnList = "timestamp"),
    @Index(name = "idx_merchant_id", columnList = "merchantId")
})
public class Transaction {
    
    @Id
    @Column(columnDefinition = "UUID")
    private UUID transactionId;
    
    @Column(nullable = false, length = 50)
    private String customerId;
    
    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal amount;
    
    @Column(nullable = false, length = 3)
    private String currency;
    
    @Column(nullable = false, length = 50)
    private String merchantId;
    
    @Column(nullable = false)
    private LocalDateTime timestamp;
    
    @Enumerated(EnumType.STRING)
    private TransactionChannel channel;
    
    @Embedded
    private GeoLocation location;
    
    @Column(length = 256)
    private String deviceFingerprint;
    
    // Constructors, getters, setters
}

@Embeddable
public class GeoLocation {
    @Column(precision = 10, scale = 8)
    private Double latitude;
    
    @Column(precision = 11, scale = 8)
    private Double longitude;
    
    @Column(length = 100)
    private String country;
    
    @Column(length = 100)
    private String city;
}
```

### 1.3 Kafka Configuration
```yaml
# application.yml
spring:
  kafka:
    producer:
      bootstrap-servers: ${KAFKA_BROKERS:localhost:9092}
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
      properties:
        acks: all
        retries: 3
        batch.size: 16384
        linger.ms: 5
        buffer.memory: 33554432
        compression.type: snappy
        max.in.flight.requests.per.connection: 1
        enable.idempotence: true
```

## 2. ML Model Serving Implementation

### 2.1 Feature Store Service
```python
from feast import FeatureStore
from redis import Redis
import asyncio
from typing import Dict, List, Optional

class FeatureStoreService:
    def __init__(self):
        self.feast_store = FeatureStore(repo_path=".")
        self.redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1
        )
    
    async def get_features(self, entity_id: str, feature_names: List[str]) -> Dict:
        """Get real-time features with <5ms latency"""
        try:
            # Try Redis cache first
            cached_features = await self._get_cached_features(entity_id, feature_names)
            if cached_features:
                return cached_features
            
            # Fallback to Feast feature store
            features = self.feast_store.get_online_features(
                features=feature_names,
                entity_rows=[{"customer_id": entity_id}]
            ).to_dict()
            
            # Cache for future requests
            await self._cache_features(entity_id, features)
            
            return features
            
        except Exception as e:
            logger.error(f"Feature retrieval failed for {entity_id}: {e}")
            return self._get_default_features(feature_names)
    
    async def _get_cached_features(self, entity_id: str, feature_names: List[str]) -> Optional[Dict]:
        """Retrieve features from Redis cache"""
        pipeline = self.redis_client.pipeline()
        for feature_name in feature_names:
            pipeline.hget(f"features:{entity_id}", feature_name)
        
        results = pipeline.execute()
        
        if all(result is not None for result in results):
            return {
                feature_names[i]: float(results[i]) if results[i] else 0.0
                for i in range(len(feature_names))
            }
        return None
    
    async def _cache_features(self, entity_id: str, features: Dict):
        """Cache features in Redis with TTL"""
        pipeline = self.redis_client.pipeline()
        for feature_name, value in features.items():
            pipeline.hset(f"features:{entity_id}", feature_name, str(value))
        pipeline.expire(f"features:{entity_id}", 300)  # 5 minute TTL
        pipeline.execute()
```

### 2.2 ML Model Ensemble Implementation
```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier
import tensorflow as tf
from typing import Tuple, Dict, List
import asyncio

class MLModelEnsemble:
    def __init__(self):
        self.models = {
            'random_forest': self._load_random_forest(),
            'isolation_forest': self._load_isolation_forest(),
            'neural_network': self._load_neural_network(),
            'xgboost': self._load_xgboost()
        }
        self.model_weights = {
            'random_forest': 0.3,
            'isolation_forest': 0.2,
            'neural_network': 0.3,
            'xgboost': 0.2
        }
    
    async def predict(self, features: np.ndarray) -> Tuple[float, Dict]:
        """Ensemble prediction with <50ms latency"""
        start_time = time.time()
        
        # Run all models in parallel
        tasks = [
            self._predict_random_forest(features),
            self._predict_isolation_forest(features),
            self._predict_neural_network(features),
            self._predict_xgboost(features)
        ]
        
        predictions = await asyncio.gather(*tasks)
        
        # Calculate weighted ensemble score
        ensemble_score = sum(
            pred * self.model_weights[model_name] 
            for pred, model_name in zip(predictions, self.models.keys())
        )
        
        # Calculate confidence and feature importance
        confidence = self._calculate_confidence(predictions)
        feature_importance = self._calculate_feature_importance(features)
        
        processing_time = (time.time() - start_time) * 1000
        
        return ensemble_score, {
            'individual_predictions': dict(zip(self.models.keys(), predictions)),
            'confidence': confidence,
            'feature_importance': feature_importance,
            'processing_time_ms': processing_time
        }
    
    async def _predict_random_forest(self, features: np.ndarray) -> float:
        """Random Forest prediction with pattern detection"""
        prediction = self.models['random_forest'].predict_proba(features.reshape(1, -1))[0][1]
        return float(prediction)
    
    async def _predict_isolation_forest(self, features: np.ndarray) -> float:
        """Isolation Forest prediction for anomaly detection"""
        anomaly_score = self.models['isolation_forest'].decision_function(features.reshape(1, -1))[0]
        # Convert to probability (higher score = more normal)
        probability = 1 / (1 + np.exp(-anomaly_score))
        return float(1 - probability)  # Return fraud probability
    
    async def _predict_neural_network(self, features: np.ndarray) -> float:
        """Neural Network prediction for complex patterns"""
        prediction = self.models['neural_network'].predict(features.reshape(1, -1))[0][0]
        return float(prediction)
    
    async def _predict_xgboost(self, features: np.ndarray) -> float:
        """XGBoost prediction with feature importance"""
        prediction = self.models['xgboost'].predict_proba(features.reshape(1, -1))[0][1]
        return float(prediction)
```

## 3. Rule Engine Implementation

### 3.1 Regulatory Compliance Engine
```java
@Service
public class RegulatoryComplianceEngine {
    
    @Autowired
    private DroolsRuleEngine droolsEngine;
    
    @Autowired
    private OFACScreeningService ofacService;
    
    @Autowired
    private SARReportingService sarService;
    
    @Cacheable(value = "compliance-rules", key = "#transaction.customerId")
    public ComplianceResult evaluateCompliance(Transaction transaction) {
        
        ComplianceContext context = new ComplianceContext(transaction);
        
        // Execute AML/KYC rules
        RuleExecutionResult amlResult = droolsEngine.execute("AML_RULES", context);
        
        // Execute sanctions screening
        SanctionsResult sanctionsResult = ofacService.screenTransaction(transaction);
        
        // Execute currency transaction reporting
        CTRResult ctrResult = evaluateCTRRequirements(transaction);
        
        // Calculate composite compliance score
        int complianceScore = calculateComplianceScore(amlResult, sanctionsResult, ctrResult);
        
        // Generate SAR if required
        if (complianceScore > 80) {
            sarService.generateSAR(transaction, context);
        }
        
        return new ComplianceResult(
            complianceScore,
            amlResult.getFlags(),
            sanctionsResult.getMatches(),
            ctrResult.isRequired()
        );
    }
    
    private int calculateComplianceScore(RuleExecutionResult aml, 
                                       SanctionsResult sanctions, 
                                       CTRResult ctr) {
        int score = 0;
        
        // AML risk factors (0-40 points)
        score += aml.getRiskFactors().size() * 10;
        
        // Sanctions matches (0-50 points)
        if (sanctions.hasExactMatch()) score += 50;
        else if (sanctions.hasFuzzyMatch()) score += 30;
        
        // CTR requirements (0-10 points)
        if (ctr.isRequired()) score += 10;
        
        return Math.min(score, 100);
    }
}
```

### 3.2 Dynamic Rule Configuration
```yaml
# Drools rule configuration
rules:
  aml:
    - name: "Large Cash Transaction"
      condition: "transaction.amount > 10000 && transaction.paymentMethod == 'CASH'"
      action: "addRiskFactor('LARGE_CASH_TRANSACTION', 30)"
      
    - name: "Rapid Fire Transactions"
      condition: "customerProfile.transactionCount24h > 50"
      action: "addRiskFactor('RAPID_FIRE_TRANSACTIONS', 25)"
      
    - name: "Geographic Anomaly"
      condition: "distance(transaction.location, customerProfile.usualLocation) > 1000"
      action: "addRiskFactor('GEOGRAPHIC_ANOMALY', 20)"
      
  fraud:
    - name: "Card Testing Pattern"
      condition: "transaction.amount < 5 && customerProfile.declinedTransactions1h > 10"
      action: "addRiskFactor('CARD_TESTING', 40)"
      
    - name: "Impossible Travel"
      condition: "timeBetweenLocations(previousTransaction, currentTransaction) < physicalTravelTime"
      action: "addRiskFactor('IMPOSSIBLE_TRAVEL', 50)"
```

## 4. Database Schema Implementation

### 4.1 PostgreSQL Schema
```sql
-- Transactions table with partitioning by date
CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    merchant_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    channel VARCHAR(20) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    country VARCHAR(100),
    city VARCHAR(100),
    device_fingerprint VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE transactions_2024_01 PARTITION OF transactions
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Indexes for performance
CREATE INDEX CONCURRENTLY idx_transactions_customer_id 
    ON transactions (customer_id, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_transactions_merchant_id 
    ON transactions (merchant_id, timestamp DESC);
CREATE INDEX CONCURRENTLY idx_transactions_amount 
    ON transactions (amount) WHERE amount > 1000;

-- Risk scores table
CREATE TABLE risk_scores (
    transaction_id UUID PRIMARY KEY REFERENCES transactions(transaction_id),
    ml_ensemble_score DECIMAL(5,3) NOT NULL,
    rule_engine_score DECIMAL(5,3) NOT NULL,
    composite_score DECIMAL(5,3) NOT NULL,
    risk_band VARCHAR(20) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    explanation JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cases table for fraud investigation
CREATE TABLE fraud_cases (
    case_id UUID PRIMARY KEY,
    transaction_ids UUID[] NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    assigned_analyst VARCHAR(100),
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution TEXT,
    tags TEXT[]
);

-- Audit trail table
CREATE TABLE audit_trail (
    audit_id UUID PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 4.2 Redis Data Structures
```python
# Redis key patterns and data structures
REDIS_PATTERNS = {
    # Feature cache (Hash)
    'features:{customer_id}': {
        'avg_transaction_amount_7d': 'float',
        'transaction_frequency_24h': 'int',
        'unique_merchants_30d': 'int',
        'geographic_diversity_score': 'float',
        'ttl': 300  # 5 minutes
    },
    
    # Transaction cache (Hash)
    'transaction:{transaction_id}': {
        'customer_id': 'string',
        'amount': 'float',
        'timestamp': 'int',
        'risk_score': 'float',
        'ttl': 3600  # 1 hour
    },
    
    # Rate limiting (String with expiry)
    'rate_limit:{customer_id}:{window}': {
        'type': 'counter',
        'ttl': 'window_size'
    },
    
    # Model cache (Hash)
    'model:{model_name}:{version}': {
        'model_data': 'binary',
        'metadata': 'json',
        'ttl': 86400  # 24 hours
    }
}
```

## 5. API Specifications

### 5.1 REST API Endpoints
```yaml
openapi: 3.0.0
info:
  title: Banking Fraud Detection API
  version: 1.0.0
  description: Real-time fraud detection and case management API

paths:
  /api/v1/transactions:
    post:
      summary: Submit transaction for fraud detection
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TransactionRequest'
      responses:
        '200':
          description: Transaction processed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TransactionResponse'
        '400':
          description: Invalid transaction data
        '429':
          description: Rate limit exceeded
        '500':
          description: Internal server error

  /api/v1/risk/score/{transactionId}:
    get:
      summary: Get risk score and explanation
      parameters:
        - name: transactionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Risk score retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RiskScoreResponse'

components:
  schemas:
    TransactionRequest:
      type: object
      required:
        - customerId
        - amount
        - currency
        - merchantId
        - timestamp
        - channel
      properties:
        customerId:
          type: string
          maxLength: 50
        amount:
          type: number
          format: decimal
          minimum: 0.01
        currency:
          type: string
          pattern: '^[A-Z]{3}$'
        merchantId:
          type: string
          maxLength: 50
        timestamp:
          type: string
          format: date-time
        channel:
          type: string
          enum: [CARD, ACH, WIRE, MOBILE]
        location:
          $ref: '#/components/schemas/GeoLocation'
        deviceFingerprint:
          type: string
          maxLength: 256

    TransactionResponse:
      type: object
      properties:
        transactionId:
          type: string
          format: uuid
        status:
          type: string
          enum: [ACCEPTED, REJECTED, PENDING]
        riskScore:
          type: number
          format: decimal
          minimum: 0
          maximum: 1000
        decision:
          type: string
          enum: [APPROVE, DECLINE, REVIEW]
        processingTimeMs:
          type: integer
        explanation:
          type: string
```

## 6. Performance Optimization Implementation

### 6.1 Caching Strategy
```java
@Configuration
@EnableCaching
public class CacheConfiguration {
    
    @Bean
    public CacheManager cacheManager() {
        RedisCacheManager.Builder builder = RedisCacheManager
            .RedisCacheManagerBuilder
            .fromConnectionFactory(redisConnectionFactory())
            .cacheDefaults(cacheConfiguration());
        
        return builder.build();
    }
    
    private RedisCacheConfiguration cacheConfiguration() {
        return RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(5))
            .serializeKeysWith(RedisSerializationContext.SerializationPair
                .fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(RedisSerializationContext.SerializationPair
                .fromSerializer(new GenericJackson2JsonRedisSerializer()));
    }
    
    // Cache configurations for different data types
    @Bean
    public RedisCacheConfiguration featureCacheConfig() {
        return RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(5))
            .prefixCacheNameWith("features:");
    }
    
    @Bean
    public RedisCacheConfiguration modelCacheConfig() {
        return RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofHours(24))
            .prefixCacheNameWith("models:");
    }
}
```

### 6.2 Connection Pool Configuration
```yaml
# Database connection pool
spring:
  datasource:
    hikari:
      maximum-pool-size: 50
      minimum-idle: 10
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
      leak-detection-threshold: 60000
      
  # Redis connection pool
  redis:
    lettuce:
      pool:
        max-active: 100
        max-idle: 50
        min-idle: 10
        max-wait: 30000ms
      timeout: 5000ms
```

This LLD provides comprehensive implementation-ready specifications that development teams can use to build the banking fraud detection system while maintaining full traceability to all previous requirements documents.
