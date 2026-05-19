import os
import sys
import argparse
import requests
import ipaddress
import logging
import csv
import io
import concurrent.futures
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv
from requests.exceptions import RequestException
from tabulate import tabulate

# Load environment variables
load_dotenv()
_DEBUG_LOGGING = os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG'

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
            if _DEBUG_LOGGING:
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
                
                if _DEBUG_LOGGING:
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
            print(f"🔍 DEBUG: Timeout set to: {os.getenv('TIMEOUT_SECONDS', '60')} seconds")
            start_time = datetime.now()

        try:
            response = requests.get(url, headers=headers, params=params, timeout=int(os.getenv('TIMEOUT_SECONDS', '60')))
            
            if debug:
                elapsed_time = (datetime.now() - start_time).total_seconds()
                print(f"🔍 DEBUG: Request completed in {elapsed_time:.2f} seconds")
                print(f"🔍 DEBUG: Response status: {response.status_code}")
                print(f"🔍 DEBUG: Response headers: {dict(response.headers)}")
            
            # If we get a 401 and haven't already retried, refresh token and try again
            if response.status_code == 401 and retry_on_auth_error:
                if _DEBUG_LOGGING:
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
            error_msg = "Request timed out. Try a shorter time range or check your network connection."
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

def _extract_hostname(url: str) -> str:
    try:
        parsed = urlparse(url if '://' in url else 'https://' + url)
        return (parsed.hostname or '').lower()
    except Exception:
        return ''

def _doh_lookup(hostname: str, server: str) -> str:
    try:
        endpoint = 'https://1.1.1.1/dns-query' if server == 'cloudflare' else 'https://dns.google/resolve'
        r = requests.get(endpoint, params={'name': hostname, 'type': 'A'},
                         headers={'accept': 'application/dns-json'}, timeout=3)
        data = r.json()
        answers = [a['data'] for a in data.get('Answer', []) if a.get('type') == 1]
        return answers[0] if answers else ''
    except Exception:
        return ''

def _batch_resolve(raw_events):
    all_hostnames = [_extract_hostname(e.get('request_url', '')) for e in raw_events]
    uncached = list({h for h in all_hostnames if h})
    if not uncached:
        return {}
    workers = min(len(uncached) * 2, 40)
    resolved = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for h in uncached:
            futures[pool.submit(_doh_lookup, h, 'cloudflare')] = h
            futures[pool.submit(_doh_lookup, h, 'google')] = h
        for fut in concurrent.futures.as_completed(futures):
            h = futures[fut]
            if h in resolved:
                continue
            try:
                ip = fut.result()
                if ip:
                    resolved[h] = ip
            except Exception:
                pass
    return resolved

def format_events(events, limit=None, resolved_ips=None):
    """Format events into a readable table"""
    if not events.get('lookup_access_events'):
        return "No events found in the specified time range"
    
    resolved_ips = resolved_ips or {}
    table_data = []
    for event in events['lookup_access_events'][:limit]:
        timestamp_ms = event['timestamp']
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        utc_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
        timestamp_display = f"{utc_str}\n{local_str}"

        resolved_ip = event.get('resolved_ip_address', '')
        dns_mode, ip_type = get_ip_type_and_mode(resolved_ip)

        if dns_mode == "VPN Mode":
            hostname = _extract_hostname(event.get('request_url', ''))
            doh_ip = resolved_ips.get(hostname, '') if hostname else ''
            if doh_ip:
                ip_display = f"{doh_ip} (DoH)"
            else:
                ip_display = "N/A"
        else:
            ip_display = f"{resolved_ip} ({ip_type})"

        table_data.append([
            timestamp_display,
            event['device_guid'][:8] + '...' + event['device_guid'][-3:],
            event['region'],
            event['request_url'],
            dns_mode,
            ip_display,
            event['id'][:8] + '...'
        ])

    return tabulate(
        table_data,
        headers=['Timestamp', 'Device', 'Region', 'URL', 'DNS Mode', 'Resolved IP', 'Event ID'],
        tablefmt='fancy_grid',
        maxcolwidths=[None, 15, None, 35, 12, 25, None]
    )

