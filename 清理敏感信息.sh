#!/bin/bash

echo "🔐 清理 Git 历史中的敏感信息"
echo "================================"
echo ""
echo "⚠️  警告：此操作将重写 Git 历史！"
echo "⚠️  如果已推送到远程仓库，需要强制推送！"
echo ""
read -p "确认继续？(y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo "已取消操作"
    exit 0
fi

echo ""
echo "📋 备份当前仓库..."
cd ..
backup_name="video-to-text-tool-backup-$(date +%Y%m%d-%H%M%S)"
cp -r video-to-text-tool "$backup_name"
echo "✓ 已备份到: $backup_name"
cd video-to-text-tool

echo ""
echo "🧹 从 Git 历史中移除 models.json..."
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch models.json" \
  --prune-empty --tag-name-filter cat -- --all

echo ""
echo "🧹 从 Git 历史中移除 ocr_apis.json..."
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch ocr_apis.json" \
  --prune-empty --tag-name-filter cat -- --all

echo ""
echo "🗑️  清理引用..."
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "✅ 清理完成！"
echo ""
echo "📝 后续步骤："
echo "1. 检查 Git 历史: git log --all --oneline -- models.json"
echo "2. 如果已推送到远程，需要强制推送: git push origin --force --all"
echo "3. 通知协作者重新克隆仓库"
echo "4. 立即撤销/重置所有泄露的 API 密钥！"
