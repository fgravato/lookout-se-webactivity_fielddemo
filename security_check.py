#!/usr/bin/env python3
"""
Security Check Script for Lookout SE Web Activity Field Demo

This script scans the repository for potential security issues before publication:
- Checks for hardcoded credentials
- Validates .gitignore coverage
- Identifies sensitive file patterns
- Provides recommendations for secure publication
"""

import os
import re
import glob
from pathlib import Path

class SecurityChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        
        # Patterns that might indicate sensitive data
        self.sensitive_patterns = [
            (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^"\'\s]+', 'Potential password'),
            (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[^"\'\s]+', 'Potential API key'),
            (r'(?i)(secret|token)\s*[=:]\s*["\']?[^"\'\s]+', 'Potential secret/token'),
            (r'(?i)(access[_-]?token)\s*[=:]\s*["\']?[^"\'\s]+', 'Potential access token'),
            (r'(?i)(private[_-]?key)\s*[=:]\s*["\']?[^"\'\s]+', 'Potential private key'),
            (r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[=:]\s*["\']?[^"\'\s]+', 'AWS Access Key'),
            (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']?[^"\'\s]+', 'AWS Secret Key'),
            (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID pattern'),
            (r'[0-9a-zA-Z/+]{40}', 'Potential AWS Secret Key pattern'),
            (r'eyJ[A-Za-z0-9_/+-]*\.eyJ[A-Za-z0-9_/+-]*\.[A-Za-z0-9_/+-]*', 'JWT Token pattern'),
        ]
        
        # Files that should definitely be in .gitignore
        self.sensitive_files = [
            '.env',
            'access_token.txt',
            'token-test.txt',
            '*.db',
            '*.sqlite',
            '*.sqlite3',
            '.aws/',
            'aws-credentials.txt',
        ]
        
        # File extensions to scan
        self.scan_extensions = ['.py', '.sh', '.yml', '.yaml', '.json', '.txt', '.md', '.env']

    def check_gitignore(self):
        """Check if .gitignore exists and covers sensitive files"""
        gitignore_path = Path('.gitignore')
        
        if not gitignore_path.exists():
            self.issues.append("❌ .gitignore file is missing!")
            return
            
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
            
        missing_patterns = []
        for pattern in self.sensitive_files:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)
                
        if missing_patterns:
            self.warnings.append(f"⚠️  .gitignore might be missing patterns: {', '.join(missing_patterns)}")
        else:
            self.info.append("✅ .gitignore appears to cover sensitive file patterns")

    def scan_file_content(self, file_path):
        """Scan a file for sensitive patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for pattern, description in self.sensitive_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    self.warnings.append(f"⚠️  {file_path}: {description} found - {matches[0][:50]}...")
                    
        except Exception as e:
            self.warnings.append(f"⚠️  Could not scan {file_path}: {e}")

    def check_sensitive_files_exist(self):
        """Check if sensitive files exist in the working directory"""
        sensitive_found = []
        
        for pattern in self.sensitive_files:
            if '*' in pattern:
                matches = glob.glob(pattern)
                if matches:
                    sensitive_found.extend(matches)
            else:
                if os.path.exists(pattern):
                    sensitive_found.append(pattern)
                    
        if sensitive_found:
            self.issues.append(f"❌ Sensitive files found in working directory: {', '.join(sensitive_found)}")
        else:
            self.info.append("✅ No obvious sensitive files found in working directory")

    def scan_repository(self):
        """Scan all relevant files in the repository"""
        scanned_files = 0
        
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env']]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext in self.scan_extensions:
                    self.scan_file_content(file_path)
                    scanned_files += 1
                    
        self.info.append(f"📊 Scanned {scanned_files} files")

    def check_environment_files(self):
        """Check for environment files and their security"""
        env_files = ['.env', '.env.local', '.env.production', '.env.development']
        
        for env_file in env_files:
            if os.path.exists(env_file):
                self.issues.append(f"❌ Environment file {env_file} exists - should not be committed!")
                
        # Check for .env.example files
        example_files = ['.env.example', '.env.s3.example']
        for example_file in example_files:
            if os.path.exists(example_file):
                self.info.append(f"✅ Example environment file {example_file} found")

    def generate_report(self):
        """Generate and display the security report"""
        print("🔒 SECURITY CHECK REPORT")
        print("=" * 50)
        
        if self.issues:
            print("\n❌ CRITICAL ISSUES (Must fix before publication):")
            for issue in self.issues:
                print(f"  {issue}")
                
        if self.warnings:
            print("\n⚠️  WARNINGS (Review carefully):")
            for warning in self.warnings:
                print(f"  {warning}")
                
        if self.info:
            print("\n✅ INFORMATION:")
            for info in self.info:
                print(f"  {info}")
                
        print("\n" + "=" * 50)
        
        if self.issues:
            print("❌ REPOSITORY NOT READY FOR PUBLICATION")
            print("Please fix all critical issues before publishing.")
            return False
        elif self.warnings:
            print("⚠️  REPOSITORY NEEDS REVIEW")
            print("Please review all warnings before publishing.")
            return True
        else:
            print("✅ REPOSITORY APPEARS READY FOR PUBLICATION")
            return True

    def run_full_check(self):
        """Run all security checks"""
        print("🔍 Running security checks...")
        
        self.check_gitignore()
        self.check_sensitive_files_exist()
        self.check_environment_files()
        self.scan_repository()
        
        return self.generate_report()

def main():
    """Main function"""
    checker = SecurityChecker()
    is_safe = checker.run_full_check()
    
    print("\n📋 RECOMMENDATIONS:")
    print("1. Ensure all sensitive files are in .gitignore")
    print("2. Remove any actual credentials from code")
    print("3. Use environment variables for all secrets")
    print("4. Provide .env.example files with dummy values")
    print("5. Review all warnings before publication")
    print("6. Test the repository in a clean environment")
    
    if not is_safe:
        exit(1)

if __name__ == "__main__":
    main()
