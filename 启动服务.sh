#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 设置环境变量（解决 OpenMP 库冲突）
export KMP_DUPLICATE_LIB_OK=TRUE

# 激活虚拟环境
source venv/bin/activate

# 启动服务
python3 app_advanced.py
