# 视频转文字工具

自动提取视频内容并生成结构化文档的AI工具。支持本地视频批量处理，使用Whisper进行语音识别，结合GPT进行智能整理。

## 🚀 快速开始

**首次使用？** 运行一键安装脚本：

```bash
# macOS/Linux
./环境检查与安装.sh

# Windows
环境检查与安装.bat
```

脚本会自动检查环境、安装依赖、配置国内镜像源、下载模型。

**✨ 离线安装支持**: 如果项目包含 `offline_packages/` 目录，脚本会优先使用离线包，无需网络！

📖 **详细说明**: [快速开始.md](快速开始.md) | [离线安装指南.md](离线安装指南.md)

---

## 功能特点

- 🎥 **视频转文字**: 使用OpenAI Whisper模型进行高精度语音识别
- 🤖 **AI智能整理**: 自动生成教程、摘要或学习笔记
- 📦 **批量处理**: 支持文件夹批量处理多个视频
- 🌐 **Web界面**: 提供简洁的网页操作界面
- 💾 **多格式导出**: 支持TXT、SRT字幕、分段文本、Markdown等格式

## 安装步骤

### 1. 安装依赖

首先需要安装 FFmpeg（用于音频提取）：

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
下载 FFmpeg 并添加到系统PATH

### 2. 安装Python依赖

```bash
cd /Users/apple/开发/DevOps/video-to-text-tool
pip install -r requirements.txt
```

### 3. 配置API密钥

#### 方式一：使用 .env 文件（推荐）

复制配置文件并填入你的API信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o
```

#### 方式二：使用多模型配置

复制模型配置示例：

```bash
cp models.json.example models.json
cp ocr_apis.json.example ocr_apis.json
```

然后在 Web 界面的"模型设置"中配置你的 API 密钥。

**⚠️ 安全提示**: 请勿将包含真实 API 密钥的配置文件提交到 Git！详见 `README_SECURITY.md`

## 使用方法

### 方式一：命令行工具

#### 处理单个视频

```bash
python main.py -i video.mp4 -o output
```

#### 批量处理文件夹

```bash
python main.py -i videos/ -o output --batch
```

#### 只转录不使用AI

```bash
python main.py -i video.mp4 -o output --skip-ai
```

#### 选择不同的整理风格

```bash
# 教程格式（默认）
python main.py -i video.mp4 -o output --style tutorial

# 摘要格式
python main.py -i video.mp4 -o output --style summary

# 笔记格式
python main.py -i video.mp4 -o output --style notes
```

#### 选择识别模型

```bash
# tiny - 最快，准确度较低
python main.py -i video.mp4 -o output -m tiny

# base - 推荐，平衡速度和准确度（默认）
python main.py -i video.mp4 -o output -m base

# small - 较慢，准确度较高
python main.py -i video.mp4 -o output -m small

# medium - 慢，准确度高
python main.py -i video.mp4 -o output -m medium

# large - 最慢，准确度最高
python main.py -i video.mp4 -o output -m large
```

### 方式二：Web界面

启动Web服务器：

```bash
python app.py
```

然后在浏览器中访问 `http://localhost:5000`

Web界面功能：
- 拖拽上传视频文件
- 选择识别模型和整理风格
- 实时查看处理进度
- 在线预览和下载结果

## 输出文件说明

处理完成后会生成以下文件：

- `{视频名}_transcript.txt` - 完整转录文本
- `{视频名}_subtitles.srt` - SRT字幕文件
- `{视频名}_segments.txt` - 带时间戳的分段文本
- `{视频名}_{style}.md` - AI整理后的Markdown文档

## 参数说明

### 模型大小选择

| 模型 | 速度 | 准确度 | 内存占用 | 推荐场景 |
|------|------|--------|----------|----------|
| tiny | 最快 | 较低 | ~1GB | 快速预览 |
| base | 快 | 中等 | ~1GB | 日常使用（推荐） |
| small | 中等 | 较高 | ~2GB | 重要内容 |
| medium | 慢 | 高 | ~5GB | 专业用途 |
| large | 最慢 | 最高 | ~10GB | 最高质量要求 |

### AI整理风格

- **tutorial**: 结构化教程格式，包含章节、步骤、代码示例
- **summary**: 简洁摘要格式，提取核心要点
- **notes**: 学习笔记格式，适合知识整理

## 常见问题

### 1. 处理速度慢？

- 使用更小的模型（tiny或base）
- 确保有足够的内存和CPU资源
- 考虑使用GPU加速（需要CUDA支持）

### 2. 识别准确度不高？

- 使用更大的模型（medium或large）
- 确保视频音质清晰
- 对于特定领域内容，可能需要微调模型

### 3. API调用失败？

- 检查 `.env` 文件中的API密钥是否正确
- 确认API额度是否充足
- 检查网络连接

## 技术栈

- **语音识别**: OpenAI Whisper
- **AI整理**: GPT-4o (通过青云API)
- **音频处理**: FFmpeg
- **Web框架**: Flask
- **前端**: TailwindCSS + Vanilla JS

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
