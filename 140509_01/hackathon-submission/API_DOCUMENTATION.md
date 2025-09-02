# 📚 RetailAI Platform - Comprehensive API Documentation

## Overview

The RetailAI Platform is a comprehensive AI-powered retail inventory optimization system that provides real-time analytics, machine learning-driven forecasting, and intelligent inventory management. This documentation covers all REST APIs across the platform's microservices architecture.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│                 RetailAI Platform                   │
├─────────────────────────────────────────────────────┤
│  🔍 Monitoring API (8007)    📊 Dashboard API (8005) │
│  📬 Notifications API (8006) 📊 Reporting API (8006) │
│  🔐 Authentication API (8004) ⚠️  Alert Engine (8003)│
│  🌤️  External Data API (8002) 🧠 ML Engine API (8001)│
│  📡 Kafka Streaming Pipeline   🗃️  PostgreSQL DB    │
└─────────────────────────────────────────────────────┘
```

## 🔑 Authentication

All APIs use Bearer token authentication:
```bash
Authorization: Bearer <your-jwt-token>
```

### Get Authentication Token
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123",
  "mfa_token": "123456" // Optional for MFA-enabled accounts
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "admin_001",
  "username": "admin",
  "roles": ["super_admin"],
  "permissions": ["read_sales_data", "manage_users", ...],
  "expires_at": "2024-01-15T10:30:00Z"
}
```

---

## 🧠 ML Engine API (Port 8001)

### Base URL: `http://localhost:8001`

#### Get Available Models
```http
GET /api/ml/models
```

**Response:**
```json
{
  "models": [
    {
      "model_id": "arima_forecaster",
      "name": "ARIMA Forecasting Model",
      "type": "forecasting",
      "status": "trained",
      "accuracy": 0.85,
      "last_trained": "2024-01-10T15:30:00Z"
    }
  ]
}
```

#### Generate Forecast
```http
POST /api/ml/forecast
Content-Type: application/json

{
  "product_id": "PROD_001",
  "store_id": "STORE_001",
  "forecast_days": 30,
  "model_type": "arima"
}
```

**Response:**
```json
{
  "forecast_id": "forecast_abc123",
  "product_id": "PROD_001",
  "store_id": "STORE_001",
  "forecasted_demand": [
    {"date": "2024-01-11", "demand": 45.2, "confidence_lower": 38.1, "confidence_upper": 52.3},
    {"date": "2024-01-12", "demand": 48.7, "confidence_lower": 41.2, "confidence_upper": 56.2}
  ],
  "model_performance": {
    "mae": 2.34,
    "mse": 8.97,
    "rmse": 2.99
  }
}
```

#### Optimize Inventory
```http
POST /api/ml/optimize-inventory
Content-Type: application/json

{
  "product_id": "PROD_001",
  "store_id": "STORE_001",
  "current_stock": 150,
  "lead_time_days": 7,
  "service_level": 0.95
}
```

**Response:**
```json
{
  "optimization_id": "opt_xyz789",
  "product_id": "PROD_001",
  "recommendations": {
    "optimal_order_quantity": 120,
    "reorder_point": 35,
    "safety_stock": 15,
    "estimated_savings": 850.50
  },
  "calculations": {
    "eoq": 120,
    "annual_demand": 2400,
    "holding_cost_per_unit": 2.50,
    "order_cost": 25.00
  }
}
```

---

## 🌤️ External Data API (Port 8002)

### Base URL: `http://localhost:8002`

#### Get Weather Data
```http
GET /api/external/weather?city=New York&days=7
```

**Response:**
```json
{
  "location": "New York, NY",
  "current_weather": {
    "temperature": 22.5,
    "condition": "partly_cloudy",
    "humidity": 65,
    "wind_speed": 12.3
  },
  "forecast": [
    {
      "date": "2024-01-11",
      "temperature_high": 25,
      "temperature_low": 18,
      "condition": "sunny",
      "precipitation_probability": 10
    }
  ],
  "demand_impact_score": 7.2
}
```

