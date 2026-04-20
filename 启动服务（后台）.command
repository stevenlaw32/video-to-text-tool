#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 检查是否已经在运行
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "服务器已在运行"
    open http://localhost:5000
    exit 0
fi

# 激活虚拟环境并在后台启动服务器
nohup bash -c "cd '$DIR' && export KMP_DUPLICATE_LIB_OK=TRUE && source venv/bin/activate && python3 app_advanced.py" > /tmp/video-to-text.log 2>&1 &

# 等待服务器启动
echo "正在启动服务器..."
sleep 3

# 检查服务器是否成功启动
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✓ 服务器启动成功"
    echo "✓ 访问地址: http://localhost:5000"
    echo "✓ 日志文件: /tmp/video-to-text.log"
    
    # 自动打开浏览器
    open http://localhost:5000
    
    # 显示通知
    osascript -e 'display notification "服务器已启动，浏览器将自动打开" with title "视频转文字工具"'
else
    echo "❌ 服务器启动失败"
    echo "请查看日志: /tmp/video-to-text.log"
    tail -20 /tmp/video-to-text.log
fi
