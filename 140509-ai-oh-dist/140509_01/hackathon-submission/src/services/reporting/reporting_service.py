#!/usr/bin/env python3
"""
Automated Reporting and Audit Trails Service
Implements FR-022 (Automated Reporting) and NFR-009 (Audit Trails)
"""

import asyncio
import logging
import json
import secrets
import smtplib
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import psycopg2
import redis
import pandas as pd
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from jinja2 import Template
import io
import base64
from threading import Thread
import pickle
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportType(Enum):
    """Report types."""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_BUSINESS_REVIEW = "weekly_business_review"
    MONTHLY_EXECUTIVE = "monthly_executive"
    INVENTORY_ANALYSIS = "inventory_analysis"
    SALES_PERFORMANCE = "sales_performance"
    ML_MODEL_PERFORMANCE = "ml_model_performance"
    ALERT_SUMMARY = "alert_summary"
    AUDIT_COMPLIANCE = "audit_compliance"

class ReportFormat(Enum):
    """Report output formats."""
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"

class ReportFrequency(Enum):
    """Report scheduling frequencies."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ON_DEMAND = "on_demand"

@dataclass
class ReportSchedule:
    """Report scheduling configuration."""
    schedule_id: str
    report_type: ReportType
    frequency: ReportFrequency
    recipients: List[str]
    format: ReportFormat
    filters: Dict[str, Any]
    is_active: bool
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

@dataclass
class ReportExecution:
    """Report execution record."""
    execution_id: str
    schedule_id: str
    report_type: ReportType
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # pending, running, completed, failed
    output_path: Optional[str]
    error_message: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class AuditTrail:
    """Comprehensive audit trail entry."""
    audit_id: str
    user_id: str
    session_id: Optional[str]
    entity_type: str  # user, inventory, sale, alert, etc.
    entity_id: str
    action: str  # CREATE, READ, UPDATE, DELETE, EXECUTE
    changes: Dict[str, Any]  # before/after values
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool
    error_details: Optional[Dict[str, Any]]
    compliance_tags: List[str]  # GDPR, SOX, HIPAA, etc.

class ReportingService:
    """Production-ready automated reporting and audit service."""
    
    def __init__(self, db_connection, redis_client=None, smtp_config=None):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.smtp_config = smtp_config or {
            'host': 'localhost',
            'port': 587,
            'username': 'reports@retailai.com',
            'password': 'smtp_password',
            'use_tls': True
        }
        
        # Report storage
        self.reports_directory = "/tmp/retailai_reports"
        os.makedirs(self.reports_directory, exist_ok=True)
        
        # Plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Initialize database schema
        self.init_database_schema()
        
        # Start background scheduler
        self.scheduler_running = True
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Reporting service initialized")
    
    def init_database_schema(self):
        """Initialize reporting and audit database schema."""
        
        try:
            cursor = self.db.cursor()
            
            # Report schedules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_schedules (
                    schedule_id VARCHAR(50) PRIMARY KEY,
                    report_type VARCHAR(50) NOT NULL,
                    frequency VARCHAR(20) NOT NULL,
                    recipients TEXT[] NOT NULL,
                    format VARCHAR(20) NOT NULL,
                    filters JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    created_by VARCHAR(50)
                )
            """)
            
            # Report executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_executions (
                    execution_id VARCHAR(50) PRIMARY KEY,
                    schedule_id VARCHAR(50) REFERENCES report_schedules(schedule_id),
                    report_type VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    output_path TEXT,
                    error_message TEXT,
                    metadata JSONB DEFAULT '{}',
                    file_size_mb DECIMAL(10,2)
                )
            """)
            
            # Comprehensive audit trails table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trails (
                    audit_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(50),
                    session_id VARCHAR(100),
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(100) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    changes JSONB,
                    ip_address INET,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_details JSONB,
                    compliance_tags TEXT[] DEFAULT '{}',
                    retention_until DATE
                )
            """)
            
            # Data lineage tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_lineage (
                    lineage_id VARCHAR(50) PRIMARY KEY,
                    source_entity VARCHAR(50) NOT NULL,
                    source_id VARCHAR(100) NOT NULL,
                    target_entity VARCHAR(50) NOT NULL,
                    target_id VARCHAR(100) NOT NULL,
                    transformation VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_trails_timestamp ON audit_trails(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_trails_user_id ON audit_trails(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_trails_entity ON audit_trails(entity_type, entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_report_executions_status ON report_executions(status)")
            
            self.db.commit()
            cursor.close()
            logger.info("✅ Reporting database schema initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize reporting schema: {e}")
            raise
    
    async def create_report_schedule(self, report_type: ReportType, frequency: ReportFrequency,
                                   recipients: List[str], format: ReportFormat, 
                                   filters: Dict[str, Any] = None, user_id: str = None) -> str:
        """Create a new report schedule."""
        
        try:
            schedule_id = f"schedule_{int(datetime.now().timestamp())}_{secrets.token_hex(8)}"
            
            # Calculate next run time
            next_run = self._calculate_next_run(frequency)
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO report_schedules 
                (schedule_id, report_type, frequency, recipients, format, filters, next_run, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                schedule_id, report_type.value, frequency.value, recipients,
                format.value, json.dumps(filters or {}), next_run, user_id
            ))
            
            self.db.commit()
            cursor.close()
            
            # Log audit trail
            await self.log_audit_trail(
                user_id=user_id or "system",
                entity_type="report_schedule",
                entity_id=schedule_id,
                action="CREATE",
                changes={"report_type": report_type.value, "frequency": frequency.value},
                ip_address="127.0.0.1"
            )
            
            logger.info(f"✅ Report schedule created: {schedule_id}")
            return schedule_id
            
        except Exception as e:
            logger.error(f"Failed to create report schedule: {e}")
            raise
    
    async def generate_report(self, report_type: ReportType, format: ReportFormat, 
                            filters: Dict[str, Any] = None, schedule_id: str = None) -> str:
        """Generate a report on-demand or scheduled."""
        
        execution_id = f"exec_{int(datetime.now().timestamp())}_{secrets.token_hex(8)}"
        
        try:
            # Create execution record
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO report_executions 
                (execution_id, schedule_id, report_type, status)
                VALUES (%s, %s, %s, 'running')
            """, (execution_id, schedule_id, report_type.value))
            self.db.commit()
            cursor.close()
            
            # Generate report based on type
            if report_type == ReportType.DAILY_SUMMARY:
                report_data = await self._generate_daily_summary(filters)
            elif report_type == ReportType.WEEKLY_BUSINESS_REVIEW:
                report_data = await self._generate_weekly_business_review(filters)
            elif report_type == ReportType.MONTHLY_EXECUTIVE:
                report_data = await self._generate_monthly_executive(filters)
            elif report_type == ReportType.INVENTORY_ANALYSIS:
                report_data = await self._generate_inventory_analysis(filters)
            elif report_type == ReportType.SALES_PERFORMANCE:
                report_data = await self._generate_sales_performance(filters)
            elif report_type == ReportType.ML_MODEL_PERFORMANCE:
                report_data = await self._generate_ml_performance(filters)
            elif report_type == ReportType.ALERT_SUMMARY:
                report_data = await self._generate_alert_summary(filters)
            elif report_type == ReportType.AUDIT_COMPLIANCE:
                report_data = await self._generate_audit_compliance(filters)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            # Format and save report
            output_path = await self._format_and_save_report(
                report_data, report_type, format, execution_id
            )
            
            # Update execution record
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE report_executions 
                SET completed_at = %s, status = 'completed', output_path = %s, file_size_mb = %s
                WHERE execution_id = %s
            """, (datetime.now(), output_path, file_size, execution_id))
            self.db.commit()
            cursor.close()
            
            logger.info(f"✅ Report generated: {execution_id} ({file_size:.2f} MB)")
            return output_path
            
        except Exception as e:
            # Update execution with error
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE report_executions 
                SET completed_at = %s, status = 'failed', error_message = %s
                WHERE execution_id = %s
            """, (datetime.now(), str(e), execution_id))
            self.db.commit()
            cursor.close()
            
            logger.error(f"Report generation failed for {execution_id}: {e}")
            raise
    
    async def _generate_daily_summary(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate daily summary report."""
        
        try:
            cursor = self.db.cursor()
            yesterday = datetime.now() - timedelta(days=1)
            
            # Sales metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as transaction_count,
                    SUM(total_amount) as total_revenue,
                    AVG(total_amount) as avg_transaction_value,
                    COUNT(DISTINCT customer_id) as unique_customers
                FROM sales_transactions 
                WHERE transaction_date >= %s AND transaction_date < %s
            """, (yesterday.date(), datetime.now().date()))
            
            sales_data = cursor.fetchone()
            
            # Top products
            cursor.execute("""
                SELECT p.product_name, SUM(st.quantity) as units_sold, SUM(st.total_amount) as revenue
                FROM sales_transactions st
                JOIN products p ON st.product_id = p.product_id
                WHERE st.transaction_date >= %s AND st.transaction_date < %s
                GROUP BY p.product_id, p.product_name
                ORDER BY revenue DESC
                LIMIT 10
            """, (yesterday.date(), datetime.now().date()))
            
            top_products = cursor.fetchall()
            
            # Store performance
            cursor.execute("""
                SELECT s.name, s.city, COUNT(*) as transactions, SUM(st.total_amount) as revenue
                FROM sales_transactions st
                JOIN stores s ON st.store_id = s.id
                WHERE st.transaction_date >= %s AND st.transaction_date < %s
                GROUP BY s.id, s.name, s.city
                ORDER BY revenue DESC
                LIMIT 5
            """, (yesterday.date(), datetime.now().date()))
            
            top_stores = cursor.fetchall()
            
            # Alert summary
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM alerts
                WHERE created_at >= %s AND created_at < %s
                GROUP BY severity
            """, (yesterday, datetime.now()))
            
            alerts_summary = dict(cursor.fetchall())
            
            cursor.close()
            
            return {
                'report_date': yesterday.strftime('%Y-%m-%d'),
                'sales_summary': {
                    'transaction_count': sales_data[0] or 0,
                    'total_revenue': float(sales_data[1] or 0),
                    'avg_transaction_value': float(sales_data[2] or 0),
                    'unique_customers': sales_data[3] or 0
                },
                'top_products': [
                    {'name': name, 'units_sold': units, 'revenue': float(revenue)}
                    for name, units, revenue in top_products
                ],
                'top_stores': [
                    {'name': name, 'city': city, 'transactions': trans, 'revenue': float(revenue)}
                    for name, city, trans, revenue in top_stores
                ],
                'alerts_summary': alerts_summary,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {e}")
            raise
    
    async def _generate_weekly_business_review(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate weekly business review report."""
        
        try:
            cursor = self.db.cursor()
            week_start = datetime.now() - timedelta(days=7)
            
            # Weekly trends
            cursor.execute("""
                SELECT 
                    DATE(transaction_date) as date,
                    COUNT(*) as transactions,
                    SUM(total_amount) as revenue
                FROM sales_transactions
                WHERE transaction_date >= %s
                GROUP BY DATE(transaction_date)
                ORDER BY date
            """, (week_start,))
            
            daily_trends = [
                {
                    'date': date.strftime('%Y-%m-%d'),
                    'transactions': trans,
                    'revenue': float(revenue)
                }
                for date, trans, revenue in cursor.fetchall()
            ]
            
            # Category performance
            cursor.execute("""
                SELECT 
                    p.category,
                    COUNT(*) as transactions,
                    SUM(st.total_amount) as revenue,
                    SUM(st.quantity) as units_sold
                FROM sales_transactions st
                JOIN products p ON st.product_id = p.product_id
                WHERE st.transaction_date >= %s
                GROUP BY p.category
                ORDER BY revenue DESC
            """, (week_start,))
            
            category_performance = [
                {
                    'category': cat,
                    'transactions': trans,
                    'revenue': float(revenue),
                    'units_sold': units
                }
                for cat, trans, revenue, units in cursor.fetchall()
            ]
            
            # Inventory alerts
            cursor.execute("""
                SELECT alert_type, severity, COUNT(*) as count
                FROM alerts
                WHERE created_at >= %s AND alert_type IN ('LOW_STOCK', 'OUT_OF_STOCK', 'OVERSTOCK')
                GROUP BY alert_type, severity
                ORDER BY count DESC
            """, (week_start,))
            
            inventory_alerts = [
                {'type': alert_type, 'severity': severity, 'count': count}
                for alert_type, severity, count in cursor.fetchall()
            ]
            
            cursor.close()
            
            return {
                'week_start': week_start.strftime('%Y-%m-%d'),
                'week_end': datetime.now().strftime('%Y-%m-%d'),
                'daily_trends': daily_trends,
                'category_performance': category_performance,
                'inventory_alerts': inventory_alerts,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate weekly business review: {e}")
            raise
    
    async def _generate_monthly_executive(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monthly executive report."""
        
        try:
            cursor = self.db.cursor()
            month_start = datetime.now().replace(day=1)
            
            # Executive KPIs
            cursor.execute("""
                SELECT 
                    SUM(total_amount) as monthly_revenue,
                    COUNT(*) as total_transactions,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    COUNT(DISTINCT store_id) as active_stores
                FROM sales_transactions
                WHERE transaction_date >= %s
            """, (month_start,))
            
            kpis = cursor.fetchone()
            
            # ML model performance
            cursor.execute("""
                SELECT 
                    model_name,
                    AVG(accuracy) as avg_accuracy,
                    AVG(mae) as avg_mae,
                    COUNT(*) as predictions_count
                FROM ml_model_predictions
                WHERE created_at >= %s
                GROUP BY model_name
            """, (month_start,))
            
            ml_performance = [
                {
                    'model': model,
                    'accuracy': float(acc or 0),
                    'mae': float(mae or 0),
                    'predictions': count
                }
                for model, acc, mae, count in cursor.fetchall()
            ]
            
            # Cost savings from optimization
            cursor.execute("""
                SELECT 
                    SUM(estimated_savings) as total_savings,
                    COUNT(*) as optimization_actions
                FROM inventory_optimizations
                WHERE created_at >= %s AND status = 'applied'
            """, (month_start,))
            
            cost_savings = cursor.fetchone()
            
            cursor.close()
            
            return {
                'month': month_start.strftime('%B %Y'),
                'executive_kpis': {
                    'monthly_revenue': float(kpis[0] or 0),
                    'total_transactions': kpis[1] or 0,
                    'unique_customers': kpis[2] or 0,
                    'active_stores': kpis[3] or 0
                },
                'ml_performance': ml_performance,
                'cost_optimization': {
                    'total_savings': float(cost_savings[0] or 0),
                    'optimization_actions': cost_savings[1] or 0
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate monthly executive report: {e}")
            raise
    
    async def _generate_audit_compliance(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate audit compliance report."""
        
        try:
            cursor = self.db.cursor()
            period_start = datetime.now() - timedelta(days=30)
            
            # User activity summary
            cursor.execute("""
                SELECT 
                    user_id,
                    COUNT(*) as total_actions,
                    COUNT(CASE WHEN success = false THEN 1 END) as failed_actions,
                    array_agg(DISTINCT action) as action_types
                FROM audit_trails
                WHERE timestamp >= %s
                GROUP BY user_id
                ORDER BY total_actions DESC
            """, (period_start,))
            
            user_activity = [
                {
                    'user_id': user_id,
                    'total_actions': total,
                    'failed_actions': failed,
                    'action_types': list(set(actions))
                }
                for user_id, total, failed, actions in cursor.fetchall()
            ]
            
            # Data access patterns
            cursor.execute("""
                SELECT 
                    entity_type,
                    action,
                    COUNT(*) as frequency,
                    COUNT(DISTINCT user_id) as unique_users
                FROM audit_trails
                WHERE timestamp >= %s
                GROUP BY entity_type, action
                ORDER BY frequency DESC
            """, (period_start,))
            
            access_patterns = [
                {
                    'entity_type': entity,
                    'action': action,
                    'frequency': freq,
                    'unique_users': users
                }
                for entity, action, freq, users in cursor.fetchall()
            ]
            
            # Compliance violations
            cursor.execute("""
                SELECT 
                    compliance_tags,
                    COUNT(*) as violation_count,
                    array_agg(DISTINCT user_id) as involved_users
                FROM audit_trails
                WHERE timestamp >= %s AND success = false 
                AND array_length(compliance_tags, 1) > 0
                GROUP BY compliance_tags
            """, (period_start,))
            
            compliance_violations = [
                {
                    'compliance_tags': tags,
                    'violation_count': count,
                    'involved_users': list(set(users))
                }
                for tags, count, users in cursor.fetchall()
            ]
            
            cursor.close()
            
            return {
                'period_start': period_start.strftime('%Y-%m-%d'),
                'period_end': datetime.now().strftime('%Y-%m-%d'),
                'user_activity': user_activity,
                'access_patterns': access_patterns,
                'compliance_violations': compliance_violations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate audit compliance report: {e}")
            raise
    
    async def _format_and_save_report(self, report_data: Dict[str, Any], 
                                    report_type: ReportType, format: ReportFormat, 
                                    execution_id: str) -> str:
        """Format and save report to file."""
        
        try:
            filename = f"{report_type.value}_{execution_id}.{format.value}"
            output_path = os.path.join(self.reports_directory, filename)
            
            if format == ReportFormat.JSON:
                with open(output_path, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
                    
            elif format == ReportFormat.CSV:
                # Convert to DataFrame and save as CSV
                df = pd.json_normalize(report_data)
                df.to_csv(output_path, index=False)
                
            elif format == ReportFormat.HTML:
                html_content = self._generate_html_report(report_data, report_type)
                with open(output_path, 'w') as f:
                    f.write(html_content)
                    
            elif format == ReportFormat.EXCEL:
                # Create Excel with multiple sheets
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    for key, value in report_data.items():
                        if isinstance(value, list) and value:
                            df = pd.DataFrame(value)
                            df.to_excel(writer, sheet_name=key[:31], index=False)
            
            logger.info(f"✅ Report saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to format and save report: {e}")
            raise
    
    def _generate_html_report(self, data: Dict[str, Any], report_type: ReportType) -> str:
        """Generate HTML report with charts."""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ report_title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #667eea; color: white; padding: 20px; border-radius: 8px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .kpi { display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 5px; min-width: 150px; text-align: center; }
                .kpi-value { font-size: 2em; font-weight: bold; color: #667eea; }
                .kpi-label { color: #666; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background: #f8f9fa; }
                .chart { text-align: center; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ report_title }}</h1>
                <p>Generated on {{ generated_at }}</p>
            </div>
            
            {% if sales_summary %}
            <div class="section">
                <h2>📊 Sales Summary</h2>
                <div class="kpi">
                    <div class="kpi-value">${{ "%.2f"|format(sales_summary.total_revenue) }}</div>
                    <div class="kpi-label">Total Revenue</div>
                </div>
                <div class="kpi">
                    <div class="kpi-value">{{ sales_summary.transaction_count }}</div>
                    <div class="kpi-label">Transactions</div>
                </div>
                <div class="kpi">
                    <div class="kpi-value">${{ "%.2f"|format(sales_summary.avg_transaction_value) }}</div>
                    <div class="kpi-label">Avg Transaction</div>
                </div>
            </div>
            {% endif %}
            
            {% if top_products %}
            <div class="section">
                <h2>🏆 Top Products</h2>
                <table>
                    <tr><th>Product</th><th>Units Sold</th><th>Revenue</th></tr>
                    {% for product in top_products %}
                    <tr>
                        <td>{{ product.name }}</td>
                        <td>{{ product.units_sold }}</td>
                        <td>${{ "%.2f"|format(product.revenue) }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}
            
            {% if alerts_summary %}
            <div class="section">
                <h2>🚨 Alert Summary</h2>
                {% for severity, count in alerts_summary.items() %}
                <div class="kpi">
                    <div class="kpi-value">{{ count }}</div>
                    <div class="kpi-label">{{ severity|title }} Alerts</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
        </body>
        </html>
        """
        
        template = Template(html_template)
        return template.render(
            report_title=f"{report_type.value.replace('_', ' ').title()} Report",
            generated_at=data.get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            **data
        )
    
    async def log_audit_trail(self, user_id: str, entity_type: str, entity_id: str, 
                            action: str, changes: Dict[str, Any] = None, 
                            ip_address: str = "127.0.0.1", session_id: str = None,
                            user_agent: str = "System", success: bool = True,
                            error_details: Dict[str, Any] = None,
                            compliance_tags: List[str] = None) -> str:
        """Log comprehensive audit trail."""
        
        try:
            audit_id = f"audit_{int(datetime.now().timestamp())}_{secrets.token_hex(8)}"
            
            # Calculate retention period based on compliance requirements
            retention_until = datetime.now().date() + timedelta(days=2555)  # 7 years default
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO audit_trails 
                (audit_id, user_id, session_id, entity_type, entity_id, action, changes,
                 ip_address, user_agent, success, error_details, compliance_tags, retention_until)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                audit_id, user_id, session_id, entity_type, entity_id, action,
                json.dumps(changes or {}), ip_address, user_agent, success,
                json.dumps(error_details or {}), compliance_tags or [], retention_until
            ))
            
            self.db.commit()
            cursor.close()
            
            # Cache recent audit entries for quick access
            cache_key = f"audit:recent:{user_id}"
            recent_audits = self.redis.lrange(cache_key, 0, 99)
            self.redis.lpush(cache_key, json.dumps({
                'audit_id': audit_id,
                'action': action,
                'entity_type': entity_type,
                'timestamp': datetime.now().isoformat()
            }))
            self.redis.ltrim(cache_key, 0, 99)  # Keep only last 100
            self.redis.expire(cache_key, 86400)  # 24 hours
            
            logger.info(f"✅ Audit trail logged: {audit_id}")
            return audit_id
            
        except Exception as e:
            logger.error(f"Failed to log audit trail: {e}")
            raise
    
    def _calculate_next_run(self, frequency: ReportFrequency) -> datetime:
        """Calculate next run time for report schedule."""
        
        now = datetime.now()
        
        if frequency == ReportFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif frequency == ReportFrequency.DAILY:
            return now.replace(hour=6, minute=0, second=0) + timedelta(days=1)
        elif frequency == ReportFrequency.WEEKLY:
            days_ahead = 6 - now.weekday()  # Monday = 0, Sunday = 6
            return (now + timedelta(days=days_ahead)).replace(hour=6, minute=0, second=0)
        elif frequency == ReportFrequency.MONTHLY:
            next_month = now.replace(day=1) + timedelta(days=32)
            return next_month.replace(day=1, hour=6, minute=0, second=0)
        else:
            return now + timedelta(hours=24)
    
    def _run_scheduler(self):
        """Background scheduler for automated reports."""
        
        logger.info("📅 Report scheduler started")
        
        while self.scheduler_running:
            try:
                # Check for due reports
                cursor = self.db.cursor()
                cursor.execute("""
                    SELECT schedule_id, report_type, frequency, recipients, format, filters
                    FROM report_schedules
                    WHERE is_active = TRUE AND next_run <= %s
                """, (datetime.now(),))
                
                due_schedules = cursor.fetchall()
                cursor.close()
                
                for schedule in due_schedules:
                    schedule_id, report_type, frequency, recipients, format, filters = schedule
                    
                    try:
                        # Generate report
                        asyncio.run(self.generate_report(
                            ReportType(report_type),
                            ReportFormat(format),
                            json.loads(filters),
                            schedule_id
                        ))
                        
                        # Update next run time
                        next_run = self._calculate_next_run(ReportFrequency(frequency))
                        cursor = self.db.cursor()
                        cursor.execute("""
                            UPDATE report_schedules 
                            SET last_run = %s, next_run = %s
                            WHERE schedule_id = %s
                        """, (datetime.now(), next_run, schedule_id))
                        self.db.commit()
                        cursor.close()
                        
                        logger.info(f"✅ Scheduled report generated: {schedule_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate scheduled report {schedule_id}: {e}")
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Sleep 5 minutes on error
    
    def stop_scheduler(self):
        """Stop the background scheduler."""
        self.scheduler_running = False
        logger.info("📅 Report scheduler stopped")

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
    
    # Initialize reporting service
    reporting_service = ReportingService(db_conn)
    
    async def test_reporting_service():
        """Test reporting service functionality."""
        
        print("📊 Testing Reporting Service...")
        
        # Create report schedule
        schedule_id = await reporting_service.create_report_schedule(
            report_type=ReportType.DAILY_SUMMARY,
            frequency=ReportFrequency.DAILY,
            recipients=["manager@retailai.com"],
            format=ReportFormat.HTML
        )
        print(f"✅ Report schedule created: {schedule_id}")
        
        # Generate report on-demand
        report_path = await reporting_service.generate_report(
            report_type=ReportType.DAILY_SUMMARY,
            format=ReportFormat.JSON
        )
        print(f"✅ Report generated: {report_path}")
        
        # Log audit trail
        audit_id = await reporting_service.log_audit_trail(
            user_id="test_user",
            entity_type="product",
            entity_id="PROD_001",
            action="UPDATE",
            changes={"price": {"before": 10.00, "after": 12.00}},
            compliance_tags=["FINANCIAL_DATA"]
        )
        print(f"✅ Audit trail logged: {audit_id}")
        
        print("📊 Reporting service testing complete!")
    
    # Run test
    asyncio.run(test_reporting_service())