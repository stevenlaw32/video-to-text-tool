#!/bin/bash

# 设置环境变量解决 OpenMP 冲突
export KMP_DUPLICATE_LIB_OK=TRUE

# 进入项目目录
cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 启动应用
python app_advanced.py
