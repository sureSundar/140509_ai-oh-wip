# Low Level Design (LLD)
## HR Talent Matching and Recruitment AI Platform

*Building upon PRD, FRD, NFRD, Architecture Diagram, and HLD for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 45 functional requirements covering all system capabilities
- ✅ NFRD completed with 38 non-functional requirements for performance, security, compliance
- ✅ Architecture Diagram completed with technology stack and system architecture
- ✅ HLD completed with detailed component specifications and interfaces
- ✅ Technology stack validated and approved for enterprise HR environment

### TASK
Create implementation-ready low-level design specifications including detailed class diagrams, database schemas, API specifications, algorithm implementations, configuration parameters, and deployment scripts that enable direct development of the HR talent matching platform.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All classes and methods have detailed specifications with parameters and return types
- [ ] Database schemas support all data requirements from HLD components
- [ ] API specifications include request/response formats, error codes, and authentication
- [ ] AI/ML algorithm implementations satisfy performance requirements (<2s response, 90% accuracy)
- [ ] Configuration parameters support all operational requirements
- [ ] Code structure follows enterprise security and quality standards

**Validation Criteria:**
- [ ] Implementation specifications reviewed with development team for feasibility
- [ ] Database design validated with DBA team for performance and scalability
- [ ] API specifications validated with integration team and ATS/job board partners
- [ ] Security implementations reviewed with cybersecurity team for compliance
- [ ] AI/ML specifications validated with data science team for accuracy targets
- [ ] Code quality standards confirmed with architecture review board

### EXIT CRITERIA
- ✅ Complete implementation specifications ready for development team
- ✅ Database schemas, API specs, and class diagrams documented
- ✅ AI/ML algorithm implementations with performance optimizations specified
- ✅ Configuration management and deployment procedures defined
- ✅ Foundation established for pseudocode and implementation phase

---

### Reference to Previous Documents
This LLD provides implementation-ready specifications based on **ALL** previous documents:
- **PRD Success Metrics** → Implementation targets for 60% time-to-hire reduction, 40% quality improvement, 90% bias reduction
- **FRD Functional Requirements (FR-001-045)** → Detailed method implementations for all system functions
- **NFRD Performance Requirements (NFR-001-038)** → Optimized algorithms and data structures for performance targets
- **Architecture Diagram** → Technology stack implementation with specific versions and configurations
- **HLD Component Design** → Detailed class structures, database schemas, and API implementations

## 1. Database Schema Design

### 1.1 Core Tables (PostgreSQL)
```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('CANDIDATE', 'RECRUITER', 'HIRING_MANAGER', 'HR_DIRECTOR')),
    company_id UUID REFERENCES companies(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Candidate Profiles
CREATE TABLE candidate_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    resume_url VARCHAR(500),
    skills JSONB,
    total_experience_years DECIMAL(4,2),
    current_location VARCHAR(200),
    salary_expectation_min INTEGER,
    salary_expectation_max INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Job Postings
CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    required_skills JSONB NOT NULL,
    salary_min INTEGER,
    salary_max INTEGER,
    location VARCHAR(200),
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Job Applications and Matching
CREATE TABLE job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_posting_id UUID NOT NULL REFERENCES job_postings(id),
    candidate_profile_id UUID NOT NULL REFERENCES candidate_profiles(id),
    match_score DECIMAL(5,2),
    match_explanation JSONB,
    status VARCHAR(50) DEFAULT 'APPLIED',
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bias Detection Logs
CREATE TABLE bias_detection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    bias_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    confidence_score DECIMAL(3,2),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_candidate_skills ON candidate_profiles USING GIN (skills);
CREATE INDEX idx_job_skills ON job_postings USING GIN (required_skills);
CREATE INDEX idx_applications_score ON job_applications(match_score DESC);
```

## 2. API Specifications

### 2.1 Resume Processing API
```typescript
interface ResumeUploadRequest {
  file: File;
  candidateId: string;
}

interface ParsedResumeData {
  personalInfo: {
    name: string;
    email: string;
    phone: string;
    location: string;
  };
  skills: Array<{
    name: string;
    category: string;
    proficiencyLevel: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  }>;
  workExperience: Array<{
    company: string;
    title: string;
    startDate: string;
    endDate?: string;
    description: string;
  }>;
  education: Array<{
    institution: string;
    degree: string;
    field: string;
    graduationDate: string;
  }>;
}

// Endpoints
POST /api/v1/resumes/upload
GET /api/v1/resumes/{resumeId}/parsed-data
```

### 2.2 Matching Engine API
```typescript
interface MatchRequest {
  candidateId?: string;
  jobId?: string;
  limit?: number;
}

interface MatchResult {
  candidateId: string;
  jobId: string;
  overallScore: number;
  scoreBreakdown: {
    skillsMatch: number;
    experienceMatch: number;
    locationMatch: number;
    salaryAlignment: number;
  };
  explanation: {
    strengths: string[];
    gaps: Array<{
      skill: string;
      required: boolean;
      candidateLevel: string;
      requiredLevel: string;
    }>;
  };
}

// Endpoints
POST /api/v1/matching/find-candidates
POST /api/v1/matching/find-jobs
GET /api/v1/matching/{matchId}/explanation
```

