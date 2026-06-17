#!/bin/bash
echo "🚀 Creating demonstration PR..."
echo "================================"

# 策略：回退main，创建包含所有改动的feature分支，然后创建PR

# 1. 保存当前commit
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "📌 Current commit: $CURRENT_COMMIT"

# 2. 切换到main并创建空的初始commit
echo ""
echo "📝 Creating base branch with empty commit..."
git checkout main
git checkout --orphan base-branch
git rm -rf .
cat > README.md << 'EOREADME'
# Campaign Optimizer

This is the base branch for PR demonstration.
EOREADME
git add README.md
git commit -m "chore: initial commit"
git push -u origin base-branch -f

# 3. 从原commit创建feature分支
echo ""
echo "🔄 Creating feature branch from original commit..."
git checkout -b feature/full-implementation $CURRENT_COMMIT
git push -u origin feature/full-implementation -f

# 4. 创建PR
echo ""
echo "📋 Creating Pull Request..."
gh pr create \
  --base base-branch \
  --head feature/full-implementation \
  --title "feat: Campaign optimizer with all 7 features implemented" \
  --body-file PULL_REQUEST_TEMPLATE.md

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Pull Request created successfully!"
    echo "🔗 View: gh pr view --web"
else
    echo ""
    echo "⚠️  PR creation had issues, but you can create it manually:"
    echo "   Visit: https://github.com/yli949-gif/ad-campaign-optimizer/compare/base-branch...feature/full-implementation"
fi

# 5. 切回main分支
git checkout main