def format_events_csv(events, limit=None, resolved_ips=None):
    """Format events into CSV format"""
    if not events.get('lookup_access_events'):
        return "UTC Timestamp,Local Timestamp,Device,Region,URL,DNS Mode,Resolved IP,IP Source,Event ID\n"

    resolved_ips = resolved_ips or {}
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['UTC Timestamp', 'Local Timestamp', 'Device', 'Region', 'URL', 'DNS Mode', 'Resolved IP', 'IP Source', 'Event ID'])

    for event in events['lookup_access_events'][:limit]:
        timestamp_ms = event['timestamp']
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        utc_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

        resolved_ip = event.get('resolved_ip_address', '')
        dns_mode, ip_type = get_ip_type_and_mode(resolved_ip)

        if dns_mode == "VPN Mode":
            hostname = _extract_hostname(event.get('request_url', ''))
            doh_ip = resolved_ips.get(hostname, '') if hostname else ''
            ip_display = doh_ip if doh_ip else 'N/A'
            ip_source = 'DoH' if doh_ip else 'N/A'
        else:
            ip_display = resolved_ip
            ip_source = ip_type

        writer.writerow([
            utc_str,
            local_str,
            event['device_guid'],
            event['region'],
            event['request_url'],
            dns_mode,
            ip_display,
            ip_source,
            event['id']
        ])


    return output.getvalue()

def main():
    parser = argparse.ArgumentParser(description='Lookout Web Access Feed API Client')
    parser.add_argument('--start-time', help='Start time in format: YYYY-M-DDTHH:MM:SS+HH:MM (e.g., 2025-6-13T00:00:00+00:00)')
    parser.add_argument('--last-30m', action='store_true', help='Show events from last 30 minutes')
    parser.add_argument('--last-1h', action='store_true', help='Show events from last 1 hour')
    parser.add_argument('--last-12h', action='store_true', help='Show events from last 12 hours')
    parser.add_argument('--last-24h', action='store_true', help='Show events from last 24 hours')
    parser.add_argument('--last-48h', action='store_true', help='Show events from last 48 hours')
    parser.add_argument('--limit', type=int, default=10, help='Number of events to display (default: 10)')
    parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table', help='Output format')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh access token before making API calls')
    parser.add_argument('--debug', action='store_true', help='Enable debug output to troubleshoot API requests')
    parser.add_argument('--device', help='Filter by device GUID (supports partial match)')
    
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
    
    if args.last_30m:
        start_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        time_description = "Last 30 minutes"
    elif args.last_1h:
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

        if args.device and 'lookup_access_events' in events:
            original_count = len(events['lookup_access_events'])
            events['lookup_access_events'] = [
                e for e in events['lookup_access_events']
                if args.device.lower() in e.get('device_guid', '').lower()
            ]
            device_filter_msg = f" (filtered from {original_count} total)"
        else:
            device_filter_msg = ""

        if 'lookup_access_events' in events:
            events['lookup_access_events'].sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        raw = events.get('lookup_access_events', [])
        resolved_ips = _batch_resolve(raw[:args.limit]) if raw else {}

        print(f"=== Lookout Web Access Activity Feed ===")
        print(f"Time range: {time_description}")
        if args.device:
            print(f"Device filter: {args.device}")
        print()

        if args.format == 'json':
            import json
            enhanced_events = events.copy()
            if 'lookup_access_events' in enhanced_events:
                for event in enhanced_events['lookup_access_events']:
                    ip_address = event.get('resolved_ip_address', '')
                    dns_mode, ip_type = get_ip_type_and_mode(ip_address)
                    event['dns_mode'] = dns_mode
                    event['ip_type'] = ip_type
                    if dns_mode == "VPN Mode":
                        hostname = _extract_hostname(event.get('request_url', ''))
                        event['doh_resolved_ip'] = resolved_ips.get(hostname, '') if hostname else ''
            print(json.dumps(enhanced_events, indent=2))
        elif args.format == 'csv':
            print(format_events_csv(events, limit=args.limit, resolved_ips=resolved_ips))
        else:
            print(format_events(events, limit=args.limit, resolved_ips=resolved_ips))
            
        event_count = len(events.get('lookup_access_events', []))
        print(f"\nTotal events found: {event_count}{device_filter_msg}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
