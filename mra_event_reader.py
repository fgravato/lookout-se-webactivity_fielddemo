#!/usr/bin/env python3
"""
Lookout MRA Event Reader
Simple event reader following the MRA client pattern for streaming events
"""

import datetime
import time
import json
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EventForwarder:
    """Base class for event forwarding"""
    def write(self, event: dict, entName: str = ""):
        raise NotImplementedError

class StdoutForwarder(EventForwarder):
    """Event forwarder that outputs events to stdout"""
    def write(self, event: dict, entName: str = ""):
        print(json.dumps(event, indent=2))

class LookoutMRAClient:
    """
    Lookout MRA Client for streaming events
    Follows the pattern from the lookout-mra-client package
    """
    
    def __init__(self, api_domain, api_key, start_time=None, event_types=None):
        self.api_domain = api_domain
        self.api_key = api_key
        self.start_time = start_time
        self.event_types = event_types or ["DEVICE", "THREAT", "AUDIT"]
        self.access_token = None
        self.running = False
        
    def _get_access_token(self):
        """Exchange API key for access token using OAuth2 client credentials flow"""
        oauth_url = f"{self.api_domain}/oauth2/token"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(oauth_url, headers=headers, data=data, timeout=15)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                print(f"✅ Access token obtained (expires in {token_data.get('expires_in', 'unknown')} seconds)")
                return access_token
            else:
                raise ValueError("No access_token in response")
                
        except requests.RequestException as e:
            print(f"❌ Token exchange failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            sys.exit(1)
    
    def start_streaming(self, forwarder: EventForwarder, enterprise_name: str = ""):
        """Start streaming events from the MRA API"""
        if not self.access_token:
            self.access_token = self._get_access_token()
        
        # Build streaming URL
        stream_url = f"{self.api_domain}/mra/stream/v2/events"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }
        
        params = {}
        if self.event_types:
            params['types'] = ','.join(self.event_types)
        if self.start_time:
            # Convert datetime to URL-encoded ISO8601 format
            if isinstance(self.start_time, datetime.datetime):
                start_time_str = self.start_time.isoformat()
            else:
                start_time_str = str(self.start_time)
            params['start_time'] = start_time_str
        
        print(f"🔄 Starting event stream...")
        print(f"   URL: {stream_url}")
        print(f"   Event types: {', '.join(self.event_types)}")
        print(f"   Start time: {self.start_time or 'now'}")
        print(f"   Enterprise: {enterprise_name or 'default'}")
        print("   Press Ctrl+C to stop\n")
        
        self.running = True
        
        try:
            with requests.get(stream_url, headers=headers, params=params, 
                            stream=True, timeout=30) as response:
                response.raise_for_status()
                
                event_count = 0
                for line in response.iter_lines(decode_unicode=True):
                    if not self.running:
                        break
                        
                    if line:
                        # Parse Server-Sent Events format
                        if line.startswith('data:'):
                            try:
                                data_content = line[5:].strip()  # Remove 'data:' prefix
                                if data_content and data_content != '{}':
                                    event_data = json.loads(data_content)
                                    
                                    # Process events array
                                    events = event_data.get('events', [])
                                    for event in events:
                                        event_count += 1
                                        print(f"--- Event #{event_count} ---")
                                        forwarder.write(event, enterprise_name)
                                        print()
                                        
                            except json.JSONDecodeError as e:
                                print(f"⚠️  JSON decode error: {e}")
                                print(f"   Raw line: {line}")
                        
                        elif line.startswith('event:'):
                            event_type = line[6:].strip()
                            if event_type == 'heartbeat':
                                print("💓 Heartbeat received")
                            elif event_type == 'reconnect':
                                print("🔄 Server requested reconnect")
                        
                        elif line.startswith('id:'):
                            last_event_id = line[3:].strip()
                            # Could store this for reconnection purposes
                            pass
                            
        except requests.RequestException as e:
            print(f"❌ Streaming error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
        except KeyboardInterrupt:
            print("\n🛑 Stream stopped by user")
        finally:
            self.running = False

def main():
    """Main function following the MRA client pattern"""
    
    # Get API key from environment or prompt
    api_key = os.getenv('LOOKOUT_APPLICATION_KEY')
    if not api_key:
        try:
            with open('application_key.txt', 'r') as f:
                api_key = f.read().strip()
        except FileNotFoundError:
            pass
    
    if not api_key:
        print("❌ No API key found!")
        print("   Set LOOKOUT_APPLICATION_KEY environment variable")
        print("   Or create application_key.txt file")
        print("\nTo get an application key:")
        print("1. Log into Lookout Mobile Endpoint Protection Console")
        print("2. Navigate to System > Application Keys")
        print("3. Click GENERATE KEY")
        print("4. Copy the generated key")
        sys.exit(1)
    
    # Initialize event forwarder
    forwarder = StdoutForwarder()
    
    # Set start time (last 24 hours for demo)
    start_time = datetime.datetime.now() - datetime.timedelta(days=1)
    start_time = start_time.replace(tzinfo=datetime.timezone.utc)
    
    # Configure event types
    event_types = ["THREAT", "DEVICE", "AUDIT"]
    
    # Create MRA client
    client = LookoutMRAClient(
        api_domain="https://api.lookout.com",
        api_key=api_key,
        start_time=start_time,
        event_types=event_types
    )
    
    # Start streaming
    try:
        client.start_streaming(forwarder, "demo_enterprise")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
