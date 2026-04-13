#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 设置终端标题
echo -ne "\033]0;视频转文字工具\007"

# 清屏
clear

# 显示欢迎信息
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║           🎥  视频转文字工具 - 增强版客户端              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

功能特性：
  ✓ 批量拖拽上传视频
  ✓ 手动调整处理顺序
  ✓ 自动衔接转录结果
  ✓ 自定义AI模型
  ✓ 自定义AI提示词

EOF

echo "正在检查环境..."
echo ""

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python 3.9 或更高版本"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python 版本: $PYTHON_VERSION"

# 检查虚拟环境，如果不存在则创建
VENV_DIR="$DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  未找到虚拟环境，正在创建..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ 创建虚拟环境失败"
        read -p "按回车键退出..."
        exit 1
    fi
    echo "✓ 虚拟环境创建完成"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"
echo "✓ 已激活虚拟环境"

# 检查并安装依赖
echo "✓ 检查依赖包..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  正在安装依赖包，请稍候..."
    pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请检查网络连接"
        read -p "按回车键退出..."
        exit 1
    fi
fi
echo "✓ 依赖检查完成"
echo ""

# 检查FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  警告: 未找到 FFmpeg"
    echo "   视频音频提取功能需要 FFmpeg"
    echo "   请运行: brew install ffmpeg"
    echo ""
fi

# 定义端口
PORT=5000

# 启动服务器
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 正在启动服务器..."
echo ""
echo "┌──────────────────────────────────────────────────────┐"
echo "│                                                      │"
echo "│   📎 请在浏览器中访问:  http://localhost:${PORT}        │"
echo "│                                                      │"
echo "│   按 Ctrl+C 停止服务器                               │"
echo "│                                                      │"
echo "└──────────────────────────────────────────────────────┘"
echo ""

# 等待1秒后自动打开浏览器
sleep 1
open "http://localhost:${PORT}" 2>/dev/null &

# 启动Flask应用
python3 app_advanced.py

# 如果服务器停止
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "服务器已停止"
echo ""
read -p "按回车键退出..."