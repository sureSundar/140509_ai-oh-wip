# High Level Design (HLD)
## Sales Performance Analytics and Optimization Platform

*Building upon PRD, FRD, NFRD, and AD for detailed system design*

## ETVX Framework

### ENTRY CRITERIA
- ✅ PRD completed with business objectives, success metrics, and market analysis
- ✅ FRD completed with 40 functional requirements across 8 system modules
- ✅ NFRD completed with 30 non-functional requirements for performance, security, compliance
- ✅ AD completed with microservices architecture, technology stack, and integration patterns
- ✅ System architecture defined with presentation, API gateway, microservices, AI/ML, data, and integration layers
- ✅ Security architecture established with zero-trust principles and compliance controls

### TASK
Design detailed high-level system components, interfaces, data models, processing workflows, and operational procedures that implement the architecture from AD while satisfying all functional requirements from FRD and non-functional requirements from NFRD, providing implementation-ready specifications for development teams.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All FRD functional requirements mapped to specific HLD components
- [ ] NFRD performance requirements addressed in component design (<2s response, 50K+ activities/day)
- [ ] AD architecture patterns implemented in detailed component specifications
- [ ] Data models support all sales analytics, forecasting, and lead scoring workflows
- [ ] API specifications enable seamless integration with CRM, marketing automation, and sales enablement systems
- [ ] Security and compliance controls integrated into all component designs

**Validation Criteria:**
- [ ] Component designs reviewed with development teams and technical architects
- [ ] Data models validated with database architects and data engineering teams
- [ ] API specifications validated with integration partners and external system vendors
- [ ] Security controls validated with cybersecurity experts and compliance officers
- [ ] Performance characteristics validated through capacity planning and load modeling
- [ ] Operational procedures validated with DevOps and infrastructure teams

### EXIT CRITERIA
- ✅ Detailed component specifications for all microservices and system modules
- ✅ Comprehensive data models and database schemas defined
- ✅ API specifications and interface contracts documented
- ✅ Processing workflows and business logic detailed
- ✅ Security and compliance controls integrated into design
- ✅ Foundation prepared for low-level design and implementation specifications

---

### Reference to Previous Documents
This HLD builds upon **PRD**, **FRD**, **NFRD**, and **AD** foundations:
- **PRD Success Metrics** → Component designs supporting 25% forecast accuracy, 30% conversion improvement, 20% productivity gains
- **FRD Functional Requirements** → Detailed component specifications for all 40 functional requirements
- **NFRD Performance Requirements** → Component designs meeting <2s response time, 99.9% uptime, 50K+ activities/day
- **NFRD Security Requirements** → Security controls integrated into all component designs
- **AD System Architecture** → Microservices implementation with detailed component interfaces
- **AD Technology Stack** → Component implementations using specified technologies

## 1. System Component Overview

### 1.1 Component Hierarchy and Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          COMPONENT DEPENDENCY MAP                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Frontend Components                    Backend Services                        │
│  ┌─────────────────┐                   ┌─────────────────┐                     │
│  │ Web Portal      │◄──────────────────┤ API Gateway     │                     │
│  │ Mobile Apps     │                   │ (Kong)          │                     │
│  │ Executive Dash  │                   └─────────────────┘                     │
│  │ Admin Console   │                            │                              │
│  └─────────────────┘                            ▼                              │
│                                        ┌─────────────────┐                     │
│                                        │ Core Services   │                     │
│                                        ├─────────────────┤                     │
│                                        │ • Performance   │                     │
│                                        │ • Forecasting   │                     │
│                                        │ • Lead Scoring  │                     │
│                                        │ • Territory Opt │                     │
│                                        │ • Activity Intel│                     │
│                                        │ • Customer Journey│                   │
│                                        └─────────────────┘                     │
│                                                 │                              │
│                                                 ▼                              │
│                                        ┌─────────────────┐                     │
│                                        │ Support Services│                     │
│                                        ├─────────────────┤                     │
│                                        │ • User Mgmt     │                     │
│                                        │ • Notification  │                     │
│                                        │ • Integration   │                     │
│                                        │ • Reporting     │                     │
│                                        │ • Workflow      │                     │
│                                        └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Service Communication Patterns
- **Synchronous**: REST APIs for real-time user interactions and queries
- **Asynchronous**: Event-driven messaging for data processing and notifications
- **Streaming**: Real-time data streams for analytics and monitoring
- **Batch**: Scheduled batch processing for reports and ML model training

