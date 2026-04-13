# 快速开始指南

## 📦 第一步：安装依赖

运行一键安装脚本（已优化）：

```bash
cd /Users/apple/开发/DevOps/video-to-text-tool
chmod +x 一键安装依赖.sh
./一键安装依赖.sh
```

安装脚本会：
- ✓ 检查 Python 环境（需要 3.9+）
- ✓ 可选创建虚拟环境（推荐）
- ✓ 自动安装所有 Python 依赖
- ✓ 检查并提示安装 FFmpeg
- ✓ 验证所有模块是否正常

## ⚙️ 第二步：配置 API 密钥

编辑 `.env` 文件（如果不存在，从 `.env.example` 复制）：

```bash
cp .env.example .env
nano .env  # 或使用其他编辑器
```

填入你的 API 信息：
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.qingyuntop.top/v1
MODEL_NAME=gpt-4o
```

## 🚀 第三步：开始使用

### 方式一：命令行处理单个视频

```bash
# 如果使用了虚拟环境，先激活
source venv/bin/activate

# 处理单个视频文件
python3 main.py -i ~/Downloads/课程视频.mp4 -o output
```

处理完成后，会在 `output` 文件夹生成：
- `课程视频_transcript.txt` - 完整转录文本
- `课程视频_subtitles.srt` - SRT字幕文件
- `课程视频_segments.txt` - 带时间戳的分段文本
- `课程视频_tutorial.md` - AI整理的教程文档

### 方式二：批量处理文件夹

```bash
# 处理整个文件夹中的所有视频
python3 main.py -i ~/Videos/在线课程 -o output --batch
```

### 方式三：Web界面 - 增强版（推荐）

```bash
# 启动增强版Web服务器
python3 app_advanced.py

# 浏览器会自动打开: http://localhost:5000
```

增强版Web界面功能：
- ✓ 批量拖拽上传视频
- ✓ 手动调整处理顺序
- ✓ 自动衔接转录结果
- ✓ 自定义AI模型和提示词
- ✓ 在线预览和下载结果
- ✓ API配置管理界面

## 📝 常用命令示例

### 只转录不使用AI整理
```bash
python3 main.py -i video.mp4 -o output --skip-ai
```

### 使用不同的整理风格
```bash
# 教程格式（默认）- 结构化教程
python3 main.py -i video.mp4 -o output --style tutorial

# 摘要格式 - 简洁总结
python3 main.py -i video.mp4 -o output --style summary

# 笔记格式 - 学习笔记
python3 main.py -i video.mp4 -o output --style notes
```

### 选择识别模型
```bash
# base模型（推荐，平衡速度和准确度）
python3 main.py -i video.mp4 -o output -m base

# small模型（更准确，稍慢）
python3 main.py -i video.mp4 -o output -m small

# tiny模型（最快，适合快速预览）
python3 main.py -i video.mp4 -o output -m tiny
```

## 💡 使用技巧

### 1. 提升识别准确度
- 使用 `small` 或 `medium` 模型
- 确保视频音质清晰
- 对于专业术语较多的内容，可能需要后期人工校对

### 2. 加快处理速度
- 使用 `tiny` 或 `base` 模型
- 如果只需要文字不需要AI整理，使用 `--skip-ai`
- 批量处理时可以在后台运行

### 3. 节省API费用
- 只对重要内容使用AI整理
- 使用 `--skip-ai` 只做转录
- 先用 `tiny` 模型预览，确认后再用更大模型

### 4. 批量处理工作流
```bash
# 1. 先快速转录所有视频（不使用AI）
python3 main.py -i ~/Videos/课程 -o output --batch --skip-ai -m base

# 2. 查看转录结果，挑选重要的视频

# 3. 对重要视频单独使用AI整理
python3 main.py -i ~/Videos/课程/重要课程.mp4 -o output -m small --style tutorial
```

## 📊 输出格式说明

### 转录文本 (transcript.txt)
纯文本格式，包含完整的语音转文字内容。

### 字幕文件 (subtitles.srt)
标准SRT格式，可直接导入视频播放器或编辑软件。

### 分段文本 (segments.txt)
每段文字带有时间戳，方便定位原视频位置。

### AI整理文档 (.md)
Markdown格式，结构化的教程/笔记/摘要，可直接在Obsidian等笔记软件中使用。

## 🔧 故障排除

### 问题：视频格式不支持
**解决**：使用FFmpeg转换格式
```bash
ffmpeg -i input.webm -c:v copy -c:a aac output.mp4
```

### 问题：内存不足
**解决**：使用更小的模型（tiny或base）

### 问题：API调用失败
**解决**：
1. 检查 `.env` 文件中的API密钥
2. 确认API额度充足
3. 检查网络连接

### 问题：识别语言不对
**解决**：Whisper会自动检测语言，如需强制指定，可修改代码中的 `language` 参数

## 📚 下一步

- 查看完整文档：`README.md`
- 了解代码结构：查看源代码注释
- 自定义AI提示词：编辑 `ai_summarizer.py` 中的 prompts
- 集成到工作流：可以编写脚本自动化处理

## 🎯 实际应用场景

1. **在线课程学习**：将视频课程转为文字教程，提升学习效率
2. **会议记录**：自动生成会议纪要
3. **视频内容整理**：将收藏的视频内容转为可搜索的文字
4. **字幕制作**：快速生成视频字幕
5. **知识管理**：将视频知识转为笔记，便于复习和检索

---

**需要帮助？** 查看 `README.md` 获取更多详细信息。
