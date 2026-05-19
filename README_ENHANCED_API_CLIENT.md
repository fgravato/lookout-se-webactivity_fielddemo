# Enhanced Lookout API Client with Device Mapping

The `lookout_api_client.py` has been enhanced to automatically map device GUIDs to user emails using our local device database. This provides a much richer view of web activity events by showing which users are accessing which websites.

## 🚀 Key Features

### 1. **Automatic Device-to-User Mapping**
- Automatically enriches web access events with user email information
- Adds device platform (iOS/Android) and security status
- Shows mapping statistics (how many events were successfully mapped)

### 2. **Enhanced Output Formats**
- **Table Format**: Beautiful formatted tables with user information
- **JSON Format**: Complete JSON output with enriched data fields

### 3. **Flexible Configuration**
- Enable/disable user mapping with `--no-user-mapping` flag
- View database statistics with `--mapping-stats`
- All existing functionality preserved

## 📊 Usage Examples

### Basic Web Activity with User Mapping
```bash
# Get last 12 hours of web activity with user mapping
python3 lookout_api_client.py --api web-access --last-12h --format table --limit 10

# Output includes:
# ✅ Device mapping database connected
# 🔗 Device-to-user mapping: ENABLED
# 
# ╒═════════════════════════╤════════════════╤═══════════════════════════╤════════════╤═══════════╤═══════════════╤════════════╕
# │ Timestamp               │ Device         │ User Email                │ Platform   │ Region    │ URL           │ Security   │
# ╞═════════════════════════╪════════════════╪═══════════════════════════╪════════════╪═══════════╪═══════════════╪════════════╡
# │ 2025-06-20 15:58:50 UTC │ 828560be...97b │ frank.gravato@lookout.com │ IOS        │ us-west-2 │ mac.com/      │ SECURE     │
# ╘═════════════════════════╧════════════════╧═══════════════════════════╧════════════╧═══════════╧═══════════════╧════════════╛
# 
# 📊 User Mapping: 1082/1082 events mapped (100.0%)
```

### JSON Output with Enriched Data
```bash
# Get JSON format with enriched user data
python3 lookout_api_client.py --api web-access --last-12h --format json --limit 5

# Each event now includes:
# {
#   "id": "01978e10-6e35-76b8-8479-995e2002e174",
#   "device_guid": "828560be-3ec6-49cb-b785-6794c643897b",
#   "region": "us-west-2",
#   "request_url": "mac.com/",
#   "timestamp": 1750435130933,
#   "user_email": "frank.gravato@lookout.com",    # ← Added
#   "platform": "IOS",                           # ← Added
#   "security_status": "SECURE"                  # ← Added
# }
```

### Database Statistics
```bash
# View device mapping database statistics
python3 lookout_api_client.py --mapping-stats

# Output:
# === Device Mapping Database Statistics ===
# Database Path: lookout_devices.db
# Total Devices: 5
# Unique Users: 5
# Total Web Events: 618
# Recent Events (24h): 618
# 
# Platform Breakdown:
#   ANDROID: 2
#   IOS: 3
```

### Disable User Mapping
```bash
# Run without user mapping (original behavior)
python3 lookout_api_client.py --api web-access --last-12h --no-user-mapping
```

## 🔧 Command Line Options

### New Options
- `--no-user-mapping`: Disable automatic device-to-user mapping
- `--mapping-stats`: Show device mapping database statistics

### Existing Options
- `--api {web-access,mra-devices,both}`: Which API to query
- `--last-12h`: Show events from last 12 hours
- `--last-24h`: Show events from last 24 hours
- `--start-time`: Custom start time (ISO8601 format)
- `--limit N`: Number of items to display
- `--format {table,json}`: Output format
- `--show-token-info`: Show current token information
- `--exchange-key`: Force exchange application key for new access token

## 📈 Data Enrichment

When device mapping is enabled, each web access event is enriched with:

