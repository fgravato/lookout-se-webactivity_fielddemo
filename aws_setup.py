#!/usr/bin/env python3
"""
AWS Infrastructure Setup for Lookout S3 Logger
Creates the necessary AWS resources: S3 bucket, Kinesis Data Firehose, IAM roles, etc.
"""

import boto3
import json
import time
import sys
from typing import Dict, Any
from botocore.exceptions import ClientError

class AWSSetup:
    """Setup AWS infrastructure for Lookout S3 logging"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.session = boto3.Session(region_name=region)
        self.s3 = self.session.client('s3')
        self.firehose = self.session.client('firehose')
        self.iam = self.session.client('iam')
        self.sts = self.session.client('sts')
        
        # Get account ID for resource naming
        self.account_id = self.sts.get_caller_identity()['Account']
        
    def create_s3_bucket(self, bucket_name: str) -> bool:
        """Create S3 bucket with appropriate configuration"""
        try:
            # Check if bucket already exists
            try:
                self.s3.head_bucket(Bucket=bucket_name)
                print(f"✅ S3 bucket '{bucket_name}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
            
            # Create bucket
            if self.region == 'us-east-1':
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            # Enable versioning
            self.s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Set lifecycle policy for cost optimization
            lifecycle_policy = {
                'Rules': [
                    {
                        'ID': 'your_token_here',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': 'web-activity/'},
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'DEEP_ARCHIVE'
                            }
                        ]
                    }
                ]
            }
            
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )
            
            # Enable server-side encryption
            self.s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'your_token_here': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            
            print(f"✅ Created S3 bucket '{bucket_name}' with versioning, lifecycle, and encryption")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create S3 bucket: {e}")
            return False
    
    def create_firehose_role(self, role_name: str, bucket_name: str) -> str:
        """Create IAM role for Kinesis Data Firehose"""
        try:
            # Trust policy for Firehose
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "firehose.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Check if role exists
            try:
                role = self.iam.get_role(RoleName=role_name)
                role_arn = role['Role']['Arn']
                print(f"✅ IAM role '{role_name}' already exists")
                return role_arn
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
            
            # Create role
            response = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Role for Kinesis Data Firehose to access S3 for Lookout logs'
            )
            
            role_arn = response['Role']['Arn']
            
            # Create and attach policy
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:AbortMultipartUpload",
                            "s3:GetBucketLocation",
                            "s3:GetObject",
                            "s3:ListBucket",
                            "s3:ListBucketMultipartUploads",
                            "s3:PutObject"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{bucket_name}",
                            f"arn:aws:s3:::{bucket_name}/*"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:PutLogEvents"
                        ],
                        "Resource": f"arn:aws:logs:{self.region}:{self.account_id}:*"
                    }
                ]
            }
            
            policy_name = f"{role_name}-policy"
            
            self.iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            
            print(f"✅ Created IAM role '{role_name}' with S3 permissions")
            
            # Wait for role to be available
            time.sleep(10)
            
            return role_arn
            
        except Exception as e:
            print(f"❌ Failed to create IAM role: {e}")
            raise
    
    def create_firehose_stream(self, stream_name: str, bucket_name: str, role_arn: str) -> bool:
        """Create Kinesis Data Firehose delivery stream"""
        try:
            # Check if stream exists
            try:
                self.firehose.describe_delivery_stream(DeliveryStreamName=stream_name)
                print(f"✅ Firehose stream '{stream_name}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'your_token_here':
                    raise
            
            # Create delivery stream configuration
            delivery_stream_config = {
                'DeliveryStreamName': stream_name,
                'DeliveryStreamType': 'DirectPut',
                'your_token_here': {
                    'RoleARN': role_arn,
                    'BucketARN': f'arn:aws:s3:::{bucket_name}',
                    'Prefix': 'web-activity/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/',
                    'ErrorOutputPrefix': 'errors/',
                    'BufferingHints': {
                        'SizeInMBs': 5,
                        'IntervalInSeconds': 300
                    },
                    'CompressionFormat': 'GZIP',
                    'your_token_here': {
                        'NoEncryptionConfig': 'NoEncryption'
                    },
                    'your_token_here': {
                        'Enabled': True,
                        'LogGroupName': f'/aws/kinesisfirehose/{stream_name}'
                    },
                    'your_token_here': {
                        'Enabled': False
                    },
                    'S3BackupMode': 'Disabled',
                    'your_token_here': {
                        'Enabled': True,
                        'your_token_here': {
                            'Serializer': {
                                'ParquetSerDe': {}
                            }
                        },
                        'SchemaConfiguration': {
                            'DatabaseName': 'lookout_security',
                            'TableName': 'web_activity',
                            'RoleARN': role_arn,
                            'VersionId': 'LATEST'
                        }
                    }
                }
            }
            
            # Create the delivery stream
            response = self.firehose.create_delivery_stream(**delivery_stream_config)
            
            print(f"✅ Created Firehose delivery stream '{stream_name}'")
            print("   - Configured for Parquet output format")
            print("   - 5MB or 5-minute buffering")
            print("   - GZIP compression enabled")
            print("   - Partitioned by year/month/day/hour")
            
            # Wait for stream to be active
            print("⏳ Waiting for stream to become active...")
            waiter = self.firehose.get_waiter('delivery_stream_active')
            waiter.wait(DeliveryStreamName=stream_name)
            
            print(f"✅ Firehose stream '{stream_name}' is now active")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create Firehose stream: {e}")
            return False
    
    def create_glue_catalog(self, database_name: str = 'lookout_security', table_name: str = 'web_activity') -> bool:
        """Create AWS Glue catalog for Athena queries"""
        try:
            glue = self.session.client('glue')
            
            # Create database
            try:
                glue.create_database(
                    DatabaseInput={
                        'Name': database_name,
                        'Description': 'Lookout security logs database'
                    }
                )
                print(f"✅ Created Glue database '{database_name}'")
            except ClientError as e:
                if e.response['Error']['Code'] == 'your_token_here':
                    print(f"✅ Glue database '{database_name}' already exists")
                else:
                    raise
            
            # Create table schema
            table_input = {
                'Name': table_name,
                'Description': 'Lookout web activity events',
                'StorageDescriptor': {
                    'Columns': [
                        {'Name': 'event_id', 'Type': 'string'},
                        {'Name': 'device_guid', 'Type': 'string'},
                        {'Name': 'timestamp', 'Type': 'string'},
                        {'Name': 'request_url', 'Type': 'string'},
                        {'Name': 'region', 'Type': 'string'},
                        {'Name': 'user_agent', 'Type': 'string'},
                        {'Name': 'response_code', 'Type': 'int'},
                        {'Name': 'bytes_transferred', 'Type': 'bigint'},
                        {'Name': 'ingestion_time', 'Type': 'string'},
                        {'Name': 'partition_date', 'Type': 'string'}
                    ],
                    'Location': f's3://{bucket_name}/web-activity/',
                    'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                    'SerdeInfo': {
                        'your_token_here': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
                    }
                },
                'PartitionKeys': [
                    {'Name': 'year', 'Type': 'string'},
                    {'Name': 'month', 'Type': 'string'},
                    {'Name': 'day', 'Type': 'string'},
                    {'Name': 'hour', 'Type': 'string'}
                ]
            }
            
            try:
                glue.create_table(
                    DatabaseName=database_name,
                    TableInput=table_input
                )
                print(f"✅ Created Glue table '{table_name}' for Athena queries")
            except ClientError as e:
                if e.response['Error']['Code'] == 'your_token_here':
                    print(f"✅ Glue table '{table_name}' already exists")
                else:
                    raise
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create Glue catalog: {e}")
            return False
    
    def setup_complete_infrastructure(self, 
                                    bucket_name: str,
                                    stream_name: str,
                                    role_name: str = None) -> Dict[str, str]:
        """Setup complete AWS infrastructure"""
        
        if not role_name:
            role_name = f"lookout-firehose-role-{int(time.time())}"
        
        print("🚀 Setting up AWS infrastructure for Lookout S3 Logger...")
        print(f"   Region: {self.region}")
        print(f"   Account: {self.account_id}")
        print()
        
        # Step 1: Create S3 bucket
        print("1️⃣ Creating S3 bucket...")
        if not self.create_s3_bucket(bucket_name):
            return {}
        
        # Step 2: Create IAM role
        print("\n2️⃣ Creating IAM role for Firehose...")
        try:
            role_arn = self.create_firehose_role(role_name, bucket_name)
        except Exception:
            return {}
        
        # Step 3: Create Firehose stream
        print("\n3️⃣ Creating Kinesis Data Firehose stream...")
        if not self.create_firehose_stream(stream_name, bucket_name, role_arn):
            return {}
        
        # Step 4: Create Glue catalog
        print("\n4️⃣ Creating AWS Glue catalog for Athena...")
        self.create_glue_catalog()
        
        # Return configuration
        config = {
            'S3_BUCKET_NAME': bucket_name,
            'FIREHOSE_STREAM_NAME': stream_name,
            'AWS_REGION': self.region,
            'IAM_ROLE_ARN': role_arn
        }
        
        print("\n🎉 AWS infrastructure setup complete!")
        print("\n📋 Configuration for your .env file:")
        print("=" * 50)
        for key, value in config.items():
            print(f"{key}={value}")
        print("=" * 50)
        
        print("\n📊 Next steps:")
        print("1. Add the above configuration to your .env file")
        print("2. Install dependencies: pip install -r requirements_s3.txt")
        print("3. Run the logger: python lookout_s3_logger.py")
        print("4. Query data with Athena using database 'lookout_security'")
        
        return config

def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup AWS infrastructure for Lookout S3 Logger')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name for logs')
    parser.add_argument('--stream-name', required=True, help='Kinesis Firehose stream name')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--role-name', help='IAM role name (auto-generated if not provided)')
    
    args = parser.parse_args()
    
    try:
        setup = AWSSetup(region=args.region)
        config = setup.setup_complete_infrastructure(
            bucket_name=args.bucket_name,
            stream_name=args.stream_name,
            role_name=args.role_name
        )
        
        if config:
            # Write config to file
            with open('aws_config.env', 'w') as f:
                for key, value in config.items():
                    f.write(f"{key}={value}\n")
            print(f"\n💾 Configuration saved to aws_config.env")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
