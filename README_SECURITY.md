# 🔐 安全配置说明

## ⚠️ 重要提示

**请勿将包含真实 API 密钥的配置文件提交到 Git 仓库！**

本项目已将以下敏感文件加入 `.gitignore`：
- `.env`
- `models.json`
- `ocr_apis.json`

## 📋 首次使用配置

### 1. 复制示例配置文件

```bash
# 复制模型配置示例
cp models.json.example models.json

# 复制 OCR 配置示例
cp ocr_apis.json.example ocr_apis.json
```

### 2. 填写你的 API 密钥

编辑 `models.json` 和 `ocr_apis.json`，将示例密钥替换为你的真实密钥。

### 3. 验证 gitignore

确保敏感文件不会被提交：

```bash
git status
# 不应该看到 models.json 或 ocr_apis.json
```

## 🛡️ 安全最佳实践

1. **永远不要硬编码 API 密钥**
2. **使用环境变量或配置文件**（已加入 .gitignore）
3. **定期轮换 API 密钥**
4. **限制 API 密钥权限**
5. **监控 API 使用情况**

## 🔄 如果密钥已泄露

1. **立即撤销/重置泄露的 API 密钥**
2. **检查 Git 历史记录**：
   ```bash
   git log --all --full-history -- models.json
   ```
3. **如果已提交到远程仓库，需要清理历史**：
   ```bash
   # 使用 git filter-branch 或 BFG Repo-Cleaner
   # 谨慎操作！建议先备份
   ```

## 📞 获取 API 密钥

- **OpenAI**: https://platform.openai.com/api-keys
- **百度 OCR**: https://console.bce.baidu.com/ai/#/ai/ocr/overview
- **腾讯云 OCR**: https://console.cloud.tencent.com/ocr
- **阿里云 OCR**: https://www.aliyun.com/product/ocr
