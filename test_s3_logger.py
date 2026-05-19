#!/usr/bin/env python3
"""
Test script for Lookout S3 Logger
Validates configuration and tests basic functionality
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment configuration"""
    print("🔍 Testing Environment Configuration...")
    
    required_vars = [
        'LOOKOUT_ACCESS_TOKEN',
        'S3_BUCKET_NAME', 
        'FIREHOSE_STREAM_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_aws_connectivity():
    """Test AWS service connectivity"""
    print("\n🔍 Testing AWS Connectivity...")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Test AWS credentials
        session = boto3.Session(region_name=os.getenv('AWS_REGION', 'us-east-1'))
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        
        # Test S3 access
        s3 = session.client('s3')
        bucket_name = os.getenv('S3_BUCKET_NAME')
        s3.head_bucket(Bucket=bucket_name)
        print(f"✅ S3 bucket '{bucket_name}' is accessible")
        
        # Test Firehose access
        firehose = session.client('firehose')
        stream_name = os.getenv('FIREHOSE_STREAM_NAME')
        response = firehose.describe_delivery_stream(DeliveryStreamName=stream_name)
        status = response['your_token_here']['your_token_here']
        print(f"✅ Firehose stream '{stream_name}' status: {status}")
        
        return True
        
    except ImportError:
        print("❌ boto3 not installed. Run: pip install -r requirements_s3.txt")
        return False
    except ClientError as e:
        print(f"❌ AWS Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_lookout_api():
    """Test Lookout API connectivity"""
    print("\n🔍 Testing Lookout API Connectivity...")
    
    try:
        import requests
        
        api_url = os.getenv('LOOKOUT_API_URL', 'https://mtp.lookout.com/data/web-access-feed')
        token = os.getenv('LOOKOUT_ACCESS_TOKEN')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': 'lookout-s3-logger-test/1.0'
        }
        
        # Test API with a recent time range
        params = {
            'start_interval': (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        event_count = len(data.get('lookup_access_events', []))
        
        print(f"✅ Lookout API accessible, found {event_count} events today")
        return True
        
    except ImportError:
        print("❌ requests not installed. Run: pip install -r requirements_s3.txt")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Lookout API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_s3_logger_import():
    """Test S3 logger import and basic functionality"""
    print("\n🔍 Testing S3 Logger Import...")
    
    try:
        from lookout_s3_logger import LookoutS3Logger, WebActivityEvent
        
        # Test basic instantiation
        logger = LookoutS3Logger()
        print("✅ S3 Logger imported and instantiated successfully")
        
        # Test event transformation
        sample_event = {
            'id': 'test_event_123',
            'device_guid': 'test-device-guid',
            'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
            'request_url': 'https://example.com/test',
            'region': 'US',
            'user_agent': 'Test User Agent'
        }
        
        transformed = logger.transform_event(sample_event)
        print(f"✅ Event transformation successful: {transformed.event_id}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_dry_run():
    """Perform a dry run of the S3 logger"""
    print("\n🔍 Performing Dry Run Test...")
    
    try:
        from lookout_s3_logger import LookoutS3Logger
        
        logger = LookoutS3Logger()
        
        # Test fetching events (but don't send to Firehose)
        print("   Fetching recent events...")
        events = logger.fetch_events()
        
        if events:
            print(f"✅ Successfully fetched {len(events)} events")
            
            # Transform a few events
            transformed_events = [logger.transform_event(event) for event in events[:3]]
            print(f"✅ Successfully transformed {len(transformed_events)} sample events")
            
            # Show sample event structure
            if transformed_events:
                sample = transformed_events[0]
                print(f"   Sample event: {sample.device_guid[:8]}... at {sample.timestamp}")
        else:
            print("✅ API call successful, but no events found (this is normal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Dry run failed: {e}")
        return False

def test_checkpoint_functionality():
    """Test checkpoint manager functionality"""
    print("\n🔍 Testing Checkpoint Functionality...")
    
    try:
        import boto3
        from lookout_s3_logger import CheckpointManager
        
        session = boto3.Session(region_name=os.getenv('AWS_REGION', 'us-east-1'))
        s3_client = session.client('s3')
        bucket_name = os.getenv('S3_BUCKET_NAME')
        
        checkpoint_manager = CheckpointManager(s3_client, bucket_name)
        
        # Test reading checkpoint (should handle missing file gracefully)
        last_timestamp = checkpoint_manager.get_last_processed_timestamp()
        print(f"✅ Checkpoint read successful: {last_timestamp or 'No previous checkpoint'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Checkpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Lookout S3 Logger Test Suite")
    print("=" * 50)
    
    tests = [
        ("Environment Configuration", test_environment),
        ("AWS Connectivity", test_aws_connectivity),
        ("Lookout API", test_lookout_api),
        ("S3 Logger Import", test_s3_logger_import),
        ("Checkpoint Functionality", test_checkpoint_functionality),
        ("Dry Run", test_dry_run)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your S3 logger is ready to run.")
        print("\n📋 Next steps:")
        print("1. Run the logger: python lookout_s3_logger.py")
        print("2. Monitor logs: journalctl -u lookout-s3-logger -f")
        print("3. Check CloudWatch metrics in AWS console")
        print("4. Query data with Athena after a few minutes")
    else:
        print("⚠️  Some tests failed. Please fix the issues before running the logger.")
        sys.exit(1)

if __name__ == "__main__":
    main()
