# 更新日志 (Changelog)

所有重要的项目变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [1.0.1] - 2026-04-14

### 🐛 修复

- **OpenMP 库冲突**：在启动脚本中添加 `KMP_DUPLICATE_LIB_OK=TRUE` 环境变量
  - 修复了 macOS 上多个库包含 OpenMP 运行时导致的冲突
  - 影响文件：`启动服务.sh`, `启动服务（带日志窗口）.command`

- **Faster-Whisper 兼容性问题**：回退到稳定的 openai-whisper
  - faster-whisper 在某些 macOS 系统上出现段错误（segmentation fault）
  - 为保证稳定性，继续使用 openai-whisper
  - 虽然速度较慢，但可靠性更高

### ✨ 新增

- **离线安装包**：创建 `offline_packages/` 目录
  - 包含所有 Python 依赖包（44个，约 220 MB）
  - 包含 Whisper base 模型（139 MB）
  - 总大小约 360 MB
  - 支持完全离线安装和部署

- **离线安装文档**：
  - `离线安装指南.md` - 详细的离线安装步骤和故障排除
  - `offline_packages/使用说明.txt` - 快速使用说明

- **Faster-Whisper 升级文档**：
  - `FASTER_WHISPER_升级说明.md` - 记录了升级尝试过程
  - 包含性能对比、技术细节和已知问题
  - 为未来的优化提供参考

### 📝 文档

- **查看详细日志说明**：`查看详细日志说明.md`
  - 3种查看 Whisper 详细转录日志的方法
  - 终端日志和网页日志的区别说明
  - 故障排除指南

### 🔧 改进

- **.gitignore 优化**：
  - 允许 `离线安装指南.md`
  - 允许 `offline_packages/` 下的文档文件
  - 允许 `FASTER_WHISPER_升级说明.md`

### 📦 依赖

- 保持使用 `openai-whisper` (稳定版本)
- 所有依赖已打包到 `offline_packages/`

### ⚠️ 已知问题

- **MPS 不兼容**：Apple Silicon 的 MPS 后端与 Whisper 部分操作不兼容，已自动降级到 CPU
- **Faster-Whisper 段错误**：在某些 macOS 系统上会崩溃，暂不推荐使用
- **处理速度**：CPU 模式下，large 模型处理速度较慢，建议使用 base 或 small 模型

### 🎯 性能

**Whisper 模型性能**（10 分钟视频，CPU 模式）：
- tiny: 2-3 分钟
- base: 5-8 分钟（推荐）
- small: 15-20 分钟
- medium: 30-40 分钟
- large: 60+ 分钟

---

## [1.0.0] - 2026-04-14

### ✨ 新增功能

#### 核心功能
- **视频转文字**：支持多种视频/音频格式（mp4, avi, mov, mkv, mp3, wav 等）
- **批量处理**：支持拖拽上传多个视频文件
- **手动排序**：可调整视频处理顺序
- **自动衔接**：多个视频的转录结果自动合并

#### Whisper 语音识别
- **多模型支持**：tiny, base, small, medium, large
- **语言选择**：支持中文、英文等多种语言
- **自动降级**：检测 GPU 可用性，MPS 不兼容时自动使用 CPU
- **详细日志**：实时显示转录进度和逐句文本

#### AI 智能整理
- **多模型配置**：支持配置多个 AI 模型（OpenAI, Claude, 自定义等）
- **自定义提示词**：每个模型可设置专属提示词
- **模板系统**：内置课程笔记整理模板
- **可选功能**：可选择是否启用 AI 摘要

#### 用户界面
- **现代化设计**：使用 TailwindCSS，响应式布局
- **实时进度**：显示处理进度、当前步骤、已用时间
- **实时日志窗口**：网页端显示处理日志（左右布局）
- **SSE 日志流**：后端实时推送日志到前端
- **状态保护**：处理中禁用导航，防止意外离开页面

#### API 配置
- **灵活配置**：支持配置 API Key, Base URL, 模型名称
- **可选参数**：Temperature 和 Max Tokens 可选配置
- **环境变量**：支持 .env 文件配置

#### 工具脚本
- **批量导入**：`import_models.py` - 从 YAML 批量导入模型配置
- **启动脚本**：
  - `启动服务.sh` - 命令行启动
  - `启动客户端.command` - 双击启动（自动打开浏览器）
  - `启动服务（带日志窗口）.command` - 新终端窗口显示日志

### 🎨 界面优化

- **进度显示**：
  - 百分比进度条
  - 当前步骤说明
  - 详细状态信息
  - 已用时间计时器
  
- **日志窗口**：
  - 左侧：进度信息（进度条、步骤、时间）
  - 右侧：实时日志（终端风格，黑底绿字）
  - 支持清空日志
  - 自动滚动到底部

- **模型选择**：
  - Whisper 模型下拉框（带速度/准确度说明）
  - AI 模型下拉框（从配置加载）
  - 语言选择

### 🔧 技术特性

- **后端框架**：Flask
- **前端技术**：HTML5 + TailwindCSS + Vanilla JavaScript
- **AI 模型**：OpenAI Whisper (openai-whisper)
- **实时通信**：Server-Sent Events (SSE)
- **日志系统**：单例模式的日志流管理器
- **文件处理**：FFmpeg 音频提取

### 📝 文档

- `README.md` - 项目说明
- `QUICKSTART.md` - 快速开始指南
- `查看详细日志说明.md` - 日志查看教程
- `本地Whisper安装指南.md` - Whisper 安装说明
- `使用说明-增强版.md` - 详细使用说明

### 🐛 已知问题

- **MPS 不兼容**：Apple Silicon 的 MPS 后端与 Whisper 部分操作不兼容，已自动降级到 CPU
- **性能限制**：CPU 模式下，large 模型处理速度较慢，建议使用 base 或 small 模型

### 🔒 安全性

- API Key 通过环境变量或加密配置存储
- 上传文件自动清理
- 输入验证和文件类型检查

### 📦 依赖

主要依赖包：
- Flask >= 2.0.0
- openai-whisper
- openai >= 1.0.0
- ffmpeg-python
- torch
- python-dotenv

### 🎯 性能

**Whisper 模型性能参考**（10 分钟视频，CPU 模式）：
- tiny: 2-3 分钟
- base: 5-8 分钟（推荐）
- small: 15-20 分钟
- medium: 30-40 分钟
- large: 60+ 分钟

---

## 版本说明

版本号格式：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

---

**最后更新：** 2026-04-14
