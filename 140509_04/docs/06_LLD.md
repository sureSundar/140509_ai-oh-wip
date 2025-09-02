# Low Level Design (LLD)
## IoT Predictive Maintenance Platform

*Building upon PRD, FRD, NFRD, Architecture Diagram, and HLD for implementation-ready specifications*

## ETVX Framework

### ENTRY CRITERIA
- ✅ PRD completed with business objectives and success metrics
- ✅ FRD completed with 126 functional requirements (FR-001 to FR-126)
- ✅ NFRD completed with 138 non-functional requirements (NFR-001 to NFR-138)
- ✅ Architecture Diagram completed with technology stack and system architecture
- ✅ HLD completed with detailed component specifications and interfaces
- ✅ Technology stack validated and approved for industrial IoT environment

### TASK
Create implementation-ready low-level design specifications including detailed class diagrams, database schemas, API specifications, algorithm implementations, configuration parameters, and deployment scripts that enable direct development of the IoT predictive maintenance platform.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All classes and methods have detailed specifications with parameters and return types
- [ ] Database schemas support all data requirements from HLD components
- [ ] API specifications include request/response formats, error codes, and authentication
- [ ] Algorithm implementations satisfy performance requirements (<2 min response, 1M+ readings/min)
- [ ] Configuration parameters support all operational requirements
- [ ] Code structure follows industrial IoT security and quality standards

**Validation Criteria:**
- [ ] Implementation specifications reviewed with development team for feasibility
- [ ] Database design validated with DBA team for performance and scalability
- [ ] API specifications validated with integration team and industrial system partners
- [ ] Security implementations reviewed with cybersecurity team for IEC 62443 compliance
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
- **PRD Success Metrics** → Implementation targets for 70% downtime reduction, 25% cost reduction, >90% prediction accuracy
- **FRD Functional Requirements (FR-001-126)** → Detailed method implementations for all system functions
- **NFRD Performance Requirements (NFR-001-138)** → Optimized algorithms and data structures for performance targets
- **Architecture Diagram** → Technology stack implementation with specific versions and configurations
- **HLD Component Design** → Detailed class structures, database schemas, and API implementations

## 1. Edge Gateway Implementation

