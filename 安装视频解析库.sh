#!/bin/bash

# 视频解析库安装脚本
# 安装抖音和小红书解析库

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  视频解析库安装脚本${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "app_advanced.py" ]; then
    echo -e "${RED}❌ 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    echo -e "${YELLOW}激活虚拟环境...${NC}"
    source venv/bin/activate
else
    echo -e "${RED}❌ 未找到虚拟环境${NC}"
    exit 1
fi

# 创建解析器目录
echo -e "${YELLOW}[1/6] 创建解析器目录...${NC}"
mkdir -p parsers
cd parsers

# 安装必要的依赖
echo ""
echo -e "${YELLOW}[2/6] 安装基础依赖...${NC}"
pip install httpx aiofiles qrcode browser-cookie3 pyperclip rich -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet

# 安装抖音解析器
echo ""
echo -e "${YELLOW}[3/6] 安装抖音解析器...${NC}"
if [ -d "douyin_parser" ]; then
    echo -e "${GREEN}✓ 抖音解析器已存在，跳过${NC}"
else
    echo -e "${BLUE}正在克隆 TikTokDownloader...${NC}"
    git clone --depth=1 https://github.com/JoeanAmier/TikTokDownloader.git douyin_parser 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 抖音解析器克隆成功${NC}"
    else
        echo -e "${YELLOW}尝试使用镜像...${NC}"
        git clone --depth=1 https://ghproxy.com/https://github.com/JoeanAmier/TikTokDownloader.git douyin_parser 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 抖音解析器克隆成功（镜像）${NC}"
        else
            echo -e "${RED}❌ 抖音解析器克隆失败${NC}"
        fi
    fi
fi

# 安装小红书解析器
echo ""
echo -e "${YELLOW}[4/6] 安装小红书解析器...${NC}"
if [ -d "xhs_parser" ]; then
    echo -e "${GREEN}✓ 小红书解析器已存在，跳过${NC}"
else
    echo -e "${BLUE}正在克隆 XHS-Downloader...${NC}"
    git clone --depth=1 https://github.com/JoeanAmier/XHS-Downloader.git xhs_parser 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 小红书解析器克隆成功${NC}"
    else
        echo -e "${YELLOW}尝试使用镜像...${NC}"
        git clone --depth=1 https://ghproxy.com/https://github.com/JoeanAmier/XHS-Downloader.git xhs_parser 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 小红书解析器克隆成功（镜像）${NC}"
        else
            echo -e "${RED}❌ 小红书解析器克隆失败${NC}"
        fi
    fi
fi

# 创建配置文件模板
echo ""
echo -e "${YELLOW}[5/6] 创建配置文件...${NC}"
if [ ! -f "config.json" ]; then
    cat > config.json << 'EOF'
{
  "douyin": {
    "cookie": "",
    "comment": "抖音 Cookie（可选，建议配置以获取更高画质）"
  },
  "xiaohongshu": {
    "cookie": "",
    "comment": "小红书 Cookie（可选，建议配置以获取更高画质）"
  }
}
EOF
    echo -e "${GREEN}✓ 配置文件已创建: parsers/config.json${NC}"
else
    echo -e "${GREEN}✓ 配置文件已存在${NC}"
fi

# 返回项目根目录
cd ..

# 测试安装
echo ""
echo -e "${YELLOW}[6/6] 测试安装...${NC}"

python3 << 'PYTHON_TEST'
import sys
import os

errors = []

try:
    import httpx
    print("✓ httpx")
except Exception as e:
    errors.append(f"httpx: {e}")

try:
    import aiofiles
    print("✓ aiofiles")
except Exception as e:
    errors.append(f"aiofiles: {e}")

if errors:
    print("\n❌ 以下模块导入失败:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("\n✅ 所有依赖验证通过!")
PYTHON_TEST

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}  ✓ 安装完成！${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo -e "${BLUE}📝 后续步骤：${NC}"
    echo ""
    echo "1. 配置 Cookie（可选但推荐）："
    echo "   编辑 parsers/config.json"
    echo ""
    echo "2. 获取 Cookie 方法："
    echo "   - 打开抖音/小红书网页版"
    echo "   - 按 F12 打开开发者工具"
    echo "   - 切换到 Network 标签"
    echo "   - 刷新页面，复制任意请求的 Cookie"
    echo ""
    echo "3. 重启服务："
    echo "   ./启动服务（带日志窗口）.command"
    echo ""
    echo "4. 测试功能："
    echo "   访问 http://localhost:5000"
    echo "   点击"视频链接解析"TAB"
    echo ""
    echo -e "${YELLOW}⚠️  注意：${NC}"
    echo "   - Cookie 可能会过期，需要定期更新"
    echo "   - 请合理使用，避免频繁请求"
    echo "   - 仅供个人学习研究使用"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 安装验证失败${NC}"
    echo "请检查错误信息并重试"
    echo ""
    exit 1
fi