### 2.3 Bias Detection API
```typescript
interface BiasAnalysisRequest {
  entityType: 'JOB_POSTING' | 'CANDIDATE_SCREENING' | 'HIRING_DECISION';
  entityId: string;
}

interface BiasAnalysisResponse {
  overallRisk: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  biasIndicators: Array<{
    type: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    confidence: number;
    description: string;
  }>;
  recommendations: Array<{
    issue: string;
    recommendation: string;
    priority: 'LOW' | 'MEDIUM' | 'HIGH';
  }>;
}

// Endpoints
POST /api/v1/bias/analyze
GET /api/v1/bias/reports/{companyId}
```

## 3. Core Class Implementations

### 3.1 Resume Processing Service
```python
class ResumeProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        self.skills_extractor = SkillsExtractor()
        
    async def process_resume(self, file_path: str) -> ParsedResumeData:
        # Extract text from document
        text = await self.extract_text(file_path)
        
        # Parse with NLP
        doc = self.nlp(text)
        
        # Extract structured data
        personal_info = self.extract_personal_info(doc)
        skills = self.skills_extractor.extract_skills(doc)
        experience = self.extract_work_experience(doc)
        education = self.extract_education(doc)
        
        return ParsedResumeData(
            personal_info=personal_info,
            skills=skills,
            work_experience=experience,
            education=education
        )
```

### 3.2 Matching Engine
```python
class MatchingEngine:
    def __init__(self):
        self.semantic_matcher = SemanticMatcher()
        self.skills_matcher = SkillsMatcher()
        
    async def find_matches(self, candidate_id: str, limit: int = 50) -> List[MatchResult]:
        # Get candidate profile
        candidate = await self.get_candidate_profile(candidate_id)
        
        # Get active job postings
        jobs = await self.get_active_jobs()
        
        matches = []
        for job in jobs:
            # Calculate match score
            score = await self.calculate_match_score(candidate, job)
            
            if score > 0.3:  # Minimum threshold
                match_result = MatchResult(
                    candidate_id=candidate_id,
                    job_id=job.id,
                    overall_score=score,
                    score_breakdown=self.get_score_breakdown(candidate, job),
                    explanation=self.generate_explanation(candidate, job)
                )
                matches.append(match_result)
        
        # Sort by score and return top matches
        return sorted(matches, key=lambda x: x.overall_score, reverse=True)[:limit]
    
    async def calculate_match_score(self, candidate, job) -> float:
        # Skills matching (40% weight)
        skills_score = self.skills_matcher.calculate_similarity(
            candidate.skills, job.required_skills
        )
        
        # Experience matching (30% weight)
        experience_score = self.calculate_experience_match(
            candidate.total_experience_years, job.experience_requirements
        )
        
        # Location matching (20% weight)
        location_score = self.calculate_location_match(
            candidate.location, job.location
        )
        
        # Salary alignment (10% weight)
        salary_score = self.calculate_salary_alignment(
            candidate.salary_expectation, job.salary_range
        )
        
        # Weighted average
        overall_score = (
            skills_score * 0.4 +
            experience_score * 0.3 +
            location_score * 0.2 +
            salary_score * 0.1
        )
        
        return overall_score
```

### 3.3 Bias Detection Service
```python
class BiasDetectionService:
    def __init__(self):
        self.language_analyzer = LanguageBiasAnalyzer()
        self.demographic_analyzer = DemographicBiasAnalyzer()
        
    async def analyze_bias(self, entity_type: str, entity_id: str) -> BiasAnalysisResponse:
        if entity_type == "JOB_POSTING":
            return await self.analyze_job_posting_bias(entity_id)
        elif entity_type == "HIRING_DECISION":
            return await self.analyze_hiring_decision_bias(entity_id)
        
    async def analyze_job_posting_bias(self, job_id: str) -> BiasAnalysisResponse:
        job = await self.get_job_posting(job_id)
        
        # Language bias analysis
        language_bias = self.language_analyzer.analyze(job.description)
        
        # Requirements bias analysis
        requirements_bias = self.analyze_requirements_bias(job.required_skills)
        
        # Combine results
        bias_indicators = language_bias + requirements_bias
        
        overall_risk = self.calculate_overall_risk(bias_indicators)
        recommendations = self.generate_recommendations(bias_indicators)
        
        return BiasAnalysisResponse(
            overall_risk=overall_risk,
            bias_indicators=bias_indicators,
            recommendations=recommendations
        )
```

## 4. Configuration and Deployment

### 4.1 Environment Configuration
```yaml
# config/production.yaml
database:
  host: ${DB_HOST}
  port: ${DB_PORT}
  name: ${DB_NAME}
  user: ${DB_USER}
  password: ${DB_PASSWORD}

redis:
  host: ${REDIS_HOST}
  port: ${REDIS_PORT}
  password: ${REDIS_PASSWORD}

ml_models:
  resume_ner_model: "models/resume_ner_v2.1"
  skills_classifier: "models/skills_classifier_v1.3"
  bias_detector: "models/bias_detector_v1.0"

api:
  rate_limit: 1000  # requests per minute
  max_file_size: 10485760  # 10MB
  supported_formats: [".pdf", ".docx", ".doc", ".txt"]

security:
  jwt_secret: ${JWT_SECRET}
  encryption_key: ${ENCRYPTION_KEY}
  session_timeout: 14400  # 4 hours
```

### 4.2 Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hr-talent-matching
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hr-talent-matching
  template:
    metadata:
      labels:
        app: hr-talent-matching
    spec:
      containers:
      - name: api-server
        image: hr-talent-matching:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

This LLD provides comprehensive implementation-ready specifications that development teams can use to build the HR talent matching platform while maintaining full traceability to all previous requirements documents.
