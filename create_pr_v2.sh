#!/bin/bash
echo "🚀 Creating Pull Request (alternative method)..."
echo "================================================"

# 切换到main
git checkout main

# 创建feature分支从main
echo ""
echo "📝 Creating feature branch..."
git checkout -b feature/campaign-optimizer-implementation

# 推送feature分支
echo ""
echo "⬆️  Pushing feature branch..."
git push -u origin feature/campaign-optimizer-implementation

# 创建PR从feature到main
echo ""
echo "📋 Creating Pull Request from feature to main..."
gh pr create \
  --base main \
  --head feature/campaign-optimizer-implementation \
  --title "feat: Campaign optimizer with all 7 features implemented" \
  --body-file PULL_REQUEST_TEMPLATE.md

echo ""
echo "✅ Pull Request created!"
echo "🔗 View PR: gh pr view --web"
