#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PORT=5001

echo "================================================"
echo "  视频转文字工具"
echo "================================================"
echo ""

# 检查是否已在运行
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  服务已在运行，直接打开浏览器..."
    open "http://localhost:$PORT"
    exit 0
fi

# 检查虚拟环境
if [ ! -d "$DIR/venv311" ]; then
    echo "❌ 未找到虚拟环境 venv311，请先运行 环境检查与安装.sh"
    read -n 1 -s -r -p "按任意键退出..."
    exit 1
fi

export KMP_DUPLICATE_LIB_OK=TRUE
source "$DIR/venv311/bin/activate"

echo "✓ 虚拟环境已激活（Python 3.11）"
echo "✓ 启动服务，地址: http://localhost:$PORT"
echo "✓ 浏览器将在服务就绪后自动打开"
echo ""
echo "提示：转录进度日志会实时显示在此窗口"
echo "按 Ctrl+C 停止服务"
echo "------------------------------------------------"
echo ""

# 延迟打开浏览器
(sleep 2 && open "http://localhost:$PORT") &

python3 app_advanced.py