## 2. Core Service Detailed Design

### 2.1 Sales Performance Analytics Service

#### 2.1.1 Component Architecture
```typescript
interface SalesPerformanceService {
  dashboardEngine: RealTimeDashboardEngine;
  benchmarkingEngine: PerformanceBenchmarkingEngine;
  activityAnalytics: ActivityAnalyticsEngine;
  pipelineHealth: PipelineHealthAssessment;
  cycleAnalysis: SalesCycleAnalysisEngine;
}
```

#### 2.1.2 Real-Time Dashboard Engine
**Purpose**: Generate real-time executive and operational dashboards with key sales metrics
**Technology**: React.js, D3.js, WebSocket, Redis
**Performance**: <2 second dashboard loading with real-time updates

```typescript
class RealTimeDashboardEngine {
  private websocketManager: WebSocketManager;
  private metricsCache: RedisCache;
  private queryEngine: AnalyticsQueryEngine;

  async generateDashboard(userId: string, dashboardConfig: DashboardConfig): Promise<Dashboard> {
    // Load user-specific dashboard configuration
    const config = await this.loadDashboardConfig(userId, dashboardConfig);
    
    // Fetch real-time metrics from cache
    const cachedMetrics = await this.metricsCache.getMetrics(config.metricKeys);
    
    // Fetch missing metrics from database
    const missingMetrics = await this.queryEngine.fetchMissingMetrics(
      config.metricKeys.filter(key => !cachedMetrics[key])
    );
    
    // Combine cached and fresh metrics
    const allMetrics = { ...cachedMetrics, ...missingMetrics };
    
    // Generate dashboard widgets
    const widgets = await this.generateWidgets(config.widgets, allMetrics);
    
    // Set up real-time subscriptions
    await this.setupRealtimeSubscriptions(userId, config.metricKeys);
    
    return {
      dashboardId: config.dashboardId,
      widgets,
      lastUpdated: new Date(),
      refreshInterval: config.refreshInterval
    };
  }

  async setupRealtimeSubscriptions(userId: string, metricKeys: string[]): Promise<void> {
    // Subscribe to real-time metric updates
    for (const metricKey of metricKeys) {
      await this.websocketManager.subscribe(userId, `metrics:${metricKey}`);
    }
  }

  private async generateWidgets(widgetConfigs: WidgetConfig[], metrics: MetricsData): Promise<Widget[]> {
    const widgets: Widget[] = [];
    
    for (const config of widgetConfigs) {
      const widget = await this.createWidget(config, metrics);
      widgets.push(widget);
    }
    
    return widgets;
  }
}
```

#### 2.1.3 Performance Benchmarking Engine
**Purpose**: Enable performance comparison and ranking across individuals and teams
**Technology**: PostgreSQL, ClickHouse, statistical algorithms
**Performance**: <3 second response for complex benchmarking queries

