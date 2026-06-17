#!/bin/bash
echo "🔧 Fixing git author information..."
echo "===================================="

# 1. 更新git配置为正确的账号
echo "📝 Updating git config..."
git config user.name "yli949-gif"
git config user.email "yli949@users.noreply.github.com"  # GitHub no-reply email

echo "✅ New git config:"
echo "   Name: $(git config user.name)"
echo "   Email: $(git config user.email)"

# 2. 修改最后一次commit的作者信息
echo ""
echo "🔄 Amending last commit with correct author..."
git commit --amend --reset-author --no-edit

# 3. 强制推送更新
echo ""
echo "🚀 Force pushing to update GitHub..."
git push origin main --force

echo ""
echo "✅ Done! Commit author updated."
echo "📍 Check: https://github.com/yli949-gif/ad-campaign-optimizer/commits/main"
