# Lookout Device Database and User Mapping Solution

This solution provides a complete SQLite-based system for managing Lookout device information and mapping web activity events to device owners using the Lookout Mobile Risk API (MRA) and Web Activity Feed API.

## 🎯 Overview

The system solves the challenge of correlating web activity events (which contain device GUIDs) with actual users by:

1. **Syncing device data** from the Lookout MRA API to build a local device-to-user mapping database
2. **Storing web activity events** with automatic user email resolution
3. **Providing fast lookups** for device-to-user mapping and user-to-devices mapping
4. **Offering CLI tools** for easy data exploration and management

## 📁 Files

- **`device_database.py`** - Core database management and API integration
- **`device_manager_cli.py`** - Command-line interface for database operations
- **`demo_device_mapping.py`** - Demonstration script showing complete workflow
- **`lookout_devices.db`** - SQLite database (created automatically)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install requests python-dotenv tabulate
```

### 2. Set Up Authentication

Create a `.env` file or set environment variable:
```bash
export LOOKOUT_ACCESS_TOKEN="your_bearer_token_here"
```

Or place your token in `access_token.txt`

### 3. Run the Demo

```bash
python demo_device_mapping.py
```

This will:
- Initialize the SQLite database
- Sync devices from Lookout API
- Fetch web activity events
- Demonstrate device-to-user mapping
- Show usage examples

## 🗄️ Database Schema

### Devices Table
```sql
CREATE TABLE devices (
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
);
```

### Web Activity Events Table
```sql
CREATE TABLE web_activity_events (
    id TEXT PRIMARY KEY,
    device_guid TEXT,
    timestamp INTEGER,
    region TEXT,
    request_url TEXT,
    user_email TEXT,  -- Automatically resolved from device mapping
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_guid) REFERENCES devices (guid)
);
```

### Device Lookup Cache Table
```sql
CREATE TABLE device_lookup_cache (
    device_guid TEXT PRIMARY KEY,
    user_email TEXT,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## 🛠️ CLI Usage

### Show Database Statistics
```bash
python device_manager_cli.py stats
```

### Sync Devices from API
```bash
python device_manager_cli.py sync-devices --limit 100
```

### Sync Web Activity Events
```bash
python device_manager_cli.py sync-web-activity --hours-back 24
```

### Show All Devices
```bash
python device_manager_cli.py show-devices --limit 10
python device_manager_cli.py show-devices --platform ANDROID
python device_manager_cli.py show-devices --security-status SECURE --details
```

### Show Web Activity with User Mapping
```bash
python device_manager_cli.py show-web-activity --limit 20 --hours-back 48
```

### Look Up User's Devices
```bash
python device_manager_cli.py lookup-user frank.gravato@lookout.com
python device_manager_cli.py lookup-user frank.gravato@lookout.com --details
```

### Look Up Device Information
```bash
python device_manager_cli.py lookup-device 828560be-1234-5678-9abc-def012345678
```

### Map Device GUID to User
```bash
python device_manager_cli.py map-device 828560be-1234-5678-9abc-def012345678
```

## 🔧 Programmatic Usage

### Basic Device Management
```python
from device_database import LookoutDeviceManager

# Initialize manager
manager = LookoutDeviceManager()

# Sync devices from API
new_count, updated_count = manager.sync_devices(limit=1000)

# Fetch web activity events
events_count = manager.fetch_and_store_web_activity()

# Get database statistics
stats = manager.db.get_database_stats()
print(f"Total devices: {stats['total_devices']}")
```

### Device-to-User Mapping
```python
# Quick lookup: device GUID to user email
user_email = manager.db.get_user_email_by_device_guid(device_guid)

# Get device details
device = manager.db.get_device_by_guid(device_guid)

# Get all devices for a user
devices = manager.db.get_devices_by_user("frank.gravato@lookout.com")
```

### Web Activity with User Context
```python
# Get recent web activity with user mapping
events = manager.db.get_web_activity_with_users(limit=100, hours_back=24)

for event in events:
    print(f"User: {event['user_email']}")
    print(f"Device: {event['device_guid']}")
    print(f"URL: {event['request_url']}")
    print(f"Platform: {event['platform']}")
```

## 📊 Example Output

### Database Statistics
```
📊 Database Statistics
==================================================
Database Path: lookout_devices.db
Total Devices: 5
Unique Users: 5
Total Web Events: 618
Recent Events (24h): 618

Platform Breakdown:
  ANDROID: 2
  IOS: 3
```

### Device Listing
```
📱 Devices in Database
==================================================
╒═══════════════╤═══════════════════════════╤════════════╤════════════╤═══════════╕
│ Device GUID   │ Email                     │ Platform   │ Security   │ Status    │
╞═══════════════╪═══════════════════════════╪════════════╪════════════╪═══════════╡
│ 828560be...   │ frank.gravato@lookout.com │ IOS        │ SECURE     │ ACTIVATED │
│ 0394d842...   │ frankie.gravato@gmail.com │ ANDROID    │ SECURE     │ ACTIVATED │
╘═══════════════╧═══════════════════════════╧════════════╧════════════╧═══════════╛
```

### Web Activity with User Mapping
```
🌐 Web Activity Events (Last 24 hours)
================================================================================
╒═════════════════════╤═════════════╤═══════════════════════════╤════════════╤═══════════╤════════════════════════════════════════╕
│ Timestamp           │ Device      │ User Email                │ Platform   │ Region    │ URL                                    │
╞═════════════════════╪═════════════╪═══════════════════════════╪════════════╪═══════════╪════════════════════════════════════════╡
│ 2025-06-20 19:23:18 │ 828560be... │ frank.gravato@lookout.com │ IOS        │ us-west-2 │ mail.google.com/                       │
│ 2025-06-20 19:23:17 │ 828560be... │ frank.gravato@lookout.com │ IOS        │ us-west-2 │ googleusercontent.com/                 │
╘═════════════════════╧═════════════╧═══════════════════════════╧════════════╧═══════════╧════════════════════════════════════════╛
```

## 🔄 Data Flow

1. **Device Sync**: Fetch devices from `/mra/api/v2/devices` endpoint
2. **User Mapping**: Extract email addresses and create device-to-user mappings
3. **Web Activity**: Fetch events from web activity feed API
4. **Correlation**: Automatically resolve device GUIDs to user emails in web events
5. **Storage**: Store everything in SQLite with proper indexing for fast lookups

## 🎯 Key Features

- **Fast Lookups**: Optimized database schema with indexes for quick device-to-user mapping
- **Automatic Correlation**: Web activity events automatically include user email resolution
- **Pagination Support**: Handle large datasets with proper API pagination
- **Error Handling**: Robust error handling for API failures and token expiration
- **CLI Interface**: Easy-to-use command-line tools for data exploration
- **Flexible Filtering**: Filter devices by platform, security status, activation status
- **Time-based Queries**: Query web activity by time ranges
- **User-centric Views**: Look up all devices for a specific user

## 🔐 Security Considerations

- Store access tokens securely (environment variables or secure files)
- Database contains PII (email addresses) - handle according to privacy policies
- Consider encryption for sensitive data in production environments
- Implement proper access controls for the database file

## 🚀 Production Deployment

For production use, consider:

1. **Database**: Use PostgreSQL or MySQL instead of SQLite for better concurrency
2. **Scheduling**: Set up cron jobs or scheduled tasks for regular data sync
3. **Monitoring**: Add logging and monitoring for API failures and data quality
4. **Backup**: Implement regular database backups
5. **Scaling**: Consider data retention policies for large datasets
6. **API Limits**: Implement rate limiting and retry logic for API calls

## 📝 API Endpoints Used

- **Device API**: `GET /mra/api/v2/devices` - Fetch device information with user mappings
- **Web Activity API**: `GET /data/web-access-feed` - Fetch web activity events

## 🤝 Contributing

To extend this solution:

1. Add new device fields to the `Device` dataclass and database schema
2. Implement additional API endpoints in `LookoutDeviceManager`
3. Add new CLI commands in `device_manager_cli.py`
4. Create custom queries in the database layer

## 📄 License

This solution is provided as-is for demonstration purposes. Adapt according to your organization's requirements and security policies.
