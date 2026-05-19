# Timeout and Retry Improvements

## Overview

This document describes the timeout and retry improvements made to the Lookout API client to resolve connection timeout issues.

## Problem

The original implementation had hardcoded 15-second timeouts that were causing connection failures:

```
API request failed: HTTPSConnectionPool(host='mtp.lookout.com', port=443): Read timed out. (read timeout=15)
```

## Solution

### 1. Configurable Timeout Settings

- **Default timeout increased**: From 15 seconds to 120 seconds
- **Configurable timeout**: Can be set via constructor or command line
- **Configurable retry count**: Default 3 retries, customizable

### 2. Retry Logic with Exponential Backoff

- **Automatic retries**: Failed requests are automatically retried
- **Exponential backoff**: Wait time increases between retries (1s, 2s, 4s, etc.)
- **Smart retry conditions**: Only retries on timeouts and server errors (5xx)

### 3. Enhanced Error Handling

- **Detailed error messages**: Clear indication of timeout vs other errors
- **Retry progress**: Shows retry attempts and wait times
- **Graceful degradation**: Falls back after max retries exceeded

## Usage

### Command Line Options

```bash
# Use default settings (120s timeout, 3 retries)
python lookout_api_client.py --api web-access

# Custom timeout and retries
python lookout_api_client.py --api web-access --timeout 180 --max-retries 5

# For very slow connections
python lookout_api_client.py --api web-access --timeout 300 --max-retries 10
```

### Programmatic Usage

```python
from lookout_api_client import LookoutAPIClient

# Default settings
client = LookoutAPIClient()

# Custom settings
client = LookoutAPIClient(timeout=90, max_retries=5)
```

## Implementation Details

### New Constructor Parameters

```python
def __init__(self, enable_device_mapping=True, timeout=60, max_retries=3):
```

### Retry Method

The new `_make_request_with_retry()` method handles:
- Timeout retries with exponential backoff
- Server error retries (5xx status codes)
- Progress reporting during retries
- Proper exception handling

### Updated API Methods

All API methods now use the retry logic:
- `_exchange_application_key_for_token()`
- `fetch_web_access_events()`
- `fetch_mra_devices()`

## Benefits

1. **Improved Reliability**: Automatic retries handle temporary network issues
2. **Better Performance**: Longer timeouts accommodate slow API responses
3. **Configurable**: Users can adjust settings based on their network conditions
4. **User-Friendly**: Clear progress indicators and error messages
5. **Backward Compatible**: Existing code continues to work with better defaults

## Testing

Run the test script to verify improvements:

```bash
python test_timeout_fix.py
```

## Recommended Settings

| Use Case | Timeout | Max Retries | Notes |
|----------|---------|-------------|-------|
| Fast Network | 60s | 2 | Quick failures, minimal retries |
| Normal Network | 120s | 3 | Default settings (API can take 74+ seconds) |
| Slow Network | 180s | 5 | Patient with retries |
| Very Slow/Unreliable | 300s | 10 | Maximum patience |

## Error Messages

### Before (Immediate Failure)
```
API request failed: HTTPSConnectionPool(host='mtp.lookout.com', port=443): Read timed out. (read timeout=15)
```

### After (With Retries)
```
⏱️  Request timeout (attempt 1/3), retrying in 1s...
⏱️  Request timeout (attempt 2/3), retrying in 2s...
⏱️  Request timeout (attempt 3/3), retrying in 4s...
❌ Request failed after 3 attempts due to timeout
```

## Files Modified

- `lookout_api_client.py`: Main timeout and retry improvements
- `test_timeout_fix.py`: Test script for verification
- `README_TIMEOUT_IMPROVEMENTS.md`: This documentation

## Future Improvements

- Add connection pooling for better performance
- Implement circuit breaker pattern for failing endpoints
- Add metrics collection for timeout analysis
- Consider async/await for concurrent requests