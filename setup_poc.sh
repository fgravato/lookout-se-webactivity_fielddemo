#!/bin/bash

# Simple POC Setup Script
# Quick setup for testing Lookout API to S3 data flow

set -e

echo "🚀 Lookout S3 POC Quick Setup"
echo "============================="
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    echo "Please provide the following information:"
    echo
    
    read -p "Lookout API Token: " LOOKOUT_TOKEN
    read -p "S3 Bucket Name: " BUCKET_NAME
    read -p "AWS Region [us-east-1]: " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}
    
    cat > .env << EOF
# POC Configuration
LOOKOUT_ACCESS_TOKEN=$LOOKOUT_TOKEN
S3_BUCKET_NAME=$BUCKET_NAME
AWS_REGION=$AWS_REGION
LOOKOUT_API_URL=https://mtp.lookout.com/data/web-access-feed
EOF
    
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo
echo "📦 Installing dependencies..."
pip install -r requirements_poc.txt

echo
echo "🧪 Running POC..."
python simple_s3_poc.py

echo
echo "🎉 POC Complete!"
echo
echo "If successful, you should see:"
echo "- Data fetched from Lookout API"
echo "- JSON file uploaded to S3"
echo "- Verification that the file was uploaded correctly"
echo
echo "Check your S3 bucket for the uploaded file in the 'lookout-poc/' folder"
