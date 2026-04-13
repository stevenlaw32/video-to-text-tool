#!/bin/bash

# 视频转文字工具 - 一键安装脚本
# 适用于 macOS 系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║      视频转文字工具 - 依赖安装脚本                      ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. 检查Python版本
echo -e "${BLUE}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 Python3${NC}"
    echo ""
    echo "请先安装 Python 3.9 或更高版本："
    echo "  方式1: 访问 https://www.python.org/downloads/"
    echo "  方式2: 使用 Homebrew: brew install python3"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查Python版本是否 >= 3.9
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}❌ Python 版本过低，需要 3.9 或更高版本${NC}"
    exit 1
fi

# 2. 检查并创建虚拟环境（可选）
echo ""
echo -e "${BLUE}[2/6] 检查虚拟环境...${NC}"
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ 发现已存在的虚拟环境${NC}"
    read -p "是否使用虚拟环境? (推荐) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source venv/bin/activate
        echo -e "${GREEN}✓ 已激活虚拟环境${NC}"
        USE_VENV=true
    else
        USE_VENV=false
    fi
else
    read -p "是否创建虚拟环境? (推荐，可避免依赖冲突) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}正在创建虚拟环境...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        echo -e "${GREEN}✓ 虚拟环境已创建并激活${NC}"
        USE_VENV=true
    else
        echo -e "${YELLOW}⚠️  跳过虚拟环境创建${NC}"
        USE_VENV=false
    fi
fi

# 3. 检查pip
echo ""
echo -e "${BLUE}[3/6] 检查 pip...${NC}"
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${YELLOW}⚠️  未找到 pip，正在安装...${NC}"
    python3 -m ensurepip --upgrade
fi
echo -e "${GREEN}✓ pip 已就绪${NC}"

# 4. 升级pip
echo ""
echo -e "${BLUE}[4/6] 升级 pip 到最新版本...${NC}"
python3 -m pip install --upgrade pip --quiet

# 5. 安装Python依赖
echo ""
echo -e "${BLUE}[5/6] 安装 Python 依赖包...${NC}"
echo -e "${YELLOW}这可能需要几分钟时间，请耐心等待...${NC}"
echo ""

# 检查 requirements.txt 是否存在
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ 未找到 requirements.txt 文件${NC}"
    exit 1
fi

# 安装依赖
if python3 -m pip install -r requirements.txt --quiet; then
    echo -e "${GREEN}✓ Python 依赖安装成功${NC}"
else
    echo -e "${RED}❌ Python 依赖安装失败${NC}"
    echo ""
    echo "请尝试手动安装："
    echo "  pip3 install -r requirements.txt"
    echo ""
    exit 1
fi

# 6. 检查FFmpeg
echo ""
echo -e "${BLUE}[6/6] 检查 FFmpeg...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1 | awk '{print $3}')
    echo -e "${GREEN}✓ FFmpeg 已安装 (版本: $FFMPEG_VERSION)${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 FFmpeg${NC}"
    echo ""
    echo "FFmpeg 用于从视频中提取音频，强烈建议安装。"
    echo ""
    
    # 检查是否有Homebrew
    if command -v brew &> /dev/null; then
        read -p "是否使用 Homebrew 安装 FFmpeg? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "正在安装 FFmpeg..."
            brew install ffmpeg
            echo -e "${GREEN}✓ FFmpeg 安装完成${NC}"
        else
            echo -e "${YELLOW}⚠️  跳过 FFmpeg 安装${NC}"
            echo "你可以稍后手动安装: brew install ffmpeg"
        fi
    else
        echo "请手动安装 FFmpeg："
        echo "  1. 安装 Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  2. 安装 FFmpeg: brew install ffmpeg"
        echo ""
    fi
fi

# 6. 验证安装
echo ""
echo -e "${BLUE}验证安装...${NC}"
echo ""

# 测试导入关键模块
python3 << 'PYEOF'
import sys
errors = []

try:
    import flask
    print("✓ Flask")
except Exception as e:
    errors.append(f"Flask: {e}")

try:
    import whisper
    print("✓ OpenAI-Whisper")
except Exception as e:
    errors.append(f"OpenAI-Whisper: {e}")

try:
    import openai
    print("✓ OpenAI")
except Exception as e:
    errors.append(f"OpenAI: {e}")

try:
    import numpy
    print("✓ NumPy")
except Exception as e:
    errors.append(f"NumPy: {e}")

if errors:
    print("\n❌ 以下模块导入失败:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("\n✅ 所有依赖验证通过!")
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${GREEN}🎉 安装完成！${NC}"
    echo ""
    echo "接下来的步骤："
    echo "  1. 配置 API 密钥（编辑 .env 文件）"
    if [ "$USE_VENV" = true ]; then
        echo "  2. 激活虚拟环境: source venv/bin/activate"
        echo "  3. 运行: python3 app_advanced.py"
    else
        echo "  2. 运行: python3 app_advanced.py"
    fi
    echo "  4. 在浏览器访问: http://localhost:5000"
    echo ""
    echo "提示："
    echo "  - 命令行工具: python3 main.py -i video.mp4 -o output"
    echo "  - Web界面（增强版）: python3 app_advanced.py"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 安装验证失败${NC}"
    echo "请检查错误信息并重试"
    echo ""
    exit 1
fi
