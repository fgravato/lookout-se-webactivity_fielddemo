#!/usr/bin/env python3
"""
Demo Version of Lookout API Client with Simulated Data
This version provides fake data for demonstrations when the real API is unavailable
"""

import os
import sys
import argparse
import json
import time
import random
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from tabulate import tabulate

# Import our device database for user mapping
try:
    from device_database import DeviceDatabase
    DEVICE_MAPPING_AVAILABLE = True
except ImportError:
    DEVICE_MAPPING_AVAILABLE = False
    print("⚠️  Device mapping not available. Run 'pip install' and ensure device_database.py exists.")

# Load environment variables
load_dotenv()

class LookoutAPIClientDemo:
    """
    Demo version of Lookout API Client with simulated data
    Perfect for demonstrations when the real API is unavailable
    """
    
    def __init__(self, enable_device_mapping=True, timeout=120, max_retries=3):
        # API endpoints (demo mode)
        self.web_access_feed_url = 'https://mtp.lookout.com/data/web-access-feed'
        self.oauth_url = 'https://api.lookout.com/oauth2/token'
        self.mra_base_url = 'https://api.lookout.com'
        
        # Request configuration
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Demo mode indicator
        self.demo_mode = True
        
        # Authentication (simulated)
        self.application_key = "demo_application_key_12345"
        self.access_token = "demo_access_token_abcdef123456"
        
        # Device mapping
        self.device_db = None
        if enable_device_mapping and DEVICE_MAPPING_AVAILABLE:
            try:
                self.device_db = DeviceDatabase()
                print("✅ Device mapping database connected (demo mode)")
            except Exception as e:
                print(f"⚠️  Device mapping database unavailable: {e}")
        
        print("🎭 DEMO MODE: Using simulated data for demonstration")

    def _generate_fake_device_guid(self):
        """Generate a realistic-looking device GUID"""
        import uuid
        return str(uuid.uuid4())

    def _generate_fake_web_access_events(self, count=10):
        """Generate fake web access events for demo"""
        events = []
        
        # Sample URLs and regions for realistic demo data
        sample_urls = [
            "https://www.google.com/search?q=security+best+practices",
            "https://github.com/company/project",
            "https://stackoverflow.com/questions/python-security",
            "https://docs.aws.amazon.com/s3/",
            "https://www.linkedin.com/in/johndoe",
            "https://mail.google.com/mail/u/0/",
            "https://calendar.google.com/calendar/",
            "https://drive.google.com/drive/my-drive",
            "https://www.salesforce.com/products/",
            "https://app.slack.com/client/"
        ]
        
        regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        
        # Sample user emails
        sample_emails = [
            "john.doe@company.com",
            "jane.smith@company.com", 
            "mike.johnson@company.com",
            "sarah.wilson@company.com",
            "david.brown@company.com"
        ]
        
        platforms = ["ANDROID", "IOS"]
        security_statuses = ["SECURE", "AT_RISK", "COMPROMISED"]
        
        base_time = datetime.now(timezone.utc)
        
        for i in range(count):
            # Generate timestamp within last 24 hours
            hours_ago = random.randint(0, 24)
            minutes_ago = random.randint(0, 59)
            event_time = base_time - timedelta(hours=hours_ago, minutes=minutes_ago)
            timestamp_ms = int(event_time.timestamp() * 1000)
            
            device_guid = self._generate_fake_device_guid()
            user_email = random.choice(sample_emails)
            
            event = {
                "timestamp": timestamp_ms,
                "device_guid": device_guid,
                "region": random.choice(regions),
                "request_url": random.choice(sample_urls),
                "user_email": user_email,
                "platform": random.choice(platforms),
                "security_status": random.choice(security_statuses)
            }
            events.append(event)
        
        return events

    def _generate_fake_mra_devices(self, count=10):
        """Generate fake MRA device data for demo"""
        devices = []
        
        sample_emails = [
            "john.doe@company.com",
            "jane.smith@company.com", 
            "mike.johnson@company.com",
            "sarah.wilson@company.com",
            "david.brown@company.com"
        ]
        
        platforms = ["ANDROID", "IOS"]
        security_statuses = ["SECURE", "AT_RISK", "COMPROMISED"]
        protection_statuses = ["PROTECTED", "UNPROTECTED", "PARTIAL"]
        activation_statuses = ["ACTIVATED", "PENDING", "DEACTIVATED"]
        
        for i in range(count):
            device = {
                "guid": self._generate_fake_device_guid(),
                "email": random.choice(sample_emails),
                "platform": random.choice(platforms),
                "security_status": random.choice(security_statuses),
                "protection_status": random.choice(protection_statuses),
                "activation_status": random.choice(activation_statuses)
            }
            devices.append(device)
        
        return {"devices": devices, "count": len(devices)}

    def fetch_web_access_events(self, start_time=None, include_user_mapping=True):
        """Fetch simulated web access events"""
        print("🎭 Simulating API call to Web Access Feed...")
        
        # Simulate API delay
        time.sleep(random.uniform(1, 3))
        
        # Generate fake events
        events = self._generate_fake_web_access_events(count=random.randint(5, 15))
        
        events_data = {
            "lookup_access_events": events,
            "demo_mode": True,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add mapping stats if user mapping is enabled
        if include_user_mapping:
            events_data["user_mapping_stats"] = {
                "mapped": len(events),
                "unmapped": 0
            }
        
        print(f"✅ Generated {len(events)} demo web access events")
        return events_data

    def fetch_mra_devices(self, limit=10):
        """Fetch simulated MRA device data"""
        print("🎭 Simulating API call to MRA Devices...")
        
        # Simulate API delay
        time.sleep(random.uniform(1, 2))
        
        # Generate fake devices
        devices_data = self._generate_fake_mra_devices(count=min(limit, 15))
        
        print(f"✅ Generated {len(devices_data['devices'])} demo devices")
        return devices_data

def format_web_access_events(events, limit=None, include_user_mapping=True):
    """Format web access events into a readable table with demo indicator"""
    if not events.get('lookup_access_events'):
        return "No web access events found"
    
    table_data = []
    
    for event in events['lookup_access_events'][:limit]:
        timestamp_ms = event['timestamp']
        readable_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        row = [
            readable_time,
            event['device_guid'][:8] + '...' + event['device_guid'][-3:],
            event.get('user_email', 'Unknown')[:25],
            event.get('platform', 'N/A'),
            event['region'],
            event['request_url'][:40] + '...' if len(event['request_url']) > 40 else event['request_url'],
            event.get('security_status', 'N/A')
        ]
        
        table_data.append(row)
    
    headers = ['Timestamp', 'Device', 'User Email', 'Platform', 'Region', 'URL', 'Security']
    maxcolwidths = [None, 15, 25, 10, None, 43, 12]
    
    table = tabulate(
        table_data,
        headers=headers,
        tablefmt='fancy_grid',
        maxcolwidths=maxcolwidths
    )
    
    # Add demo indicator and mapping statistics
    demo_note = "\n🎭 DEMO DATA - Simulated for demonstration purposes"
    if events.get('user_mapping_stats'):
        stats = events['user_mapping_stats']
        total = stats['mapped'] + stats['unmapped']
        mapping_rate = (stats['mapped'] / total * 100) if total > 0 else 0
        demo_note += f"\n📊 User Mapping: {stats['mapped']}/{total} events mapped ({mapping_rate:.1f}%)"
    
    return table + demo_note

def format_mra_devices(devices_response, limit=None):
    """Format MRA device data into a readable table with demo indicator"""
    if not devices_response or not devices_response.get('devices'):
        return "No devices found"
    
    table_data = []
    for device in devices_response['devices'][:limit]:
        table_data.append([
            device.get('guid', 'N/A')[:8] + '...',
            device.get('email', 'N/A'),
            device.get('platform', 'N/A'),
            device.get('security_status', 'N/A'),
            device.get('protection_status', 'N/A'),
            device.get('activation_status', 'N/A')
        ])
    
    table = tabulate(
        table_data,
        headers=['Device GUID', 'Email', 'Platform', 'Security', 'Protection', 'Status'],
        tablefmt='fancy_grid',
        maxcolwidths=[12, 25, 10, 12, 12, 12]
    )
    
    return table + "\n🎭 DEMO DATA - Simulated for demonstration purposes"

def main():
    parser = argparse.ArgumentParser(description='Lookout API Client - DEMO VERSION with Simulated Data')
    parser.add_argument('--api', choices=['web-access', 'mra-devices', 'both'], default='web-access',
                       help='Which API to query (demo data)')
    parser.add_argument('--start-time', help='Start time for web access events (ignored in demo)')
    parser.add_argument('--last-12h', action='store_true', help='Show events from last 12 hours (demo)')
    parser.add_argument('--last-24h', action='store_true', help='Show events from last 24 hours (demo)')
    parser.add_argument('--limit', type=int, default=10, help='Number of items to display')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    parser.add_argument('--no-user-mapping', action='store_true',
                       help='Disable automatic device-to-user mapping')
    parser.add_argument('--timeout', type=int, default=120,
                       help='Request timeout in seconds (demo mode)')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum number of retry attempts (demo mode)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎭 LOOKOUT API CLIENT - DEMO MODE")
    print("=" * 60)
    print("This is a demonstration version using simulated data.")
    print("Perfect for demos when the real API is unavailable!")
    print("=" * 60)
    
    try:
        client = LookoutAPIClientDemo(
            enable_device_mapping=not args.no_user_mapping,
            timeout=args.timeout,
            max_retries=args.max_retries
        )
        
        # Determine time description for display
        time_description = "Recent events (simulated)"
        if args.last_12h:
            time_description = "Last 12 hours (simulated)"
        elif args.last_24h:
            time_description = "Last 24 hours (simulated)"
        elif args.start_time:
            time_description = f"{args.start_time} to present (simulated)"
        
        # Execute API calls based on selection
        if args.api in ['web-access', 'both']:
            print(f"\n=== Lookout Web Access Activity Feed (DEMO) ===")
            print(f"Time range: {time_description}")
            print(f"🔗 Device-to-user mapping: {'ENABLED' if not args.no_user_mapping else 'DISABLED'}")
            print()
            
            events = client.fetch_web_access_events(
                start_time=args.start_time, 
                include_user_mapping=not args.no_user_mapping
            )
            
            if args.format == 'json':
                print(json.dumps(events, indent=2))
            else:
                print(format_web_access_events(
                    events, 
                    limit=args.limit, 
                    include_user_mapping=not args.no_user_mapping
                ))
                event_count = len(events.get('lookup_access_events', []))
                print(f"\nTotal web access events found: {event_count}")
        
        if args.api in ['mra-devices', 'both']:
            if args.api == 'both':
                print("\n" + "="*60 + "\n")
            
            print(f"=== Lookout MRA Devices (DEMO) ===")
            print(f"Limit: {args.limit}\n")
            
            devices = client.fetch_mra_devices(limit=args.limit)
            
            if devices:
                if args.format == 'json':
                    print(json.dumps(devices, indent=2))
                else:
                    print(format_mra_devices(devices, limit=args.limit))
                    device_count = devices.get('count', 0)
                    print(f"\nTotal devices found: {device_count}")
            else:
                print("No device data available")
        
        print(f"\n🎭 Demo completed successfully!")
        print("💡 This simulated data is perfect for demonstrations and testing.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()