"""
Real-Time Alert System for AI-Powered Inventory Optimization
Implements comprehensive business rules for stockout, overstock, and performance alerts.
"""

import asyncio
import smtplib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2
import redis
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"
    MOBILE_PUSH = "mobile_push"

@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    condition: str  # SQL-like condition
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 60  # Prevent alert spam
    is_active: bool = True
    
@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    title: str
    message: str
    severity: AlertSeverity
    product_id: Optional[str] = None
    store_id: Optional[str] = None
    data: Optional[Dict] = None
    created_at: datetime = None
    
class RealTimeAlertSystem:
    """Production-ready alert system with business rules engine."""
    
    def __init__(self, db_connection, redis_client=None, smtp_config=None):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.smtp_config = smtp_config
        self.alert_rules = {}
        self.load_alert_rules()
        self.running = False
        
    def load_alert_rules(self):
        """Load alert rules from configuration."""
        
        # Stockout Risk Alerts (CRITICAL)
        self.alert_rules['STOCKOUT_CRITICAL'] = AlertRule(
            rule_id='STOCKOUT_CRITICAL',
            name='Critical Stockout Risk',
            condition='current_stock <= 0',
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD, AlertChannel.MOBILE_PUSH],
            cooldown_minutes=30
        )
        
        self.alert_rules['STOCKOUT_HIGH'] = AlertRule(
            rule_id='STOCKOUT_HIGH',
            name='High Stockout Risk',
            condition='current_stock <= reorder_point * 0.5',
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD],
            cooldown_minutes=120
        )
        
        # Overstock Alerts (MEDIUM)
        self.alert_rules['OVERSTOCK_HIGH'] = AlertRule(
            rule_id='OVERSTOCK_HIGH',
            name='Overstock Alert',
            condition='current_stock >= max_stock_level * 1.5',
            severity=AlertSeverity.MEDIUM,
            channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD],
            cooldown_minutes=240
        )
        
        # Forecast Accuracy Alerts (MEDIUM)
        self.alert_rules['FORECAST_ACCURACY_DROP'] = AlertRule(
            rule_id='FORECAST_ACCURACY_DROP',
            name='Forecast Accuracy Drop',
            condition='forecast_accuracy < 0.7',
            severity=AlertSeverity.MEDIUM,
            channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD],
            cooldown_minutes=480
        )
        
        # Demand Spike Alerts (HIGH)
        self.alert_rules['DEMAND_SPIKE'] = AlertRule(
            rule_id='DEMAND_SPIKE',
            name='Demand Spike Detected',
            condition='daily_sales > average_daily_sales * 3',
            severity=AlertSeverity.HIGH,
            channels=[AlertChannel.EMAIL, AlertChannel.DASHBOARD],
            cooldown_minutes=60
        )
        
        # Slow Moving Inventory (LOW)
        self.alert_rules['SLOW_MOVING'] = AlertRule(
            rule_id='SLOW_MOVING',
            name='Slow Moving Inventory',
            condition='days_since_last_sale > 30',
            severity=AlertSeverity.LOW,
            channels=[AlertChannel.DASHBOARD],
            cooldown_minutes=1440  # Daily
        )
        
        logger.info(f"Loaded {len(self.alert_rules)} alert rules")
    
    async def check_stockout_alerts(self) -> List[Alert]:
        """Check for stockout risk conditions."""
        alerts = []
        
        try:
            query = """
            SELECT 
                i.product_id,
                i.store_id,
                i.current_stock,
                i.reserved_stock,
                i.reorder_point,
                i.max_stock_level,
                p.name as product_name,
                s.name as store_name,
                (i.current_stock - i.reserved_stock) as available_stock
            FROM inventory i
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN stores s ON i.store_id = s.id
            WHERE i.current_stock > 0
            """
            
            cursor = self.db.cursor()
            cursor.execute(query)
            inventory_data = cursor.fetchall()
            
            for row in inventory_data:
                product_id, store_id, current_stock, reserved_stock, reorder_point, max_stock, product_name, store_name, available_stock = row
                
                # Critical: Out of stock or negative available stock
                if available_stock <= 0:
                    if not self.is_alert_in_cooldown('STOCKOUT_CRITICAL', f"{product_id}_{store_id}"):
                        alert = Alert(
                            alert_id=f"STOCKOUT_CRITICAL_{product_id}_{store_id}_{datetime.now().timestamp()}",
                            rule_id='STOCKOUT_CRITICAL',
                            title=f"CRITICAL: Stockout - {product_name}",
                            message=f"IMMEDIATE ACTION REQUIRED: {product_name} at {store_name} is out of stock. Available: {available_stock} units",
                            severity=AlertSeverity.CRITICAL,
                            product_id=product_id,
                            store_id=store_id,
                            data={
                                'current_stock': current_stock,
                                'available_stock': available_stock,
                                'reorder_point': reorder_point,
                                'urgency': 'IMMEDIATE'
                            },
                            created_at=datetime.now()
                        )
                        alerts.append(alert)
                        
                # High: Below half of reorder point
                elif available_stock <= (reorder_point or 10) * 0.5:
                    if not self.is_alert_in_cooldown('STOCKOUT_HIGH', f"{product_id}_{store_id}"):
                        alert = Alert(
                            alert_id=f"STOCKOUT_HIGH_{product_id}_{store_id}_{datetime.now().timestamp()}",
                            rule_id='STOCKOUT_HIGH',
                            title=f"HIGH RISK: Low Stock - {product_name}",
                            message=f"HIGH PRIORITY: {product_name} at {store_name} is critically low. Available: {available_stock} units, Reorder Point: {reorder_point}",
                            severity=AlertSeverity.HIGH,
                            product_id=product_id,
                            store_id=store_id,
                            data={
                                'current_stock': current_stock,
                                'available_stock': available_stock,
                                'reorder_point': reorder_point,
                                'days_until_stockout': max(1, int(available_stock / max(1, self.get_daily_demand_estimate(product_id, store_id))))
                            },
                            created_at=datetime.now()
                        )
                        alerts.append(alert)
                
                # Medium: Overstock condition
                if current_stock >= (max_stock or 100) * 1.5:
                    if not self.is_alert_in_cooldown('OVERSTOCK_HIGH', f"{product_id}_{store_id}"):
                        alert = Alert(
                            alert_id=f"OVERSTOCK_HIGH_{product_id}_{store_id}_{datetime.now().timestamp()}",
                            rule_id='OVERSTOCK_HIGH',
                            title=f"OVERSTOCK: Excess Inventory - {product_name}",
                            message=f"OVERSTOCK DETECTED: {product_name} at {store_name} has excess inventory. Current: {current_stock}, Max: {max_stock}",
                            severity=AlertSeverity.MEDIUM,
                            product_id=product_id,
                            store_id=store_id,
                            data={
                                'current_stock': current_stock,
                                'max_stock_level': max_stock,
                                'excess_units': current_stock - max_stock,
                                'carrying_cost_impact': (current_stock - max_stock) * 0.25  # Estimated annual carrying cost
                            },
                            created_at=datetime.now()
                        )
                        alerts.append(alert)
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error checking stockout alerts: {e}")
        
        return alerts
    
    async def check_performance_alerts(self) -> List[Alert]:
        """Check for performance and forecast accuracy alerts."""
        alerts = []
        
        try:
            # Check for demand spikes
            query = """
            SELECT 
                st.product_id,
                st.store_id,
                p.name as product_name,
                s.name as store_name,
                SUM(st.quantity) as today_sales,
                AVG(daily_sales.avg_daily) as historical_avg
            FROM sales_transactions st
            LEFT JOIN products p ON st.product_id = p.id
            LEFT JOIN stores s ON st.store_id = s.id
            LEFT JOIN (
                SELECT 
                    product_id, store_id,
                    AVG(daily_total) as avg_daily
                FROM (
                    SELECT 
                        product_id, store_id, DATE(transaction_timestamp),
                        SUM(quantity) as daily_total
                    FROM sales_transactions 
                    WHERE transaction_timestamp >= NOW() - INTERVAL '30 days'
                    AND transaction_timestamp < DATE(NOW())
                    GROUP BY product_id, store_id, DATE(transaction_timestamp)
                ) daily_totals
                GROUP BY product_id, store_id
            ) daily_sales ON st.product_id = daily_sales.product_id AND st.store_id = daily_sales.store_id
            WHERE DATE(st.transaction_timestamp) = DATE(NOW())
            GROUP BY st.product_id, st.store_id, p.name, s.name, daily_sales.avg_daily
            HAVING SUM(st.quantity) > AVG(daily_sales.avg_daily) * 3
            """
            
            cursor = self.db.cursor()
            cursor.execute(query)
            spike_data = cursor.fetchall()
            
            for row in spike_data:
                product_id, store_id, product_name, store_name, today_sales, historical_avg = row
                
                if not self.is_alert_in_cooldown('DEMAND_SPIKE', f"{product_id}_{store_id}"):
                    alert = Alert(
                        alert_id=f"DEMAND_SPIKE_{product_id}_{store_id}_{datetime.now().timestamp()}",
                        rule_id='DEMAND_SPIKE',
                        title=f"DEMAND SPIKE: {product_name}",
                        message=f"DEMAND SPIKE DETECTED: {product_name} at {store_name} sales today ({today_sales}) are {today_sales/historical_avg:.1f}x normal average ({historical_avg:.1f})",
                        severity=AlertSeverity.HIGH,
                        product_id=product_id,
                        store_id=store_id,
                        data={
                            'today_sales': today_sales,
                            'historical_average': historical_avg,
                            'spike_multiplier': today_sales / historical_avg,
                            'recommended_action': 'CHECK_INVENTORY_LEVELS'
                        },
                        created_at=datetime.now()
                    )
                    alerts.append(alert)
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
        
        return alerts
    
    def is_alert_in_cooldown(self, rule_id: str, entity_key: str) -> bool:
        """Check if alert is in cooldown period to prevent spam."""
        
        cooldown_key = f"alert_cooldown:{rule_id}:{entity_key}"
        
        try:
            last_alert = self.redis.get(cooldown_key)
            if last_alert:
                last_alert_time = datetime.fromisoformat(last_alert.decode())
                rule = self.alert_rules.get(rule_id)
                if rule and datetime.now() - last_alert_time < timedelta(minutes=rule.cooldown_minutes):
                    return True
        except Exception as e:
            logger.warning(f"Error checking alert cooldown: {e}")
        
        return False
    
    def set_alert_cooldown(self, rule_id: str, entity_key: str):
        """Set cooldown for alert to prevent spam."""
        
        cooldown_key = f"alert_cooldown:{rule_id}:{entity_key}"
        rule = self.alert_rules.get(rule_id)
        
        try:
            ttl_seconds = (rule.cooldown_minutes if rule else 60) * 60
            self.redis.setex(cooldown_key, ttl_seconds, datetime.now().isoformat())
        except Exception as e:
            logger.warning(f"Error setting alert cooldown: {e}")
    
    def get_daily_demand_estimate(self, product_id: str, store_id: str) -> float:
        """Get estimated daily demand for stockout calculations."""
        
        try:
            query = """
            SELECT AVG(daily_demand) as avg_demand
            FROM (
                SELECT DATE(transaction_timestamp), SUM(quantity) as daily_demand
                FROM sales_transactions 
                WHERE product_id = %s AND store_id = %s
                AND transaction_timestamp >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(transaction_timestamp)
            ) daily_sales
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (product_id, store_id))
            result = cursor.fetchone()
            cursor.close()
            
            return float(result[0]) if result and result[0] else 1.0
            
        except Exception as e:
            logger.error(f"Error getting daily demand estimate: {e}")
            return 1.0
    
    async def send_alert(self, alert: Alert):
        """Send alert through configured channels."""
        
        rule = self.alert_rules.get(alert.rule_id)
        if not rule or not rule.is_active:
            return
        
        # Store alert in database
        await self.store_alert(alert)
        
        # Send through each configured channel
        for channel in rule.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    await self.send_email_alert(alert)
                elif channel == AlertChannel.DASHBOARD:
                    await self.send_dashboard_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self.send_webhook_alert(alert)
                elif channel == AlertChannel.MOBILE_PUSH:
                    await self.send_mobile_push_alert(alert)
                    
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")
        
        # Set cooldown to prevent spam
        entity_key = f"{alert.product_id}_{alert.store_id}" if alert.product_id and alert.store_id else "system"
        self.set_alert_cooldown(alert.rule_id, entity_key)
        
        logger.info(f"Alert sent: {alert.title} [{alert.severity.value.upper()}]")
    
    async def store_alert(self, alert: Alert):
        """Store alert in database for audit trail."""
        
        try:
            query = """
            INSERT INTO alerts (alert_type, severity, title, message, product_id, store_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (
                alert.rule_id,
                alert.severity.value,
                alert.title,
                alert.message,
                alert.product_id,
                alert.store_id,
                alert.created_at or datetime.now()
            ))
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error storing alert in database: {e}")
    
    async def send_email_alert(self, alert: Alert):
        """Send alert via email."""
        
        if not self.smtp_config:
            logger.warning("SMTP not configured, skipping email alert")
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from']
            msg['To'] = self.smtp_config['to']
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create HTML email body
            html_body = f"""
            <html>
            <body>
                <h2 style="color: {'#dc3545' if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH] else '#ffc107'}">
                    {alert.title}
                </h2>
                <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p><strong>Time:</strong> {alert.created_at}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                
                {f'<p><strong>Product:</strong> {alert.product_id}</p>' if alert.product_id else ''}
                {f'<p><strong>Store:</strong> {alert.store_id}</p>' if alert.store_id else ''}
                
                {f'<h3>Additional Data:</h3><pre>{json.dumps(alert.data, indent=2)}</pre>' if alert.data else ''}
                
                <p><em>This is an automated alert from the AI-Powered Inventory Optimization System.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                if self.smtp_config.get('use_tls'):
                    server.starttls()
                if self.smtp_config.get('username'):
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
                
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def send_dashboard_alert(self, alert: Alert):
        """Send alert to dashboard (via Redis)."""
        
        try:
            alert_data = {
                'alert_id': alert.alert_id,
                'rule_id': alert.rule_id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'product_id': alert.product_id,
                'store_id': alert.store_id,
                'data': alert.data,
                'created_at': alert.created_at.isoformat() if alert.created_at else datetime.now().isoformat()
            }
            
            # Publish to dashboard channel
            self.redis.publish('dashboard_alerts', json.dumps(alert_data))
            
            # Store in dashboard alerts list (keep last 100)
            self.redis.lpush('recent_alerts', json.dumps(alert_data))
            self.redis.ltrim('recent_alerts', 0, 99)
            
        except Exception as e:
            logger.error(f"Failed to send dashboard alert: {e}")
    
    async def send_webhook_alert(self, alert: Alert):
        """Send alert via webhook."""
        # Placeholder for webhook implementation
        logger.info(f"Webhook alert: {alert.title}")
    
    async def send_mobile_push_alert(self, alert: Alert):
        """Send mobile push notification."""
        # Placeholder for mobile push implementation
        logger.info(f"Mobile push alert: {alert.title}")
    
    async def run_alert_monitoring(self):
        """Main alert monitoring loop."""
        
        self.running = True
        logger.info("Starting real-time alert monitoring...")
        
        while self.running:
            try:
                # Check all alert conditions
                stockout_alerts = await self.check_stockout_alerts()
                performance_alerts = await self.check_performance_alerts()
                
                all_alerts = stockout_alerts + performance_alerts
                
                # Send alerts
                for alert in all_alerts:
                    await self.send_alert(alert)
                
                if all_alerts:
                    logger.info(f"Processed {len(all_alerts)} alerts")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(30)  # Shorter retry interval on error
    
    def stop_monitoring(self):
        """Stop alert monitoring."""
        self.running = False
        logger.info("Alert monitoring stopped")
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts from dashboard."""
        
        try:
            alerts = self.redis.lrange('recent_alerts', 0, limit - 1)
            return [json.loads(alert.decode()) for alert in alerts]
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []

# Example usage and configuration
if __name__ == "__main__":
    # Database connection
    db_conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='retailai',
        user='retailai',
        password='retailai123'
    )
    
    # SMTP configuration (optional)
    smtp_config = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True,
        'username': 'your-email@gmail.com',
        'password': 'your-app-password',
        'from': 'retailai-alerts@company.com',
        'to': 'manager@company.com'
    }
    
    # Initialize alert system
    alert_system = RealTimeAlertSystem(db_conn, smtp_config=smtp_config)
    
    # Run monitoring
    asyncio.run(alert_system.run_alert_monitoring())