#!/bin/bash
echo "🚀 Creating Pull Request workflow..."
echo "===================================="

# 方案1: 如果想展示所有改动，创建initial分支作为base
echo ""
echo "📝 Creating initial branch as base..."
git checkout --orphan initial
git rm -rf .
echo "# Campaign Optimizer" > README.md
echo "" >> README.md
echo "Initial empty commit for PR base" >> README.md
git add README.md
git commit -m "chore: initial empty commit for PR base"
git push -u origin initial

# 切回main分支
echo ""
echo "🔄 Switching back to main..."
git checkout main

# 创建PR从main到initial（展示所有改动）
echo ""
echo "📋 Creating Pull Request..."
gh pr create \
  --base initial \
  --head main \
  --title "feat: Campaign optimizer with all 7 features implemented" \
  --body-file PULL_REQUEST_TEMPLATE.md

echo ""
echo "✅ Pull Request created!"
