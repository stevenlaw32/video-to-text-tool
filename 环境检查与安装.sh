#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  视频转文字工具 - 环境检查${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查是否在正确的目录
if [ ! -f "app_advanced.py" ]; then
    echo -e "${RED}❌ 错误：请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 记录需要安装的项目
NEED_INSTALL=()

# ============================================
# 1. 检查 Python 版本
# ============================================
echo -e "${YELLOW}[1/8] 检查 Python 环境...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION 已安装${NC}"
    else
        echo -e "${RED}❌ Python 版本过低 ($PYTHON_VERSION)，需要 3.8+${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python 3.8+${NC}"
    exit 1
fi

# ============================================
# 2. 检查 FFmpeg
# ============================================
echo -e "${YELLOW}[2/8] 检查 FFmpeg...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1 | awk '{print $3}')
    echo -e "${GREEN}✓ FFmpeg $FFMPEG_VERSION 已安装${NC}"
else
    echo -e "${RED}❌ FFmpeg 未安装${NC}"
    NEED_INSTALL+=("ffmpeg")
fi

# ============================================
# 3. 检查 pip 并配置国内镜像源
# ============================================
echo -e "${YELLOW}[3/8] 配置 pip 国内镜像源...${NC}"

# 创建 pip 配置目录
PIP_CONFIG_DIR="$HOME/.pip"
PIP_CONFIG_FILE="$PIP_CONFIG_DIR/pip.conf"

mkdir -p "$PIP_CONFIG_DIR"

# 写入清华镜像源配置
cat > "$PIP_CONFIG_FILE" << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF

echo -e "${GREEN}✓ pip 镜像源已配置为清华大学镜像${NC}"

# ============================================
# 4. 检查虚拟环境
# ============================================
echo -e "${YELLOW}[4/8] 检查 Python 虚拟环境...${NC}"

if [ -d "venv" ]; then
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
else
    echo -e "${YELLOW}⚠ 虚拟环境不存在，正在创建...${NC}"
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"
    else
        echo -e "${RED}❌ 虚拟环境创建失败${NC}"
        exit 1
    fi
fi

# 激活虚拟环境
source venv/bin/activate

# ============================================
# 5. 升级 pip
# ============================================
echo -e "${YELLOW}[5/8] 升级 pip...${NC}"
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple > /dev/null 2>&1
echo -e "${GREEN}✓ pip 已升级到最新版本${NC}"

# ============================================
# 6. 安装 Python 依赖
# ============================================
echo -e "${YELLOW}[6/8] 检查 Python 依赖包...${NC}"

