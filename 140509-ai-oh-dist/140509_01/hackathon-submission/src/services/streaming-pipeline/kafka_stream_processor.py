#!/usr/bin/env python3
"""
Real-Time Data Pipeline with Kafka Streaming
Implements NFR-005: High-volume transaction processing and real-time analytics
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import pandas as pd
import psycopg2
import redis
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading
import time
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StreamEvent:
    """Represents a streaming event."""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    source: str
    metadata: Optional[Dict] = None

@dataclass
class ProcessingResult:
    """Result of stream processing."""
    success: bool
    processed_events: int
    errors: List[str]
    processing_time: float
    alerts_generated: int

class KafkaStreamProcessor:
    """Production-ready Kafka streaming pipeline for real-time data processing."""
    
    def __init__(self, kafka_config: Dict, db_connection, redis_client=None):
        self.kafka_config = kafka_config
        self.db = db_connection
        self.redis = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        
        # Kafka setup
        self.producer = None
        self.consumers = {}
        self.topics = {
            'sales_transactions': 'retail-sales-stream',
            'inventory_updates': 'inventory-updates-stream', 
            'alerts': 'alert-notifications-stream',
            'ml_predictions': 'ml-predictions-stream',
            'system_events': 'system-events-stream'
        }
        
        # Processing components
        self.event_handlers = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.metrics = {
            'events_processed': 0,
            'events_failed': 0,
            'processing_latency': [],
            'alerts_generated': 0
        }
        
        self.initialize_kafka()
        self.register_event_handlers()
    
    def initialize_kafka(self):
        """Initialize Kafka producer and consumers."""
        try:
            # Producer configuration
            producer_config = {
                'bootstrap_servers': self.kafka_config.get('bootstrap_servers', ['localhost:9092']),
                'value_serializer': lambda x: json.dumps(x, default=str).encode('utf-8'),
                'key_serializer': lambda x: str(x).encode('utf-8') if x else None,
                'acks': 'all',  # Wait for all replicas
                'retries': 3,
                'batch_size': 16384,
                'linger_ms': 10,  # Small delay to batch events
                'compression_type': 'snappy'
            }
            
            self.producer = KafkaProducer(**producer_config)
            logger.info("✅ Kafka producer initialized")
            
            # Consumer configuration  
            consumer_config = {
                'bootstrap_servers': self.kafka_config.get('bootstrap_servers', ['localhost:9092']),
                'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
                'key_deserializer': lambda x: x.decode('utf-8') if x else None,
                'group_id': 'retailai-processing-group',
                'auto_offset_reset': 'latest',
                'enable_auto_commit': False,  # Manual commit for reliability
                'max_poll_records': 500,
                'session_timeout_ms': 30000
            }
            
            # Initialize consumers for each topic
            for topic_name, topic_id in self.topics.items():
                consumer = KafkaConsumer(topic_id, **consumer_config)
                self.consumers[topic_name] = consumer
                logger.info(f"✅ Kafka consumer initialized for {topic_name} -> {topic_id}")
                
        except Exception as e:
            logger.error(f"❌ Kafka initialization failed: {e}")
            raise
    
    def register_event_handlers(self):
        """Register event processing handlers."""
        
        # Sales transaction handler
        self.event_handlers['sales_transactions'] = self.process_sales_transaction
        self.event_handlers['inventory_updates'] = self.process_inventory_update
        self.event_handlers['system_events'] = self.process_system_event
        
        logger.info(f"✅ Registered {len(self.event_handlers)} event handlers")
    
    async def publish_event(self, topic: str, event: StreamEvent) -> bool:
        """Publish event to Kafka stream."""
        
        try:
            topic_id = self.topics.get(topic)
            if not topic_id:
                logger.error(f"Unknown topic: {topic}")
                return False
            
            # Prepare event data
            event_data = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'data': event.data,
                'source': event.source,
                'metadata': event.metadata or {}
            }
            
            # Publish to Kafka
            future = self.producer.send(
                topic_id, 
                value=event_data, 
                key=event.event_id
            )
            
            # Wait for acknowledgment (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.info(f"✅ Event published to {topic}: {event.event_id}")
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Kafka publish failed for {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Event publish failed: {e}")
            return False
    
    async def process_sales_transaction(self, event_data: Dict) -> ProcessingResult:
        """Process sales transaction events in real-time."""
        
        start_time = time.time()
        errors = []
        alerts_generated = 0
        
        try:
            # Extract transaction data
            transaction = event_data.get('data', {})
            product_id = transaction.get('product_id')
            store_id = transaction.get('store_id')
            quantity = transaction.get('quantity', 0)
            timestamp = datetime.fromisoformat(event_data.get('timestamp'))
            
            # Update real-time analytics
            await self.update_realtime_analytics(product_id, store_id, quantity, timestamp)
            
            # Update inventory
            inventory_updated = await self.update_inventory_levels(product_id, store_id, quantity)
            
            if inventory_updated:
                # Check for alert conditions
                alerts = await self.check_transaction_alerts(product_id, store_id, quantity)
                alerts_generated = len(alerts)
                
                # Publish alerts
                for alert in alerts:
                    await self.publish_event('alerts', StreamEvent(
                        event_id=f"alert_{alert['alert_id']}",
                        event_type='inventory_alert',
                        timestamp=datetime.now(),
                        data=alert,
                        source='stream_processor'
                    ))
            
            # Update ML features in real-time
            await self.update_ml_features(product_id, store_id, transaction)
            
            processing_time = time.time() - start_time
            self.metrics['processing_latency'].append(processing_time)
            self.metrics['events_processed'] += 1
            self.metrics['alerts_generated'] += alerts_generated
            
            return ProcessingResult(
                success=True,
                processed_events=1,
                errors=errors,
                processing_time=processing_time,
                alerts_generated=alerts_generated
            )
            
        except Exception as e:
            error_msg = f"Sales transaction processing failed: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            self.metrics['events_failed'] += 1
            
            return ProcessingResult(
                success=False,
                processed_events=0,
                errors=errors,
                processing_time=time.time() - start_time,
                alerts_generated=0
            )
    
    async def process_inventory_update(self, event_data: Dict) -> ProcessingResult:
        """Process inventory update events."""
        
        start_time = time.time()
        
        try:
            data = event_data.get('data', {})
            product_id = data.get('product_id')
            store_id = data.get('store_id') 
            new_stock = data.get('new_stock', 0)
            update_type = data.get('update_type', 'manual')
            
            # Update database
            query = """
            UPDATE inventory 
            SET current_stock = %s, last_updated = %s 
            WHERE product_id = %s AND store_id = %s
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (new_stock, datetime.now(), product_id, store_id))
            self.db.commit()
            cursor.close()
            
            # Update Redis cache
            cache_key = f"inventory:{product_id}:{store_id}"
            self.redis.hset(cache_key, 'current_stock', new_stock)
            self.redis.hset(cache_key, 'last_updated', datetime.now().isoformat())
            self.redis.expire(cache_key, 3600)  # 1 hour TTL
            
            # Check for reorder alerts
            alerts = await self.check_inventory_alerts(product_id, store_id, new_stock)
            
            # Publish alerts
            for alert in alerts:
                await self.publish_event('alerts', StreamEvent(
                    event_id=f"inventory_alert_{product_id}_{store_id}_{int(time.time())}",
                    event_type='inventory_alert',
                    timestamp=datetime.now(),
                    data=alert,
                    source='inventory_processor'
                ))
            
            processing_time = time.time() - start_time
            self.metrics['events_processed'] += 1
            self.metrics['alerts_generated'] += len(alerts)
            
            return ProcessingResult(
                success=True,
                processed_events=1,
                errors=[],
                processing_time=processing_time,
                alerts_generated=len(alerts)
            )
            
        except Exception as e:
            error_msg = f"Inventory update processing failed: {e}"
            logger.error(error_msg)
            self.metrics['events_failed'] += 1
            
            return ProcessingResult(
                success=False,
                processed_events=0,
                errors=[error_msg],
                processing_time=time.time() - start_time,
                alerts_generated=0
            )
    
    async def process_system_event(self, event_data: Dict) -> ProcessingResult:
        """Process system-level events."""
        
        try:
            event_type = event_data.get('event_type')
            data = event_data.get('data', {})
            
            # Handle different system events
            if event_type == 'model_retrained':
                await self.handle_model_retrain_event(data)
            elif event_type == 'bulk_import_completed':
                await self.handle_bulk_import_event(data)
            elif event_type == 'system_health_check':
                await self.handle_health_check_event(data)
            
            self.metrics['events_processed'] += 1
            
            return ProcessingResult(
                success=True,
                processed_events=1,
                errors=[],
                processing_time=0.1,
                alerts_generated=0
            )
            
        except Exception as e:
            logger.error(f"System event processing failed: {e}")
            self.metrics['events_failed'] += 1
            
            return ProcessingResult(
                success=False,
                processed_events=0,
                errors=[str(e)],
                processing_time=0.1,
                alerts_generated=0
            )
    
    async def update_realtime_analytics(self, product_id: str, store_id: str, quantity: int, timestamp: datetime):
        """Update real-time analytics aggregations."""
        
        try:
            # Redis keys for real-time metrics
            daily_key = f"analytics:daily:{product_id}:{store_id}:{timestamp.date()}"
            hourly_key = f"analytics:hourly:{product_id}:{store_id}:{timestamp.strftime('%Y-%m-%d-%H')}"
            
            # Update daily aggregations
            self.redis.hincrby(daily_key, 'total_quantity', quantity)
            self.redis.hincrby(daily_key, 'transaction_count', 1)
            self.redis.expire(daily_key, 86400 * 7)  # Keep for 7 days
            
            # Update hourly aggregations
            self.redis.hincrby(hourly_key, 'total_quantity', quantity)
            self.redis.hincrby(hourly_key, 'transaction_count', 1)
            self.redis.expire(hourly_key, 86400)  # Keep for 1 day
            
            # Update moving averages
            window_key = f"moving_avg:{product_id}:{store_id}"
            self.redis.lpush(window_key, quantity)
            self.redis.ltrim(window_key, 0, 29)  # Keep last 30 values
            self.redis.expire(window_key, 86400)
            
        except Exception as e:
            logger.error(f"Real-time analytics update failed: {e}")
    
    async def update_inventory_levels(self, product_id: str, store_id: str, quantity_sold: int) -> bool:
        """Update inventory levels after sale."""
        
        try:
            # Update database
            query = """
            UPDATE inventory 
            SET current_stock = GREATEST(current_stock - %s, 0),
                last_updated = %s
            WHERE product_id = %s AND store_id = %s
            RETURNING current_stock
            """
            
            cursor = self.db.cursor()
            cursor.execute(query, (quantity_sold, datetime.now(), product_id, store_id))
            result = cursor.fetchone()
            self.db.commit()
            cursor.close()
            
            if result:
                new_stock = result[0]
                
                # Update Redis cache
                cache_key = f"inventory:{product_id}:{store_id}"
                self.redis.hset(cache_key, 'current_stock', new_stock)
                self.redis.hset(cache_key, 'last_updated', datetime.now().isoformat())
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Inventory level update failed: {e}")
            return False
    
    async def check_transaction_alerts(self, product_id: str, store_id: str, quantity: int) -> List[Dict]:
        """Check for alert conditions after transaction."""
        
        alerts = []
        
        try:
            # Get current inventory
            cache_key = f"inventory:{product_id}:{store_id}"
            current_stock = self.redis.hget(cache_key, 'current_stock')
            
            if current_stock:
                current_stock = int(current_stock)
                
                # Check for low stock alerts
                if current_stock <= 5:  # Configurable threshold
                    alerts.append({
                        'alert_id': f"low_stock_{product_id}_{store_id}_{int(time.time())}",
                        'alert_type': 'LOW_STOCK',
                        'severity': 'HIGH' if current_stock <= 2 else 'MEDIUM',
                        'product_id': product_id,
                        'store_id': store_id,
                        'current_stock': current_stock,
                        'message': f'Low stock alert: {current_stock} units remaining',
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Check for demand spike
                avg_key = f"moving_avg:{product_id}:{store_id}"
                recent_sales = self.redis.lrange(avg_key, 0, 9)  # Last 10 sales
                
                if len(recent_sales) >= 5:
                    recent_avg = sum(int(x) for x in recent_sales) / len(recent_sales)
                    
                    if quantity > recent_avg * 2:  # 2x average
                        alerts.append({
                            'alert_id': f"demand_spike_{product_id}_{store_id}_{int(time.time())}",
                            'alert_type': 'DEMAND_SPIKE',
                            'severity': 'MEDIUM',
                            'product_id': product_id,
                            'store_id': store_id,
                            'quantity': quantity,
                            'average': recent_avg,
                            'spike_ratio': quantity / recent_avg,
                            'message': f'Demand spike detected: {quantity} vs avg {recent_avg:.1f}',
                            'timestamp': datetime.now().isoformat()
                        })
            
        except Exception as e:
            logger.error(f"Alert checking failed: {e}")
        
        return alerts
    
    async def check_inventory_alerts(self, product_id: str, store_id: str, new_stock: int) -> List[Dict]:
        """Check for inventory-related alerts."""
        
        alerts = []
        
        try:
            # Get reorder point
            query = "SELECT reorder_point, max_stock_level FROM inventory WHERE product_id = %s AND store_id = %s"
            cursor = self.db.cursor()
            cursor.execute(query, (product_id, store_id))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                reorder_point, max_stock = result
                
                # Stockout alert
                if new_stock <= 0:
                    alerts.append({
                        'alert_id': f"stockout_{product_id}_{store_id}_{int(time.time())}",
                        'alert_type': 'STOCKOUT',
                        'severity': 'CRITICAL',
                        'product_id': product_id,
                        'store_id': store_id,
                        'current_stock': new_stock,
                        'message': 'CRITICAL: Product is out of stock',
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Reorder alert
                elif reorder_point and new_stock <= reorder_point:
                    alerts.append({
                        'alert_id': f"reorder_{product_id}_{store_id}_{int(time.time())}",
                        'alert_type': 'REORDER_NEEDED',
                        'severity': 'HIGH',
                        'product_id': product_id,
                        'store_id': store_id,
                        'current_stock': new_stock,
                        'reorder_point': reorder_point,
                        'message': f'Reorder needed: {new_stock} <= {reorder_point}',
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Overstock alert  
                elif max_stock and new_stock >= max_stock * 1.2:
                    alerts.append({
                        'alert_id': f"overstock_{product_id}_{store_id}_{int(time.time())}",
                        'alert_type': 'OVERSTOCK',
                        'severity': 'LOW',
                        'product_id': product_id,
                        'store_id': store_id,
                        'current_stock': new_stock,
                        'max_stock': max_stock,
                        'message': f'Overstock detected: {new_stock} >= {max_stock * 1.2}',
                        'timestamp': datetime.now().isoformat()
                    })
            
        except Exception as e:
            logger.error(f"Inventory alert checking failed: {e}")
        
        return alerts
    
    async def update_ml_features(self, product_id: str, store_id: str, transaction: Dict):
        """Update ML feature store with new transaction data."""
        
        try:
            # Update feature aggregations in Redis
            feature_key = f"ml_features:{product_id}:{store_id}"
            
            # Update transaction count
            self.redis.hincrby(feature_key, 'transaction_count', 1)
            
            # Update revenue
            amount = transaction.get('total_amount', 0)
            self.redis.hincrbyfloat(feature_key, 'total_revenue', amount)
            
            # Update last transaction timestamp
            self.redis.hset(feature_key, 'last_transaction', datetime.now().isoformat())
            
            # Set expiration
            self.redis.expire(feature_key, 86400 * 30)  # Keep for 30 days
            
        except Exception as e:
            logger.error(f"ML feature update failed: {e}")
    
    async def start_stream_processing(self):
        """Start the streaming pipeline."""
        
        self.running = True
        logger.info("🚀 Starting Kafka stream processing...")
        
        # Start consumer threads
        consumer_threads = []
        
        for topic_name, consumer in self.consumers.items():
            thread = threading.Thread(
                target=self.consumer_loop,
                args=(topic_name, consumer),
                daemon=True
            )
            thread.start()
            consumer_threads.append(thread)
            logger.info(f"✅ Started consumer thread for {topic_name}")
        
        # Start metrics collection
        metrics_thread = threading.Thread(target=self.metrics_collection_loop, daemon=True)
        metrics_thread.start()
        
        logger.info("✅ Kafka streaming pipeline started successfully")
        return consumer_threads
    
    def consumer_loop(self, topic_name: str, consumer: KafkaConsumer):
        """Main consumer processing loop."""
        
        logger.info(f"🔄 Consumer loop started for {topic_name}")
        
        while self.running:
            try:
                # Poll for messages
                message_batch = consumer.poll(timeout_ms=1000)
                
                if message_batch:
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            try:
                                # Process message
                                event_data = message.value
                                handler = self.event_handlers.get(topic_name)
                                
                                if handler:
                                    # Run handler asynchronously
                                    future = self.executor.submit(
                                        asyncio.run,
                                        handler(event_data)
                                    )
                                    
                                    # Don't wait for completion to maintain throughput
                                    # Results will be logged by the handler
                                
                                else:
                                    logger.warning(f"No handler for topic: {topic_name}")
                                
                            except Exception as e:
                                logger.error(f"Message processing error in {topic_name}: {e}")
                        
                        # Commit offsets
                        consumer.commit()
                
            except Exception as e:
                logger.error(f"Consumer loop error in {topic_name}: {e}")
                time.sleep(5)  # Brief pause before retry
    
    def metrics_collection_loop(self):
        """Collect and publish processing metrics."""
        
        while self.running:
            try:
                # Calculate metrics
                avg_latency = (
                    sum(self.metrics['processing_latency'][-100:]) / 
                    len(self.metrics['processing_latency'][-100:])
                    if self.metrics['processing_latency'] else 0
                )
                
                metrics_data = {
                    'events_processed': self.metrics['events_processed'],
                    'events_failed': self.metrics['events_failed'],
                    'avg_processing_latency_ms': avg_latency * 1000,
                    'alerts_generated': self.metrics['alerts_generated'],
                    'throughput_per_minute': self.metrics['events_processed'],  # Simplified
                    'timestamp': datetime.now().isoformat()
                }
                
                # Store in Redis
                self.redis.hmset('streaming_metrics', metrics_data)
                self.redis.expire('streaming_metrics', 300)  # 5 minute TTL
                
                # Reset counters (keep running totals)
                self.metrics['processing_latency'] = self.metrics['processing_latency'][-100:]  # Keep last 100
                
                time.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(60)
    
    def stop_stream_processing(self):
        """Stop the streaming pipeline."""
        
        logger.info("🛑 Stopping Kafka stream processing...")
        self.running = False
        
        # Close consumers
        for consumer in self.consumers.values():
            consumer.close()
        
        # Close producer
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("✅ Kafka streaming pipeline stopped")
    
    def get_processing_metrics(self) -> Dict:
        """Get current processing metrics."""
        
        return {
            'events_processed': self.metrics['events_processed'],
            'events_failed': self.metrics['events_failed'],
            'success_rate': (
                (self.metrics['events_processed'] / 
                 (self.metrics['events_processed'] + self.metrics['events_failed'])) * 100
                if (self.metrics['events_processed'] + self.metrics['events_failed']) > 0 else 0
            ),
            'avg_latency_ms': (
                sum(self.metrics['processing_latency'][-100:]) * 1000 / 
                len(self.metrics['processing_latency'][-100:])
                if self.metrics['processing_latency'] else 0
            ),
            'alerts_generated': self.metrics['alerts_generated'],
            'active_consumers': len(self.consumers),
            'last_updated': datetime.now().isoformat()
        }

# Example usage and configuration
if __name__ == "__main__":
    # Configuration
    kafka_config = {
        'bootstrap_servers': ['localhost:9092']
    }
    
    # Database connection
    db_conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='retailai',
        user='retailai',
        password='retailai123'
    )
    
    # Initialize stream processor
    stream_processor = KafkaStreamProcessor(kafka_config, db_conn)
    
    # Start processing
    asyncio.run(stream_processor.start_stream_processing())
    
    try:
        # Keep running
        while True:
            time.sleep(60)
            metrics = stream_processor.get_processing_metrics()
            logger.info(f"📊 Processing metrics: {metrics}")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stream_processor.stop_stream_processing()