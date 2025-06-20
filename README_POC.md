# Lookout to S3 Proof of Concept

A simple proof of concept to validate that we can pull web activity data from the Lookout API and dump it directly to an S3 bucket.

## 🎯 What This Does

1. **Fetches** recent web activity events from Lookout API (last 24 hours)
2. **Uploads** the raw JSON data directly to your S3 bucket
3. **Verifies** the upload was successful by reading the file back
4. **Reports** success/failure with detailed information

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
./setup_poc.sh
```

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements_poc.txt

# 2. Configure environment (create .env file)
LOOKOUT_ACCESS_TOKEN=your_token_here
S3_BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1

# 3. Run the POC
python simple_s3_poc.py
```

## 📋 Prerequisites

- **Python 3.7+** with pip
- **AWS credentials** configured (via AWS CLI, environment variables, or IAM role)
- **S3 bucket** that you have write access to
- **Lookout API token** with web activity feed access

## 🔧 Configuration

Only 3 environment variables needed:

| Variable | Required | Description |
|----------|----------|-------------|
| `LOOKOUT_ACCESS_TOKEN` | ✅ | Your Lookout API access token |
| `S3_BUCKET_NAME` | ✅ | S3 bucket name for uploads |
| `AWS_REGION` | ⚠️ | AWS region (defaults to us-east-1) |

## 📊 What You'll See

### Successful Run:
```
🚀 Lookout to S3 Proof of Concept
========================================
🔍 Fetching data from Lookout API...
✅ Fetched 42 events from Lookout API
📤 Uploading data to S3...
✅ Uploaded 42 events to s3://my-bucket/lookout-poc/web_activity_20250620_155030.json
🔍 Verifying upload...
✅ Verification successful:
   - File size: 15234 bytes
   - Event count: 42
   - Upload time: 2025-06-20T15:50:30.123456+00:00
   - Sample event: abc12345... -> https://example.com/page...

🎉 Proof of Concept Successful!
   Data successfully flowed: Lookout API → S3 Bucket
   File location: s3://my-bucket/lookout-poc/web_activity_20250620_155030.json
```

### No Recent Data:
If there's no web activity in the last 24 hours, the POC will create a test event to demonstrate the upload process.

## 📁 S3 File Structure

Files are uploaded to: `s3://your-bucket/lookout-poc/web_activity_YYYYMMDD_HHMMSS.json`

Example file content:
```json
{
  "timestamp": "2025-06-20T15:50:30.123456+00:00",
  "event_count": 42,
  "events": [
    {
      "id": "evt_12345",
      "device_guid": "abc-123-def-456",
      "timestamp": 1719764230000,
      "request_url": "https://example.com/page",
      "region": "US",
      "user_agent": "Mozilla/5.0..."
    }
  ]
}
```

## 🔍 Troubleshooting

### Common Issues:

**1. Missing AWS Credentials**
```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**2. S3 Bucket Access Denied**
- Verify bucket name is correct
- Check IAM permissions for S3 access
- Ensure bucket exists in the specified region

**3. Lookout API Authentication Failed**
- Verify your API token is correct
- Check token hasn't expired
- Ensure token has web activity feed permissions

**4. No Events Found**
- This is normal if there's no recent web activity
- The POC will create a test event for demonstration
- Try extending the time range in the code if needed

## 🎯 Next Steps After Successful POC

1. **Examine the uploaded file** in your S3 bucket
2. **Verify the data structure** meets your requirements
3. **Consider the full production system** with:
   - Continuous streaming
   - Parquet format for analytics
   - Partitioning by device/date
   - Error handling and monitoring
   - Integration with security tools

## 📚 Files in This POC

- `simple_s3_poc.py` - Main POC script
- `requirements_poc.txt` - Minimal dependencies
- `setup_poc.sh` - Automated setup script
- `README_POC.md` - This documentation

## 🔒 Security Notes

- The POC uploads raw JSON data (not optimized for analytics)
- No encryption beyond S3 default settings
- No data partitioning or organization
- For production use, consider the full S3 logging system

---

**This POC validates the basic data flow. For production deployment, use the full S3 logging system with proper partitioning, monitoring, and security controls.**
