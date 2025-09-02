#!/usr/bin/env python3
"""
Multi-Channel Notification Service
Implements FR-028: Multi-channel notifications (Email, SMS, Push, Slack, Teams)
"""

import asyncio
import logging
import json
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
import redis
import aiohttp
import requests
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
from jinja2 import Template
import twilio
from twilio.rest import Client as TwilioClient
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"

class NotificationPriority(Enum):
    """Notification priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    RETRYING = "retrying"

@dataclass
class NotificationTemplate:
    """Notification template structure."""
    template_id: str
    name: str
    notification_type: NotificationType
    subject_template: str
    body_template: str
    variables: List[str]
    is_active: bool
    created_at: datetime

@dataclass
class NotificationRecipient:
    """Notification recipient."""
    recipient_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    slack_user_id: Optional[str] = None
    push_token: Optional[str] = None
    preferences: Dict[str, Any] = None
    timezone: str = "UTC"

@dataclass
class NotificationMessage:
    """Notification message structure."""
    message_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    recipient: NotificationRecipient
    subject: str
    body: str
    template_id: Optional[str] = None
    variables: Dict[str, Any] = None
    attachments: List[str] = None
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class NotificationRule:
    """Notification rules for automated alerts."""
    rule_id: str
    name: str
    trigger_conditions: Dict[str, Any]
    notification_types: List[NotificationType]
    recipients: List[str]
    template_id: str
    priority: NotificationPriority
    rate_limit: Optional[Dict[str, Any]] = None  # e.g., {"max_per_hour": 10}
    is_active: bool = True
    created_at: datetime = None

class NotificationService:
    """Production-ready multi-channel notification service."""
    
    def __init__(self, db_connection, redis_client=None, config=None):
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        
        # Configuration with defaults
        self.config = config or {}
        self.email_config = self.config.get('email', {
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'notifications@retailai.com',
            'password': 'app_password',
            'use_tls': True,
            'from_name': 'RetailAI Platform'
        })
        
        self.sms_config = self.config.get('sms', {
            'provider': 'twilio',
            'account_sid': 'your_account_sid',
            'auth_token': 'your_auth_token',
            'from_number': '+1234567890'
        })
        
        self.slack_config = self.config.get('slack', {
            'bot_token': 'xoxb-your-bot-token',
            'webhook_url': 'https://hooks.slack.com/services/...'
        })
        
        self.teams_config = self.config.get('teams', {
            'webhook_url': 'https://outlook.office.com/webhook/...'
        })
        
        self.push_config = self.config.get('push', {
            'provider': 'firebase',  # or 'aws_sns'
            'server_key': 'your_firebase_server_key',
            'aws_region': 'us-east-1'
        })
        
        # Initialize providers
        self._init_providers()
        
        # Initialize database schema
        self.init_database_schema()
        
        # Start background workers
        self.workers_running = True
        self._start_background_workers()
        
        logger.info("✅ Notification service initialized")
    
    def _init_providers(self):
        """Initialize notification providers."""
        
        # Twilio SMS client
        if self.sms_config.get('account_sid'):
            try:
                self.twilio_client = TwilioClient(
                    self.sms_config['account_sid'],
                    self.sms_config['auth_token']
                )
                logger.info("✅ Twilio SMS client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio: {e}")
                self.twilio_client = None
        else:
            self.twilio_client = None
        
        # AWS SNS for push notifications
        if self.push_config.get('provider') == 'aws_sns':
            try:
                self.sns_client = boto3.client(
                    'sns',
                    region_name=self.push_config.get('aws_region', 'us-east-1')
                )
                logger.info("✅ AWS SNS client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS SNS: {e}")
                self.sns_client = None
        else:
            self.sns_client = None
    
    def init_database_schema(self):
        """Initialize notification database schema."""
        
        try:
            cursor = self.db.cursor()
            
            # Notification templates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_templates (
                    template_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    notification_type VARCHAR(20) NOT NULL,
                    subject_template TEXT,
                    body_template TEXT NOT NULL,
                    variables TEXT[] DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recipients table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_recipients (
                    recipient_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(20),
                    slack_user_id VARCHAR(50),
                    push_token TEXT,
                    preferences JSONB DEFAULT '{}',
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Notification messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_messages (
                    message_id VARCHAR(50) PRIMARY KEY,
                    notification_type VARCHAR(20) NOT NULL,
                    priority VARCHAR(20) DEFAULT 'normal',
                    recipient_id VARCHAR(50) REFERENCES notification_recipients(recipient_id),
                    subject TEXT,
                    body TEXT NOT NULL,
                    template_id VARCHAR(50),
                    variables JSONB DEFAULT '{}',
                    attachments TEXT[] DEFAULT '{}',
                    scheduled_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    error_message TEXT,
                    provider_response JSONB
                )
            """)
            
            # Notification rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_rules (
                    rule_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    trigger_conditions JSONB NOT NULL,
                    notification_types TEXT[] NOT NULL,
                    recipients TEXT[] NOT NULL,
                    template_id VARCHAR(50) REFERENCES notification_templates(template_id),
                    priority VARCHAR(20) DEFAULT 'normal',
                    rate_limit JSONB,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP
                )
            """)
            
            # Delivery statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_stats (
                    stat_id VARCHAR(50) PRIMARY KEY,
                    notification_type VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    count INTEGER DEFAULT 1,
                    date DATE DEFAULT CURRENT_DATE,
                    hour INTEGER DEFAULT EXTRACT(HOUR FROM CURRENT_TIMESTAMP),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_status ON notification_messages(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_scheduled ON notification_messages(scheduled_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON notification_messages(notification_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_date ON notification_stats(date, notification_type)")
            
            self.db.commit()
            cursor.close()
            logger.info("✅ Notification database schema initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize notification schema: {e}")
            raise
    
    async def create_template(self, name: str, notification_type: NotificationType,
                            subject_template: str, body_template: str,
                            variables: List[str] = None) -> str:
        """Create notification template."""
        
        try:
            template_id = f"template_{int(datetime.now().timestamp())}_{secrets.token_hex(6)}"
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO notification_templates 
                (template_id, name, notification_type, subject_template, body_template, variables)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                template_id, name, notification_type.value, subject_template,
                body_template, variables or []
            ))
            
            self.db.commit()
            cursor.close()
            
            logger.info(f"✅ Notification template created: {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Failed to create notification template: {e}")
            raise
    
    async def add_recipient(self, name: str, email: str = None, phone: str = None,
                          slack_user_id: str = None, push_token: str = None,
                          preferences: Dict[str, Any] = None) -> str:
        """Add notification recipient."""
        
        try:
            recipient_id = f"recipient_{int(datetime.now().timestamp())}_{secrets.token_hex(6)}"
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO notification_recipients 
                (recipient_id, name, email, phone, slack_user_id, push_token, preferences)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                recipient_id, name, email, phone, slack_user_id,
                push_token, json.dumps(preferences or {})
            ))
            
            self.db.commit()
            cursor.close()
            
            logger.info(f"✅ Notification recipient added: {recipient_id}")
            return recipient_id
            
        except Exception as e:
            logger.error(f"Failed to add notification recipient: {e}")
            raise
    
    async def send_notification(self, notification_type: NotificationType,
                              recipient_id: str, subject: str, body: str,
                              priority: NotificationPriority = NotificationPriority.NORMAL,
                              template_id: str = None, variables: Dict[str, Any] = None,
                              attachments: List[str] = None,
                              scheduled_at: datetime = None) -> str:
        """Send notification message."""
        
        try:
            message_id = f"msg_{int(datetime.now().timestamp())}_{secrets.token_hex(8)}"
            
            # Get recipient details
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT name, email, phone, slack_user_id, push_token, preferences
                FROM notification_recipients
                WHERE recipient_id = %s AND is_active = TRUE
            """, (recipient_id,))
            
            recipient_data = cursor.fetchone()
            if not recipient_data:
                raise ValueError(f"Recipient not found: {recipient_id}")
            
            name, email, phone, slack_user_id, push_token, preferences = recipient_data
            
            # Create recipient object
            recipient = NotificationRecipient(
                recipient_id=recipient_id,
                name=name,
                email=email,
                phone=phone,
                slack_user_id=slack_user_id,
                push_token=push_token,
                preferences=json.loads(preferences) if preferences else {}
            )
            
            # Create message object
            message = NotificationMessage(
                message_id=message_id,
                notification_type=notification_type,
                priority=priority,
                recipient=recipient,
                subject=subject,
                body=body,
                template_id=template_id,
                variables=variables,
                attachments=attachments or [],
                scheduled_at=scheduled_at,
                expires_at=datetime.now() + timedelta(hours=24),  # Default expiry
                created_at=datetime.now()
            )
            
            # Store message in database
            cursor.execute("""
                INSERT INTO notification_messages 
                (message_id, notification_type, priority, recipient_id, subject, body,
                 template_id, variables, attachments, scheduled_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                message_id, notification_type.value, priority.value, recipient_id,
                subject, body, template_id, json.dumps(variables or {}),
                attachments or [], scheduled_at, message.expires_at
            ))
            
            self.db.commit()
            cursor.close()
            
            # Send immediately if not scheduled
            if not scheduled_at or scheduled_at <= datetime.now():
                await self._deliver_message(message)
            
            logger.info(f"✅ Notification queued: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise
    
    async def _deliver_message(self, message: NotificationMessage):
        """Deliver notification message using appropriate channel."""
        
        try:
            # Update status to sending
            await self._update_message_status(message.message_id, NotificationStatus.SENDING)
            
            # Route to appropriate delivery method
            if message.notification_type == NotificationType.EMAIL:
                result = await self._send_email(message)
            elif message.notification_type == NotificationType.SMS:
                result = await self._send_sms(message)
            elif message.notification_type == NotificationType.SLACK:
                result = await self._send_slack(message)
            elif message.notification_type == NotificationType.TEAMS:
                result = await self._send_teams(message)
            elif message.notification_type == NotificationType.PUSH:
                result = await self._send_push(message)
            elif message.notification_type == NotificationType.WEBHOOK:
                result = await self._send_webhook(message)
            else:
                raise ValueError(f"Unsupported notification type: {message.notification_type}")
            
            if result['success']:
                await self._update_message_status(
                    message.message_id, 
                    NotificationStatus.DELIVERED,
                    provider_response=result.get('response')
                )
                await self._update_delivery_stats(message.notification_type, NotificationStatus.DELIVERED)
                logger.info(f"✅ Message delivered: {message.message_id}")
            else:
                await self._handle_delivery_failure(message, result.get('error', 'Unknown error'))
                
        except Exception as e:
            await self._handle_delivery_failure(message, str(e))
    
    async def _send_email(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send email notification."""
        
        try:
            if not message.recipient.email:
                return {'success': False, 'error': 'No email address for recipient'}
            
            # Create email message
            msg = MimeMultipart()
            msg['From'] = f"{self.email_config['from_name']} <{self.email_config['username']}>"
            msg['To'] = message.recipient.email
            msg['Subject'] = message.subject
            
            # Add body
            msg.attach(MimeText(message.body, 'html' if '<html>' in message.body else 'plain'))
            
            # Add attachments
            for attachment_path in message.attachments:
                try:
                    with open(attachment_path, "rb") as attachment:
                        part = MimeBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment_path.split("/")[-1]}'
                        )
                        msg.attach(part)
                except Exception as e:
                    logger.warning(f"Failed to attach file {attachment_path}: {e}")
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.email_config['smtp_host'], self.email_config['smtp_port']) as server:
                if self.email_config['use_tls']:
                    server.starttls(context=context)
                server.login(self.email_config['username'], self.email_config['password'])
                server.sendmail(self.email_config['username'], message.recipient.email, msg.as_string())
            
            return {'success': True, 'response': 'Email sent successfully'}
            
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_sms(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send SMS notification."""
        
        try:
            if not message.recipient.phone:
                return {'success': False, 'error': 'No phone number for recipient'}
            
            if not self.twilio_client:
                return {'success': False, 'error': 'SMS provider not configured'}
            
            # Send SMS via Twilio
            sms_message = self.twilio_client.messages.create(
                body=message.body,
                from_=self.sms_config['from_number'],
                to=message.recipient.phone
            )
            
            return {
                'success': True,
                'response': {
                    'message_sid': sms_message.sid,
                    'status': sms_message.status
                }
            }
            
        except Exception as e:
            logger.error(f"SMS delivery failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_slack(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send Slack notification."""
        
        try:
            if not message.recipient.slack_user_id and not self.slack_config.get('webhook_url'):
                return {'success': False, 'error': 'No Slack configuration for recipient'}
            
            # Prepare Slack message payload
            payload = {
                "text": message.subject,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": message.subject
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message.body
                        }
                    }
                ]
            }
            
            # Add user mention if available
            if message.recipient.slack_user_id:
                payload["channel"] = f"@{message.recipient.slack_user_id}"
            
            # Send via webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_config['webhook_url'],
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        return {'success': True, 'response': 'Slack message sent'}
                    else:
                        error_text = await response.text()
                        return {'success': False, 'error': f'Slack API error: {error_text}'}
            
        except Exception as e:
            logger.error(f"Slack delivery failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_teams(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send Microsoft Teams notification."""
        
        try:
            if not self.teams_config.get('webhook_url'):
                return {'success': False, 'error': 'Teams webhook not configured'}
            
            # Prepare Teams message payload
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": message.subject,
                "sections": [
                    {
                        "activityTitle": message.subject,
                        "activitySubtitle": f"Notification for {message.recipient.name}",
                        "text": message.body,
                        "markdown": True
                    }
                ]
            }
            
            # Send via webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.teams_config['webhook_url'],
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        return {'success': True, 'response': 'Teams message sent'}
                    else:
                        error_text = await response.text()
                        return {'success': False, 'error': f'Teams API error: {error_text}'}
            
        except Exception as e:
            logger.error(f"Teams delivery failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_push(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send push notification."""
        
        try:
            if not message.recipient.push_token:
                return {'success': False, 'error': 'No push token for recipient'}
            
            if self.push_config['provider'] == 'firebase':
                return await self._send_firebase_push(message)
            elif self.push_config['provider'] == 'aws_sns':
                return await self._send_aws_push(message)
            else:
                return {'success': False, 'error': 'Push provider not supported'}
            
        except Exception as e:
            logger.error(f"Push notification delivery failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_firebase_push(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send push notification via Firebase."""
        
        try:
            payload = {
                "to": message.recipient.push_token,
                "notification": {
                    "title": message.subject,
                    "body": message.body,
                    "sound": "default"
                },
                "data": {
                    "message_id": message.message_id,
                    "priority": message.priority.value
                }
            }
            
            headers = {
                'Authorization': f'key={self.push_config["server_key"]}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://fcm.googleapis.com/fcm/send',
                    json=payload,
                    headers=headers
                ) as response:
                    result = await response.json()
                    if result.get('success', 0) > 0:
                        return {'success': True, 'response': result}
                    else:
                        return {'success': False, 'error': result.get('failure', 'Firebase error')}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _send_webhook(self, message: NotificationMessage) -> Dict[str, Any]:
        """Send webhook notification."""
        
        try:
            # Webhook URL should be in recipient preferences
            webhook_url = message.recipient.preferences.get('webhook_url')
            if not webhook_url:
                return {'success': False, 'error': 'No webhook URL configured for recipient'}
            
            payload = {
                "message_id": message.message_id,
                "notification_type": message.notification_type.value,
                "priority": message.priority.value,
                "recipient": message.recipient.name,
                "subject": message.subject,
                "body": message.body,
                "timestamp": message.created_at.isoformat(),
                "variables": message.variables
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if 200 <= response.status < 300:
                        return {'success': True, 'response': f'Webhook delivered (status: {response.status})'}
                    else:
                        error_text = await response.text()
                        return {'success': False, 'error': f'Webhook failed (status: {response.status}): {error_text}'}
            
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _update_message_status(self, message_id: str, status: NotificationStatus,
                                   provider_response: Dict = None):
        """Update message delivery status."""
        
        try:
            cursor = self.db.cursor()
            
            if status == NotificationStatus.SENDING:
                cursor.execute("""
                    UPDATE notification_messages 
                    SET status = %s, sent_at = %s
                    WHERE message_id = %s
                """, (status.value, datetime.now(), message_id))
            elif status == NotificationStatus.DELIVERED:
                cursor.execute("""
                    UPDATE notification_messages 
                    SET status = %s, delivered_at = %s, provider_response = %s
                    WHERE message_id = %s
                """, (status.value, datetime.now(), json.dumps(provider_response or {}), message_id))
            else:
                cursor.execute("""
                    UPDATE notification_messages 
                    SET status = %s
                    WHERE message_id = %s
                """, (status.value, message_id))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
    
    async def _handle_delivery_failure(self, message: NotificationMessage, error: str):
        """Handle notification delivery failure with retry logic."""
        
        try:
            message.retry_count += 1
            message.error_message = error
            
            if message.retry_count <= message.max_retries:
                # Schedule retry with exponential backoff
                retry_delay = min(300, 30 * (2 ** message.retry_count))  # Max 5 minutes
                retry_at = datetime.now() + timedelta(seconds=retry_delay)
                
                cursor = self.db.cursor()
                cursor.execute("""
                    UPDATE notification_messages 
                    SET status = %s, retry_count = %s, error_message = %s, scheduled_at = %s
                    WHERE message_id = %s
                """, (
                    NotificationStatus.RETRYING.value, message.retry_count,
                    error, retry_at, message.message_id
                ))
                self.db.commit()
                cursor.close()
                
                await self._update_delivery_stats(message.notification_type, NotificationStatus.RETRYING)
                logger.warning(f"⚠️  Message retry scheduled: {message.message_id} (attempt {message.retry_count})")
            else:
                # Mark as permanently failed
                cursor = self.db.cursor()
                cursor.execute("""
                    UPDATE notification_messages 
                    SET status = %s, error_message = %s
                    WHERE message_id = %s
                """, (NotificationStatus.FAILED.value, error, message.message_id))
                self.db.commit()
                cursor.close()
                
                await self._update_delivery_stats(message.notification_type, NotificationStatus.FAILED)
                logger.error(f"❌ Message permanently failed: {message.message_id}")
                
        except Exception as e:
            logger.error(f"Failed to handle delivery failure: {e}")
    
    async def _update_delivery_stats(self, notification_type: NotificationType, status: NotificationStatus):
        """Update delivery statistics."""
        
        try:
            cursor = self.db.cursor()
            
            # Try to update existing stat
            cursor.execute("""
                UPDATE notification_stats 
                SET count = count + 1
                WHERE notification_type = %s AND status = %s 
                AND date = CURRENT_DATE AND hour = EXTRACT(HOUR FROM CURRENT_TIMESTAMP)
            """, (notification_type.value, status.value))
            
            # If no rows updated, insert new stat
            if cursor.rowcount == 0:
                stat_id = f"stat_{int(datetime.now().timestamp())}_{secrets.token_hex(6)}"
                cursor.execute("""
                    INSERT INTO notification_stats (stat_id, notification_type, status, count)
                    VALUES (%s, %s, %s, 1)
                """, (stat_id, notification_type.value, status.value))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Failed to update delivery stats: {e}")
    
    def _start_background_workers(self):
        """Start background workers for processing notifications."""
        
        # Start message processor worker
        asyncio.create_task(self._message_processor_worker())
        
        # Start cleanup worker
        asyncio.create_task(self._cleanup_worker())
        
        logger.info("✅ Background workers started")
    
    async def _message_processor_worker(self):
        """Background worker to process queued messages."""
        
        logger.info("📬 Message processor worker started")
        
        while self.workers_running:
            try:
                # Get pending messages
                cursor = self.db.cursor()
                cursor.execute("""
                    SELECT message_id, notification_type, priority, recipient_id, subject, body,
                           template_id, variables, attachments, scheduled_at, expires_at, retry_count
                    FROM notification_messages
                    WHERE status IN ('pending', 'retrying') 
                    AND (scheduled_at IS NULL OR scheduled_at <= %s)
                    AND expires_at > %s
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 50
                """, (datetime.now(), datetime.now()))
                
                messages = cursor.fetchall()
                cursor.close()
                
                for message_data in messages:
                    try:
                        # Get recipient details
                        cursor = self.db.cursor()
                        cursor.execute("""
                            SELECT name, email, phone, slack_user_id, push_token, preferences
                            FROM notification_recipients
                            WHERE recipient_id = %s
                        """, (message_data[3],))
                        
                        recipient_data = cursor.fetchone()
                        cursor.close()
                        
                        if not recipient_data:
                            continue
                        
                        # Create message object
                        recipient = NotificationRecipient(
                            recipient_id=message_data[3],
                            name=recipient_data[0],
                            email=recipient_data[1],
                            phone=recipient_data[2],
                            slack_user_id=recipient_data[3],
                            push_token=recipient_data[4],
                            preferences=json.loads(recipient_data[5]) if recipient_data[5] else {}
                        )
                        
                        message = NotificationMessage(
                            message_id=message_data[0],
                            notification_type=NotificationType(message_data[1]),
                            priority=NotificationPriority(message_data[2]),
                            recipient=recipient,
                            subject=message_data[4],
                            body=message_data[5],
                            template_id=message_data[6],
                            variables=json.loads(message_data[7]) if message_data[7] else {},
                            attachments=message_data[8] or [],
                            scheduled_at=message_data[9],
                            expires_at=message_data[10],
                            retry_count=message_data[11]
                        )
                        
                        # Process message
                        await self._deliver_message(message)
                        
                    except Exception as e:
                        logger.error(f"Failed to process message {message_data[0]}: {e}")
                
                # Sleep between processing cycles
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                await asyncio.sleep(60)  # Sleep longer on error
    
    async def _cleanup_worker(self):
        """Background worker for cleaning up expired messages."""
        
        logger.info("🧹 Cleanup worker started")
        
        while self.workers_running:
            try:
                # Clean up expired messages
                cursor = self.db.cursor()
                cursor.execute("""
                    UPDATE notification_messages 
                    SET status = 'failed', error_message = 'Expired'
                    WHERE expires_at <= %s AND status IN ('pending', 'retrying')
                """, (datetime.now(),))
                
                expired_count = cursor.rowcount
                if expired_count > 0:
                    logger.info(f"🧹 Cleaned up {expired_count} expired messages")
                
                # Clean up old statistics (keep 90 days)
                cursor.execute("""
                    DELETE FROM notification_stats 
                    WHERE date < %s
                """, (datetime.now().date() - timedelta(days=90),))
                
                stats_deleted = cursor.rowcount
                if stats_deleted > 0:
                    logger.info(f"🧹 Cleaned up {stats_deleted} old statistics")
                
                self.db.commit()
                cursor.close()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(3600)  # Sleep on error
    
    def stop_workers(self):
        """Stop background workers."""
        self.workers_running = False
        logger.info("🛑 Background workers stopped")
    
    async def get_delivery_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get notification delivery statistics."""
        
        try:
            cursor = self.db.cursor()
            
            start_date = datetime.now().date() - timedelta(days=days)
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    SUM(count) as total,
                    SUM(CASE WHEN status = 'delivered' THEN count ELSE 0 END) as delivered,
                    SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) as failed
                FROM notification_stats
                WHERE date >= %s
            """, (start_date,))
            
            overall = cursor.fetchone()
            total, delivered, failed = overall
            
            # Stats by type
            cursor.execute("""
                SELECT notification_type, status, SUM(count) as count
                FROM notification_stats
                WHERE date >= %s
                GROUP BY notification_type, status
                ORDER BY notification_type, status
            """, (start_date,))
            
            by_type = {}
            for row in cursor.fetchall():
                notification_type, status, count = row
                if notification_type not in by_type:
                    by_type[notification_type] = {}
                by_type[notification_type][status] = count
            
            # Daily trends
            cursor.execute("""
                SELECT date, SUM(count) as count
                FROM notification_stats
                WHERE date >= %s
                GROUP BY date
                ORDER BY date
            """, (start_date,))
            
            daily_trends = [
                {"date": str(date), "count": count}
                for date, count in cursor.fetchall()
            ]
            
            cursor.close()
            
            return {
                "period_days": days,
                "overall": {
                    "total": total or 0,
                    "delivered": delivered or 0,
                    "failed": failed or 0,
                    "success_rate": ((delivered or 0) / (total or 1)) * 100
                },
                "by_type": by_type,
                "daily_trends": daily_trends,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get delivery stats: {e}")
            raise

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
    
    # Initialize notification service
    notification_service = NotificationService(db_conn)
    
    async def test_notification_service():
        """Test notification service functionality."""
        
        print("📬 Testing Notification Service...")
        
        # Create notification template
        template_id = await notification_service.create_template(
            name="Alert Notification",
            notification_type=NotificationType.EMAIL,
            subject_template="🚨 RetailAI Alert: {{alert_type}}",
            body_template="<h2>Alert Details</h2><p>{{alert_message}}</p><p>Store: {{store_name}}</p>",
            variables=["alert_type", "alert_message", "store_name"]
        )
        print(f"✅ Template created: {template_id}")
        
        # Add recipient
        recipient_id = await notification_service.add_recipient(
            name="Store Manager",
            email="manager@retailai.com",
            phone="+1234567890",
            preferences={"timezone": "EST"}
        )
        print(f"✅ Recipient added: {recipient_id}")
        
        # Send email notification
        message_id = await notification_service.send_notification(
            notification_type=NotificationType.EMAIL,
            recipient_id=recipient_id,
            subject="Test Email Notification",
            body="This is a test email notification from RetailAI.",
            priority=NotificationPriority.HIGH
        )
        print(f"✅ Email notification sent: {message_id}")
        
        # Wait a moment and check stats
        await asyncio.sleep(5)
        
        stats = await notification_service.get_delivery_stats(days=1)
        print(f"✅ Delivery stats: {stats['overall']}")
        
        print("📬 Notification service testing complete!")
    
    # Run test
    asyncio.run(test_notification_service())