import os
import sys
import argparse
import requests
import ipaddress
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from requests.exceptions import RequestException
from tabulate import tabulate

# Load environment variables
load_dotenv()

class LookoutAPIClient:
    def __init__(self):
        self.base_url = 'https://mtp.lookout.com/data/web-access-feed'
        self.oauth_url = 'https://api.lookout.com/oauth2/token'
        self.access_token = None
        self.web_activity_key = os.getenv('WEB_ACTIVITY_KEY')
        
        # Try to get existing token first, then refresh if needed
        self.access_token = self._get_existing_token()
        if not self.access_token:
            self._refresh_access_token()
    
    def _get_existing_token(self):
        """Get existing access token from environment variable or file"""
        # Try environment variable first
        token = os.getenv('LOOKOUT_ACCESS_TOKEN')
        if token:
            return token
            
        # Try token file
        try:
            with open('access_token.txt', 'r') as f:
                token = f.read().strip()
                if token:
                    return token
        except FileNotFoundError:
            pass
            
        return None
    
    def _refresh_access_token(self):
        """Get a new access token using the WEB_ACTIVITY_KEY"""
        if not self.web_activity_key:
            raise SystemExit("❌ WEB_ACTIVITY_KEY not found in environment variables. Please check your .env file.")
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {self.web_activity_key}'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            print("🔄 Refreshing access token...")
            response = requests.post(self.oauth_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            new_token = token_data.get('access_token')
            if new_token:
                # Save to file
                with open('access_token.txt', 'w') as f:
                    f.write(new_token)
                
                # Update environment variable for this session
                os.environ['LOOKOUT_ACCESS_TOKEN'] = new_token
                self.access_token = new_token
                
                print("✅ Access token refreshed successfully!")
                return new_token
            else:
                raise ValueError("No access_token in response")
                
        except RequestException as e:
            error_msg = f"Token refresh failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"Token refresh failed: {error_detail}"
                except:
                    error_msg = f"Token refresh failed: {e.response.text}"
            raise SystemExit(f"❌ {error_msg}")
    
    def _make_authenticated_request(self, url, params=None, retry_on_auth_error=True, debug=False):
        """Make an authenticated request with automatic token refresh on 401 errors"""
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        if debug:
            print(f"🔍 DEBUG: Making request to: {url}")
            print(f"🔍 DEBUG: Parameters: {params}")
            print(f"🔍 DEBUG: Timeout set to: 720 seconds (12 minutes)")
            start_time = datetime.now()
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=720)
            
            if debug:
                elapsed_time = (datetime.now() - start_time).total_seconds()
                print(f"🔍 DEBUG: Request completed in {elapsed_time:.2f} seconds")
                print(f"🔍 DEBUG: Response status: {response.status_code}")
                print(f"🔍 DEBUG: Response headers: {dict(response.headers)}")
            
            # If we get a 401 and haven't already retried, refresh token and try again
            if response.status_code == 401 and retry_on_auth_error:
                print("🔄 Access token expired, refreshing...")
                self._refresh_access_token()
                return self._make_authenticated_request(url, params, retry_on_auth_error=False, debug=debug)
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                if debug:
                    event_count = len(response_data.get('lookup_access_events', []))
                    print(f"🔍 DEBUG: Response contains {event_count} events")
                return response_data
            except ValueError as json_error:
                if debug:
                    print(f"🔍 DEBUG: Failed to parse JSON response")
                    print(f"🔍 DEBUG: Response content type: {response.headers.get('content-type', 'unknown')}")
                    print(f"🔍 DEBUG: Response content (first 500 chars): {response.text[:500]}")
                raise ValueError(f"Invalid JSON response from API. Content-Type: {response.headers.get('content-type', 'unknown')}. Response: {response.text[:200]}...")
            
        except requests.exceptions.Timeout as e:
            elapsed_time = (datetime.now() - start_time).total_seconds() if debug else "unknown"
            error_msg = f"Request timed out after {elapsed_time} seconds. The API response is taking longer than the 720-second (12-minute) timeout."
            if debug:
                print(f"🔍 DEBUG: Timeout occurred after {elapsed_time} seconds")
            raise SystemExit(f"❌ {error_msg}")
        except RequestException as e:
            if debug:
                elapsed_time = (datetime.now() - start_time).total_seconds()
                print(f"🔍 DEBUG: Request failed after {elapsed_time} seconds")
            
            error_msg = f"API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API request failed: {error_detail}"
                except:
                    error_msg = f"API request failed: {e.response.text}"
            raise SystemExit(f"❌ {error_msg}")

    def fetch_events(self, start_time=None, debug=False):
        """Fetch web access events from Lookout API"""
        # Use the correct parameter name from API documentation: start_time
        params = {}
        if start_time:
            params['start_time'] = start_time
        
        return self._make_authenticated_request(self.base_url, params, debug=debug)

