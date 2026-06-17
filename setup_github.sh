#!/bin/bash
# GitHub Setup Script for ad-campaign-optimizer

GITHUB_USER="yli949-gif"
REPO_NAME="ad-campaign-optimizer"

echo "🚀 Setting up GitHub repository..."
echo "=================================="

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not found. Please install it:"
    echo "   brew install gh"
    echo "   or visit: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "🔐 Authenticating with GitHub..."
    gh auth login
fi

echo ""
echo "📦 Creating repository on GitHub..."
gh repo create ${REPO_NAME} \
    --public \
    --description "AI-powered campaign optimization agent with autonomous decision-making" \
    --source=. \
    --remote=origin \
    --push

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Repository created and code pushed!"
    echo "📍 URL: https://github.com/${GITHUB_USER}/${REPO_NAME}"
    echo ""
    echo "Next steps:"
    echo "  1. View your repository: gh repo view --web"
    echo "  2. Create a PR (if needed): gh pr create"
else
    echo ""
    echo "⚠️  Repository might already exist. Adding remote manually..."
    git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git" 2>/dev/null || git remote set-url origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
    git push -u origin main
fi

echo ""
echo "✨ Done! Repository is ready."