if [ -f "requirements.txt" ]; then
    # 检查是否有离线包
    if [ -d "offline_packages" ] && [ "$(ls -A offline_packages/*.whl 2>/dev/null)" ]; then
        OFFLINE_COUNT=$(ls offline_packages/*.whl 2>/dev/null | wc -l | tr -d ' ')
        echo -e "${GREEN}✓ 发现离线包目录，包含 $OFFLINE_COUNT 个包${NC}"
        echo -e "${BLUE}正在从离线包安装依赖（优先）...${NC}"
        
        # 先尝试纯离线安装
        pip install --no-index --find-links=offline_packages -r requirements.txt 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 所有依赖已从离线包安装完成${NC}"
        else
            # 如果离线包不完整，补充从网络安装缺失的包
            echo -e "${YELLOW}⚠ 离线包不完整，从网络补充安装缺失的包...${NC}"
            pip install --find-links=offline_packages -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ Python 依赖包安装完成（离线包 + 网络补充）${NC}"
            else
                echo -e "${RED}❌ 依赖包安装失败${NC}"
                exit 1
            fi
        fi
    else
        echo -e "${YELLOW}⚠ 未发现离线包，从网络安装...${NC}"
        echo -e "${BLUE}正在安装依赖包（使用清华镜像源）...${NC}"
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Python 依赖包安装完成${NC}"
        else
            echo -e "${RED}❌ 依赖包安装失败${NC}"
            exit 1
        fi
    fi
else
    echo -e "${RED}❌ 未找到 requirements.txt${NC}"
    exit 1
fi

# ============================================
# 7. 检查并下载 Whisper 模型
# ============================================
echo -e "${YELLOW}[7/8] 检查 Whisper 模型...${NC}"

# Whisper 模型缓存目录
WHISPER_CACHE="$HOME/.cache/whisper"
mkdir -p "$WHISPER_CACHE"

# 检查常用模型
MODELS=("tiny" "base" "small")
FOUND_MODEL=false

for model in "${MODELS[@]}"; do
    if ls "$WHISPER_CACHE"/*${model}*.pt 2>/dev/null | grep -q .; then
        echo -e "${GREEN}✓ 找到 Whisper ${model} 模型${NC}"
        FOUND_MODEL=true
    fi
done

if [ "$FOUND_MODEL" = false ]; then
    # 检查是否有离线模型
    if [ -d "offline_packages/whisper_models" ] && [ -f "offline_packages/whisper_models/base.pt" ]; then
        echo -e "${GREEN}✓ 发现离线 Whisper 模型${NC}"
        echo -e "${BLUE}正在从离线包复制模型...${NC}"
        cp offline_packages/whisper_models/*.pt "$WHISPER_CACHE/" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Whisper 模型已从离线包安装${NC}"
            FOUND_MODEL=true
        fi
    fi
    
    # 如果离线模型也没有，才从网络下载
    if [ "$FOUND_MODEL" = false ]; then
        echo -e "${YELLOW}⚠ 未找到 Whisper 模型，正在下载 base 模型...${NC}"
        echo -e "${BLUE}提示：首次下载可能需要几分钟${NC}"
        
        # 使用 Python 下载模型（会自动使用 Whisper 的下载机制）
        python3 << 'PYTHON_SCRIPT'
import whisper
import os

# 设置国内镜像（如果可用）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("正在下载 Whisper base 模型...")
try:
    model = whisper.load_model("base")
    print("✓ 模型下载成功")
except Exception as e:
    print(f"❌ 模型下载失败: {e}")
    exit(1)
PYTHON_SCRIPT
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Whisper 模型下载完成${NC}"
        else
            echo -e "${RED}❌ Whisper 模型下载失败${NC}"
            echo -e "${YELLOW}提示：可以稍后在使用时自动下载${NC}"
        fi
    fi
else
    echo -e "${GREEN}✓ Whisper 模型已就绪${NC}"
fi

# ============================================
# 8. 检查配置文件
# ============================================
echo -e "${YELLOW}[8/8] 检查配置文件...${NC}"

# 检查 models.json
if [ ! -f "models.json" ]; then
    if [ -f "models.json.example" ]; then
        echo -e "${YELLOW}⚠ models.json 不存在，从示例创建...${NC}"
        cp models.json.example models.json
        echo -e "${GREEN}✓ 已创建 models.json（请配置你的 API 密钥）${NC}"
    else
        echo -e "${YELLOW}⚠ models.json 不存在，创建空配置...${NC}"
        echo '{"models": [], "active_model": null}' > models.json
    fi
else
    echo -e "${GREEN}✓ models.json 已存在${NC}"
fi

# 检查 ocr_apis.json
if [ ! -f "ocr_apis.json" ]; then
    if [ -f "ocr_apis.json.example" ]; then
        echo -e "${YELLOW}⚠ ocr_apis.json 不存在，从示例创建...${NC}"
        cp ocr_apis.json.example ocr_apis.json
        echo -e "${GREEN}✓ 已创建 ocr_apis.json${NC}"
    fi
else
    echo -e "${GREEN}✓ ocr_apis.json 已存在${NC}"
fi

# 检查 .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠ .env 不存在，从示例创建...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ 已创建 .env（请配置你的 API 密钥）${NC}"
    fi
else
    echo -e "${GREEN}✓ .env 已存在${NC}"
fi

# 创建必要的目录
mkdir -p output uploads

# ============================================
# 安装系统依赖（如果需要）
# ============================================
if [ ${#NEED_INSTALL[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}================================${NC}"
    echo -e "${YELLOW}需要安装以下系统依赖：${NC}"
    for item in "${NEED_INSTALL[@]}"; do
        echo -e "  - $item"
    done
    echo -e "${YELLOW}================================${NC}"
    echo ""
    
    # 检测操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            read -p "是否使用 Homebrew 安装？(y/N): " install_confirm
            if [[ $install_confirm == [yY] ]]; then
                for item in "${NEED_INSTALL[@]}"; do
                    echo -e "${BLUE}正在安装 $item...${NC}"
                    brew install $item
                done
            fi
        else
            echo -e "${RED}未找到 Homebrew，请手动安装：${NC}"
            echo -e "  brew install ${NEED_INSTALL[@]}"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        read -p "是否使用 apt 安装？(y/N): " install_confirm
        if [[ $install_confirm == [yY] ]]; then
            for item in "${NEED_INSTALL[@]}"; do
                echo -e "${BLUE}正在安装 $item...${NC}"
                sudo apt-get install -y $item
            done
        fi
    fi
fi

# ============================================
# 完成总结
# ============================================
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  ✓ 环境检查完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}📝 后续步骤：${NC}"
echo ""
echo -e "1. ${YELLOW}配置 API 密钥${NC}"
echo -e "   编辑 models.json 或 .env 文件，填入你的 API 密钥"
echo -e "   详见: ${BLUE}README_SECURITY.md${NC}"
echo ""
echo -e "2. ${YELLOW}启动服务${NC}"
echo -e "   方式一（带日志）: ${GREEN}./启动服务（带日志窗口）.command${NC}"
echo -e "   方式二（后台）:   ${GREEN}./启动服务（后台）.command${NC}"
echo -e "   方式三（手动）:   ${GREEN}source venv/bin/activate && python app_advanced.py${NC}"
echo ""
echo -e "3. ${YELLOW}访问 Web 界面${NC}"
echo -e "   浏览器打开: ${BLUE}http://localhost:5000${NC}"
echo ""
echo -e "${BLUE}📚 更多信息：${NC}"
echo -e "   - 使用说明: ${GREEN}README.md${NC}"
echo -e "   - 安全配置: ${GREEN}README_SECURITY.md${NC}"
echo -e "   - OCR 功能: ${GREEN}OCR功能说明.md${NC}"
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo -e "   - 已配置 pip 使用清华大学镜像源加速下载"
echo -e "   - Whisper 模型会在首次使用时自动下载"
echo -e "   - 如遇问题请查看详细日志"
echo ""
