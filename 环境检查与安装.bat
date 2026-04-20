@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================
echo   视频转文字工具 - 环境检查
echo ================================
echo.

REM 检查是否在正确的目录
if not exist "app_advanced.py" (
    echo [错误] 请在项目根目录运行此脚本
    pause
    exit /b 1
)

REM ============================================
REM 1. 检查 Python 版本
REM ============================================
echo [1/8] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [√] Python !PYTHON_VERSION! 已安装
)

REM ============================================
REM 2. 检查 FFmpeg
REM ============================================
echo [2/8] 检查 FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [X] FFmpeg 未安装
    echo 请下载并安装 FFmpeg: https://ffmpeg.org/download.html
    echo 并将 FFmpeg 添加到系统 PATH
    set NEED_FFMPEG=1
) else (
    echo [√] FFmpeg 已安装
)

REM ============================================
REM 3. 配置 pip 国内镜像源
REM ============================================
echo [3/8] 配置 pip 国内镜像源...

set PIP_CONFIG_DIR=%APPDATA%\pip
set PIP_CONFIG_FILE=%PIP_CONFIG_DIR%\pip.ini

if not exist "%PIP_CONFIG_DIR%" mkdir "%PIP_CONFIG_DIR%"

(
echo [global]
echo index-url = https://pypi.tuna.tsinghua.edu.cn/simple
echo trusted-host = pypi.tuna.tsinghua.edu.cn
echo.
echo [install]
echo trusted-host = pypi.tuna.tsinghua.edu.cn
) > "%PIP_CONFIG_FILE%"

echo [√] pip 镜像源已配置为清华大学镜像

REM ============================================
REM 4. 检查虚拟环境
REM ============================================
echo [4/8] 检查 Python 虚拟环境...

if exist "venv" (
    echo [√] 虚拟环境已存在
) else (
    echo [!] 虚拟环境不存在，正在创建...
    python -m venv venv
    if errorlevel 1 (
        echo [X] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [√] 虚拟环境创建成功
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM ============================================
REM 5. 升级 pip
REM ============================================
echo [5/8] 升级 pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
echo [√] pip 已升级到最新版本

REM ============================================
REM 6. 安装 Python 依赖
REM ============================================
echo [6/8] 检查 Python 依赖包...

if exist "requirements.txt" (
    REM 检查是否有离线包
    if exist "offline_packages\*.whl" (
        echo [√] 发现离线包目录
        echo 正在从离线包安装依赖（优先）...
        
        REM 先尝试纯离线安装
        pip install --no-index --find-links=offline_packages -r requirements.txt >nul 2>&1
        
        if errorlevel 1 (
            REM 如果离线包不完整，补充从网络安装
            echo [!] 离线包不完整，从网络补充安装缺失的包...
            pip install --find-links=offline_packages -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
            
            if errorlevel 1 (
                echo [X] 依赖包安装失败
                pause
                exit /b 1
            )
            echo [√] Python 依赖包安装完成（离线包 + 网络补充）
        ) else (
            echo [√] 所有依赖已从离线包安装完成
        )
    ) else (
        echo [!] 未发现离线包，从网络安装...
        echo 正在安装依赖包（使用清华镜像源）...
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        
        if errorlevel 1 (
            echo [X] 依赖包安装失败
            pause
            exit /b 1
        )
        echo [√] Python 依赖包安装完成
    )
) else (
    echo [X] 未找到 requirements.txt
    pause
    exit /b 1
)

REM ============================================
REM 7. 检查 Whisper 模型
REM ============================================
echo [7/8] 检查 Whisper 模型...

set WHISPER_CACHE=%USERPROFILE%\.cache\whisper
if not exist "%WHISPER_CACHE%" mkdir "%WHISPER_CACHE%"

REM 检查是否有模型文件
dir /b "%WHISPER_CACHE%\*.pt" >nul 2>&1
if errorlevel 1 (
    REM 检查是否有离线模型
    if exist "offline_packages\whisper_models\base.pt" (
        echo [√] 发现离线 Whisper 模型
        echo 正在从离线包复制模型...
        copy /Y offline_packages\whisper_models\*.pt "%WHISPER_CACHE%\" >nul 2>&1
        
        if errorlevel 1 (
            echo [X] 模型复制失败
        ) else (
            echo [√] Whisper 模型已从离线包安装
        )
    ) else (
        echo [!] 未找到 Whisper 模型，正在下载 base 模型...
        echo 提示：首次下载可能需要几分钟
        
        python -c "import whisper; import os; os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'; print('正在下载 Whisper base 模型...'); model = whisper.load_model('base'); print('模型下载成功')"
        
        if errorlevel 1 (
            echo [X] Whisper 模型下载失败
            echo 提示：可以稍后在使用时自动下载
        ) else (
            echo [√] Whisper 模型下载完成
        )
    )
) else (
    echo [√] Whisper 模型已就绪
)

REM ============================================
REM 8. 检查配置文件
REM ============================================
echo [8/8] 检查配置文件...

if not exist "models.json" (
    if exist "models.json.example" (
        echo [!] models.json 不存在，从示例创建...
        copy models.json.example models.json >nul
        echo [√] 已创建 models.json（请配置你的 API 密钥）
    ) else (
        echo [!] models.json 不存在，创建空配置...
        echo {"models": [], "active_model": null} > models.json
    )
) else (
    echo [√] models.json 已存在
)

if not exist "ocr_apis.json" (
    if exist "ocr_apis.json.example" (
        echo [!] ocr_apis.json 不存在，从示例创建...
        copy ocr_apis.json.example ocr_apis.json >nul
        echo [√] 已创建 ocr_apis.json
    )
) else (
    echo [√] ocr_apis.json 已存在
)

if not exist ".env" (
    if exist ".env.example" (
        echo [!] .env 不存在，从示例创建...
        copy .env.example .env >nul
        echo [√] 已创建 .env（请配置你的 API 密钥）
    )
) else (
    echo [√] .env 已存在
)

REM 创建必要的目录
if not exist "output" mkdir output
if not exist "uploads" mkdir uploads

REM ============================================
REM 完成总结
REM ============================================
echo.
echo ================================
echo   √ 环境检查完成！
echo ================================
echo.
echo 后续步骤：
echo.
echo 1. 配置 API 密钥
echo    编辑 models.json 或 .env 文件，填入你的 API 密钥
echo    详见: README_SECURITY.md
echo.
echo 2. 启动服务
echo    双击运行: 启动服务（带日志窗口）.command
echo    或手动运行: venv\Scripts\activate ^&^& python app_advanced.py
echo.
echo 3. 访问 Web 界面
echo    浏览器打开: http://localhost:5000
echo.
echo 更多信息：
echo    - 使用说明: README.md
echo    - 安全配置: README_SECURITY.md
echo.
echo 提示：
echo    - 已配置 pip 使用清华大学镜像源加速下载
echo    - Whisper 模型会在首次使用时自动下载

if defined NEED_FFMPEG (
    echo.
    echo [!] 警告：FFmpeg 未安装，请手动安装后才能使用音频提取功能
)

echo.
pause