```typescript
class PerformanceBenchmarkingEngine {
  private analyticsDB: ClickHouseClient;
  private statisticsEngine: StatisticsEngine;
  
  async generateBenchmarkReport(
    targetEntity: BenchmarkTarget,
    benchmarkCriteria: BenchmarkCriteria
  ): Promise<BenchmarkReport> {
    // Fetch performance data for target entity
    const targetData = await this.fetchPerformanceData(targetEntity, benchmarkCriteria.timeRange);
    
    // Fetch peer group data for comparison
    const peerData = await this.fetchPeerGroupData(targetEntity, benchmarkCriteria);
    
    // Calculate benchmark metrics
    const benchmarkMetrics = await this.calculateBenchmarkMetrics(targetData, peerData);
    
    // Generate performance ranking
    const ranking = await this.calculateRanking(targetEntity, peerData, benchmarkCriteria.metrics);
    
    // Identify improvement opportunities
    const improvements = await this.identifyImprovementOpportunities(
      targetData, peerData, benchmarkMetrics
    );
    
    return {
      target: targetEntity,
      metrics: benchmarkMetrics,
      ranking,
      improvements,
      peerComparison: this.generatePeerComparison(targetData, peerData),
      generatedAt: new Date()
    };
  }

  private async calculateBenchmarkMetrics(
    targetData: PerformanceData,
    peerData: PerformanceData[]
  ): Promise<BenchmarkMetrics> {
    const peerMetrics = peerData.map(data => this.extractMetrics(data));
    
    return {
      targetMetrics: this.extractMetrics(targetData),
      peerAverage: this.statisticsEngine.calculateMean(peerMetrics),
      peerMedian: this.statisticsEngine.calculateMedian(peerMetrics),
      percentileRank: this.statisticsEngine.calculatePercentileRank(
        this.extractMetrics(targetData), peerMetrics
      ),
      standardDeviation: this.statisticsEngine.calculateStandardDeviation(peerMetrics)
    };
  }
}
```

### 2.2 Predictive Forecasting Service

#### 2.2.1 Component Architecture
```typescript
interface PredictiveForecastingService {
  revenueForecastEngine: RevenueForecastingEngine;
  dealProbabilityScorer: DealProbabilityScorer;
  scenarioModeler: ScenarioModelingEngine;
  pipelineForecaster: PipelineForecastingEngine;
  accuracyTracker: ForecastAccuracyTracker;
}
```

#### 2.2.2 Revenue Forecasting Engine
**Purpose**: Generate accurate revenue forecasts using machine learning algorithms
**Technology**: XGBoost, TensorFlow, MLflow, Python
**Performance**: 25% improvement in forecast accuracy, <30 second generation time

```typescript
class RevenueForecastingEngine {
  private mlModelRegistry: MLModelRegistry;
  private featureEngine: FeatureEngineeringPipeline;
  private dataProcessor: SalesDataProcessor;

  async generateRevenueForecast(
    forecastRequest: ForecastRequest
  ): Promise<RevenueForecast> {
    // Load appropriate ML model
    const model = await this.mlModelRegistry.getModel(
      'revenue_forecast', 
      forecastRequest.modelVersion
    );
    
    // Prepare historical data
    const historicalData = await this.dataProcessor.getHistoricalSalesData(
      forecastRequest.entityId,
      forecastRequest.lookbackPeriod
    );
    
    // Engineer features for forecasting
    const features = await this.featureEngine.generateForecastFeatures(
      historicalData,
      forecastRequest.externalFactors
    );
    
    // Generate base forecast
    const baseForecast = await model.predict(features);
    
    // Apply business rules and adjustments
    const adjustedForecast = await this.applyBusinessAdjustments(
      baseForecast,
      forecastRequest.adjustments
    );
    
    // Calculate confidence intervals
    const confidenceIntervals = await this.calculateConfidenceIntervals(
      model,
      features,
      adjustedForecast
    );
    
    // Generate forecast explanation
    const explanation = await this.generateForecastExplanation(
      model,
      features,
      adjustedForecast
    );
    
    return {
      forecastId: generateUUID(),
      entityId: forecastRequest.entityId,
      forecastPeriod: forecastRequest.forecastPeriod,
      baseForecast: adjustedForecast,
      confidenceIntervals,
      explanation,
      modelMetadata: model.getMetadata(),
      generatedAt: new Date()
    };
  }

  private async applyBusinessAdjustments(
    baseForecast: ForecastData,
    adjustments: BusinessAdjustment[]
  ): Promise<ForecastData> {
    let adjustedForecast = { ...baseForecast };
    
    for (const adjustment of adjustments) {
      switch (adjustment.type) {
        case 'seasonal':
          adjustedForecast = this.applySeasonalAdjustment(adjustedForecast, adjustment);
          break;
        case 'market_condition':
          adjustedForecast = this.applyMarketAdjustment(adjustedForecast, adjustment);
          break;
        case 'manual_override':
          adjustedForecast = this.applyManualOverride(adjustedForecast, adjustment);
          break;
      }
    }
    
    return adjustedForecast;
  }
}
```

