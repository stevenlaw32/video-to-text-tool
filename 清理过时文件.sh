#!/bin/bash

# 清理项目中过时和重复的文件

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  清理过时文件${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "app_advanced.py" ]; then
    echo -e "${RED}❌ 请在项目根目录运行此脚本${NC}"
    exit 1
fi

echo -e "${YELLOW}以下文件将被删除：${NC}"
echo ""

# 过时的安装脚本（已被 环境检查与安装.sh 替代）
echo -e "${RED}[过时的安装脚本]${NC}"
echo "  - 一键安装依赖.sh (已被 环境检查与安装.sh 替代)"
echo "  - 安装OCR依赖.sh (功能已整合到主安装脚本)"

# 过时的启动脚本（已被 启动服务（带日志窗口）.command 替代）
echo ""
echo -e "${RED}[过时的启动脚本]${NC}"
echo "  - 启动服务.sh (已被 启动服务（带日志窗口）.command 替代)"
echo "  - 启动客户端.command (功能重复)"

# 重复的文档
echo ""
echo -e "${RED}[重复的文档]${NC}"
echo "  - QUICKSTART.md (已被 快速开始.md 替代)"
echo "  - 使用说明-增强版.md (内容已过时，路径错误)"
echo "  - 启动说明.md (内容已整合到 快速开始.md)"
echo "  - 音频提取快速测试.md (测试文档，非必需)"

# 过时的Python文件
echo ""
echo -e "${RED}[过时的Python文件]${NC}"
echo "  - ai_summarizer.py (已被 api_client.py 替代)"
echo "  - ai_summarizer_v2.py (已被 api_client.py 替代)"
echo "  - import_models.py (一次性工具，已完成使命)"

# 空目录
echo ""
echo -e "${RED}[空目录]${NC}"
echo "  - audio_output/ (空目录)"

# 系统文件
echo ""
echo -e "${RED}[系统文件]${NC}"
echo "  - .DS_Store (macOS 系统文件)"

echo ""
echo -e "${YELLOW}================================${NC}"
echo ""

read -p "确认删除以上文件？(y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo -e "${YELLOW}已取消操作${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}开始清理...${NC}"
echo ""

# 删除过时的安装脚本
if [ -f "一键安装依赖.sh" ]; then
    rm "一键安装依赖.sh"
    echo -e "${GREEN}✓ 已删除: 一键安装依赖.sh${NC}"
fi

if [ -f "安装OCR依赖.sh" ]; then
    rm "安装OCR依赖.sh"
    echo -e "${GREEN}✓ 已删除: 安装OCR依赖.sh${NC}"
fi

# 删除过时的启动脚本
if [ -f "启动服务.sh" ]; then
    rm "启动服务.sh"
    echo -e "${GREEN}✓ 已删除: 启动服务.sh${NC}"
fi

if [ -f "启动客户端.command" ]; then
    rm "启动客户端.command"
    echo -e "${GREEN}✓ 已删除: 启动客户端.command${NC}"
fi

# 删除重复的文档
if [ -f "QUICKSTART.md" ]; then
    rm "QUICKSTART.md"
    echo -e "${GREEN}✓ 已删除: QUICKSTART.md${NC}"
fi

if [ -f "使用说明-增强版.md" ]; then
    rm "使用说明-增强版.md"
    echo -e "${GREEN}✓ 已删除: 使用说明-增强版.md${NC}"
fi

if [ -f "启动说明.md" ]; then
    rm "启动说明.md"
    echo -e "${GREEN}✓ 已删除: 启动说明.md${NC}"
fi

if [ -f "音频提取快速测试.md" ]; then
    rm "音频提取快速测试.md"
    echo -e "${GREEN}✓ 已删除: 音频提取快速测试.md${NC}"
fi

# 删除过时的Python文件
if [ -f "ai_summarizer.py" ]; then
    rm "ai_summarizer.py"
    echo -e "${GREEN}✓ 已删除: ai_summarizer.py${NC}"
fi

if [ -f "ai_summarizer_v2.py" ]; then
    rm "ai_summarizer_v2.py"
    echo -e "${GREEN}✓ 已删除: ai_summarizer_v2.py${NC}"
fi

if [ -f "import_models.py" ]; then
    rm "import_models.py"
    echo -e "${GREEN}✓ 已删除: import_models.py${NC}"
fi

# 删除空目录
if [ -d "audio_output" ] && [ -z "$(ls -A audio_output)" ]; then
    rmdir "audio_output"
    echo -e "${GREEN}✓ 已删除: audio_output/${NC}"
fi

# 删除系统文件
if [ -f ".DS_Store" ]; then
    rm ".DS_Store"
    echo -e "${GREEN}✓ 已删除: .DS_Store${NC}"
fi

# 清理所有 .DS_Store 文件
find . -name ".DS_Store" -type f -delete 2>/dev/null
echo -e "${GREEN}✓ 已清理所有 .DS_Store 文件${NC}"

# 清理 __pycache__
if [ -d "__pycache__" ]; then
    rm -rf "__pycache__"
    echo -e "${GREEN}✓ 已删除: __pycache__/${NC}"
fi

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✓ 已清理所有 __pycache__ 目录${NC}"

# 清理 .pyc 文件
find . -name "*.pyc" -type f -delete 2>/dev/null
echo -e "${GREEN}✓ 已清理所有 .pyc 文件${NC}"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  ✓ 清理完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}已删除的文件类型：${NC}"
echo "  - 过时的安装脚本: 2 个"
echo "  - 过时的启动脚本: 2 个"
echo "  - 重复的文档: 4 个"
echo "  - 过时的Python文件: 3 个"
echo "  - 空目录: 1 个"
echo "  - 系统缓存文件: 若干"
echo ""
echo -e "${YELLOW}建议：${NC}"
echo "  1. 运行 git status 检查变更"
echo "  2. 测试项目是否正常运行"
echo "  3. 如果一切正常，提交变更"
echo ""