#### Get Local Events
```http
GET /api/external/events?city=New York&date=2024-01-15
```

**Response:**
```json
{
  "events": [
    {
      "event_id": "evt_123",
      "name": "New York Marathon",
      "date": "2024-01-15",
      "category": "sports",
      "expected_attendance": 50000,
      "impact_score": 8.5,
      "affected_categories": ["sports_apparel", "energy_drinks", "water"]
    }
  ]
}
```

#### Get Demographics Data
```http
GET /api/external/demographics?store_id=STORE_001&radius_miles=5
```

**Response:**
```json
{
  "store_id": "STORE_001",
  "demographics": {
    "population": 45230,
    "median_age": 34.2,
    "median_income": 68500,
    "education_levels": {
      "high_school": 0.25,
      "bachelor": 0.45,
      "graduate": 0.30
    }
  },
  "market_insights": {
    "premium_product_affinity": 0.72,
    "organic_product_preference": 0.58
  }
}
```

---

## ⚠️ Alert Engine API (Port 8003)

### Base URL: `http://localhost:8003`

#### Get Active Alerts
```http
GET /api/alerts/active?severity=high&limit=50
```

**Response:**
```json
{
  "alerts": [
    {
      "alert_id": "alert_abc123",
      "alert_type": "LOW_STOCK",
      "severity": "high",
      "product_id": "PROD_001",
      "store_id": "STORE_001",
      "current_stock": 5,
      "threshold": 15,
      "message": "Product PROD_001 at STORE_001 is below minimum stock level",
      "created_at": "2024-01-10T14:30:00Z",
      "acknowledged": false
    }
  ],
  "total_count": 1
}
```

#### Create Custom Alert Rule
```http
POST /api/alerts/rules
Content-Type: application/json

{
  "name": "High Demand Alert",
  "description": "Alert when demand exceeds forecast by 50%",
  "conditions": {
    "metric": "daily_demand",
    "operator": "greater_than",
    "threshold": 1.5,
    "comparison": "forecast"
  },
  "severity": "medium",
  "notification_channels": ["email", "slack"],
  "recipients": ["manager@retailai.com"]
}
```

#### Acknowledge Alert
```http
POST /api/alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "acknowledged_by": "user_123",
  "notes": "Inventory replenishment ordered"
}
```

---

## 🔐 Authentication & RBAC API (Port 8004)

### Base URL: `http://localhost:8004`

#### Get User Profile
```http
GET /api/auth/session
Authorization: Bearer <token>
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "user_id": "user_001",
  "username": "manager",
  "roles": ["manager", "analyst"],
  "permissions": ["read_sales_data", "view_analytics"],
  "expires_at": "2024-01-10T18:00:00Z",
  "store_access": ["STORE_001", "STORE_002"]
}
```

#### Create User
```http
POST /api/auth/users
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@retailai.com",
  "full_name": "New User",
  "password": "securepassword123",
  "roles": ["analyst"],
  "store_access": ["STORE_001"]
}
```

#### Get Audit Logs
```http
GET /api/auth/audit-logs?limit=100
Authorization: Bearer <token>
```

**Response:**
```json
{
  "audit_logs": [
    {
      "log_id": "log_123",
      "action": "LOGIN_SUCCESS",
      "resource": "authentication",
      "ip_address": "192.168.1.100",
      "timestamp": "2024-01-10T15:30:00Z",
      "success": true
    }
  ]
}
```

---

## 📊 Dashboard API (Port 8005)

### Base URL: `http://localhost:8005`

#### Get Real-time KPIs
```http
GET /api/dashboard/kpis
```

