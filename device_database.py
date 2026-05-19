#!/usr/bin/env python3
"""
Lookout Device Database Manager
Creates and manages SQLite database for device information and user mapping
"""

import sqlite3
import json
import requests
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Device:
    """Device information data class"""
    guid: str
    email: str
    platform: str
    activation_status: str
    security_status: str
    protection_status: str
    customer_device_id: Optional[str] = None
    mdm_connector_id: Optional[str] = None
    mdm_device_id: Optional[str] = None
    hardware_manufacturer: Optional[str] = None
    hardware_model: Optional[str] = None
    os_version: Optional[str] = None
    last_checkin: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DeviceDatabase:
    """SQLite database manager for device information"""
    
    def __init__(self, db_path: str = "lookout_devices.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create devices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    guid TEXT PRIMARY KEY,
                    email TEXT,
                    platform TEXT,
                    activation_status TEXT,
                    security_status TEXT,
                    protection_status TEXT,
                    customer_device_id TEXT,
                    mdm_connector_id TEXT,
                    mdm_device_id TEXT,
                    hardware_manufacturer TEXT,
                    hardware_model TEXT,
                    os_version TEXT,
                    last_checkin TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create web activity events table for tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_activity_events (
                    id TEXT PRIMARY KEY,
                    device_guid TEXT,
                    timestamp INTEGER,
                    region TEXT,
                    request_url TEXT,
                    user_email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_guid) REFERENCES devices (guid)
                )
            ''')
            
            # Create device lookup cache for performance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_lookup_cache (
                    device_guid TEXT PRIMARY KEY,
                    user_email TEXT,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create refresh tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS refresh_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    refresh_type TEXT NOT NULL,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    devices_new INTEGER DEFAULT 0,
                    devices_updated INTEGER DEFAULT 0,
                    events_added INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    error_message TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_email ON devices(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_platform ON devices(platform)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_updated_at ON devices(updated_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_web_events_device_guid ON web_activity_events(device_guid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_web_events_timestamp ON web_activity_events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lookup_cache_email ON device_lookup_cache(user_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_refresh_history_type ON refresh_history(refresh_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_refresh_history_started ON refresh_history(started_at)')
            
            conn.commit()
            print(f"✅ Database initialized: {self.db_path}")
    
    def insert_or_update_device(self, device: Device) -> bool:
        """Insert or update device information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if device exists
            cursor.execute('SELECT guid FROM devices WHERE guid = ?', (device.guid,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing device
                cursor.execute('''
                    UPDATE devices SET
                        email = ?, platform = ?, activation_status = ?,
                        security_status = ?, protection_status = ?,
                        customer_device_id = ?, mdm_connector_id = ?, mdm_device_id = ?,
                        hardware_manufacturer = ?, hardware_model = ?, os_version = ?,
                        last_checkin = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE guid = ?
                ''', (
                    device.email, device.platform, device.activation_status,
                    device.security_status, device.protection_status,
                    device.customer_device_id, device.mdm_connector_id, device.mdm_device_id,
                    device.hardware_manufacturer, device.hardware_model, device.os_version,
                    device.last_checkin, device.guid
                ))
            else:
                # Insert new device
                cursor.execute('''
                    INSERT INTO devices (
                        guid, email, platform, activation_status, security_status,
                        protection_status, customer_device_id, mdm_connector_id,
                        mdm_device_id, hardware_manufacturer, hardware_model,
                        os_version, last_checkin
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    device.guid, device.email, device.platform, device.activation_status,
                    device.security_status, device.protection_status,
                    device.customer_device_id, device.mdm_connector_id, device.mdm_device_id,
                    device.hardware_manufacturer, device.hardware_model, device.os_version,
                    device.last_checkin
                ))
            
            # Update lookup cache
            cursor.execute('''
                INSERT OR REPLACE INTO device_lookup_cache (device_guid, user_email)
                VALUES (?, ?)
            ''', (device.guid, device.email))
            
            conn.commit()
            return not exists  # Return True if new device was inserted
    
    def get_device_by_guid(self, guid: str) -> Optional[Device]:
        """Get device information by GUID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM devices WHERE guid = ?', (guid,))
            row = cursor.fetchone()
            
            if row:
                return Device(
                    guid=row[0], email=row[1], platform=row[2],
                    activation_status=row[3], security_status=row[4],
                    protection_status=row[5], customer_device_id=row[6],
                    mdm_connector_id=row[7], mdm_device_id=row[8],
                    hardware_manufacturer=row[9], hardware_model=row[10],
                    os_version=row[11], last_checkin=row[12],
                    created_at=row[13], updated_at=row[14]
                )
            return None
    
    def get_user_email_by_device_guid(self, device_guid: str) -> Optional[str]:
        """Quick lookup of user email by device GUID using cache"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_email FROM device_lookup_cache WHERE device_guid = ?',
                (device_guid,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_devices_by_user(self, email: str) -> List[Device]:
        """Get all devices for a specific user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM devices WHERE email = ?', (email,))
            rows = cursor.fetchall()
            
            devices = []
            for row in rows:
                devices.append(Device(
                    guid=row[0], email=row[1], platform=row[2],
                    activation_status=row[3], security_status=row[4],
                    protection_status=row[5], customer_device_id=row[6],
                    mdm_connector_id=row[7], mdm_device_id=row[8],
                    hardware_manufacturer=row[9], hardware_model=row[10],
                    os_version=row[11], last_checkin=row[12],
                    created_at=row[13], updated_at=row[14]
                ))
            return devices
    
    def insert_web_activity_event(self, event_data: Dict) -> bool:
        """Insert web activity event with user mapping"""
        device_guid = event_data.get('device_guid')
        if not device_guid:
            return False
        
        # Get user email for this device
        user_email = self.get_user_email_by_device_guid(device_guid)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert event with user mapping
            cursor.execute('''
                INSERT OR REPLACE INTO web_activity_events (
                    id, device_guid, timestamp, region, request_url, user_email
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event_data.get('id'),
                device_guid,
                event_data.get('timestamp'),
                event_data.get('region'),
                event_data.get('request_url'),
                user_email
            ))
            
            conn.commit()
            return True
    
    def get_web_activity_with_users(self, limit: int = 100, hours_back: int = 24) -> List[Dict]:
        """Get web activity events with user information"""
        cutoff_time = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp() * 1000)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    w.id, w.device_guid, w.timestamp, w.region, 
                    w.request_url, w.user_email,
                    d.platform, d.security_status, d.protection_status
                FROM web_activity_events w
                LEFT JOIN devices d ON w.device_guid = d.guid
                WHERE w.timestamp >= ?
                ORDER BY w.timestamp DESC
                LIMIT ?
            ''', (cutoff_time, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'device_guid': row[1],
                    'timestamp': row[2],
                    'region': row[3],
                    'request_url': row[4],
                    'user_email': row[5],
                    'platform': row[6],
                    'security_status': row[7],
                    'protection_status': row[8]
                })
            
            return results
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count devices
            cursor.execute('SELECT COUNT(*) FROM devices')
            device_count = cursor.fetchone()[0]
            
            # Count web events
            cursor.execute('SELECT COUNT(*) FROM web_activity_events')
            event_count = cursor.fetchone()[0]
            
            # Count unique users
            cursor.execute('SELECT COUNT(DISTINCT email) FROM devices WHERE email IS NOT NULL')
            user_count = cursor.fetchone()[0]
            
            # Platform breakdown
            cursor.execute('SELECT platform, COUNT(*) FROM devices GROUP BY platform')
            platform_stats = dict(cursor.fetchall())
            
            # Recent activity (last 24 hours)
            cutoff_time = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp() * 1000)
            cursor.execute('SELECT COUNT(*) FROM web_activity_events WHERE timestamp >= ?', (cutoff_time,))
            recent_events = cursor.fetchone()[0]
            
            # Last refresh information
            cursor.execute('''
                SELECT refresh_type, completed_at, devices_new, devices_updated, status
                FROM refresh_history 
                WHERE status = 'completed'
                ORDER BY completed_at DESC 
                LIMIT 1
            ''')
            last_refresh = cursor.fetchone()
            
            # Data freshness check
            cursor.execute('SELECT MAX(updated_at) FROM devices')
            last_device_update = cursor.fetchone()[0]
            
            stats = {
                'total_devices': device_count,
                'total_web_events': event_count,
                'unique_users': user_count,
                'platform_breakdown': platform_stats,
                'recent_events_24h': recent_events,
                'database_path': self.db_path,
                'last_device_update': last_device_update
            }
            
            if last_refresh:
                stats['last_refresh'] = {
                    'type': last_refresh[0],
                    'completed_at': last_refresh[1],
                    'devices_new': last_refresh[2],
                    'devices_updated': last_refresh[3],
                    'status': last_refresh[4]
                }
            
            return stats
    
    def is_data_stale(self, max_age_hours: int = 24) -> bool:
        """Check if device data is stale and needs refresh"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check when devices were last updated
            cursor.execute('SELECT MAX(updated_at) FROM devices')
            last_update = cursor.fetchone()[0]
            
            if not last_update:
                return True  # No data at all
            
            # Parse the timestamp and check age
            try:
                last_update_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                age_hours = (datetime.now(timezone.utc) - last_update_dt).total_seconds() / 3600
                return age_hours > max_age_hours
            except (ValueError, AttributeError):
                return True  # Invalid timestamp format
    
    def log_refresh_start(self, refresh_type: str) -> int:
        """Log the start of a refresh operation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO refresh_history (refresh_type, status)
                VALUES (?, 'running')
            ''', (refresh_type,))
            conn.commit()
            return cursor.lastrowid
    
    def log_refresh_complete(self, refresh_id: int, devices_new: int = 0, 
                           devices_updated: int = 0, events_added: int = 0, 
                           error_message: str = None):
        """Log the completion of a refresh operation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            status = 'failed' if error_message else 'completed'
            cursor.execute('''
                UPDATE refresh_history SET
                    completed_at = CURRENT_TIMESTAMP,
                    devices_new = ?,
                    devices_updated = ?,
                    events_added = ?,
                    status = ?,
                    error_message = ?
                WHERE id = ?
            ''', (devices_new, devices_updated, events_added, status, error_message, refresh_id))
            conn.commit()
    
    def get_refresh_history(self, limit: int = 10) -> List[Dict]:
        """Get recent refresh history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT refresh_type, started_at, completed_at, devices_new, 
                       devices_updated, events_added, status, error_message
                FROM refresh_history
                ORDER BY started_at DESC
                LIMIT ?
            ''', (limit,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'refresh_type': row[0],
                    'started_at': row[1],
                    'completed_at': row[2],
                    'devices_new': row[3],
                    'devices_updated': row[4],
                    'events_added': row[5],
                    'status': row[6],
                    'error_message': row[7]
                })
            
            return history

class LookoutDeviceManager:
    """Main class for managing device data from Lookout APIs"""
    
    def __init__(self, db_path: str = "lookout_devices.db"):
        self.db = DeviceDatabase(db_path)
        self.access_token = self._get_access_token()
        self.mra_base_url = 'https://api.lookout.com'
        self.web_feed_url = 'https://mtp.lookout.com/data/web-access-feed'
    
    def _get_access_token(self) -> str:
        """Get access token from environment or file"""
        # Try environment variable first
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
            
        # Fallback to hardcoded token
        return 'your_jwt_token_here'
    
    def fetch_devices_from_api(self, limit: int = 1000) -> List[Device]:
        """Fetch devices from Lookout MRA API"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        devices = []
        oid = None
        
        while True:
            params = {'limit': min(limit, 1000)}  # API max is 1000
            if oid:
                params['oid'] = oid
            
            try:
                response = requests.get(
                    f"{self.mra_base_url}/mra/api/v2/devices",
                    headers=headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get('devices'):
                    break
                
                for device_data in data['devices']:
                    device = Device(
                        guid=device_data.get('guid'),
                        email=device_data.get('email'),
                        platform=device_data.get('platform'),
                        activation_status=device_data.get('activation_status'),
                        security_status=device_data.get('security_status'),
                        protection_status=device_data.get('protection_status'),
                        customer_device_id=device_data.get('customer_device_id'),
                        mdm_connector_id=str(device_data.get('details', {}).get('mdm_connector_id', '')),
                        mdm_device_id=device_data.get('details', {}).get('external_id'),
                        hardware_manufacturer=device_data.get('hardware', {}).get('manufacturer'),
                        hardware_model=device_data.get('hardware', {}).get('model'),
                        os_version=device_data.get('software', {}).get('os_version'),
                        last_checkin=device_data.get('checkin_time')
                    )
                    devices.append(device)
                
                # Check if we have more data to fetch
                if len(data['devices']) < params['limit']:
                    break
                
                # Set oid for next page
                oid = data['devices'][-1].get('oid')
                
                # Check if we've reached our limit
                if len(devices) >= limit:
                    break
                    
            except requests.RequestException as e:
                print(f"Error fetching devices: {e}")
                break
        
        return devices[:limit]  # Ensure we don't exceed the requested limit
    
    def sync_devices(self, limit: int = 1000, force_refresh: bool = False) -> Tuple[int, int]:
        """Sync devices from API to database with refresh tracking"""
        # Check if refresh is needed
        if not force_refresh and not self.db.is_data_stale():
            print("ℹ️  Device data is fresh, skipping refresh (use --force-refresh to override)")
            return 0, 0
        
        refresh_id = self.db.log_refresh_start('device_sync')
        
        try:
            print(f"🔄 Fetching devices from Lookout API (limit: {limit})...")
            devices = self.fetch_devices_from_api(limit)
            
            new_devices = 0
            updated_devices = 0
            
            for device in devices:
                if device.guid:  # Ensure we have a valid GUID
                    is_new = self.db.insert_or_update_device(device)
                    if is_new:
                        new_devices += 1
                    else:
                        updated_devices += 1
            
            self.db.log_refresh_complete(refresh_id, new_devices, updated_devices)
            print(f"✅ Device sync complete: {new_devices} new, {updated_devices} updated")
            return new_devices, updated_devices
            
        except Exception as e:
            self.db.log_refresh_complete(refresh_id, error_message=str(e))
            print(f"❌ Device sync failed: {e}")
            raise
    
    def auto_refresh_if_needed(self, max_age_hours: int = 24, limit: int = 1000) -> bool:
        """Automatically refresh device data if it's stale"""
        if self.db.is_data_stale(max_age_hours):
            print(f"🔄 Device data is stale (>{max_age_hours}h old), refreshing...")
            try:
                new_count, updated_count = self.sync_devices(limit, force_refresh=True)
                return True
            except Exception as e:
                print(f"❌ Auto-refresh failed: {e}")
                return False
        return False
    
    def fetch_and_store_web_activity(self, start_time: Optional[str] = None) -> int:
        """Fetch web activity events and store with user mapping"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        params = {}
        if start_time:
            params['start_interval'] = start_time
        
        try:
            response = requests.get(self.web_feed_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            events_stored = 0
            for event in data.get('lookup_access_events', []):
                if self.db.insert_web_activity_event(event):
                    events_stored += 1
            
            print(f"✅ Stored {events_stored} web activity events")
            return events_stored
            
        except requests.RequestException as e:
            print(f"Error fetching web activity: {e}")
            return 0

if __name__ == "__main__":
    # Example usage
    manager = LookoutDeviceManager()
    
    # Sync devices from API
    new_count, updated_count = manager.sync_devices(limit=100)
    
    # Fetch recent web activity
    events_count = manager.fetch_and_store_web_activity()
    
    # Show database stats
    stats = manager.db.get_database_stats()
    print(f"\n📊 Database Statistics:")
    print(f"   Total devices: {stats['total_devices']}")
    print(f"   Unique users: {stats['unique_users']}")
    print(f"   Web events: {stats['total_web_events']}")
    print(f"   Recent events (24h): {stats['recent_events_24h']}")
    print(f"   Platform breakdown: {stats['platform_breakdown']}")
