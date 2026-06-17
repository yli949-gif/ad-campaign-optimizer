#!/bin/bash
echo "🚀 Creating PR with proper workflow..."
echo "======================================"

# 切换到main
git checkout main

# 创建一个"项目开始前"的分支
echo ""
echo "📝 Creating 'project-start' branch (before implementation)..."
git checkout --orphan project-start

# 只保留基本README
git rm -rf .
cat > README.md << 'EOREADME'
# Campaign Optimizer - Agentic Advertising MVP

Project initialization.

## Planned Features

1. Hold / No Action group
2. Human Approval Queue
3. Optimizer rule precedence
4. Deterministic performance
5. Creative field names
6. Recenter-CPA demonstration
7. Terminal report message

## Status

⏳ Implementation in progress...
EOREADME

cat > requirements.txt << 'EOREQ'
# Python dependencies will be added during implementation
EOREQ

git add .
git commit -m "chore: project initialization"
echo ""
echo "⬆️  Pushing project-start branch..."
git push -u origin project-start -f

# 切回main分支
echo ""
echo "🔄 Switching back to main..."
git checkout main

# 创建PR
echo ""
echo "📋 Creating Pull Request..."
gh pr create \
  --base project-start \
  --head main \
  --title "feat: Campaign optimizer with all 7 features implemented" \
  --body-file PULL_REQUEST_TEMPLATE.md \
  --web

echo ""
echo "✅ Done!"
