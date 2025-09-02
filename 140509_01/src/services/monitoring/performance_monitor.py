#!/usr/bin/env python3
"""
Performance Monitoring and Logging Service
Implements NFR-003 (Performance Monitoring) and NFR-004 (Application Logging)
"""

import asyncio
import logging
import json
import time
import psutil
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
import redis
import threading
from collections import deque, defaultdict
import functools
import sys
import traceback
import os

# Configure logging with structured format
class StructuredLogger:
    """Structured logging with JSON format and multiple handlers."""
    
    def __init__(self, name: str, log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Create formatters
        json_formatter = logging.Formatter(
            json.dumps({
                'timestamp': '%(asctime)s',
                'level': '%(levelname)s',
                'logger': '%(name)s',
                'message': '%(message)s',
                'module': '%(module)s',
                'function': '%(funcName)s',
                'line': '%(lineno)d'
            })
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for structured logs
        try:
            os.makedirs('/tmp/retailai_logs', exist_ok=True)
            file_handler = logging.FileHandler('/tmp/retailai_logs/application.jsonl')
            file_handler.setFormatter(json_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")
    
    def info(self, message: str, **kwargs):
        self.logger.info(self._format_message(message, kwargs))
    
    def error(self, message: str, **kwargs):
        self.logger.error(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_message(message, kwargs))
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format_message(message, kwargs))
    
    def _format_message(self, message: str, kwargs: Dict) -> str:
        if kwargs:
            return f"{message} | {json.dumps(kwargs)}"
        return message

# Initialize structured logger
logger = StructuredLogger(__name__)

class MetricType(Enum):
    """Types of metrics to collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertLevel(Enum):
    """Performance alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    unit: str
    tags: Dict[str, str]
    timestamp: datetime
    service: str
    instance_id: str

@dataclass
class SystemMetrics:
    """System-level metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: List[float]
    processes_count: int
    timestamp: datetime

@dataclass
class ApplicationMetrics:
    """Application-level metrics."""
    requests_per_second: float
    average_response_time_ms: float
    error_rate_percent: float
    active_connections: int
    database_connections: int
    cache_hit_rate: float
    memory_usage_mb: float
    gc_collections: int
    timestamp: datetime

@dataclass
class PerformanceAlert:
    """Performance alert."""
    alert_id: str
    metric_name: str
    threshold_value: float
    actual_value: float
    level: AlertLevel
    message: str
    service: str
    timestamp: datetime
    resolved_at: Optional[datetime] = None

class PerformanceMonitor:
    """Production-ready performance monitoring and logging service."""
    
    def __init__(self, db_connection, redis_client=None, service_name: str = "retailai"):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.service_name = service_name
        self.instance_id = f"{service_name}_{secrets.token_hex(6)}"
        
        # Metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        # Store tuples of (timestamp, duration_seconds)
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent': {'warning': 70, 'critical': 90},
            'memory_percent': {'warning': 80, 'critical': 95},
            'disk_usage_percent': {'warning': 80, 'critical': 90},
            'response_time_ms': {'warning': 1000, 'critical': 5000},
            'error_rate_percent': {'warning': 5, 'critical': 10},
            'database_connections': {'warning': 80, 'critical': 95}
        }
        
        # Monitoring state
        self.monitoring_active = True
        self.last_system_check = datetime.now()
        self.active_alerts = {}
        
        # Initialize database schema
        self.init_database_schema()
        
        # Start monitoring threads
        self._start_monitoring_threads()
        
        logger.info("Performance monitoring initialized", 
                   service=service_name, instance_id=self.instance_id)
    
    def init_database_schema(self):
        """Initialize performance monitoring database schema."""
        
        try:
            cursor = self.db.cursor()
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    metric_type VARCHAR(20) NOT NULL,
                    value DECIMAL(15,4) NOT NULL,
                    unit VARCHAR(20),
                    tags JSONB DEFAULT '{}',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    service VARCHAR(50) NOT NULL,
                    instance_id VARCHAR(50) NOT NULL
                )
            """)
            
            # System metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id SERIAL PRIMARY KEY,
                    cpu_percent DECIMAL(5,2),
                    memory_percent DECIMAL(5,2),
                    memory_used_mb DECIMAL(10,2),
                    memory_available_mb DECIMAL(10,2),
                    disk_usage_percent DECIMAL(5,2),
                    disk_free_gb DECIMAL(10,2),
                    network_bytes_sent BIGINT,
                    network_bytes_recv BIGINT,
                    load_average DECIMAL[],
                    processes_count INTEGER,
                    service VARCHAR(50) NOT NULL,
                    instance_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Application metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS application_metrics (
                    id SERIAL PRIMARY KEY,
                    requests_per_second DECIMAL(10,2),
                    avg_response_time_ms DECIMAL(10,2),
                    error_rate_percent DECIMAL(5,2),
                    active_connections INTEGER,
                    database_connections INTEGER,
                    cache_hit_rate DECIMAL(5,2),
                    memory_usage_mb DECIMAL(10,2),
                    gc_collections INTEGER,
                    service VARCHAR(50) NOT NULL,
                    instance_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    alert_id VARCHAR(50) PRIMARY KEY,
                    metric_name VARCHAR(100) NOT NULL,
                    threshold_value DECIMAL(15,4),
                    actual_value DECIMAL(15,4),
                    level VARCHAR(20) NOT NULL,
                    message TEXT,
                    service VARCHAR(50) NOT NULL,
                    instance_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Log entries table for centralized logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_entries (
                    id SERIAL PRIMARY KEY,
                    level VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    logger_name VARCHAR(100),
                    module VARCHAR(100),
                    function VARCHAR(100),
                    line_number INTEGER,
                    service VARCHAR(50) NOT NULL,
                    instance_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}',
                    trace_id VARCHAR(50),
                    span_id VARCHAR(50)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp, service)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp, service)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_metrics_timestamp ON application_metrics(timestamp, service)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON performance_alerts(timestamp, is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON log_entries(timestamp, service, level)")
            
            self.db.commit()
            cursor.close()
            logger.info("Performance monitoring database schema initialized")
            
        except Exception as e:
            logger.error("Failed to initialize monitoring schema", error=str(e))
            raise
    
    def _start_monitoring_threads(self):
        """Start background monitoring threads."""
        
        # System metrics collector
        system_thread = threading.Thread(target=self._system_metrics_collector, daemon=True)
        system_thread.start()
        
        # Application metrics collector
        app_thread = threading.Thread(target=self._application_metrics_collector, daemon=True)
        app_thread.start()
        
        # Metrics processor
        processor_thread = threading.Thread(target=self._metrics_processor, daemon=True)
        processor_thread.start()
        
        # Alert processor
        alert_thread = threading.Thread(target=self._alert_processor, daemon=True)
        alert_thread.start()
        
        logger.info("Background monitoring threads started")
    
    def _system_metrics_collector(self):
        """Collect system-level metrics."""
        
        logger.info("System metrics collector started")
        
        while self.monitoring_active:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_mb = memory.used / (1024 * 1024)
                memory_available_mb = memory.available / (1024 * 1024)
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_usage_percent = (disk.used / disk.total) * 100
                disk_free_gb = disk.free / (1024 * 1024 * 1024)
                
                # Network metrics
                network = psutil.net_io_counters()
                network_bytes_sent = network.bytes_sent
                network_bytes_recv = network.bytes_recv
                
                # Load average
                load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
                
                # Process count
                processes_count = len(psutil.pids())
                
                # Create metrics object
                metrics = SystemMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    memory_used_mb=memory_used_mb,
                    memory_available_mb=memory_available_mb,
                    disk_usage_percent=disk_usage_percent,
                    disk_free_gb=disk_free_gb,
                    network_bytes_sent=network_bytes_sent,
                    network_bytes_recv=network_bytes_recv,
                    load_average=list(load_avg),
                    processes_count=processes_count,
                    timestamp=datetime.now()
                )
                
                # Store metrics
                self._store_system_metrics(metrics)
                
                # Cache in Redis for real-time access
                self.redis.setex(
                    f"system_metrics:{self.instance_id}",
                    300,  # 5 minutes TTL
                    json.dumps(asdict(metrics), default=str)
                )
                
                # Check for alerts
                self._check_system_alerts(metrics)
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error("System metrics collection error", error=str(e))
                time.sleep(60)  # Sleep longer on error
    
    def _application_metrics_collector(self):
        """Collect application-level metrics."""
        
        logger.info("Application metrics collector started")
        
        while self.monitoring_active:
            try:
                # Calculate request rate
                now = datetime.now()
                minute_ago = now - timedelta(minutes=1)
                # Filter requests within the last minute
                recent = [(ts, dur) for (ts, dur) in self.request_times if ts > minute_ago]
                requests_per_second = len(recent) / 60.0
                
                # Calculate average response time
                if recent:
                    avg_response_time = (sum(dur for (_, dur) in recent) / len(recent)) * 1000  # ms
                else:
                    avg_response_time = 0
                
                # Calculate error rate
                total_requests = len(self.request_times)
                total_errors = sum(self.error_counts.values())
                error_rate = (total_errors / max(total_requests, 1)) * 100
                
                # Get database connection count
                db_connections = self._get_database_connections()
                
                # Get cache hit rate from Redis
                cache_hit_rate = self._get_cache_hit_rate()
                
                # Get current process memory usage
                process = psutil.Process()
                memory_usage_mb = process.memory_info().rss / (1024 * 1024)
                
                # Create metrics object
                metrics = ApplicationMetrics(
                    requests_per_second=requests_per_second,
                    average_response_time_ms=avg_response_time,
                    error_rate_percent=error_rate,
                    active_connections=len(recent),  # Approximation
                    database_connections=db_connections,
                    cache_hit_rate=cache_hit_rate,
                    memory_usage_mb=memory_usage_mb,
                    gc_collections=0,  # Would need gc module for real collection count
                    timestamp=now
                )
                
                # Store metrics
                self._store_application_metrics(metrics)
                
                # Cache in Redis
                self.redis.setex(
                    f"app_metrics:{self.instance_id}",
                    300,  # 5 minutes TTL
                    json.dumps(asdict(metrics), default=str)
                )
                
                # Check for alerts
                self._check_application_alerts(metrics)
                
                # Clean old data
                self._cleanup_old_metrics()
                
                # Sleep for 60 seconds
                time.sleep(60)
                
            except Exception as e:
                logger.error("Application metrics collection error", error=str(e))
                time.sleep(60)
    
    def _store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO system_metrics 
                (cpu_percent, memory_percent, memory_used_mb, memory_available_mb,
                 disk_usage_percent, disk_free_gb, network_bytes_sent, network_bytes_recv,
                 load_average, processes_count, service, instance_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                metrics.cpu_percent, metrics.memory_percent, metrics.memory_used_mb,
                metrics.memory_available_mb, metrics.disk_usage_percent, metrics.disk_free_gb,
                metrics.network_bytes_sent, metrics.network_bytes_recv, metrics.load_average,
                metrics.processes_count, self.service_name, self.instance_id, metrics.timestamp
            ))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error("Failed to store system metrics", error=str(e))
    
    def _store_application_metrics(self, metrics: ApplicationMetrics):
        """Store application metrics in database."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO application_metrics 
                (requests_per_second, avg_response_time_ms, error_rate_percent,
                 active_connections, database_connections, cache_hit_rate,
                 memory_usage_mb, gc_collections, service, instance_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                metrics.requests_per_second, metrics.average_response_time_ms,
                metrics.error_rate_percent, metrics.active_connections,
                metrics.database_connections, metrics.cache_hit_rate,
                metrics.memory_usage_mb, metrics.gc_collections,
                self.service_name, self.instance_id, metrics.timestamp
            ))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error("Failed to store application metrics", error=str(e))
    
    def _get_database_connections(self) -> int:
        """Get current database connection count."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0
    
    def _get_cache_hit_rate(self) -> float:
        """Get Redis cache hit rate."""
        
        try:
            info = self.redis.info()
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            return (hits / max(total, 1)) * 100
        except Exception:
            return 0.0
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """Check system metrics against thresholds and create alerts."""
        
        checks = [
            ('cpu_percent', metrics.cpu_percent, '%'),
            ('memory_percent', metrics.memory_percent, '%'),
            ('disk_usage_percent', metrics.disk_usage_percent, '%')
        ]
        
        for metric_name, value, unit in checks:
            self._check_threshold(metric_name, value, unit)
    
    def _check_application_alerts(self, metrics: ApplicationMetrics):
        """Check application metrics against thresholds and create alerts."""
        
        checks = [
            ('response_time_ms', metrics.average_response_time_ms, 'ms'),
            ('error_rate_percent', metrics.error_rate_percent, '%'),
            ('database_connections', metrics.database_connections, 'connections')
        ]
        
        for metric_name, value, unit in checks:
            self._check_threshold(metric_name, value, unit)
    
    def _check_threshold(self, metric_name: str, value: float, unit: str):
        """Check metric value against thresholds and create alerts if needed."""
        
        if metric_name not in self.thresholds:
            return
        
        thresholds = self.thresholds[metric_name]
        alert_level = None
        threshold_value = None
        
        if value >= thresholds.get('critical', float('inf')):
            alert_level = AlertLevel.CRITICAL
            threshold_value = thresholds['critical']
        elif value >= thresholds.get('warning', float('inf')):
            alert_level = AlertLevel.WARNING
            threshold_value = thresholds['warning']
        
        if alert_level:
            # Create alert if not already active
            alert_key = f"{metric_name}_{alert_level.value}"
            if alert_key not in self.active_alerts:
                alert = PerformanceAlert(
                    alert_id=f"alert_{int(time.time())}_{secrets.token_hex(6)}",
                    metric_name=metric_name,
                    threshold_value=threshold_value,
                    actual_value=value,
                    level=alert_level,
                    message=f"{metric_name} is {value}{unit}, exceeding {alert_level.value} threshold of {threshold_value}{unit}",
                    service=self.service_name,
                    timestamp=datetime.now()
                )
                
                self._store_alert(alert)
                self.active_alerts[alert_key] = alert
                
                logger.warning("Performance alert triggered", 
                             metric=metric_name, value=value, threshold=threshold_value, 
                             level=alert_level.value)
        else:
            # Resolve alert if it was active
            for alert_key in list(self.active_alerts.keys()):
                if alert_key.startswith(f"{metric_name}_"):
                    alert = self.active_alerts.pop(alert_key)
                    self._resolve_alert(alert.alert_id)
                    logger.info("Performance alert resolved", 
                              metric=metric_name, value=value)
    
    def _store_alert(self, alert: PerformanceAlert):
        """Store performance alert in database."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO performance_alerts 
                (alert_id, metric_name, threshold_value, actual_value, level, 
                 message, service, instance_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert.alert_id, alert.metric_name, alert.threshold_value,
                alert.actual_value, alert.level.value, alert.message,
                alert.service, self.instance_id, alert.timestamp
            ))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error("Failed to store performance alert", error=str(e))
    
    def _resolve_alert(self, alert_id: str):
        """Mark alert as resolved."""
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE performance_alerts 
                SET resolved_at = %s, is_active = FALSE
                WHERE alert_id = %s
            """, (datetime.now(), alert_id))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
    
    def _metrics_processor(self):
        """Process queued metrics."""
        
        logger.info("Metrics processor started")
        
        while self.monitoring_active:
            try:
                # Process buffered metrics
                if self.metrics_buffer:
                    metrics_to_process = []
                    while self.metrics_buffer and len(metrics_to_process) < 100:
                        metrics_to_process.append(self.metrics_buffer.popleft())
                    
                    if metrics_to_process:
                        self._batch_store_metrics(metrics_to_process)
                
                time.sleep(10)
                
            except Exception as e:
                logger.error("Metrics processor error", error=str(e))
                time.sleep(30)
    
    def _alert_processor(self):
        """Process and manage alerts."""
        
        logger.info("Alert processor started")
        
        while self.monitoring_active:
            try:
                # Auto-resolve old alerts that are no longer triggered
                cursor = self.db.cursor()
                cursor.execute("""
                    UPDATE performance_alerts 
                    SET resolved_at = %s, is_active = FALSE
                    WHERE is_active = TRUE AND timestamp < %s
                """, (datetime.now(), datetime.now() - timedelta(hours=1)))
                
                resolved_count = cursor.rowcount
                if resolved_count > 0:
                    logger.info("Auto-resolved old alerts", count=resolved_count)
                
                self.db.commit()
                cursor.close()
                
                time.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error("Alert processor error", error=str(e))
                time.sleep(300)
    
    def _batch_store_metrics(self, metrics_list: List[PerformanceMetric]):
        """Store multiple metrics in batch."""
        
        try:
            cursor = self.db.cursor()
            
            for metric in metrics_list:
                cursor.execute("""
                    INSERT INTO performance_metrics 
                    (metric_id, name, metric_type, value, unit, tags, timestamp, service, instance_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    metric.metric_id, metric.name, metric.metric_type.value,
                    metric.value, metric.unit, json.dumps(metric.tags),
                    metric.timestamp, metric.service, metric.instance_id
                ))
            
            self.db.commit()
            cursor.close()
            
            logger.debug("Batch stored metrics", count=len(metrics_list))
            
        except Exception as e:
            logger.error("Failed to batch store metrics", error=str(e))
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics data."""
        
        try:
            # Clean data older than 7 days for detailed metrics
            cutoff_date = datetime.now() - timedelta(days=7)
            
            cursor = self.db.cursor()
            
            # Clean old performance metrics
            cursor.execute("DELETE FROM performance_metrics WHERE timestamp < %s", (cutoff_date,))
            
            # Clean old system metrics (keep for 30 days)
            system_cutoff = datetime.now() - timedelta(days=30)
            cursor.execute("DELETE FROM system_metrics WHERE timestamp < %s", (system_cutoff,))
            
            # Clean old application metrics (keep for 30 days)
            cursor.execute("DELETE FROM application_metrics WHERE timestamp < %s", (system_cutoff,))
            
            # Clean resolved alerts older than 90 days
            alert_cutoff = datetime.now() - timedelta(days=90)
            cursor.execute("""
                DELETE FROM performance_alerts 
                WHERE resolved_at IS NOT NULL AND resolved_at < %s
            """, (alert_cutoff,))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error("Failed to cleanup old metrics", error=str(e))
    
    def record_request(self, duration_seconds: float, endpoint: str = None, status_code: int = None):
        """Record API request performance."""
        
        # Append (timestamp, duration)
        self.request_times.append((datetime.now(), duration_seconds))
        
        # Track errors
        if status_code and status_code >= 400:
            self.error_counts[status_code] += 1
        
        # Create custom metric
        metric = PerformanceMetric(
            metric_id=f"req_{int(time.time())}_{secrets.token_hex(4)}",
            name="request_duration",
            metric_type=MetricType.TIMER,
            value=duration_seconds * 1000,  # Convert to ms
            unit="ms",
            tags={"endpoint": endpoint or "unknown", "status": str(status_code or 200)},
            timestamp=datetime.now(),
            service=self.service_name,
            instance_id=self.instance_id
        )
        
        self.metrics_buffer.append(metric)
    
    def record_custom_metric(self, name: str, value: float, unit: str = "", 
                           tags: Dict[str, str] = None, metric_type: MetricType = MetricType.GAUGE):
        """Record custom metric."""
        
        metric = PerformanceMetric(
            metric_id=f"custom_{int(time.time())}_{secrets.token_hex(4)}",
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {},
            timestamp=datetime.now(),
            service=self.service_name,
            instance_id=self.instance_id
        )
        
        self.metrics_buffer.append(metric)
        logger.debug("Custom metric recorded", name=name, value=value)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        
        try:
            # Get cached metrics from Redis
            system_metrics = self.redis.get(f"system_metrics:{self.instance_id}")
            app_metrics = self.redis.get(f"app_metrics:{self.instance_id}")
            
            result = {
                "service": self.service_name,
                "instance_id": self.instance_id,
                "timestamp": datetime.now().isoformat(),
                "system_metrics": json.loads(system_metrics.decode()) if system_metrics else None,
                "application_metrics": json.loads(app_metrics.decode()) if app_metrics else None,
                "active_alerts": len(self.active_alerts),
                "buffer_size": len(self.metrics_buffer)
            }
            
            return result
            
        except Exception as e:
            logger.error("Failed to get current metrics", error=str(e))
            return {"error": str(e)}
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for specified time period."""
        
        try:
            cursor = self.db.cursor()
            start_time = datetime.now() - timedelta(hours=hours)
            
            # System metrics summary
            cursor.execute("""
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(memory_percent) as max_memory,
                    AVG(disk_usage_percent) as avg_disk,
                    MAX(disk_usage_percent) as max_disk
                FROM system_metrics
                WHERE timestamp >= %s AND service = %s
            """, (start_time, self.service_name))
            
            system_summary = cursor.fetchone()
            
            # Application metrics summary
            cursor.execute("""
                SELECT 
                    AVG(requests_per_second) as avg_rps,
                    MAX(requests_per_second) as max_rps,
                    AVG(avg_response_time_ms) as avg_response_time,
                    MAX(avg_response_time_ms) as max_response_time,
                    AVG(error_rate_percent) as avg_error_rate,
                    MAX(error_rate_percent) as max_error_rate
                FROM application_metrics
                WHERE timestamp >= %s AND service = %s
            """, (start_time, self.service_name))
            
            app_summary = cursor.fetchone()
            
            # Alert counts
            cursor.execute("""
                SELECT level, COUNT(*) as count
                FROM performance_alerts
                WHERE timestamp >= %s AND service = %s
                GROUP BY level
            """, (start_time, self.service_name))
            
            alert_counts = dict(cursor.fetchall())
            
            cursor.close()
            
            return {
                "period_hours": hours,
                "system_summary": {
                    "avg_cpu_percent": float(system_summary[0] or 0),
                    "max_cpu_percent": float(system_summary[1] or 0),
                    "avg_memory_percent": float(system_summary[2] or 0),
                    "max_memory_percent": float(system_summary[3] or 0),
                    "avg_disk_percent": float(system_summary[4] or 0),
                    "max_disk_percent": float(system_summary[5] or 0)
                },
                "application_summary": {
                    "avg_requests_per_second": float(app_summary[0] or 0),
                    "max_requests_per_second": float(app_summary[1] or 0),
                    "avg_response_time_ms": float(app_summary[2] or 0),
                    "max_response_time_ms": float(app_summary[3] or 0),
                    "avg_error_rate_percent": float(app_summary[4] or 0),
                    "max_error_rate_percent": float(app_summary[5] or 0)
                },
                "alert_counts": alert_counts,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get performance summary", error=str(e))
            return {"error": str(e)}
    
    def stop_monitoring(self):
        """Stop all monitoring activities."""
        
        self.monitoring_active = False
        logger.info("Performance monitoring stopped")

# Decorators for automatic performance tracking
def track_performance(monitor: PerformanceMonitor):
    """Decorator to track function performance."""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.record_custom_metric(
                    name=f"function_duration_{func.__name__}",
                    value=duration * 1000,  # ms
                    unit="ms",
                    metric_type=MetricType.TIMER
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.record_custom_metric(
                    name=f"function_error_{func.__name__}",
                    value=1,
                    metric_type=MetricType.COUNTER,
                    tags={"error": str(e)[:100]}
                )
                raise
        return wrapper
    return decorator

def track_async_performance(monitor: PerformanceMonitor):
    """Decorator to track async function performance."""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.record_custom_metric(
                    name=f"async_function_duration_{func.__name__}",
                    value=duration * 1000,  # ms
                    unit="ms",
                    metric_type=MetricType.TIMER
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.record_custom_metric(
                    name=f"async_function_error_{func.__name__}",
                    value=1,
                    metric_type=MetricType.COUNTER,
                    tags={"error": str(e)[:100]}
                )
                raise
        return wrapper
    return decorator

# Example usage and testing
if __name__ == "__main__":
    # Database connection
    db_conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='retailai',
        user='retailai',
        password='retailai123'
    )
    
    # Initialize performance monitor
    monitor = PerformanceMonitor(db_conn, service_name="test_service")
    
    # Test performance tracking
    @track_performance(monitor)
    def test_function():
        time.sleep(0.1)
        return "test result"
    
    print("🔍 Testing Performance Monitor...")
    
    # Record some metrics
    for i in range(10):
        monitor.record_request(0.05 + (i * 0.01), f"/api/test/{i}", 200 if i < 8 else 500)
        time.sleep(0.1)
    
    # Test function performance tracking
    result = test_function()
    print(f"Function result: {result}")
    
    # Record custom metrics
    monitor.record_custom_metric("test_counter", 42, "items", {"category": "test"})
    monitor.record_custom_metric("test_gauge", 85.5, "%", {"metric": "usage"})
    
    # Get current metrics
    current_metrics = monitor.get_current_metrics()
    print(f"Current metrics: {json.dumps(current_metrics, indent=2, default=str)}")
    
    # Wait a moment for metrics to be processed
    time.sleep(5)
    
    # Get performance summary
    summary = monitor.get_performance_summary(hours=1)
    print(f"Performance summary: {json.dumps(summary, indent=2, default=str)}")
    
    print("🔍 Performance monitoring testing complete!")
    
    # Stop monitoring
    monitor.stop_monitoring()
