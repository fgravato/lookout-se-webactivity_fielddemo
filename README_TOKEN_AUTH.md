# Lookout Web Activity Feed - Token Authentication

## Overview

The Lookout Web Activity Feed script now includes automatic token management that handles authentication seamlessly without requiring manual token refresh.

## How It Works

### Automatic Token Management

1. **Initial Token Check**: The script first checks for an existing valid access token from:
   - Environment variable `LOOKOUT_ACCESS_TOKEN`
   - Local file `access_token.txt`

2. **Automatic Refresh**: If no valid token is found, the script automatically refreshes the token using the `WEB_ACTIVITY_KEY` from your `.env` file

3. **Smart Retry**: If an API call fails with a 401 (Unauthorized) error, the script automatically:
   - Refreshes the access token
   - Retries the API call with the new token
   - Only retries once to prevent infinite loops

### Environment Variables Required

Make sure your `.env` file contains:

```bash
# Web Activity API Key (used for token refresh)
WEB_ACTIVITY_KEY=your_web_activity_key_here

# Optional: Current access token (will be auto-refreshed if expired)
LOOKOUT_ACCESS_TOKEN=your_current_access_token_here
```

## Usage Examples

### Basic Usage (Automatic Authentication)
```bash
# Get events from last 12 hours - token will be auto-refreshed if needed
python3 lookout_web_activity_feed.py --last-12h

# Get events from last 24 hours with 5 results
python3 lookout_web_activity_feed.py --last-24h --limit 5
```

### Force Token Refresh
```bash
# Force refresh the access token without making API calls
python3 lookout_web_activity_feed.py --force-refresh
```

### All Available Options
```bash
python3 lookout_web_activity_feed.py --help
```

## Token Storage

- **File Storage**: New tokens are automatically saved to `access_token.txt`
- **Environment Update**: The `LOOKOUT_ACCESS_TOKEN` environment variable is updated for the current session
- **Persistence**: Tokens persist between script runs via the `access_token.txt` file

## Error Handling

The script provides clear error messages for common issues:

- ❌ Missing `WEB_ACTIVITY_KEY` in environment variables
- ❌ Token refresh failures with detailed error information
- ❌ API request failures with response details

## Migration from Old Version

If you were previously using the `--refresh-token` parameter:

**Old way (manual):**
```bash
python3 lookout_web_activity_feed.py --refresh-token YOUR_REFRESH_TOKEN
```

**New way (automatic):**
```bash
# Just run normally - authentication is handled automatically
python3 lookout_web_activity_feed.py --last-12h
```

## Troubleshooting

### Token Refresh Fails
1. Verify your `WEB_ACTIVITY_KEY` is correct in the `.env` file
2. Check that the key has the proper permissions for the web activity API
3. Ensure your network connection allows HTTPS requests to `api.lookout.com`

### API Calls Fail
1. The script will automatically try to refresh the token once
2. If it still fails, check the error message for specific details
3. You can force a token refresh with `--force-refresh`

### No Events Returned
1. Check your time range parameters
2. Verify the device has web activity in the specified timeframe
3. Ensure your API key has access to the web activity feed

## Security Notes

- Tokens are stored locally in `access_token.txt` - keep this file secure
- The `WEB_ACTIVITY_KEY` should be kept confidential and not shared
- Tokens have expiration times and will be automatically refreshed as needed