#### 2.2.3 Deal Probability Scorer
**Purpose**: Calculate probability scores for individual deals using AI models
**Technology**: XGBoost, feature engineering, real-time inference
**Performance**: 85% accuracy in deal outcome prediction, <2 second scoring time

```typescript
class DealProbabilityScorer {
  private scoringModel: MLModel;
  private featureExtractor: DealFeatureExtractor;
  private explanationEngine: ModelExplanationEngine;

  async scoreDeal(dealId: string, dealData: DealData): Promise<DealProbabilityScore> {
    // Extract features from deal data
    const features = await this.featureExtractor.extractDealFeatures(dealData);
    
    // Get probability score from ML model
    const probabilityScore = await this.scoringModel.predictProbability(features);
    
    // Generate explanation for the score
    const explanation = await this.explanationEngine.explainPrediction(
      this.scoringModel,
      features,
      probabilityScore
    );
    
    // Identify key influencing factors
    const influencingFactors = await this.identifyInfluencingFactors(
      features,
      explanation
    );
    
    // Generate recommendations for improvement
    const recommendations = await this.generateImprovementRecommendations(
      dealData,
      influencingFactors
    );
    
    return {
      dealId,
      probabilityScore: probabilityScore.probability,
      confidence: probabilityScore.confidence,
      explanation,
      influencingFactors,
      recommendations,
      scoredAt: new Date()
    };
  }

  private async extractDealFeatures(dealData: DealData): Promise<FeatureVector> {
    const features = new Map<string, number>();
    
    // Deal characteristics
    features.set('deal_amount', dealData.amount);
    features.set('days_in_pipeline', this.calculateDaysInPipeline(dealData));
    features.set('stage_progression_velocity', this.calculateStageVelocity(dealData));
    
    // Account characteristics
    features.set('account_size', dealData.account.employeeCount);
    features.set('account_industry_score', this.getIndustryScore(dealData.account.industry));
    
    // Sales rep characteristics
    features.set('rep_win_rate', await this.getRepWinRate(dealData.ownerId));
    features.set('rep_experience_score', await this.getRepExperienceScore(dealData.ownerId));
    
    // Activity features
    features.set('activity_count', dealData.activities.length);
    features.set('last_activity_days', this.getDaysSinceLastActivity(dealData));
    
    // Competitive features
    features.set('competitor_count', dealData.competitors.length);
    features.set('competitive_threat_score', this.calculateCompetitiveThreat(dealData));
    
    return new FeatureVector(features);
  }
}
```

### 2.3 Lead Scoring Service

#### 2.3.1 Component Architecture
```typescript
interface LeadScoringService {
  behavioralScorer: BehavioralLeadScorer;
  predictiveQualifier: PredictiveLeadQualifier;
  routingOptimizer: LeadRoutingOptimizer;
  nurturingEngine: LeadNurturingEngine;
  sourceAnalyzer: LeadSourceAnalyzer;
}
```

#### 2.3.2 Behavioral Lead Scorer
**Purpose**: Score leads based on behavioral data and engagement patterns
**Technology**: Real-time event processing, ML models, Redis
**Performance**: 30% improvement in lead conversion prediction, <1 second scoring

