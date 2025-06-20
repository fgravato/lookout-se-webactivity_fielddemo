#!/usr/bin/env python3
"""
Lookout Device Manager CLI
Command-line interface for managing device database and user mapping
"""

import argparse
import sys
import json
from datetime import datetime, timezone, timedelta
from tabulate import tabulate
from device_database import LookoutDeviceManager, DeviceDatabase

def format_timestamp(timestamp_ms):
    """Convert timestamp from milliseconds to readable format"""
    if timestamp_ms:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    return 'N/A'

def format_devices_table(devices, show_details=False):
    """Format devices into a readable table"""
    if not devices:
        return "No devices found"
    
    if show_details:
        table_data = []
        for device in devices:
            table_data.append([
                device.guid[:8] + '...' if device.guid else 'N/A',
                device.email or 'N/A',
                device.platform or 'N/A',
                device.activation_status or 'N/A',
                device.security_status or 'N/A',
                device.protection_status or 'N/A',
                f"{device.hardware_manufacturer or ''} {device.hardware_model or ''}".strip() or 'N/A',
                device.os_version or 'N/A',
                device.last_checkin[:19] if device.last_checkin else 'N/A'
            ])
        
        return tabulate(
            table_data,
            headers=['Device GUID', 'Email', 'Platform', 'Activation', 'Security', 'Protection', 'Hardware', 'OS Version', 'Last Checkin'],
            tablefmt='fancy_grid',
            maxcolwidths=[12, 25, 10, 12, 12, 12, 20, 15, 19]
        )
    else:
        table_data = []
        for device in devices:
            table_data.append([
                device.guid[:8] + '...' if device.guid else 'N/A',
                device.email or 'N/A',
                device.platform or 'N/A',
                device.security_status or 'N/A',
                device.activation_status or 'N/A'
            ])
        
        return tabulate(
            table_data,
            headers=['Device GUID', 'Email', 'Platform', 'Security', 'Status'],
            tablefmt='fancy_grid',
            maxcolwidths=[12, 25, 10, 12, 12]
        )

def format_web_activity_table(events):
    """Format web activity events with user mapping into a table"""
    if not events:
        return "No web activity events found"
    
    table_data = []
    for event in events:
        table_data.append([
            format_timestamp(event['timestamp']),
            event['device_guid'][:8] + '...' if event['device_guid'] else 'N/A',
            event['user_email'] or 'Unknown User',
            event['platform'] or 'N/A',
            event['region'] or 'N/A',
            event['request_url'][:40] + '...' if len(event.get('request_url', '')) > 40 else event.get('request_url', 'N/A'),
            event['security_status'] or 'N/A'
        ])
    
    return tabulate(
        table_data,
        headers=['Timestamp', 'Device', 'User Email', 'Platform', 'Region', 'URL', 'Security'],
        tablefmt='fancy_grid',
        maxcolwidths=[19, 12, 25, 10, 10, 43, 12]
    )

def cmd_sync_devices(args, manager):
    """Sync devices from Lookout API"""
    print(f"🔄 Syncing devices from Lookout API...")
    new_count, updated_count = manager.sync_devices(limit=args.limit)
    print(f"✅ Sync complete: {new_count} new devices, {updated_count} updated devices")

def cmd_sync_web_activity(args, manager):
    """Sync web activity events"""
    start_time = None
    if args.hours_back:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=args.hours_back)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    elif args.start_time:
        start_time = args.start_time
    
    print(f"🔄 Syncing web activity events...")
    events_count = manager.fetch_and_store_web_activity(start_time=start_time)
    print(f"✅ Stored {events_count} web activity events")

def cmd_show_stats(args, manager):
    """Show database statistics"""
    stats = manager.db.get_database_stats()
    
    print("📊 Database Statistics")
    print("=" * 50)
    print(f"Database Path: {stats['database_path']}")
    print(f"Total Devices: {stats['total_devices']}")
    print(f"Unique Users: {stats['unique_users']}")
    print(f"Total Web Events: {stats['total_web_events']}")
    print(f"Recent Events (24h): {stats['recent_events_24h']}")
    
    if stats['platform_breakdown']:
        print(f"\nPlatform Breakdown:")
        for platform, count in stats['platform_breakdown'].items():
            print(f"  {platform}: {count}")

def cmd_lookup_device(args, manager):
    """Look up device information by GUID"""
    device = manager.db.get_device_by_guid(args.guid)
    if device:
        print(f"📱 Device Information for {args.guid}")
        print("=" * 50)
        print(f"GUID: {device.guid}")
        print(f"User Email: {device.email or 'N/A'}")
        print(f"Platform: {device.platform or 'N/A'}")
        print(f"Activation Status: {device.activation_status or 'N/A'}")
        print(f"Security Status: {device.security_status or 'N/A'}")
        print(f"Protection Status: {device.protection_status or 'N/A'}")
        print(f"Customer Device ID: {device.customer_device_id or 'N/A'}")
        print(f"MDM Connector ID: {device.mdm_connector_id or 'N/A'}")
        print(f"MDM Device ID: {device.mdm_device_id or 'N/A'}")
        print(f"Hardware: {device.hardware_manufacturer or ''} {device.hardware_model or ''}".strip() or 'N/A')
        print(f"OS Version: {device.os_version or 'N/A'}")
        print(f"Last Checkin: {device.last_checkin or 'N/A'}")
        print(f"Created: {device.created_at or 'N/A'}")
        print(f"Updated: {device.updated_at or 'N/A'}")
    else:
        print(f"❌ Device with GUID {args.guid} not found in database")