### 1.1 Industrial Protocol Adapter Classes
```go
// main.go - Edge Gateway Service
package main

import (
    "context"
    "log"
    "sync"
    "time"
    
    "github.com/eclipse/paho.mqtt.golang"
    "github.com/gopcua/opcua"
    "github.com/tbrandon/mbserver"
)

type SensorReading struct {
    DeviceID    string    `json:"device_id" validate:"required"`
    SensorID    string    `json:"sensor_id" validate:"required"`
    Timestamp   time.Time `json:"timestamp" validate:"required"`
    Value       float64   `json:"value" validate:"required"`
    Unit        string    `json:"unit" validate:"required"`
    Quality     string    `json:"quality" validate:"oneof=GOOD BAD UNCERTAIN"`
    Source      string    `json:"source" validate:"oneof=OPC_UA MODBUS MQTT DNP3"`
}

type ProtocolAdapter interface {
    Connect(ctx context.Context) error
    Subscribe(callback func(SensorReading)) error
    Disconnect() error
    IsConnected() bool
}

type OPCUAAdapter struct {
    client     *opcua.Client
    endpoint   string
    nodeIDs    []string
    connected  bool
    mutex      sync.RWMutex
}

func NewOPCUAAdapter(endpoint string, nodeIDs []string) *OPCUAAdapter {
    return &OPCUAAdapter{
        endpoint: endpoint,
        nodeIDs:  nodeIDs,
    }
}

func (o *OPCUAAdapter) Connect(ctx context.Context) error {
    o.mutex.Lock()
    defer o.mutex.Unlock()
    
    client := opcua.NewClient(o.endpoint, opcua.SecurityMode(ua.MessageSecurityModeNone))
    if err := client.Connect(ctx); err != nil {
        return fmt.Errorf("OPC-UA connection failed: %w", err)
    }
    
    o.client = client
    o.connected = true
    log.Printf("Connected to OPC-UA server: %s", o.endpoint)
    return nil
}

func (o *OPCUAAdapter) Subscribe(callback func(SensorReading)) error {
    if !o.IsConnected() {
        return errors.New("OPC-UA client not connected")
    }
    
    sub, err := o.client.Subscribe(&opcua.SubscriptionParameters{
        Interval: 100 * time.Millisecond,
    })
    if err != nil {
        return fmt.Errorf("subscription creation failed: %w", err)
    }
    
    for _, nodeID := range o.nodeIDs {
        go o.subscribeToNode(sub, nodeID, callback)
    }
    
    return nil
}

func (o *OPCUAAdapter) subscribeToNode(sub *opcua.Subscription, nodeID string, callback func(SensorReading)) {
    ch := make(chan *opcua.DataChangeNotification)
    
    if _, err := sub.Monitor(opcua.TimestampsToReturn_Both, nodeID, ch); err != nil {
        log.Printf("Failed to monitor node %s: %v", nodeID, err)
        return
    }
    
    for notification := range ch {
        reading := SensorReading{
            DeviceID:  extractDeviceID(nodeID),
            SensorID:  nodeID,
            Timestamp: notification.Value.ServerTimestamp,
            Value:     notification.Value.Value.Float(),
            Unit:      extractUnit(nodeID),
            Quality:   mapQuality(notification.Value.StatusCode),
            Source:    "OPC_UA",
        }
        callback(reading)
    }
}

type ModbusAdapter struct {
    address   string
    slaveID   byte
    registers []uint16
    client    modbus.Client
    connected bool
    mutex     sync.RWMutex
}

func NewModbusAdapter(address string, slaveID byte, registers []uint16) *ModbusAdapter {
    return &ModbusAdapter{
        address:   address,
        slaveID:   slaveID,
        registers: registers,
    }
}

func (m *ModbusAdapter) Connect(ctx context.Context) error {
    m.mutex.Lock()
    defer m.mutex.Unlock()
    
    handler := modbus.NewTCPClientHandler(m.address)
    handler.SlaveId = m.slaveID
    handler.Timeout = 5 * time.Second
    
    if err := handler.Connect(); err != nil {
        return fmt.Errorf("Modbus connection failed: %w", err)
    }
    
    m.client = modbus.NewClient(handler)
    m.connected = true
    log.Printf("Connected to Modbus device: %s", m.address)
    return nil
}

func (m *ModbusAdapter) Subscribe(callback func(SensorReading)) error {
    if !m.IsConnected() {
        return errors.New("Modbus client not connected")
    }
    
    ticker := time.NewTicker(1 * time.Second) // 1Hz polling
    go func() {
        for range ticker.C {
            m.pollRegisters(callback)
        }
    }()
    
    return nil
}

func (m *ModbusAdapter) pollRegisters(callback func(SensorReading)) {
    for _, register := range m.registers {
        results, err := m.client.ReadHoldingRegisters(register, 1)
        if err != nil {
            log.Printf("Failed to read register %d: %v", register, err)
            continue
        }
        
        value := binary.BigEndian.Uint16(results)
        reading := SensorReading{
            DeviceID:  fmt.Sprintf("modbus_%s_%d", m.address, m.slaveID),
            SensorID:  fmt.Sprintf("register_%d", register),
            Timestamp: time.Now(),
            Value:     float64(value),
            Unit:      getRegisterUnit(register),
            Quality:   "GOOD",
            Source:    "MODBUS",
        }
        callback(reading)
    }
}
```

