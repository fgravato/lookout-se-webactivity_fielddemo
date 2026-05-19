#!/usr/bin/env python3
"""
Repository Preparation Script for GitHub Publication

This script prepares the repository for safe publication by:
- Removing sensitive files
- Sanitizing code files
- Creating safe example files
- Validating the final state
"""

import os
import shutil
import re
from pathlib import Path

class RepositoryPreparer:
    def __init__(self):
        self.removed_files = []
        self.sanitized_files = []
        
        # Files to remove completely
        self.files_to_remove = [
            '.env',
            'access_token.txt',
            'token-test.txt',
            'lookout_devices.db',
            'notes.md',
        ]
        
        # Sensitive patterns to replace with placeholders
        self.sanitization_patterns = [
            # JWT tokens
            (r'eyJ[A-Za-z0-9_/+-]*\.eyJ[A-Za-z0-9_/+-]*\.[A-Za-z0-9_/+-]*', 'your_jwt_token_here'),
            # Long base64-like strings that might be tokens
            (r'[A-Za-z0-9+/]{40,}={0,2}', 'your_token_here'),
            # Specific token patterns in code
            (r'"[A-Za-z0-9+/]{20,}"', '"your_token_here"'),
            (r"'[A-Za-z0-9+/]{20,}'", "'your_token_here'"),
        ]

    def remove_sensitive_files(self):
        """Remove files that should not be published"""
        for file_path in self.files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.removed_files.append(file_path)
                print(f"✅ Removed {file_path}")

    def sanitize_file(self, file_path):
        """Sanitize a file by replacing sensitive patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply sanitization patterns
            for pattern, replacement in self.sanitization_patterns:
                content = re.sub(pattern, replacement, content)
            
            # Only write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.sanitized_files.append(file_path)
                print(f"🧹 Sanitized {file_path}")
                
        except Exception as e:
            print(f"⚠️  Could not sanitize {file_path}: {e}")

    def sanitize_code_files(self):
        """Sanitize all code files"""
        extensions_to_sanitize = ['.py', '.sh', '.yml', '.yaml']
        
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext in extensions_to_sanitize:
                    self.sanitize_file(file_path)

    def create_env_example(self):
        """Create a comprehensive .env.example file"""
        env_example_content = """# Lookout API Configuration
# Get these from your Lookout Console -> System -> Application Keys
LOOKOUT_ACCESS_TOKEN=your_access_token_here
APPLICATION_KEY=your_application_key_here
WEB_ACTIVITY_KEY=your_web_activity_key_here

# API Endpoints (usually don't need to change these)
LOOKOUT_API_BASE_URL=https://api.lookout.com
WEB_ACTIVITY_API_BASE_URL=https://mtp.lookout.com

# AWS Configuration (for S3 logging features)
S3_BUCKET_NAME=your-s3-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key

# Optional: Custom configuration
LOG_LEVEL=INFO
MAX_RETRIES=3
TIMEOUT_SECONDS=30

# Database Configuration (for device caching)
DATABASE_PATH=./lookout_devices.db

# S3 Logging Configuration
S3_LOG_PREFIX=lookout-logs/
S3_RETENTION_DAYS=30
"""
        
        with open('.env.example', 'w') as f:
            f.write(env_example_content)
        print("✅ Created .env.example")

    def update_gitignore(self):
        """Ensure .gitignore is comprehensive"""
        additional_patterns = [
            "# Additional security patterns",
            "*.key",
            "*.pem",
            "*.p12",
            "*.pfx",
            "credentials.json",
            "config.json",
            "secrets.json",
            "",
            "# IDE and editor files",
            ".vscode/settings.json",
            ".idea/workspace.xml",
            "",
            "# OS generated files",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Backup files",
            "*.bak",
            "*.backup",
            "*~",
        ]
        
        with open('.gitignore', 'a') as f:
            f.write('\n'.join(additional_patterns))
        print("✅ Updated .gitignore with additional patterns")

    def create_security_notice(self):
        """Create a security notice file"""
        security_content = """# Security Notice

## Important Security Information

This repository contains demonstration code for integrating with Lookout APIs. Please follow these security best practices:

### Before Using This Code

1. **Never commit real credentials** to version control
2. **Use environment variables** for all sensitive configuration
3. **Review all code** before deploying to production
4. **Implement proper error handling** for production use
5. **Follow the principle of least privilege** for API keys

### API Credentials

- Obtain API credentials from your Lookout Console
- Store credentials in environment variables or secure credential stores
- Rotate credentials regularly
- Monitor API usage for anomalies

### AWS Configuration

- Use IAM roles when possible instead of access keys
- Implement bucket policies with minimal required permissions
- Enable CloudTrail logging for audit purposes
- Use encryption at rest and in transit

### Production Deployment

- Use secure container registries
- Implement proper logging and monitoring
- Use secrets management solutions (AWS Secrets Manager, HashiCorp Vault, etc.)
- Regular security audits and dependency updates

### Reporting Security Issues

If you discover a security vulnerability, please report it responsibly:
- Do not create public GitHub issues for security vulnerabilities
- Contact your Lookout representative directly
- Provide detailed information about the vulnerability

---

**Remember**: This is demonstration code. Always implement additional security measures for production use.
"""
        
        with open('SECURITY.md', 'w') as f:
            f.write(security_content)
        print("✅ Created SECURITY.md")

    def generate_final_report(self):
        """Generate a final preparation report"""
        print("\n" + "="*60)
        print("🎯 REPOSITORY PREPARATION COMPLETE")
        print("="*60)
        
        if self.removed_files:
            print(f"\n🗑️  Removed {len(self.removed_files)} sensitive files:")
            for file in self.removed_files:
                print(f"   - {file}")
        
        if self.sanitized_files:
            print(f"\n🧹 Sanitized {len(self.sanitized_files)} files:")
            for file in self.sanitized_files:
                print(f"   - {file}")
        
        print("\n✅ Created additional files:")
        print("   - .env.example")
        print("   - SECURITY.md")
        print("   - Updated .gitignore")
        
        print("\n📋 NEXT STEPS:")
        print("1. Run 'python security_check.py' again to verify")
        print("2. Review all changes before committing")
        print("3. Test the repository in a clean environment")
        print("4. Initialize git repository: git init")
        print("5. Add files: git add .")
        print("6. Commit: git commit -m 'Initial commit'")
        print("7. Add remote: git remote add origin <your-repo-url>")
        print("8. Push: git push -u origin main")

    def prepare_repository(self):
        """Run the full preparation process"""
        print("🚀 Preparing repository for GitHub publication...")
        
        self.remove_sensitive_files()
        self.sanitize_code_files()
        self.create_env_example()
        self.update_gitignore()
        self.create_security_notice()
        self.generate_final_report()

def main():
    """Main function"""
    preparer = RepositoryPreparer()
    preparer.prepare_repository()

if __name__ == "__main__":
    main()