**Response:**
```json
{
  "kpis": [
    {
      "name": "Total Revenue",
      "value": 180500.00,
      "unit": "USD",
      "trend": "up",
      "trend_percentage": 12.5,
      "status": "good",
      "last_updated": "2024-01-10T15:45:00Z"
    },
    {
      "name": "Inventory Turnover",
      "value": 8.2,
      "unit": "times/year",
      "trend": "stable",
      "trend_percentage": 2.1,
      "status": "good"
    }
  ]
}
```

#### Get Sales Analytics
```http
GET /api/dashboard/sales?store_id=STORE_001
```

**Response:**
```json
{
  "store_id": "STORE_001",
  "insights": {
    "total_revenue": 45230.50,
    "daily_revenue": 1820.30,
    "transactions_count": 1250,
    "avg_transaction_value": 36.18,
    "revenue_growth": 8.5,
    "top_stores": [
      {"store_id": "STORE_001", "revenue": 45230.50},
      {"store_id": "STORE_002", "revenue": 38950.25}
    ],
    "sales_by_hour": {
      "09": 450.20, "10": 680.50, "11": 920.80
    },
    "product_performance": [
      {"product_id": "PROD_001", "revenue": 5250.00, "quantity": 180}
    ]
  }
}
```

#### Get Executive Summary
```http
GET /api/dashboard/executive-summary
```

**Response:**
```json
{
  "period": "Last 30 days",
  "key_metrics": {
    "total_revenue": 2450000.00,
    "profit_margin": 18.5,
    "inventory_turns": 2.3,
    "customer_satisfaction": 4.2
  },
  "trends": {
    "revenue_growth": 12.8,
    "cost_reduction": 5.2,
    "efficiency_improvement": 15.3
  },
  "alerts_summary": {
    "critical": 2,
    "high": 8,
    "medium": 15
  }
}
```

---

## 📊 Reporting API (Port 8006)

### Base URL: `http://localhost:8006`

#### Generate Report
```http
POST /api/reports/generate
Content-Type: application/json

{
  "report_type": "daily_summary",
  "format": "html",
  "filters": {
    "store_id": "STORE_001",
    "date_range": "2024-01-01 to 2024-01-10"
  }
}
```

**Response:**
```json
{
  "message": "Report generation started",
  "status": "processing"
}
```

#### Schedule Automated Report
```http
POST /api/reports/schedules
Content-Type: application/json

{
  "report_type": "weekly_business_review",
  "frequency": "weekly",
  "recipients": ["manager@retailai.com", "exec@retailai.com"],
  "format": "pdf",
  "filters": {
    "include_all_stores": true
  }
}
```

#### Get Report Executions
```http
GET /api/reports/executions?limit=20
```

**Response:**
```json
[
  {
    "execution_id": "exec_123",
    "report_type": "daily_summary",
    "status": "completed",
    "started_at": "2024-01-10T06:00:00Z",
    "completed_at": "2024-01-10T06:02:15Z",
    "file_size_mb": 2.5,
    "output_path": "/reports/daily_summary_exec_123.html"
  }
]
```

#### Download Report
```http
GET /api/reports/download/{execution_id}
```

---

## 🔍 Performance Monitoring API (Port 8007)

### Base URL: `http://localhost:8007`

#### Get Current Metrics
```http
GET /api/monitoring/metrics/current
```

**Response:**
```json
{
  "service": "retailai",
  "instance_id": "retailai_abc123",
  "timestamp": "2024-01-10T15:45:00Z",
  "system_metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 68.5,
    "disk_usage_percent": 72.3,
    "processes_count": 156
  },
  "application_metrics": {
    "requests_per_second": 12.5,
    "avg_response_time_ms": 125.3,
    "error_rate_percent": 0.8,
    "database_connections": 25,
    "cache_hit_rate": 94.2
  }
}
```

#### Record Custom Metric
```http
POST /api/monitoring/metrics/custom
Content-Type: application/json

{
  "name": "active_users",
  "value": 245,
  "unit": "users",
  "metric_type": "gauge",
  "tags": {
    "service": "web_app",
    "environment": "production"
  }
}
```