### 1.2 Edge Analytics Implementation
```python
# edge_analytics.py - Edge Analytics Engine
import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from kafka import KafkaConsumer, KafkaProducer
import tensorflow as tf
from influxdb_client import InfluxDBClient, Point
import redis

@dataclass
class SensorReading:
    device_id: str
    sensor_id: str
    timestamp: datetime
    value: float
    unit: str
    quality: str
    source: str

@dataclass
class AnomalyResult:
    sensor_id: str
    timestamp: datetime
    anomaly_score: float
    is_anomaly: bool
    confidence: float
    method: str

class StatisticalProcessControl:
    def __init__(self, window_size: int = 100, sigma_threshold: float = 3.0):
        self.window_size = window_size
        self.sigma_threshold = sigma_threshold
        self.data_windows: Dict[str, List[float]] = {}
        
    def update(self, sensor_id: str, value: float) -> Optional[AnomalyResult]:
        if sensor_id not in self.data_windows:
            self.data_windows[sensor_id] = []
            
        window = self.data_windows[sensor_id]
        window.append(value)
        
        if len(window) > self.window_size:
            window.pop(0)
            
        if len(window) < 30:  # Need minimum samples
            return None
            
        mean = np.mean(window)
        std = np.std(window)
        
        if std == 0:
            return None
            
        z_score = abs(value - mean) / std
        is_anomaly = z_score > self.sigma_threshold
        
        return AnomalyResult(
            sensor_id=sensor_id,
            timestamp=datetime.now(),
            anomaly_score=z_score / self.sigma_threshold,
            is_anomaly=is_anomaly,
            confidence=min(z_score / self.sigma_threshold, 1.0),
            method="SPC"
        )

class LightweightMLDetector:
    def __init__(self, model_path: str):
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.feature_buffer: Dict[str, List[float]] = {}
        
    def extract_features(self, sensor_id: str, values: List[float]) -> np.ndarray:
        """Extract time-domain features from sensor values"""
        if len(values) < 10:
            return None
            
        features = []
        values_array = np.array(values)
        
        # Statistical features
        features.extend([
            np.mean(values_array),
            np.std(values_array),
            np.min(values_array),
            np.max(values_array),
            np.median(values_array)
        ])
        
        # Time-domain features
        features.extend([
            np.sqrt(np.mean(values_array**2)),  # RMS
            np.max(values_array) - np.min(values_array),  # Peak-to-peak
            len(values_array)  # Sample count
        ])
        
        return np.array(features, dtype=np.float32).reshape(1, -1)
        
    def predict(self, sensor_id: str, value: float) -> Optional[AnomalyResult]:
        if sensor_id not in self.feature_buffer:
            self.feature_buffer[sensor_id] = []
            
        buffer = self.feature_buffer[sensor_id]
        buffer.append(value)
        
        if len(buffer) > 50:  # Keep rolling window
            buffer.pop(0)
            
        features = self.extract_features(sensor_id, buffer)
        if features is None:
            return None
            
        # Run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], features)
        self.interpreter.invoke()
        
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        anomaly_score = float(output[0][0])
        
        return AnomalyResult(
            sensor_id=sensor_id,
            timestamp=datetime.now(),
            anomaly_score=anomaly_score,
            is_anomaly=anomaly_score > 0.5,
            confidence=abs(anomaly_score - 0.5) * 2,
            method="ML_LITE"
        )

class EdgeAnalyticsEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.spc = StatisticalProcessControl()
        self.ml_detector = LightweightMLDetector(config['model_path'])
        self.influx_client = InfluxDBClient(
            url=config['influxdb_url'],
            token=config['influxdb_token'],
            org=config['influxdb_org']
        )
        self.redis_client = redis.Redis(
            host=config['redis_host'],
            port=config['redis_port'],
            decode_responses=True
        )
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=config['kafka_brokers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
    async def process_sensor_reading(self, reading: SensorReading):
        """Process individual sensor reading through analytics pipeline"""
        try:
            # Store in InfluxDB
            await self.store_reading(reading)
            
            # Run anomaly detection
            spc_result = self.spc.update(reading.sensor_id, reading.value)
            ml_result = self.ml_detector.predict(reading.sensor_id, reading.value)
            
            # Combine results
            anomaly_results = [r for r in [spc_result, ml_result] if r is not None]
            
            if anomaly_results:
                await self.handle_anomalies(reading, anomaly_results)
                
            # Update real-time cache
            await self.update_cache(reading)
            
        except Exception as e:
            logging.error(f"Error processing reading {reading.sensor_id}: {e}")
            
    async def store_reading(self, reading: SensorReading):
        """Store sensor reading in InfluxDB"""
        point = Point("sensor_data") \
            .tag("device_id", reading.device_id) \
            .tag("sensor_id", reading.sensor_id) \
            .tag("source", reading.source) \
            .field("value", reading.value) \
            .field("quality", reading.quality) \
            .time(reading.timestamp)
            
        write_api = self.influx_client.write_api()
        write_api.write(bucket=self.config['influxdb_bucket'], record=point)
        
    async def handle_anomalies(self, reading: SensorReading, anomalies: List[AnomalyResult]):
        """Handle detected anomalies"""
        for anomaly in anomalies:
            if anomaly.is_anomaly and anomaly.confidence > 0.7:
                alert = {
                    'device_id': reading.device_id,
                    'sensor_id': reading.sensor_id,
                    'timestamp': anomaly.timestamp.isoformat(),
                    'anomaly_score': anomaly.anomaly_score,
                    'confidence': anomaly.confidence,
                    'method': anomaly.method,
                    'value': reading.value,
                    'severity': self.calculate_severity(anomaly.anomaly_score)
                }
                
                # Send to Kafka for cloud processing
                self.kafka_producer.send('edge-alerts', alert)
                
                # Store in local cache for immediate access
                self.redis_client.setex(
                    f"alert:{reading.sensor_id}:{int(anomaly.timestamp.timestamp())}",
                    3600,  # 1 hour TTL
                    json.dumps(alert)
                )
                
    async def update_cache(self, reading: SensorReading):
        """Update Redis cache with latest readings"""
        cache_key = f"sensor:{reading.sensor_id}"
        
        # Store latest reading
        self.redis_client.hset(cache_key, mapping={
            'timestamp': reading.timestamp.isoformat(),
            'value': reading.value,
            'quality': reading.quality,
            'unit': reading.unit
        })
        
        # Store in time-series list (last 100 readings)
        ts_key = f"timeseries:{reading.sensor_id}"
        reading_data = {
            'timestamp': reading.timestamp.isoformat(),
            'value': reading.value
        }
        
        self.redis_client.lpush(ts_key, json.dumps(reading_data))
        self.redis_client.ltrim(ts_key, 0, 99)  # Keep only last 100
        
    def calculate_severity(self, anomaly_score: float) -> str:
        """Calculate alert severity based on anomaly score"""
        if anomaly_score >= 0.9:
            return "CRITICAL"
        elif anomaly_score >= 0.7:
            return "HIGH"
        elif anomaly_score >= 0.5:
            return "MEDIUM"
        else:
            return "LOW"
```

