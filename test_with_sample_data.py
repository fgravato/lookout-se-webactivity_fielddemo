#!/usr/bin/env python3
"""
Test script to demonstrate the Lookout Web Activity Feed with sample data
"""

import json
from datetime import datetime, timezone
from tabulate import tabulate

# Sample data from your Postman response
sample_data = {
    "enterprise_guid": "a0445e25-e5f9-4936-86e9-fcd287655ad7",
    "start_time": "2025-06-20 15:58:50.933",
    "end_time": "2025-06-20 17:34:24.761",
    "lookup_access_events": [
        {
            "id": "01978e10-6e35-76b8-8479-995e2002e174",
            "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
            "region": "us-west-2",
            "request_url": "mac.com/",
            "timestamp": 1750435130933
        },
        {
            "id": "01978e10-6e38-7930-bb09-d3db48ab5fce",
            "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
            "region": "us-west-2",
            "request_url": "icloud.com/",
            "timestamp": 1750435130936
        },
        {
            "id": "01978e10-6e44-7389-9195-8a1ed53396c4",
            "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
            "region": "us-west-2",
            "request_url": "lookout.com/",
            "timestamp": 1750435130948
        },
        {
            "id": "01978e10-6e44-77c8-9e70-64bcc8e1e611",
            "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
            "region": "us-west-2",
            "request_url": "apple.com/",
            "timestamp": 1750435130948
        },
        {
            "id": "01978e10-6e52-7095-8b59-321c7b2fdab5",
            "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
            "region": "us-west-2",
            "request_url": "mzstatic.com/",
            "timestamp": 1750435130962
        },
        {
            "id": "01978e11-5d63-7a18-acff-3a2775176d2a",
            "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
            "region": "us-west-2",
            "request_url": "slack.com/",
            "timestamp": 1750435192163
        }
    ]
}

def format_events(events, limit=None):
    """Format events into a readable table"""
    if not events.get('lookup_access_events'):
        return "No events found in the specified time range"
    
    table_data = []
    for event in events['lookup_access_events'][:limit]:
        # Convert timestamp from milliseconds to readable format
        timestamp_ms = event['timestamp']
        readable_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        table_data.append([
            readable_time,
            event['device_guid'][:8] + '...' + event['device_guid'][-3:],
            event['region'],
            event['request_url'],
            event['id'][:8] + '...'
        ])
    
    return tabulate(
        table_data,
        headers=['Timestamp', 'Device', 'Region', 'URL', 'Event ID'],
        tablefmt='fancy_grid',
        maxcolwidths=[None, 15, None, 40, None]
    )

if __name__ == "__main__":
    print("=== Lookout Web Access Activity Feed - Sample Data Demo ===")
    print(f"Enterprise: {sample_data['enterprise_guid']}")
    print(f"Time range: {sample_data['start_time']} to {sample_data['end_time']}\n")
    
    print(format_events(sample_data, limit=10))
    
    event_count = len(sample_data.get('lookup_access_events', []))
    print(f"\nTotal events found: {event_count}")
    
    print("\n=== JSON Format ===")
    print(json.dumps(sample_data, indent=2))
