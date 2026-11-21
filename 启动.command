#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PORT=5001

# 读取版本号
if [ -f "$DIR/VERSION" ]; then
    VERSION=$(cat "$DIR/VERSION" | tr -d '[:space:]')
else
    VERSION="unknown"
fi

echo "================================================"
echo "  视频转文字工具  v${VERSION}"
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

# 检查核心依赖是否已安装
MISSING=""
for pkg in flask openai dotenv requests; do
    python3 -c "import $pkg" 2>/dev/null || MISSING="$MISSING $pkg"
done
python3 -c "from importlib.metadata import version; assert int(version('openai').split('.')[0]) >= 3" 2>/dev/null || MISSING="$MISSING openai>=3"

if [ -n "$MISSING" ]; then
    echo "⚠️  检测到缺少依赖:$MISSING"
    echo "   正在自动安装 requirements.txt ..."
    pip install -r "$DIR/requirements.txt" --quiet
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请手动运行: pip install -r requirements.txt"
        read -n 1 -s -r -p "按任意键退出..."
        exit 1
    fi
    echo "✓ 依赖安装完成"
fi

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