## 2. Cloud Data Platform Implementation

### 2.1 Database Schema Design
```sql
-- PostgreSQL Schema for IoT Predictive Maintenance Platform

-- Equipment and Asset Management
CREATE TABLE equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    equipment_type VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    installation_date DATE,
    location_id UUID REFERENCES locations(id),
    parent_equipment_id UUID REFERENCES equipment(id),
    criticality VARCHAR(20) DEFAULT 'MEDIUM' CHECK (criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE', 'RETIRED')),
    specifications JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_equipment_type ON equipment(equipment_type);
CREATE INDEX idx_equipment_location ON equipment(location_id);
CREATE INDEX idx_equipment_parent ON equipment(parent_equipment_id);

-- Sensor Configuration
CREATE TABLE sensors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_code VARCHAR(50) UNIQUE NOT NULL,
    equipment_id UUID NOT NULL REFERENCES equipment(id),
    sensor_type VARCHAR(50) NOT NULL,
    measurement_type VARCHAR(50) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    min_value DECIMAL(15,6),
    max_value DECIMAL(15,6),
    sampling_frequency INTEGER, -- Hz
    protocol VARCHAR(20) NOT NULL CHECK (protocol IN ('OPC_UA', 'MODBUS', 'MQTT', 'DNP3')),
    address_config JSONB NOT NULL,
    calibration_factor DECIMAL(10,6) DEFAULT 1.0,
    calibration_offset DECIMAL(10,6) DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE', 'FAULTY')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sensors_equipment ON sensors(equipment_id);
CREATE INDEX idx_sensors_type ON sensors(sensor_type, measurement_type);

-- Health Scores and Predictions
CREATE TABLE equipment_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES equipment(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    overall_health_score DECIMAL(5,2) NOT NULL CHECK (overall_health_score >= 0 AND overall_health_score <= 100),
    subsystem_scores JSONB,
    contributing_factors JSONB,
    trend_direction VARCHAR(20) CHECK (trend_direction IN ('IMPROVING', 'STABLE', 'DEGRADING')),
    confidence_level DECIMAL(3,2) CHECK (confidence_level >= 0 AND confidence_level <= 1),
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_health_equipment_time ON equipment_health(equipment_id, timestamp DESC);
CREATE INDEX idx_health_score ON equipment_health(overall_health_score);

-- Failure Predictions
CREATE TABLE failure_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES equipment(id),
    prediction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    failure_probability DECIMAL(3,2) NOT NULL CHECK (failure_probability >= 0 AND failure_probability <= 1),
    predicted_failure_time TIMESTAMP WITH TIME ZONE,
    remaining_useful_life_days INTEGER,
    failure_mode VARCHAR(100),
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    contributing_sensors JSONB,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_predictions_equipment_time ON failure_predictions(equipment_id, prediction_timestamp DESC);
CREATE INDEX idx_predictions_probability ON failure_predictions(failure_probability DESC);

-- Maintenance Work Orders
CREATE TABLE work_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_number VARCHAR(50) UNIQUE NOT NULL,
    equipment_id UUID NOT NULL REFERENCES equipment(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    work_type VARCHAR(50) NOT NULL CHECK (work_type IN ('PREVENTIVE', 'PREDICTIVE', 'CORRECTIVE', 'EMERGENCY')),
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    assigned_technician_id UUID REFERENCES users(id),
    scheduled_start TIMESTAMP WITH TIME ZONE,
    scheduled_end TIMESTAMP WITH TIME ZONE,
    actual_start TIMESTAMP WITH TIME ZONE,
    actual_end TIMESTAMP WITH TIME ZONE,
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    labor_cost DECIMAL(10,2),
    parts_cost DECIMAL(10,2),
    total_cost DECIMAL(10,2),
    failure_prediction_id UUID REFERENCES failure_predictions(id),
    cmms_work_order_id VARCHAR(100), -- External CMMS reference
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_work_orders_equipment ON work_orders(equipment_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_technician ON work_orders(assigned_technician_id);
CREATE INDEX idx_work_orders_scheduled ON work_orders(scheduled_start, scheduled_end);

-- Alerts and Notifications
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES equipment(id),
    sensor_id UUID REFERENCES sensors(id),
    alert_type VARCHAR(50) NOT NULL CHECK (alert_type IN ('ANOMALY', 'THRESHOLD', 'PREDICTION', 'SYSTEM')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    anomaly_score DECIMAL(3,2),
    confidence_level DECIMAL(3,2),
    detection_method VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'SUPPRESSED')),
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alerts_equipment ON alerts(equipment_id);
CREATE INDEX idx_alerts_status_severity ON alerts(status, severity);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
```