def cmd_lookup_user(args, manager):
    """Look up devices by user email"""
    devices = manager.db.get_devices_by_user(args.email)
    if devices:
        print(f"👤 Devices for user: {args.email}")
        print("=" * 50)
        print(format_devices_table(devices, show_details=args.details))
        print(f"\nTotal devices: {len(devices)}")
    else:
        print(f"❌ No devices found for user {args.email}")

def cmd_show_devices(args, manager):
    """Show all devices in database"""
    # This is a simple implementation - for large databases, you'd want pagination
    import sqlite3
    with sqlite3.connect(manager.db.db_path) as conn:
        cursor = conn.cursor()
        
        query = 'SELECT * FROM devices'
        params = []
        
        if args.platform:
            query += ' WHERE platform = ?'
            params.append(args.platform)
        
        if args.security_status:
            if 'WHERE' in query:
                query += ' AND security_status = ?'
            else:
                query += ' WHERE security_status = ?'
            params.append(args.security_status)
        
        query += ' ORDER BY updated_at DESC'
        
        if args.limit:
            query += ' LIMIT ?'
            params.append(args.limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if rows:
            devices = []
            for row in rows:
                from device_database import Device
                device = Device(
                    guid=row[0], email=row[1], platform=row[2],
                    activation_status=row[3], security_status=row[4],
                    protection_status=row[5], customer_device_id=row[6],
                    mdm_connector_id=row[7], mdm_device_id=row[8],
                    hardware_manufacturer=row[9], hardware_model=row[10],
                    os_version=row[11], last_checkin=row[12],
                    created_at=row[13], updated_at=row[14]
                )
                devices.append(device)
            
            print(f"📱 Devices in Database")
            print("=" * 50)
            print(format_devices_table(devices, show_details=args.details))
            print(f"\nShowing {len(devices)} devices")
        else:
            print("No devices found matching criteria")

def cmd_show_web_activity(args, manager):
    """Show web activity events with user mapping"""
    events = manager.db.get_web_activity_with_users(
        limit=args.limit or 50,
        hours_back=args.hours_back or 24
    )
    
    if events:
        print(f"🌐 Web Activity Events (Last {args.hours_back or 24} hours)")
        print("=" * 80)
        print(format_web_activity_table(events))
        print(f"\nShowing {len(events)} events")
    else:
        print(f"No web activity events found in the last {args.hours_back or 24} hours")

def cmd_map_device_to_user(args, manager):
    """Map a device GUID to user email for testing"""
    user_email = manager.db.get_user_email_by_device_guid(args.guid)
    if user_email:
        print(f"✅ Device {args.guid} is owned by: {user_email}")
    else:
        print(f"❌ No user mapping found for device {args.guid}")
        print("   Try syncing devices first with: python device_manager_cli.py sync-devices")

def main():
    parser = argparse.ArgumentParser(description='Lookout Device Manager CLI')
    parser.add_argument('--db-path', default='lookout_devices.db', help='Path to SQLite database')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sync devices command
    sync_devices_parser = subparsers.add_parser('sync-devices', help='Sync devices from Lookout API')
    sync_devices_parser.add_argument('--limit', type=int, default=1000, help='Maximum number of devices to sync')
    
    # Sync web activity command
    sync_web_parser = subparsers.add_parser('sync-web-activity', help='Sync web activity events')
    sync_web_parser.add_argument('--hours-back', type=int, help='Hours back to fetch events')
    sync_web_parser.add_argument('--start-time', help='Start time (ISO format)')
    
    # Show stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Lookup device command
    lookup_device_parser = subparsers.add_parser('lookup-device', help='Look up device by GUID')
    lookup_device_parser.add_argument('guid', help='Device GUID to look up')
    
    # Lookup user command
    lookup_user_parser = subparsers.add_parser('lookup-user', help='Look up devices by user email')
    lookup_user_parser.add_argument('email', help='User email to look up')
    lookup_user_parser.add_argument('--details', action='store_true', help='Show detailed device information')
    
    # Show devices command
    show_devices_parser = subparsers.add_parser('show-devices', help='Show devices in database')
    show_devices_parser.add_argument('--platform', choices=['ANDROID', 'IOS'], help='Filter by platform')
    show_devices_parser.add_argument('--security-status', help='Filter by security status')
    show_devices_parser.add_argument('--limit', type=int, help='Limit number of results')
    show_devices_parser.add_argument('--details', action='store_true', help='Show detailed device information')
    
    # Show web activity command
    show_web_parser = subparsers.add_parser('show-web-activity', help='Show web activity with user mapping')
    show_web_parser.add_argument('--limit', type=int, default=50, help='Number of events to show')
    show_web_parser.add_argument('--hours-back', type=int, default=24, help='Hours back to show events')
    
    # Map device to user command
    map_parser = subparsers.add_parser('map-device', help='Map device GUID to user email')
    map_parser.add_argument('guid', help='Device GUID to map')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = LookoutDeviceManager(db_path=args.db_path)
        
        if args.command == 'sync-devices':
            cmd_sync_devices(args, manager)
        elif args.command == 'sync-web-activity':
            cmd_sync_web_activity(args, manager)
        elif args.command == 'stats':
            cmd_show_stats(args, manager)
        elif args.command == 'lookup-device':
            cmd_lookup_device(args, manager)
        elif args.command == 'lookup-user':
            cmd_lookup_user(args, manager)
        elif args.command == 'show-devices':
            cmd_show_devices(args, manager)
        elif args.command == 'show-web-activity':
            cmd_show_web_activity(args, manager)
        elif args.command == 'map-device':
            cmd_map_device_to_user(args, manager)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
