#!/usr/bin/env python3
"""
Enhanced Lookout API Client with Application Key Exchange and Device Mapping
Demonstrates both Web Access Feed API and MRA-style authentication patterns
Includes automatic device-to-user mapping from local database
"""

import os
import sys
import argparse
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from requests.exceptions import RequestException
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

class LookoutAPIClient:
    """
    Enhanced Lookout API Client supporting multiple authentication patterns:
    1. Direct JWT Bearer tokens (for Web Access Feed API)
    2. Application Key -> OAuth2 Access Token exchange (MRA pattern)
    3. Device-to-user mapping from local database
    """
    
    def __init__(self, enable_device_mapping=True):
        # API endpoints
        self.web_access_feed_url = 'https://mtp.lookout.com/data/web-access-feed'
        self.oauth_url = 'https://api.lookout.com/oauth2/token'
        self.mra_base_url = 'https://api.lookout.com'
        
        # Authentication
        self.application_key = self._get_application_key()
        self.access_token = self._get_or_refresh_access_token()
        
        # Device mapping
        self.device_db = None
        if enable_device_mapping and DEVICE_MAPPING_AVAILABLE:
            try:
                self.device_db = DeviceDatabase()
                print("✅ Device mapping database connected")
            except Exception as e:
                print(f"⚠️  Device mapping database unavailable: {e}")
        
    def _get_application_key(self):
        """Get application key from environment or file"""
        # Try environment variable first
        app_key = os.getenv('LOOKOUT_APPLICATION_KEY')
        if app_key:
            return app_key
            
        # Try reading from file
        try:
            with open('application_key.txt', 'r') as f:
                app_key = f.read().strip()
                if app_key:
                    return app_key
        except FileNotFoundError:
            pass
            
        return None
    
    def _get_or_refresh_access_token(self):
        """Get existing access token or refresh using application key"""
        # Try to get existing token first
        token = os.getenv('LOOKOUT_ACCESS_TOKEN')
        if token:
            return token
            
        # Try reading from file
        try:
            with open('access_token.txt', 'r') as f:
                token = f.read().strip()
                if token:
                    return token
        except FileNotFoundError:
            pass
        
        # If we have an application key, use it to get an access token
        if self.application_key:
            return self._exchange_application_key_for_token()
            
        # Fallback to hardcoded token (for demo purposes)
        return 'your_jwt_token_here'

    def _exchange_application_key_for_token(self, scope=None):
        """
        Exchange application key for access token using OAuth2 client credentials flow
        This follows the MRA API pattern described in the documentation
        """
        print("🔑 Exchanging application key for access token...")
        
        headers = {
            'Authorization': f'Bearer {self.application_key}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        if scope:
            data['scope'] = scope
        
        try:
            response = requests.post(self.oauth_url, headers=headers, data=data, timeout=15)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 7200)
            expires_at = token_data.get('expires_at')
            
            if access_token:
                # Save token and metadata
                with open('access_token.txt', 'w') as f:
                    f.write(access_token)
                
                with open('token_metadata.json', 'w') as f:
                    json.dump({
                        'expires_in': expires_in,
                        'expires_at': expires_at,
                        'scope': token_data.get('scope', ''),
                        'token_type': token_data.get('token_type', 'Bearer'),
                        'obtained_at': datetime.now(timezone.utc).isoformat()
                    }, f, indent=2)
                
                print(f"✅ Access token obtained successfully!")
                print(f"   Token type: {token_data.get('token_type', 'Bearer')}")
                print(f"   Expires in: {expires_in} seconds")
                print(f"   Scope: {token_data.get('scope', 'default')}")
                
                return access_token
            else:
                raise ValueError("No access_token in response")
                
        except RequestException as e:
            error_msg = f"Token exchange failed: {e}"
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {e.response.text}"
            raise SystemExit(error_msg)

    def fetch_web_access_events(self, start_time=None, include_user_mapping=True):
        """Fetch web access events from Lookout Web Access Feed API with optional user mapping"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        params = {}
        if start_time:
            params['start_interval'] = start_time
        
        try:
            response = requests.get(self.web_access_feed_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            events_data = response.json()
            
            # Add user mapping if available and requested
            if include_user_mapping and self.device_db:
                events_data = self._enrich_events_with_user_mapping(events_data)
            
            return events_data
            
        except RequestException as e:
            if hasattr(e, 'response') and e.response and e.response.status_code == 401:
                print("🔄 Access token expired, attempting to refresh...")
                if self.application_key:
                    self.access_token = self._exchange_application_key_for_token()
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.get(self.web_access_feed_url, headers=headers, params=params, timeout=15)
                    response.raise_for_status()
                    events_data = response.json()
                    
                    # Add user mapping if available and requested
                    if include_user_mapping and self.device_db:
                        events_data = self._enrich_events_with_user_mapping(events_data)
                    
                    return events_data
            raise SystemExit(f"API request failed: {e.response.text if e.response else str(e)}")

    def _enrich_events_with_user_mapping(self, events_data):
        """Enrich web access events with user email mapping from device database"""
        if not events_data.get('lookup_access_events'):
            return events_data
        
        enriched_events = []
        mapping_stats = {'mapped': 0, 'unmapped': 0}
        
        for event in events_data['lookup_access_events']:
            device_guid = event.get('device_guid')
            if device_guid:
                # Look up user email from device database
                user_email = self.device_db.get_user_email_by_device_guid(device_guid)
                if user_email:
                    event['user_email'] = user_email
                    # Also get device platform if available
                    device = self.device_db.get_device_by_guid(device_guid)
                    if device:
                        event['platform'] = device.platform
                        event['security_status'] = device.security_status
                    mapping_stats['mapped'] += 1
                else:
                    event['user_email'] = 'Unknown'
                    mapping_stats['unmapped'] += 1
            else:
                mapping_stats['unmapped'] += 1
            
            enriched_events.append(event)
        
        # Update the events data
        events_data['lookup_access_events'] = enriched_events
        events_data['user_mapping_stats'] = mapping_stats
        
        return events_data

    def fetch_mra_devices(self, limit=10):
        """Fetch devices using MRA API (example of using the same token for different APIs)"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        params = {'limit': limit}
        
        try:
            response = requests.get(f"{self.mra_base_url}/mra/api/v2/devices", 
                                  headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if hasattr(e, 'response') and e.response and e.response.status_code == 401:
                print("🔄 Access token expired, attempting to refresh...")
                if self.application_key:
                    self.access_token = self._exchange_application_key_for_token()
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.get(f"{self.mra_base_url}/mra/api/v2/devices", 
                                          headers=headers, params=params, timeout=15)
                    response.raise_for_status()
                    return response.json()
            print(f"MRA API request failed: {e.response.text if e.response else str(e)}")
            return None

def format_web_access_events(events, limit=None, include_user_mapping=True):
    """Format web access events into a readable table with optional user mapping"""
    if not events.get('lookup_access_events'):
        return "No web access events found"
    
    table_data = []
    has_user_mapping = any('user_email' in event for event in events['lookup_access_events'][:limit])
    
    for event in events['lookup_access_events'][:limit]:
        timestamp_ms = event['timestamp']
        readable_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        row = [
            readable_time,
            event['device_guid'][:8] + '...' + event['device_guid'][-3:],
        ]
        
        # Add user email if available
        if has_user_mapping and include_user_mapping:
            user_email = event.get('user_email', 'Unknown')
            # Truncate long emails for display
            if len(user_email) > 25:
                user_email = user_email[:22] + '...'
            row.append(user_email)
            
            # Add platform if available
            platform = event.get('platform', 'N/A')
            row.append(platform)
        
        row.extend([
            event['region'],
            event['request_url'],
        ])
        
        # Add security status if available
        if has_user_mapping and include_user_mapping:
            security_status = event.get('security_status', 'N/A')
            row.append(security_status)
        
        table_data.append(row)
    
    # Dynamic headers based on available data
    headers = ['Timestamp', 'Device']
    if has_user_mapping and include_user_mapping:
        headers.extend(['User Email', 'Platform'])
    headers.extend(['Region', 'URL'])
    if has_user_mapping and include_user_mapping:
        headers.append('Security')
    
    # Dynamic column widths
    maxcolwidths = [None, 15]
    if has_user_mapping and include_user_mapping:
        maxcolwidths.extend([25, 10])
    maxcolwidths.extend([None, 40])
    if has_user_mapping and include_user_mapping:
        maxcolwidths.append(12)
    
    table = tabulate(
        table_data,
        headers=headers,
        tablefmt='fancy_grid',
        maxcolwidths=maxcolwidths
    )
    
    # Add mapping statistics if available
    if events.get('user_mapping_stats'):
        stats = events['user_mapping_stats']
        total = stats['mapped'] + stats['unmapped']
        mapping_rate = (stats['mapped'] / total * 100) if total > 0 else 0
        table += f"\n\n📊 User Mapping: {stats['mapped']}/{total} events mapped ({mapping_rate:.1f}%)"
    
    return table

def format_mra_devices(devices_response, limit=None):
    """Format MRA device data into a readable table"""
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
    
    return tabulate(
        table_data,
        headers=['Device GUID', 'Email', 'Platform', 'Security', 'Protection', 'Status'],
        tablefmt='fancy_grid',
        maxcolwidths=[12, 25, 10, 12, 12, 12]
    )

def main():
    parser = argparse.ArgumentParser(description='Enhanced Lookout API Client with Application Key Exchange')
    parser.add_argument('--api', choices=['web-access', 'mra-devices', 'both'], default='web-access',
                       help='Which API to query')
    parser.add_argument('--start-time', help='Start time for web access events (ISO8601 format)')
    parser.add_argument('--last-12h', action='store_true', help='Show events from last 12 hours')
    parser.add_argument('--last-24h', action='store_true', help='Show events from last 24 hours')
    parser.add_argument('--limit', type=int, default=10, help='Number of items to display')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    parser.add_argument('--exchange-key', action='store_true', 
                       help='Force exchange application key for new access token')
    parser.add_argument('--show-token-info', action='store_true',
                       help='Show current token information')
    parser.add_argument('--no-user-mapping', action='store_true',
                       help='Disable automatic device-to-user mapping')
    parser.add_argument('--mapping-stats', action='store_true',
                       help='Show device mapping database statistics')
    
    args = parser.parse_args()
    
    try:
        client = LookoutAPIClient(enable_device_mapping=not args.no_user_mapping)
        
        # Handle mapping stats display
        if args.mapping_stats:
            if client.device_db:
                stats = client.device_db.get_database_stats()
                print("=== Device Mapping Database Statistics ===")
                print(f"Database Path: {client.device_db.db_path}")
                print(f"Total Devices: {stats['total_devices']}")
                print(f"Unique Users: {stats['unique_users']}")
                print(f"Total Web Events: {stats['total_web_events']}")
                print(f"Recent Events (24h): {stats['recent_events_24h']}")
                print("\nPlatform Breakdown:")
                for platform, count in stats['platform_breakdown'].items():
                    print(f"  {platform}: {count}")
            else:
                print("❌ Device mapping database not available")
            return
        
        # Handle token info display
        if args.show_token_info:
            print("=== Token Information ===")
            print(f"Access Token: {client.access_token[:20]}..." if client.access_token else "No access token")
            print(f"Application Key: {'Present' if client.application_key else 'Not found'}")
            
            try:
                with open('token_metadata.json', 'r') as f:
                    metadata = json.load(f)
                    print(f"Token Type: {metadata.get('token_type', 'Unknown')}")
                    print(f"Scope: {metadata.get('scope', 'Unknown')}")
                    print(f"Expires In: {metadata.get('expires_in', 'Unknown')} seconds")
                    print(f"Obtained At: {metadata.get('obtained_at', 'Unknown')}")
            except FileNotFoundError:
                print("No token metadata available")
            return
        
        # Handle forced key exchange
        if args.exchange_key:
            if client.application_key:
                client.access_token = client._exchange_application_key_for_token()
                print("✅ Token exchange completed successfully!")
                return
            else:
                print("❌ No application key found. Set LOOKOUT_APPLICATION_KEY environment variable or create application_key.txt")
                return
        
        # Determine start time for web access events
        start_time = None
        time_description = "Recent events"
        
        if args.last_12h:
            start_time = (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            time_description = "Last 12 hours"
        elif args.last_24h:
            start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            time_description = "Last 24 hours"
        elif args.start_time:
            start_time = args.start_time
            time_description = f"{args.start_time} to present"
        
        # Execute API calls based on selection
        if args.api in ['web-access', 'both']:
            print(f"=== Lookout Web Access Activity Feed ===")
            print(f"Time range: {time_description}")
            if client.device_db and not args.no_user_mapping:
                print("🔗 Device-to-user mapping: ENABLED")
            else:
                print("🔗 Device-to-user mapping: DISABLED")
            print()
            
            events = client.fetch_web_access_events(
                start_time=start_time, 
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
            
            print(f"=== Lookout MRA Devices ===")
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
                print("No device data available (may require different token scope)")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
