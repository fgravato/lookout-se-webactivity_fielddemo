#!/bin/bash

# GitHub Publication Script for lookout-se-webactivity_fielddemo
# This script helps publish the repository to GitHub

set -e  # Exit on any error

REPO_NAME="lookout-se-webactivity_fielddemo"
REPO_DESCRIPTION="Comprehensive demonstration toolkit for Lookout's Web Activity Feed API and Mobile Risk API integration"

echo "🚀 GitHub Publication Script for $REPO_NAME"
echo "=================================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository. Please run this script from the project root."
    exit 1
fi

# Check if we have commits
if ! git log --oneline -n 1 > /dev/null 2>&1; then
    echo "❌ Error: No commits found. Please commit your changes first."
    exit 1
fi

echo "✅ Git repository detected with commits"

# Function to check if GitHub CLI is installed
check_gh_cli() {
    if command -v gh &> /dev/null; then
        echo "✅ GitHub CLI (gh) is installed"
        return 0
    else
        echo "⚠️  GitHub CLI (gh) is not installed"
        return 1
    fi
}

# Function to create repository using GitHub CLI
create_repo_with_gh() {
    echo "📝 Creating GitHub repository using GitHub CLI..."
    
    # Check if user is authenticated
    if ! gh auth status > /dev/null 2>&1; then
        echo "🔐 Please authenticate with GitHub CLI:"
        gh auth login
    fi
    
    # Create the repository
    gh repo create "$REPO_NAME" \
        --description "$REPO_DESCRIPTION" \
        --public \
        --source=. \
        --remote=origin \
        --push
    
    echo "✅ Repository created and pushed successfully!"
    return 0
}

# Function to provide manual instructions
manual_instructions() {
    echo "📋 Manual GitHub Repository Creation Instructions:"
    echo "=================================================="
    echo ""
    echo "1. Go to https://github.com and sign in"
    echo "2. Click the '+' icon and select 'New repository'"
    echo "3. Repository name: $REPO_NAME"
    echo "4. Description: $REPO_DESCRIPTION"
    echo "5. Choose Public or Private (recommend Public for demos)"
    echo "6. DO NOT initialize with README, .gitignore, or license"
    echo "7. Click 'Create repository'"
    echo ""
    echo "8. Then run these commands:"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "Replace YOUR_USERNAME with your actual GitHub username or organization name."
}

# Function to add remote and push (if repository already exists)
push_to_existing_repo() {
    echo "🔗 Setting up remote and pushing to existing repository..."
    
    read -p "Enter your GitHub username or organization: " github_user
    
    if [ -z "$github_user" ]; then
        echo "❌ Error: GitHub username cannot be empty"
        exit 1
    fi
    
    REPO_URL="https://github.com/$github_user/$REPO_NAME.git"
    
    # Check if remote already exists
    if git remote get-url origin > /dev/null 2>&1; then
        echo "⚠️  Remote 'origin' already exists. Updating..."
        git remote set-url origin "$REPO_URL"
    else
        echo "➕ Adding remote origin..."
        git remote add origin "$REPO_URL"
    fi
    
    # Push to GitHub
    echo "📤 Pushing to GitHub..."
    git branch -M main
    git push -u origin main
    
    echo "✅ Successfully pushed to GitHub!"
    echo "🌐 Repository URL: https://github.com/$github_user/$REPO_NAME"
}

# Main menu
echo ""
echo "Choose an option:"
echo "1. Create repository using GitHub CLI (recommended)"
echo "2. Push to existing repository"
echo "3. Show manual instructions"
echo "4. Exit"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        if check_gh_cli; then
            create_repo_with_gh
        else
            echo ""
            echo "📦 To install GitHub CLI:"
            echo "  macOS: brew install gh"
            echo "  Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
            echo "  Windows: https://github.com/cli/cli/releases"
            echo ""
            manual_instructions
        fi
        ;;
    2)
        push_to_existing_repo
        ;;
    3)
        manual_instructions
        ;;
    4)
        echo "👋 Exiting..."
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "🎉 Publication process complete!"
echo ""
echo "📋 Next steps:"
echo "1. Visit your repository on GitHub"
echo "2. Add topics: lookout, api, security, mobile-device-management, web-activity, demo"
echo "3. Enable security features (Dependabot, security alerts)"
echo "4. Create a release (v1.0.0)"
echo "5. Set up branch protection rules"
echo ""
echo "📚 For detailed post-publication steps, see GITHUB_PUBLICATION_GUIDE.md"
