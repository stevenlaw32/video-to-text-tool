# 视频转文字工具 Video-to-Text Tool

一站式视频内容提取与智能整理工具。无论是本地视频还是在线链接，无论是语音内容还是画面文字，都能快速转化为结构化文档。

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-green?logo=flask&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-OpenAI-orange?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 项目亮点

### 双引擎语音识别 — 本地模型 + 云端模型

- **本地 Whisper 模型** — 数据不出本机，隐私无忧。Apple Silicon 设备自动启用 MLX-Whisper 原生 GPU 加速，Intel / Linux 设备使用 OpenAI Whisper + PyTorch
- **云端 AI 模型** — 支持 OpenAI GPT-4o、Claude、通义千问等任意兼容 OpenAI API 格式的大模型，用于对转录文本进行智能整理
- **多模型热切换** — 可预配置多套 API，在 Web 界面中一键切换，无需重启服务

### 双通道内容提取 — 语音识别 + OCR 文字识别

- **语音转录** — 适合演讲、会议、课程等以语音为主的视频
- **OCR 识别** — 适合 PPT 教学、代码演示、字幕截取等以画面文字为主的视频
- **云端 OCR** — 支持百度 OCR、腾讯云 OCR、阿里云 OCR 三大平台，按需选用

### 双来源视频输入 — 本地上传 + 在线链接

- **本地上传** — 支持拖拽批量上传，自定义处理顺序，支持 mp4、avi、mov、mkv 等主流视频格式及 mp3、wav、flac 等音频格式
- **在线链接** — 粘贴视频链接即可自动解析下载。抖音使用专用 API 解析，B站、快手、小红书等平台通过 yt-dlp 通用引擎下载
- **全流程打通** — 无论哪种来源，下载后均可一键继续转录 → AI 整理，无需手动衔接

### 更多实用功能

- **AI 智能整理** — 将转录文本一键生成教程、摘要、学习笔记等结构化文档
- **文档总结** — 除视频外，还支持上传 PDF / Word / Markdown / TXT 文档进行 AI 总结
- **音频提取** — 从视频中独立提取音频，支持 mp3、wav、aac、flac、ogg 格式输出
- **批量处理** — 支持文件夹批量处理，可拖拽排序确定处理顺序
- **多格式导出** — 转录文本、SRT 字幕、分段文本、Markdown 文档
- **实时日志** — Web 界面通过 SSE 实时推送处理进度，所见即所得
- **一键启动** — macOS 双击 `启动.command` 即可启动服务，零配置门槛

---

## 快速开始

### 1. 环境准备

**一键安装**（推荐）：

```bash
# macOS / Linux
./环境检查与安装.sh

# Windows
环境检查与安装.bat
```

脚本会自动检查 Python、FFmpeg 环境，安装依赖，配置国内镜像源。

**手动安装**：

```bash
# 安装 FFmpeg
brew install ffmpeg          # macOS
sudo apt-get install ffmpeg  # Linux

# 安装 Python 依赖
pip install -r requirements.txt

# 视频链接解析功能（可选）
pip install yt-dlp
```

### 2. 配置 AI 模型

复制配置模板：

```bash
cp .env.example .env
cp models.json.example models.json
cp ocr_apis.json.example ocr_apis.json
```

编辑 `.env` 文件，填入你的 API 密钥：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o
```

也可以启动服务后，在 Web 界面的 **「模型设置」** 和 **「OCR 配置」** 页面中可视化配置。

### 3. 启动服务

```bash
# macOS 一键启动
双击 启动.command

# 或命令行启动
python app_advanced.py
```

浏览器访问 `http://localhost:5000` 即可使用。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| **批量上传视频** | 拖拽上传多个视频/音频文件，支持排序，批量转录 + AI 整理 |
| **视频链接解析** | 粘贴抖音、B站、快手、小红书等平台链接，自动解析下载 |
| **音频提取** | 从视频中提取音频，支持多种格式和比特率 |
| **OCR 文字识别** | 从视频画面中提取文字，支持百度/腾讯云/阿里云 OCR |
| **文本总结** | 上传 PDF / Word / Markdown 文档，AI 生成结构化摘要 |
| **多模型管理** | 预配置多套 AI 模型，Web 界面一键切换 |
| **命令行工具** | 支持脚本化调用，适合批量自动化场景 |

---

## 命令行用法

```bash
# 处理单个视频
python main.py -i video.mp4 -o output

# 批量处理文件夹
python main.py -i videos/ -o output --batch

# 只转录，不使用 AI 整理
python main.py -i video.mp4 -o output --skip-ai

# 选择 Whisper 模型大小
python main.py -i video.mp4 -o output -m small

# 选择 AI 整理风格：tutorial / summary / notes
python main.py -i video.mp4 -o output --style notes
```

### Whisper 模型对照

| 模型 | 速度 | 准确度 | 内存占用 | 推荐场景 |
|------|------|--------|----------|----------|
| tiny | 最快 | 较低 | ~1 GB | 快速预览 |
| base | 快 | 中等 | ~1 GB | **日常使用（推荐）** |
| small | 中等 | 较高 | ~2 GB | 重要内容 |
| medium | 慢 | 高 | ~5 GB | 专业用途 |
| large | 最慢 | 最高 | ~10 GB | 最高质量要求 |

---

## 输出文件

| 文件 | 说明 |
|------|------|
| `*_transcript.txt` | 完整转录文本 |
| `*_subtitles.srt` | SRT 字幕文件 |
| `*_segments.txt` | 带时间戳的分段文本 |
| `*_{style}.md` | AI 整理后的 Markdown 文档 |

---

## 技术架构

```
视频/音频输入
├── 本地上传（批量拖拽）
└── 在线链接（yt-dlp / 抖音 API）
        ↓
内容提取
├── 语音识别（MLX-Whisper / OpenAI Whisper）
└── OCR 识别（百度 / 腾讯云 / 阿里云）
        ↓
AI 智能整理（OpenAI / Claude / 通义千问 ...）
        ↓
结构化输出（Markdown / TXT / SRT）
```

**技术栈**：Python 3.9+ · Flask · MLX-Whisper / OpenAI Whisper · OpenAI SDK · FFmpeg · TailwindCSS

---

## 常见问题

**处理速度慢？**
→ 使用更小的模型（tiny 或 base），Apple Silicon 设备确认已安装 `mlx-whisper` 以获得 GPU 加速。

**识别准确度不高？**
→ 使用更大的模型（small / medium / large），确保视频音质清晰。

**API 调用失败？**
→ 检查 `.env` 或「模型设置」中的 API 密钥和 Base URL 是否正确，确认额度充足。

**视频链接无法解析？**
→ 确认已安装 `yt-dlp`（`pip install yt-dlp`）。小红书等需要登录态的平台，请先在浏览器中登录，yt-dlp 会自动读取 Cookie。

---

## 安全说明

以下文件包含 API 密钥等敏感信息，**已被 `.gitignore` 排除**，不会上传至 GitHub：

- `.env` — AI 模型 API 配置
- `models.json` — 多模型预设配置
- `ocr_apis.json` — OCR API 配置

项目提供了对应的 `.example` 模板文件，clone 后按模板创建即可。

详见 [README_SECURITY.md](README_SECURITY.md)

---

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request！