```typescript
class BehavioralLeadScorer {
  private eventProcessor: RealTimeEventProcessor;
  private scoringModel: BehavioralScoringModel;
  private scoreCache: RedisCache;

  async scoreLeadBehavior(leadId: string, behaviorData: BehaviorData): Promise<BehavioralScore> {
    // Check for cached score
    const cachedScore = await this.scoreCache.get(`lead_score:${leadId}`);
    if (cachedScore && this.isScoreValid(cachedScore)) {
      return cachedScore;
    }
    
    // Extract behavioral features
    const behaviorFeatures = await this.extractBehavioralFeatures(behaviorData);
    
    // Calculate engagement score
    const engagementScore = await this.calculateEngagementScore(behaviorFeatures);
    
    // Calculate intent score
    const intentScore = await this.calculateIntentScore(behaviorFeatures);
    
    // Calculate fit score
    const fitScore = await this.calculateFitScore(behaviorData.leadProfile);
    
    // Combine scores using weighted model
    const compositeScore = await this.scoringModel.calculateCompositeScore({
      engagement: engagementScore,
      intent: intentScore,
      fit: fitScore
    });
    
    const behavioralScore = {
      leadId,
      compositeScore,
      engagementScore,
      intentScore,
      fitScore,
      scoringFactors: this.identifyScoringFactors(behaviorFeatures),
      scoredAt: new Date(),
      validUntil: new Date(Date.now() + 3600000) // 1 hour validity
    };
    
    // Cache the score
    await this.scoreCache.set(`lead_score:${leadId}`, behavioralScore, 3600);
    
    return behavioralScore;
  }

  private async extractBehavioralFeatures(behaviorData: BehaviorData): Promise<BehaviorFeatures> {
    return {
      // Website engagement
      pageViews: behaviorData.webActivity.pageViews.length,
      timeOnSite: behaviorData.webActivity.totalTimeSpent,
      pagesPerSession: behaviorData.webActivity.averagePagesPerSession,
      
      // Email engagement
      emailOpens: behaviorData.emailActivity.opens.length,
      emailClicks: behaviorData.emailActivity.clicks.length,
      emailReplies: behaviorData.emailActivity.replies.length,
      
      // Content engagement
      contentDownloads: behaviorData.contentActivity.downloads.length,
      webinarAttendance: behaviorData.eventActivity.webinars.length,
      
      // Social engagement
      socialShares: behaviorData.socialActivity.shares.length,
      socialComments: behaviorData.socialActivity.comments.length,
      
      // Recency factors
      lastActivityDays: this.calculateDaysSinceLastActivity(behaviorData),
      activityFrequency: this.calculateActivityFrequency(behaviorData)
    };
  }
}
```

## 3. Data Models and Schemas

### 3.1 Core Sales Data Entities

#### 3.1.1 Sales Opportunity Schema
```sql
CREATE TABLE sales_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id),
    owner_id UUID NOT NULL REFERENCES users(id),
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
    
    -- Performance indexes
    INDEX idx_opportunity_owner_stage (owner_id, stage),
    INDEX idx_opportunity_close_date (close_date),
    INDEX idx_opportunity_amount_stage (amount DESC, stage),
    INDEX idx_opportunity_account (account_id, created_date DESC)
);

-- Partitioning by close date for performance
CREATE TABLE sales_opportunities_2024 PARTITION OF sales_opportunities
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### 3.1.2 Sales Activities Schema
```sql
CREATE TABLE sales_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES sales_opportunities(id),
    account_id UUID REFERENCES accounts(id),
    contact_id UUID REFERENCES contacts(id),
    owner_id UUID NOT NULL REFERENCES users(id),
    activity_type VARCHAR(50) NOT NULL, -- 'call', 'email', 'meeting', 'demo'
    subject VARCHAR(255) NOT NULL,
    description TEXT,
    activity_date TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER,
    outcome VARCHAR(100),
    next_action TEXT,
    attendees JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance indexes
    INDEX idx_activity_owner_date (owner_id, activity_date DESC),
    INDEX idx_activity_opportunity (opportunity_id, activity_date DESC),
    INDEX idx_activity_type_date (activity_type, activity_date DESC),
    INDEX idx_activity_account_date (account_id, activity_date DESC)
);
```

#### 3.1.3 Lead Scoring Schema
```sql
CREATE TABLE lead_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    composite_score DECIMAL(5,2) NOT NULL CHECK (composite_score BETWEEN 0 AND 100),
    behavioral_score DECIMAL(5,2) NOT NULL,
    demographic_score DECIMAL(5,2) NOT NULL,
    engagement_score DECIMAL(5,2) NOT NULL,
    intent_score DECIMAL(5,2) NOT NULL,
    fit_score DECIMAL(5,2) NOT NULL,
    scoring_factors JSONB NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Ensure only one active score per lead
    UNIQUE(lead_id, scored_at),
    INDEX idx_lead_score_composite (lead_id, composite_score DESC),
    INDEX idx_lead_score_valid (valid_until, composite_score DESC)
);
```

### 3.2 Analytics and Forecasting Schemas

#### 3.2.1 Sales Forecasts Schema
```sql
CREATE TABLE sales_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(20) NOT NULL, -- 'rep', 'team', 'region', 'company'
    entity_id UUID NOT NULL,
    forecast_period_start DATE NOT NULL,
    forecast_period_end DATE NOT NULL,
    forecast_amount DECIMAL(15,2) NOT NULL,
    confidence_level DECIMAL(3,2) NOT NULL,
    confidence_intervals JSONB NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_accuracy DECIMAL(5,4),
    contributing_factors JSONB,
    adjustments JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    
    INDEX idx_forecast_entity (entity_type, entity_id, forecast_period_start),
    INDEX idx_forecast_period (forecast_period_start, forecast_period_end)
);
```

## 4. API Specifications

### 4.1 RESTful API Endpoints

#### 4.1.1 Sales Performance APIs
```typescript
// Performance analytics and dashboards
GET /api/v1/performance/dashboard/{userId}
GET /api/v1/performance/benchmarks/{entityId}
POST /api/v1/performance/reports/generate

