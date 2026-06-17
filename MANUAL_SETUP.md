# Manual GitHub Setup Instructions

If you don't have GitHub CLI installed, follow these steps:

## Option 1: Using GitHub CLI (Recommended)

```bash
# Install GitHub CLI (if not already installed)
brew install gh

# Authenticate
gh auth login

# Run the setup script
./setup_github.sh
```

## Option 2: Manual Setup

### Step 1: Create Repository on GitHub

1. Go to https://github.com/new
2. Set repository name: `ad-campaign-optimizer`
3. Description: `AI-powered campaign optimization agent with autonomous decision-making`
4. Choose "Public"
5. **Do NOT** initialize with README, .gitignore, or license
6. Click "Create repository"

### Step 2: Push Code

```bash
# Add remote
git remote add origin https://github.com/yli949-gif/ad-campaign-optimizer.git

# Push code
git push -u origin main
```

### Step 3: Create PR (if working on a feature branch)

If you want to create a PR to main:

```bash
# Create a feature branch
git checkout -b feature/optimizer-improvements

# Push branch
git push -u origin feature/optimizer-improvements

# Create PR via web
# Visit: https://github.com/yli949-gif/ad-campaign-optimizer/compare
# Or use: gh pr create --title "feat: Campaign optimizer" --body-file PULL_REQUEST_TEMPLATE.md
```

## Quick Commands

```bash
# View repository online
gh repo view --web

# Create PR
gh pr create --title "feat: Campaign optimizer with all 7 features" \
             --body-file PULL_REQUEST_TEMPLATE.md

# Check status
git status
git log --oneline

# View remote
git remote -v
```

## Repository Details

- **User**: yli949-gif
- **Repo**: ad-campaign-optimizer
- **URL**: https://github.com/yli949-gif/ad-campaign-optimizer
- **Branch**: main

## Troubleshooting

### If remote already exists:
```bash
git remote set-url origin https://github.com/yli949-gif/ad-campaign-optimizer.git
git push -u origin main
```

### If push is rejected:
```bash
git pull origin main --rebase
git push -u origin main
```

### If you need to force push (use carefully):
```bash
git push -u origin main --force
```
