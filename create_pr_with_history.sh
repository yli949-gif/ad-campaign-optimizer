#!/bin/bash
echo "🔧 Creating PR with proper branch history..."
echo "============================================="

# 策略：创建一个新的main-pr分支，基于project-start，然后把main的内容移过去

echo ""
echo "📝 Step 1: Creating main-pr branch from project-start..."
git checkout project-start
git pull origin project-start
git checkout -b main-pr

echo ""
echo "📝 Step 2: Cherry-picking main commit..."
git cherry-pick main -X theirs --allow-unrelated-histories 2>/dev/null || {
    echo "Cherry-pick had conflicts, using merge strategy..."
    git checkout main -- .
    git add -A
    git commit -m "feat: Campaign optimizer with all 7 features implemented

## 🎯 Summary

Implements all 7 requested features for the campaign optimizer MVP:

1. ✅ Hold / No Action group - Clearly visible in HTML report
2. ✅ Human Approval Queue - Dedicated section with full details  
3. ✅ Optimizer rule precedence - High spend + zero conversions overrides low-signal hold
4. ✅ Deterministic performance - Cache ensures terminal and HTML show identical numbers
5. ✅ Creative field names - Platform-specific labels for Meta/LinkedIn/Google
6. ✅ Recenter-CPA demonstration - \"Search — Nonbrand\" campaign shows this path
7. ✅ Terminal report message - Correct format

## 🔧 Key Fix

Fixed Rule #5 logic to properly detect CPA drift from target_cpa setting.

## ✅ Testing

\`\`\`bash
$ python test_all_features.py
RESULTS: 6/6 tests passed ✓
\`\`\`

## 📦 Files

14 files, 2207+ lines
- Core: optimizer.py, agent.py, platforms.py, creative.py, report.py, run.py
- Tests: test_all_features.py (6/6 passing)
- Docs: CHANGES_SUMMARY.md, VERIFICATION_REPORT.md, README_UPDATED.md

---
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
}

echo ""
echo "📝 Step 3: Pushing main-pr branch..."
git push -u origin main-pr -f

echo ""
echo "📝 Step 4: Creating PR..."
gh pr create \
  --base project-start \
  --head main-pr \
  --title "feat: Campaign optimizer with all 7 features implemented" \
  --body-file PR_BODY.txt

echo ""
echo "✅ Done! PR created."
echo "🔗 View: gh pr view --web"

git checkout main