### 2.2 API Specifications
```yaml
# OpenAPI 3.0 Specification for IoT Predictive Maintenance Platform
openapi: 3.0.0
info:
  title: IoT Predictive Maintenance Platform API
  version: 1.0.0
  description: RESTful API for industrial predictive maintenance operations

paths:
  /api/v1/equipment:
    get:
      summary: List equipment with filtering and pagination
      parameters:
        - name: type
          in: query
          schema:
            type: string
        - name: location
          in: query
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
            enum: [ACTIVE, INACTIVE, MAINTENANCE, RETIRED]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        '200':
          description: Equipment list retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Equipment'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

  /api/v1/equipment/{equipmentId}/health:
    get:
      summary: Get equipment health score and trends
      parameters:
        - name: equipmentId
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: timeRange
          in: query
          schema:
            type: string
            enum: [1h, 24h, 7d, 30d]
            default: 24h
      responses:
        '200':
          description: Health data retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/EquipmentHealth'

  /api/v1/predictions:
    get:
      summary: Get failure predictions with filtering
      parameters:
        - name: equipmentId
          in: query
          schema:
            type: string
            format: uuid
        - name: minProbability
          in: query
          schema:
            type: number
            minimum: 0
            maximum: 1
        - name: timeHorizon
          in: query
          schema:
            type: string
            enum: [1d, 7d, 30d]
      responses:
        '200':
          description: Predictions retrieved successfully
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/FailurePrediction'

components:
  schemas:
    Equipment:
      type: object
      properties:
        id:
          type: string
          format: uuid
        equipmentCode:
          type: string
        name:
          type: string
        equipmentType:
          type: string
        manufacturer:
          type: string
        model:
          type: string
        serialNumber:
          type: string
        installationDate:
          type: string
          format: date
        criticality:
          type: string
          enum: [LOW, MEDIUM, HIGH, CRITICAL]
        status:
          type: string
          enum: [ACTIVE, INACTIVE, MAINTENANCE, RETIRED]
        currentHealthScore:
          type: number
          minimum: 0
          maximum: 100
        lastMaintenanceDate:
          type: string
          format: date-time

    EquipmentHealth:
      type: object
      properties:
        equipmentId:
          type: string
          format: uuid
        currentScore:
          type: number
          minimum: 0
          maximum: 100
        trend:
          type: string
          enum: [IMPROVING, STABLE, DEGRADING]
        subsystemScores:
          type: object
          additionalProperties:
            type: number
        historicalData:
          type: array
          items:
            type: object
            properties:
              timestamp:
                type: string
                format: date-time
              score:
                type: number
              confidence:
                type: number

    FailurePrediction:
      type: object
      properties:
        id:
          type: string
          format: uuid
        equipmentId:
          type: string
          format: uuid
        failureProbability:
          type: number
          minimum: 0
          maximum: 1
        predictedFailureTime:
          type: string
          format: date-time
        remainingUsefulLifeDays:
          type: integer
        failureMode:
          type: string
        confidenceScore:
          type: number
          minimum: 0
          maximum: 1
        contributingSensors:
          type: array
          items:
            type: string
```

This LLD provides comprehensive implementation-ready specifications that development teams can use to build the IoT predictive maintenance platform while maintaining full traceability to all previous requirements documents.
