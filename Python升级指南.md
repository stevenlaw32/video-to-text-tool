# Python 3.11 升级指南

## 📦 当前状态

Python 3.11 正在通过 Homebrew 安装中...

编译过程可能需要 **5-15分钟**，请耐心等待。

---

## ✅ 安装完成后的步骤

### **步骤1：验证Python 3.11安装**

```bash
python3.11 --version
# 应该显示: Python 3.11.x
```

### **步骤2：创建新的虚拟环境**

```bash
cd /Users/apple/开发/DevOps/video-to-text-tool

# 创建Python 3.11虚拟环境
python3.11 -m venv venv311

# 激活新环境
source venv311/bin/activate

# 验证Python版本
python --version
# 应该显示: Python 3.11.x
```

### **步骤3：安装所有依赖**

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 安装额外的依赖
pip install browser-cookie3 httpx aiofiles
```

### **步骤4：重新安装视频解析库**

```bash
# 清理旧的解析库
rm -rf parsers/douyin_parser parsers/xhs_parser

# 重新运行安装脚本
./安装视频解析库.sh
```

### **步骤5：测试环境**

```bash
# 测试Whisper
python -c "import whisper; print('✓ Whisper:', whisper.__version__)"

# 测试TikTokDownloader
python -c "import sys; sys.path.insert(0, 'parsers/douyin_parser'); from src.tools import Extractor; print('✓ TikTokDownloader 可用')"

# 测试Cookie管理
python cookie_manager.py --status
```

---

## 🎯 完整的迁移命令（一键执行）

安装完成后，复制以下命令一次性执行：

```bash
cd /Users/apple/开发/DevOps/video-to-text-tool

# 创建新环境
python3.11 -m venv venv311
source venv311/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install browser-cookie3 httpx aiofiles

# 重新安装解析库
rm -rf parsers/douyin_parser parsers/xhs_parser
./安装视频解析库.sh

# 更新Cookie
python cookie_manager.py --update

# 测试抖音解析
python test_mobile_api.py

# 启动服务
python app_advanced.py
```

---

## 📝 修改启动脚本

### **更新 `启动服务（带日志窗口）.command`**

编辑文件，将：
```bash
source venv/bin/activate
```

改为：
```bash
source venv311/bin/activate
```

### **或者创建新的启动脚本**

```bash
cat > "启动服务（Python3.11）.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv311/bin/activate
python app_advanced.py
EOF

chmod +x "启动服务（Python3.11）.command"
```

---

## ⚠️ 注意事项

### **保留旧环境**

不要删除 `venv/` 目录，以防需要回退：
- `venv/` - Python 3.9 环境（旧）
- `venv311/` - Python 3.11 环境（新）

### **Whisper模型**

Whisper模型文件会自动共享，不需要重新下载：
- 模型位置：`~/.cache/whisper/`
- 新环境会自动使用已下载的模型

### **配置文件**

以下文件会自动保留：
- `parsers/config.json` - Cookie配置
- `.env` - 环境变量
- `output/` - 输出文件
- `temp_videos/` - 临时视频

---

## 🚀 升级后的优势

### **可以使用的新功能：**

1. ✅ **TikTokDownloader** - 真正的抖音视频解析
2. ✅ **XHS-Downloader** - 小红书视频解析
3. ✅ **更好的性能** - Python 3.11 比 3.9 快 10-25%
4. ✅ **新语法特性** - match语句等

### **解析成功率提升：**

- 抖音：从 0% → 预计 60-80%
- 小红书：从 0% → 预计 70-90%
- 快手：从 0% → 预计 50-70%

---

## 🔧 故障排除

### **问题1：Python 3.11 安装失败**

```bash
# 尝试使用pyenv
brew install pyenv
pyenv install 3.11.15
pyenv global 3.11.15
```

### **问题2：依赖安装失败**

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### **问题3：Whisper无法导入**

```bash
# 重新安装Whisper
pip uninstall openai-whisper
pip install openai-whisper
```

---

## 📊 安装进度检查

当前Homebrew正在后台安装Python 3.11...

检查安装状态：
```bash
# 查看安装进度
brew info python@3.11

# 检查是否安装完成
which python3.11
```

---

**等待安装完成后，按照上述步骤操作即可！** 🚀

预计完成时间：5-15分钟