| Original Field | Enriched Fields | Description |
|---------------|----------------|-------------|
| `device_guid` | `user_email` | Email address of device owner |
| | `platform` | Device platform (iOS/Android) |
| | `security_status` | Device security status (SECURE, THREATS_LOW, etc.) |

## 🔍 Mapping Statistics

The system provides detailed statistics about the mapping process:

- **Mapped Events**: Events successfully matched to users
- **Unmapped Events**: Events where device GUID wasn't found in database
- **Mapping Rate**: Percentage of events successfully mapped

## 🏗️ Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Lookout Web       │    │   Enhanced API       │    │   Device Database   │
│   Access Feed API   │───▶│   Client             │───▶│   (SQLite)          │
│                     │    │                      │    │                     │
│ • Raw events        │    │ • Fetch events       │    │ • Device GUIDs      │
│ • Device GUIDs      │    │ • Enrich with users  │    │ • User emails       │
│ • Timestamps        │    │ • Format output      │    │ • Platform info     │
│ • URLs              │    │ • Show statistics    │    │ • Security status   │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## 🔄 Integration with Device Database

The enhanced client automatically:

1. **Connects** to the device database on startup
2. **Looks up** user email for each device GUID in web events
3. **Enriches** events with additional device information
4. **Tracks** mapping success rate and displays statistics

## 🎯 Use Cases

### Security Monitoring
```bash
# Monitor web activity for security analysis
python3 lookout_api_client.py --api web-access --last-24h --format table --limit 50
```

### User Activity Analysis
```bash
# Export user web activity data for analysis
python3 lookout_api_client.py --api web-access --last-24h --format json > user_activity.json
```

### Database Health Check
```bash
# Check device database statistics
python3 lookout_api_client.py --mapping-stats
```

### Compliance Reporting
```bash
# Generate compliance report with user attribution
python3 lookout_api_client.py --api web-access --start-time "2025-06-01T00:00:00+00:00" --format json
```

## 🛠️ Technical Details

### Error Handling
- Gracefully handles missing device database
- Falls back to original behavior if mapping fails
- Shows clear status messages about mapping availability

### Performance
- Efficient database lookups using indexed queries
- Minimal overhead for event enrichment
- Caches device information during processing

### Compatibility
- Fully backward compatible with existing scripts
- All original functionality preserved
- Optional features can be disabled

## 📝 Example Output Comparison

### Before Enhancement
```
╒═════════════════════════╤════════════════╤═══════════╤═══════════════╕
│ Timestamp               │ Device         │ Region    │ URL           │
╞═════════════════════════╪════════════════╪═══════════╪═══════════════╡
│ 2025-06-20 15:58:50 UTC │ 828560be...97b │ us-west-2 │ mac.com/      │
╘═════════════════════════╧════════════════╧═══════════╧═══════════════╛
```

### After Enhancement
```
╒═════════════════════════╤════════════════╤═══════════════════════════╤════════════╤═══════════╤═══════════════╤════════════╕
│ Timestamp               │ Device         │ User Email                │ Platform   │ Region    │ URL           │ Security   │
╞═════════════════════════╪════════════════╪═══════════════════════════╪════════════╪═══════════╪═══════════════╪════════════╡
│ 2025-06-20 15:58:50 UTC │ 828560be...97b │ frank.gravato@lookout.com │ IOS        │ us-west-2 │ mac.com/      │ SECURE     │
╘═════════════════════════╧════════════════╧═══════════════════════════╧════════════╧═══════════╧═══════════════╧════════════╛

📊 User Mapping: 1082/1082 events mapped (100.0%)
```

## 🔗 Related Components

- **Device Database** (`device_database.py`): Core database functionality
- **Device Manager CLI** (`device_manager_cli.py`): Database management tools
- **Demo Scripts** (`demo_device_mapping.py`): Example usage patterns

---

*This enhanced API client bridges the gap between raw device telemetry and actionable user insights, making web activity monitoring more effective and user-friendly.*
