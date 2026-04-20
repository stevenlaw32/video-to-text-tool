#!/bin/bash

echo "正在停止服务器..."

# 查找并终止运行在5000端口的进程
PID=$(lsof -ti:5000)

if [ -z "$PID" ]; then
    echo "✓ 服务器未运行"
else
    kill $PID
    sleep 1
    
    # 检查是否成功停止
    if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  正常停止失败，强制终止..."
        kill -9 $PID
    fi
    
    echo "✓ 服务器已停止"
    
    # 显示通知
    osascript -e 'display notification "服务器已停止" with title "视频转文字工具"'
fi

sleep 1
