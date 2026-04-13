#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 使用 AppleScript 打开新的终端窗口运行服务器
osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$DIR' && source venv/bin/activate && python3 app_advanced.py"
end tell
EOF

# 等待一秒后打开浏览器
sleep 2
open http://localhost:5000

echo "服务器已在新终端窗口启动"
echo "浏览器将自动打开 http://localhost:5000"
echo "Whisper 转录的详细日志会显示在新打开的终端窗口中"
echo ""
echo "提示：处理视频时，切换到新终端窗口即可看到实时转录进度"