// Activity analytics
GET /api/v1/activities/analytics/{ownerId}
POST /api/v1/activities/effectiveness/analyze

// Pipeline health
GET /api/v1/pipeline/health/{entityId}
GET /api/v1/pipeline/velocity/{entityId}
```

#### 4.1.2 Forecasting APIs
```typescript
// Revenue forecasting
POST /api/v1/forecasts/revenue/generate
GET /api/v1/forecasts/{forecastId}
PUT /api/v1/forecasts/{forecastId}/adjust

// Deal probability scoring
POST /api/v1/deals/{dealId}/score
GET /api/v1/deals/probabilities/batch

// Scenario modeling
POST /api/v1/forecasts/scenarios/model
GET /api/v1/forecasts/scenarios/{scenarioId}
```

#### 4.1.3 Lead Scoring APIs
```typescript
// Lead scoring and qualification
POST /api/v1/leads/{leadId}/score
GET /api/v1/leads/scores/batch
PUT /api/v1/leads/{leadId}/qualify

// Lead routing
POST /api/v1/leads/routing/optimize
GET /api/v1/leads/routing/assignments

// Nurturing recommendations
GET /api/v1/leads/{leadId}/nurturing/recommendations
POST /api/v1/leads/nurturing/campaigns/trigger
```

### 4.2 GraphQL Schema
```graphql
type Query {
  salesPerformance(entityId: ID!, timeRange: DateRange): PerformanceMetrics
  forecasts(entityType: EntityType, entityId: ID!): [Forecast]
  leadScores(filter: LeadScoreFilter): [LeadScore]
  dealProbabilities(dealIds: [ID!]): [DealProbability]
}

type Mutation {
  generateForecast(input: ForecastInput!): Forecast
  scoreLeads(leadIds: [ID!]): [LeadScore]
  optimizeTerritory(input: TerritoryOptimizationInput!): TerritoryPlan
  updateDealProbability(dealId: ID!, probability: Float!): DealProbability
}

type Subscription {
  performanceUpdates(entityId: ID!): PerformanceMetrics
  leadScoreUpdates(leadIds: [ID!]): LeadScore
  forecastUpdates(forecastId: ID!): Forecast
}
```

This HLD provides comprehensive component specifications, data models, APIs, and processing workflows that build upon all previous documents, ensuring implementation-ready designs for the sales performance analytics platform.