#### Get Performance Alerts
```http
GET /api/monitoring/alerts/active
```

**Response:**
```json
[
  {
    "alert_id": "perf_alert_123",
    "metric_name": "cpu_percent",
    "threshold_value": 80.0,
    "actual_value": 85.2,
    "level": "warning",
    "message": "CPU usage is 85.2%, exceeding warning threshold of 80%",
    "service": "retailai",
    "timestamp": "2024-01-10T15:40:00Z",
    "is_active": true
  }
]
```

#### Get Centralized Logs
```http
GET /api/monitoring/logs?level=error&hours=24&limit=100
```

**Response:**
```json
{
  "logs": [
    {
      "level": "ERROR",
      "message": "Database connection timeout",
      "service": "ml_engine",
      "timestamp": "2024-01-10T15:30:00Z",
      "metadata": {
        "error_code": "DB_TIMEOUT",
        "query": "SELECT * FROM products WHERE..."
      }
    }
  ],
  "total": 1,
  "period_hours": 24
}
```

---

## 🔄 Real-time WebSocket APIs

### Dashboard Updates
```javascript
// Connect to dashboard WebSocket
const ws = new WebSocket('ws://localhost:8005/ws/dashboard');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'dashboard_update') {
    // Handle real-time KPI updates
    console.log('KPIs updated:', data.data.kpis);
    console.log('Alerts:', data.data.alerts);
  }
};

// Send ping to keep connection alive
setInterval(() => {
  ws.send('ping');
}, 30000);
```

---

## 📋 Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": { /* response data */ },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": {
      "field": "product_id",
      "issue": "Product ID is required"
    }
  }
}
```

### Paginated Response
```json
{
  "data": [ /* array of items */ ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1250,
    "pages": 25,
    "has_next": true,
    "has_previous": false
  }
}
```

---

## 📊 Status Codes

| Code | Description |
|------|-------------|
| 200  | Success |
| 201  | Created |
| 400  | Bad Request |
| 401  | Unauthorized |
| 403  | Forbidden |
| 404  | Not Found |
| 422  | Validation Error |
| 500  | Internal Server Error |
| 503  | Service Unavailable |

---

## 🧪 Testing Examples

### Using curl
```bash
# Get authentication token
curl -X POST http://localhost:8004/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Get ML forecast
curl -X POST http://localhost:8001/api/ml/forecast \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_id":"PROD_001","store_id":"STORE_001","forecast_days":7}'

# Get dashboard KPIs
curl -X GET http://localhost:8005/api/dashboard/kpis \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Using Python requests
```python
import requests
import json

# Authentication
auth_response = requests.post('http://localhost:8004/api/auth/login', 
  json={'username': 'admin', 'password': 'admin123'})
token = auth_response.json()['session_id']

headers = {'Authorization': f'Bearer {token}'}

# Generate forecast
forecast_response = requests.post('http://localhost:8001/api/ml/forecast', 
  headers=headers,
  json={
    'product_id': 'PROD_001',
    'store_id': 'STORE_001', 
    'forecast_days': 30
  })

print(json.dumps(forecast_response.json(), indent=2))
```

---

## 🛡️ Rate Limiting

All APIs implement rate limiting:
- **Standard users**: 1000 requests/hour
- **Premium users**: 10000 requests/hour  
- **Admin users**: Unlimited

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641811200
```

---

## 🔧 Environment Configuration

### Development
- Base URL: `http://localhost:800X`
- Database: PostgreSQL on localhost:5432
- Cache: Redis on localhost:6379

### Production
- Base URL: `https://api.retailai.com`
- Database: Managed PostgreSQL
- Cache: Redis Cluster
- Load Balancer: NGINX

---

## 📞 Support

For API support and questions:
- Email: api-support@retailai.com
- Documentation: https://docs.retailai.com
- Status Page: https://status.retailai.com

---

**Last Updated**: January 10, 2024
**API Version**: v1.0.0
**Documentation Version**: 1.0