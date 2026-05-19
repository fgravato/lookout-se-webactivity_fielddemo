#!/usr/bin/env python3
"""
Lookout Web Activity S3 Logger - Background Service
Continuously fetches web activity events from Lookout API and streams them to S3
via Kinesis Data Firehose for security analytics.
"""

import os
import sys
import json
import time
import logging
import signal
import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException

# Load environment variables
load_dotenv()

@dataclass
class WebActivityEvent:
    """Structured representation of a web activity event"""
    event_id: str
    device_guid: str
    timestamp: str
    request_url: str
    region: str
    user_agent: Optional[str] = None
    response_code: Optional[int] = None
    bytes_transferred: Optional[int] = None
    ingestion_time: str = None
    partition_date: str = None
    
    def __post_init__(self):
        if not self.ingestion_time:
            self.ingestion_time = datetime.now(timezone.utc).isoformat()
        if not self.partition_date:
            # Extract date from timestamp for partitioning
            try:
                ts = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
                self.partition_date = ts.strftime('%Y-%m-%d')
            except:
                self.partition_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

class CheckpointManager:
    """Manages processing state to prevent data loss and duplication"""
    
    def __init__(self, s3_client, bucket_name: str, checkpoint_key: str = "_checkpoints/last_processed.json"):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.checkpoint_key = checkpoint_key
        
    def get_last_processed_timestamp(self) -> Optional[str]:
        """Retrieve the last processed timestamp from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.checkpoint_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data.get('last_processed_timestamp')
        except self.s3_client.exceptions.NoSuchKey:
            logging.info("No checkpoint found, starting from current time")
            return None
        except Exception as e:
            logging.error(f"Error reading checkpoint: {e}")
            return None
    
    def update_last_processed_timestamp(self, timestamp: str):
        """Update the last processed timestamp in S3"""
        try:
            checkpoint_data = {
                'last_processed_timestamp': timestamp,
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'service': 'lookout-s3-logger'
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.checkpoint_key,
                Body=json.dumps(checkpoint_data, indent=2),
                ContentType='application/json'
            )
            logging.debug(f"Updated checkpoint to {timestamp}")
        except Exception as e:
            logging.error(f"Error updating checkpoint: {e}")
            raise

class LookoutS3Logger:
    """Main service class for streaming Lookout web activity to S3"""
    
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.setup_aws_clients()
        self.checkpoint_manager = CheckpointManager(self.s3_client, self.s3_bucket)
        self.running = True
        self.event_buffer = []
        self.buffer_size_limit = self.config.get('buffer_size_limit', 500)
        self.buffer_time_limit = self.config.get('buffer_time_limit', 300)  # 5 minutes
        self.last_flush_time = time.time()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def setup_logging(self):
        """Configure logging for the service"""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('/var/log/lookout-s3-logger.log') if os.path.exists('/var/log') else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger('lookout-s3-logger')
        
    def load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            'lookout_api_url': os.getenv('LOOKOUT_API_URL', 'https://mtp.lookout.com/data/web-access-feed'),
            'lookout_access_token': self._get_access_token(),
            'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
            's3_bucket': os.getenv('S3_BUCKET_NAME'),
            'firehose_stream_name': os.getenv('FIREHOSE_STREAM_NAME'),
            'poll_interval': int(os.getenv('POLL_INTERVAL', '300')),  # 5 minutes default
            'buffer_size_limit': int(os.getenv('BUFFER_SIZE_LIMIT', '500')),
            'buffer_time_limit': int(os.getenv('BUFFER_TIME_LIMIT', '300')),
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'retry_delay': int(os.getenv('RETRY_DELAY', '60'))
        }
        
        # Validate required configuration
        required_configs = ['lookout_access_token', 's3_bucket', 'firehose_stream_name']
        missing_configs = [key for key in required_configs if not self.config.get(key)]
        
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
        
        self.s3_bucket = self.config['s3_bucket']
        self.firehose_stream = self.config['firehose_stream_name']
        
    def _get_access_token(self) -> str:
        """Get Lookout access token from environment or file"""
        token = os.getenv('LOOKOUT_ACCESS_TOKEN')
        if token:
            return token
            
        try:
            with open('access_token.txt', 'r') as f:
                token = f.read().strip()
                if token:
                    return token
        except FileNotFoundError:
            pass
            
        raise ValueError("No Lookout access token found. Set LOOKOUT_ACCESS_TOKEN environment variable or create access_token.txt file")
    
    def setup_aws_clients(self):
        """Initialize AWS service clients"""
        try:
            session = boto3.Session(region_name=self.config['aws_region'])
            self.s3_client = session.client('s3')
            self.firehose_client = session.client('firehose')
            self.cloudwatch = session.client('cloudwatch')
            
            # Test AWS connectivity
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            self.firehose_client.describe_delivery_stream(DeliveryStreamName=self.firehose_stream)
            
            self.logger.info("AWS clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def fetch_events(self, start_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch events from Lookout API"""
        headers = {
            'Authorization': f'Bearer {self.config["lookout_access_token"]}',
            'User-Agent': 'lookout-s3-logger/1.0'
        }
        
        params = {}
        if start_time:
            params['start_interval'] = start_time
        
        try:
            response = requests.get(
                self.config['lookout_api_url'],
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            events = data.get('lookup_access_events', [])
            
            self.logger.info(f"Fetched {len(events)} events from Lookout API")
            return events
            
        except RequestException as e:
            self.logger.error(f"Failed to fetch events from Lookout API: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            raise
    
    def transform_event(self, raw_event: Dict[str, Any]) -> WebActivityEvent:
        """Transform raw API event to structured format"""
        # Convert timestamp from milliseconds to ISO format
        timestamp_ms = raw_event.get('timestamp', 0)
        timestamp_iso = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
        
        return WebActivityEvent(
            event_id=raw_event.get('id', ''),
            device_guid=raw_event.get('device_guid', ''),
            timestamp=timestamp_iso,
            request_url=raw_event.get('request_url', ''),
            region=raw_event.get('region', ''),
            user_agent=raw_event.get('user_agent'),
            response_code=raw_event.get('response_code'),
            bytes_transferred=raw_event.get('bytes_transferred')
        )
    
    def add_to_buffer(self, events: List[WebActivityEvent]):
        """Add events to the local buffer"""
        self.event_buffer.extend(events)
        self.logger.debug(f"Added {len(events)} events to buffer. Buffer size: {len(self.event_buffer)}")
        
        # Check if we need to flush
        if (len(self.event_buffer) >= self.buffer_size_limit or 
            time.time() - self.last_flush_time >= self.buffer_time_limit):
            self.flush_buffer()
    
    def flush_buffer(self):
        """Send buffered events to Kinesis Data Firehose"""
        if not self.event_buffer:
            return
        
        try:
            # Prepare records for Firehose
            records = []
            for event in self.event_buffer:
                record_data = json.dumps(asdict(event)) + '\n'  # Newline-delimited JSON
                records.append({
                    'Data': record_data.encode('utf-8')
                })
            
            # Send to Firehose in batches (max 500 records per batch)
            batch_size = 500
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                response = self.firehose_client.put_record_batch(
                    DeliveryStreamName=self.firehose_stream,
                    Records=batch
                )
                
                # Check for failed records
                failed_count = response.get('FailedPutCount', 0)
                if failed_count > 0:
                    self.logger.warning(f"Failed to send {failed_count} records to Firehose")
                
                self.logger.info(f"Sent batch of {len(batch)} records to Firehose")
            
            # Send metrics to CloudWatch
            self.send_metrics(len(self.event_buffer))
            
            # Clear buffer and update timestamp
            self.event_buffer.clear()
            self.last_flush_time = time.time()
            
            self.logger.info(f"Successfully flushed {len(records)} events to S3 via Firehose")
            
        except Exception as e:
            self.logger.error(f"Failed to flush buffer to Firehose: {e}")
            raise
    
    def send_metrics(self, event_count: int):
        """Send metrics to CloudWatch"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace='LookoutS3Logger',
                MetricData=[
                    {
                        'MetricName': 'EventsProcessed',
                        'Value': event_count,
                        'Unit': 'Count',
                        'Timestamp': datetime.now(timezone.utc)
                    },
                    {
                        'MetricName': 'ServiceHealth',
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.now(timezone.utc)
                    }
                ]
            )
        except Exception as e:
            self.logger.warning(f"Failed to send metrics to CloudWatch: {e}")
    
    def run_once(self):
        """Execute one iteration of the polling loop"""
        try:
            # Get last processed timestamp
            start_time = self.checkpoint_manager.get_last_processed_timestamp()
            
            # If no checkpoint, start from 1 hour ago to avoid overwhelming initial load
            if not start_time:
                start_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            
            # Fetch events
            raw_events = self.fetch_events(start_time)
            
            if raw_events:
                # Transform events
                transformed_events = [self.transform_event(event) for event in raw_events]
                
                # Add to buffer
                self.add_to_buffer(transformed_events)
                
                # Update checkpoint with the latest event timestamp
                latest_timestamp = max(event.timestamp for event in transformed_events)
                self.checkpoint_manager.update_last_processed_timestamp(latest_timestamp)
                
                self.logger.info(f"Processed {len(transformed_events)} events, latest timestamp: {latest_timestamp}")
            else:
                self.logger.info("No new events found")
                
        except Exception as e:
            self.logger.error(f"Error in run_once: {e}")
            # Send error metric
            try:
                self.cloudwatch.put_metric_data(
                    Namespace='LookoutS3Logger',
                    MetricData=[{
                        'MetricName': 'Errors',
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.now(timezone.utc)
                    }]
                )
            except:
                pass
            raise
    
    def run(self):
        """Main service loop"""
        self.logger.info("Starting Lookout S3 Logger service")
        self.logger.info(f"Configuration: S3 bucket={self.s3_bucket}, Firehose stream={self.firehose_stream}")
        self.logger.info(f"Poll interval: {self.config['poll_interval']} seconds")
        
        retry_count = 0
        max_retries = self.config['max_retries']
        retry_delay = self.config['retry_delay']
        
        while self.running:
            try:
                self.run_once()
                retry_count = 0  # Reset retry count on success
                
                # Wait for next poll interval
                time.sleep(self.config['poll_interval'])
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                break
                
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    self.logger.warning(f"Error occurred (attempt {retry_count}/{max_retries}): {e}")
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Max retries ({max_retries}) exceeded. Shutting down.")
                    break
        
        # Graceful shutdown - flush any remaining events
        if self.event_buffer:
            self.logger.info("Flushing remaining events before shutdown...")
            try:
                self.flush_buffer()
            except Exception as e:
                self.logger.error(f"Error during final flush: {e}")
        
        self.logger.info("Lookout S3 Logger service stopped")

def main():
    """Entry point for the service"""
    try:
        logger = LookoutS3Logger()
        logger.run()
    except Exception as e:
        logging.error(f"Failed to start service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
