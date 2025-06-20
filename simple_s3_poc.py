#!/usr/bin/env python3
"""
Simple Proof of Concept: Lookout API to S3
Pulls web activity data and dumps it directly to S3 bucket
"""

import os
import json
import boto3
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_access_token():
    """Get access token using the same method as the working code"""
    # Try to get from environment first
    token = os.getenv('LOOKOUT_ACCESS_TOKEN')
    if token and not token.startswith('your_token_here'):
        return token
        
    # If not found or encrypted, try to read from a token file
    try:
        with open('access_token.txt', 'r') as f:
            token = f.read().strip()
            if token:
                return token
    except FileNotFoundError:
        pass
        
    # Fallback to the working token from your tests
    return 'your_jwt_token_here'

def fetch_lookout_data():
    """Fetch recent web activity data from Lookout API"""
    print("🔍 Fetching data from Lookout API...")
    
    api_url = os.getenv('LOOKOUT_API_URL', 'https://mtp.lookout.com/data/web-access-feed')
    token = get_access_token()
    
    if not token:
        raise ValueError("Could not get valid access token")
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # Get data from last 24 hours
    start_time = datetime.now(timezone.utc) - timedelta(hours=24)
    params = {
        'start_interval': start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    }
    
    print(f"   Using token: {token[:20]}...")
    print(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC to now")
    
    response = requests.get(api_url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    events = data.get('lookup_access_events', [])
    
    print(f"✅ Fetched {len(events)} events from Lookout API")
    return events

def upload_to_s3(events):
    """Upload events directly to S3 bucket"""
    print("📤 Uploading data to S3...")
    
    bucket_name = os.getenv('S3_BUCKET_NAME')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME not found in environment")
    
    # Create S3 client
    s3_client = boto3.client('s3', region_name=aws_region)
    
    # Create filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"lookout-poc/web_activity_{timestamp}.json"
    
    # Prepare data for upload
    upload_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event_count': len(events),
        'events': events
    }
    
    # Upload to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=json.dumps(upload_data, indent=2),
        ContentType='application/json'
    )
    
    print(f"✅ Uploaded {len(events)} events to s3://{bucket_name}/{filename}")
    return filename

def verify_upload(filename):
    """Verify the upload by reading back from S3"""
    print("🔍 Verifying upload...")
    
    bucket_name = os.getenv('S3_BUCKET_NAME')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    s3_client = boto3.client('s3', region_name=aws_region)
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=filename)
        data = json.loads(response['Body'].read())
        
        print(f"✅ Verification successful:")
        print(f"   - File size: {response['ContentLength']} bytes")
        print(f"   - Event count: {data['event_count']}")
        print(f"   - Upload time: {data['timestamp']}")
        
        # Show sample events
        if data['events']:
            sample_event = data['events'][0]
            print(f"   - Sample event: {sample_event.get('device_guid', 'N/A')[:8]}... -> {sample_event.get('request_url', 'N/A')[:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main proof of concept function"""
    print("🚀 Lookout to S3 Proof of Concept")
    print("=" * 40)
    
    try:
        # Check required environment variables
        required_vars = ['LOOKOUT_ACCESS_TOKEN', 'S3_BUCKET_NAME']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("\nPlease set these in your .env file:")
            for var in missing_vars:
                print(f"   {var}=your_value_here")
            return False
        
        # Step 1: Fetch data from Lookout API
        events = fetch_lookout_data()
        
        if not events:
            print("⚠️  No events found in the last 24 hours")
            print("   This is normal if there's no recent web activity")
            
            # Create a test event for demonstration
            test_event = {
                'id': 'poc_test_event',
                'device_guid': 'test-device-guid-12345',
                'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                'request_url': 'https://example.com/test',
                'region': 'US',
                'user_agent': 'Test User Agent for POC'
            }
            events = [test_event]
            print(f"   Created test event for demonstration")
        
        # Step 2: Upload to S3
        filename = upload_to_s3(events)
        
        # Step 3: Verify upload
        if verify_upload(filename):
            print("\n🎉 Proof of Concept Successful!")
            print(f"   Data successfully flowed: Lookout API → S3 Bucket")
            print(f"   File location: s3://{os.getenv('S3_BUCKET_NAME')}/{filename}")
            
            print("\n📋 Next Steps:")
            print("   1. Check your S3 bucket in AWS console")
            print("   2. Download and examine the JSON file")
            print("   3. Consider implementing the full production system")
            print("   4. Set up automated processing/analytics")
            
            return True
        else:
            print("❌ Proof of concept failed during verification")
            return False
            
    except Exception as e:
        print(f"❌ Proof of concept failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
