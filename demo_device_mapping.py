#!/usr/bin/env python3
"""
Demo script for Lookout Device Database and User Mapping
Demonstrates the complete workflow of syncing devices and mapping web activity to users
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from device_database import LookoutDeviceManager

def main():
    print("🚀 Lookout Device Database Demo")
    print("=" * 60)
    
    # Initialize the device manager
    print("1. Initializing Device Manager...")
    manager = LookoutDeviceManager()
    
    # Show initial database stats
    print("\n2. Initial Database State:")
    stats = manager.db.get_database_stats()
    print(f"   📊 Total devices: {stats['total_devices']}")
    print(f"   👥 Unique users: {stats['unique_users']}")
    print(f"   🌐 Web events: {stats['total_web_events']}")
    
    # Sync devices from API
    print("\n3. Syncing Devices from Lookout API...")
    try:
        new_count, updated_count = manager.sync_devices(limit=50)  # Limit for demo
        print(f"   ✅ Synced: {new_count} new, {updated_count} updated")
    except Exception as e:
        print(f"   ❌ Error syncing devices: {e}")
        print("   This might be due to token expiration or API limits")
    
    # Sync web activity
    print("\n4. Syncing Web Activity Events...")
    try:
        # Get events from last 24 hours
        start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        events_count = manager.fetch_and_store_web_activity(start_time=start_time)
        print(f"   ✅ Stored {events_count} web activity events")
    except Exception as e:
        print(f"   ❌ Error syncing web activity: {e}")
        print("   This might be due to token expiration or API limits")
    
    # Show updated database stats
    print("\n5. Updated Database State:")
    stats = manager.db.get_database_stats()
    print(f"   📊 Total devices: {stats['total_devices']}")
    print(f"   👥 Unique users: {stats['unique_users']}")
    print(f"   🌐 Web events: {stats['total_web_events']}")
    print(f"   📱 Platform breakdown: {stats['platform_breakdown']}")
    print(f"   🕐 Recent events (24h): {stats['recent_events_24h']}")
    
    # Demonstrate device-to-user mapping
    print("\n6. Device-to-User Mapping Examples:")
    
    # Get some devices to demonstrate mapping
    import sqlite3
    with sqlite3.connect(manager.db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT guid, email FROM devices WHERE email IS NOT NULL LIMIT 5')
        sample_devices = cursor.fetchall()
    
    if sample_devices:
        print("   Sample device mappings:")
        for guid, email in sample_devices:
            print(f"   📱 {guid[:8]}... → 👤 {email}")
            
            # Test the lookup function
            lookup_email = manager.db.get_user_email_by_device_guid(guid)
            if lookup_email == email:
                print(f"      ✅ Lookup confirmed: {lookup_email}")
            else:
                print(f"      ❌ Lookup mismatch: expected {email}, got {lookup_email}")
    else:
        print("   No devices with email addresses found")
    
    # Show web activity with user mapping
    print("\n7. Web Activity with User Mapping:")
    events = manager.db.get_web_activity_with_users(limit=10, hours_back=24)
    
    if events:
        print("   Recent web activity events:")
        for event in events[:5]:  # Show first 5
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000, tz=timezone.utc).strftime('%H:%M:%S')
            device_short = event['device_guid'][:8] + '...' if event['device_guid'] else 'N/A'
            user_email = event['user_email'] or 'Unknown User'
            url = event['request_url'][:40] + '...' if len(event.get('request_url', '')) > 40 else event.get('request_url', 'N/A')
            
            print(f"   🕐 {timestamp} | 📱 {device_short} | 👤 {user_email} | 🌐 {url}")
    else:
        print("   No recent web activity events found")
    
    # Demonstrate user device lookup
    print("\n8. User Device Lookup Examples:")
    
    # Get some users to demonstrate lookup
    with sqlite3.connect(manager.db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT email FROM devices WHERE email IS NOT NULL LIMIT 3')
        sample_users = [row[0] for row in cursor.fetchall()]
    
    if sample_users:
        for email in sample_users:
            devices = manager.db.get_devices_by_user(email)
            print(f"   👤 {email} has {len(devices)} device(s):")
            for device in devices:
                print(f"      📱 {device.guid[:8]}... ({device.platform}, {device.security_status})")
    else:
        print("   No users found in database")
    
    print("\n9. Demo Complete! 🎉")
    print("=" * 60)
    print("You can now use the CLI tool to explore the data:")
    print("  python device_manager_cli.py stats")
    print("  python device_manager_cli.py show-devices --limit 10")
    print("  python device_manager_cli.py show-web-activity --limit 10")
    print("  python device_manager_cli.py lookup-user <email>")
    print("  python device_manager_cli.py map-device <device-guid>")

if __name__ == "__main__":
    main()