def get_ip_type_and_mode(ip_address):
    """Determine IP type and DNS mode based on resolved IP address"""
    if not ip_address or ip_address.strip() == "":
        return "VPN Mode", "N/A"
    
    try:
        ip_obj = ipaddress.ip_address(ip_address.strip())
        if isinstance(ip_obj, ipaddress.IPv4Address):
            return "SecureDNS", "IPv4"
        elif isinstance(ip_obj, ipaddress.IPv6Address):
            return "SecureDNS", "IPv6"
    except ValueError:
        return "VPN Mode", "N/A"
    
    return "Unknown", "Unknown"

def format_events(events, limit=None):
    """Format events into a readable table"""
    if not events.get('lookup_access_events'):
        return "No events found in the specified time range"
    
    table_data = []
    for event in events['lookup_access_events'][:limit]:
        # Convert timestamp from milliseconds to readable format
        timestamp_ms = event['timestamp']
        readable_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get IP address, DNS mode, and IP type
        resolved_ip = event.get('resolved_ip_address', '')
        dns_mode, ip_type = get_ip_type_and_mode(resolved_ip)
        
        # Format IP display based on mode
        if dns_mode == "VPN Mode":
            ip_display = "N/A"
        else:
            ip_display = f"{resolved_ip} ({ip_type})"
        
        table_data.append([
            readable_time,
            event['device_guid'][:8] + '...' + event['device_guid'][-3:],
            event['region'],
            event['request_url'],  # Fixed: use request_url not request_uri
            dns_mode,
            ip_display,
            event['id'][:8] + '...'  # Truncate long event IDs
        ])
    
    return tabulate(
        table_data,
        headers=['Timestamp', 'Device', 'Region', 'URL', 'DNS Mode', 'Resolved IP', 'Event ID'],
        tablefmt='fancy_grid',
        maxcolwidths=[None, 15, None, 35, 12, 25, None]
    )

def main():
    parser = argparse.ArgumentParser(description='Lookout Web Access Feed API Client')
    parser.add_argument('--start-time', help='Start time in format: YYYY-M-DDTHH:MM:SS+HH:MM (e.g., 2025-6-13T00:00:00+00:00)')
    parser.add_argument('--last-1h', action='store_true', help='Show events from last 1 hour')
    parser.add_argument('--last-12h', action='store_true', help='Show events from last 12 hours')
    parser.add_argument('--last-24h', action='store_true', help='Show events from last 24 hours')
    parser.add_argument('--last-48h', action='store_true', help='Show events from last 48 hours')
    parser.add_argument('--limit', type=int, default=10, help='Number of events to display (default: 10)')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh access token before making API calls')
    parser.add_argument('--debug', action='store_true', help='Enable debug output to troubleshoot API requests')
    
    args = parser.parse_args()
    
    client = LookoutAPIClient()
    
    # Handle force refresh if requested
    if args.force_refresh:
        try:
            client._refresh_access_token()
            print("✅ Token force refreshed successfully!")
            return
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            sys.exit(1)
    
    # Determine start time based on flags
    start_time = None
    time_description = "Recent events"
    
    if args.last_1h:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        time_description = "Last 1 hour"
    elif args.last_12h:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        time_description = "Last 12 hours"
    elif args.last_24h:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        time_description = "Last 24 hours"
    elif args.last_48h:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        time_description = "Last 48 hours"
    elif args.start_time:
        start_time = args.start_time
        time_description = f"{args.start_time} to present"
    
    try:
        events = client.fetch_events(start_time=start_time, debug=args.debug)
        
        print(f"=== Lookout Web Access Activity Feed ===")
        print(f"Time range: {time_description}\n")
        
        if args.format == 'json':
            import json
            # Enhance JSON output with DNS mode and IP type flags
            enhanced_events = events.copy()
            if 'lookup_access_events' in enhanced_events:
                for event in enhanced_events['lookup_access_events']:
                    ip_address = event.get('resolved_ip_address', '')
                    dns_mode, ip_type = get_ip_type_and_mode(ip_address)
                    event['dns_mode'] = dns_mode
                    event['ip_type'] = ip_type
            print(json.dumps(enhanced_events, indent=2))
        else:
            print(format_events(events, limit=args.limit))
            
        event_count = len(events.get('lookup_access_events', []))
        print(f"\nTotal events found: {event_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
