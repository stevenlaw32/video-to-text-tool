let uploadedFiles = [];
let combinedTranscript = '';
let aiSummary = '';
let folderName = '';
let customPromptText = ''; // 从API配置中加载

// 默认提示词（仅用于后端，前端从API配置读取）
const DEFAULT_PROMPT = `请你扮演一名"课程笔记精简&排版编辑"，对我提供的 Markdown 课程文档进行重排、精简和结构优化。要求如下：

## 整体风格
- 保留所有核心观点和方法论，删除或压缩废话、营销语、重复说明
- 风格偏向知识笔记/复习大纲，而不是长篇教程文案
- 语言简洁、直接，句子能短就短

## 结构调整
用少量清晰的一级、二级标题组织内容，例如：
- 一、课程主题/正确认知
- 二、核心目标/根本目的
- 三、常见错误或禁忌
- 四、核心方法/技巧
- 五、练习与作业/实战

要求：
- 尽量合并重复或碎片化的小节，避免"第一节/第二节/第三节"式的细碎结构，如果内容相近就归为同一大块
- 保持目录层级不超过2-3级，避免过深的标题嵌套

## 内容精简方式
- 将能列表化的内容，尽量改成有条理的项目符号或编号列表
- 同一意思只保留一次表达：若原文在不同小节重复同一个观点，合并到一个地方，用1-2句说清
- 删除或压缩以下内容：
  - 过度铺陈、空话和情绪化语句（如"通过本课程你将能够……"之类）
  - 冗长的过渡句、赘述的"背景介绍"
  - 过多、类似的例子，只保留最典型1-2个

## 重点呈现方式
- 用粗体强调关键概念和步骤（例如：**发散性思维**、**平移思维**、**需求感过强**）
- 对"方法/技巧"类内容，用清晰的结构呈现：
  1. 定义
  2. 使用步骤
  3. 示例
  4. 适用场景/注意点（如果原文有）
- 对"禁忌/错误"类内容，整合成一个汇总列表，避免散落多处重复说

## 示例与比喻
- 保留有助理解的例子和比喻，但删除明显重复或价值不高的例子
- 示例尽量简短，能用1-2条对话或一个场景说明的，不拉长叙述

## 练习与作业部分
- 独立成一个"练习/作业/实战应用"模块
- 用列表列出具体要做的事情和频次（如"每天练习20个关键词"），方便执行和回顾

## 输出格式
- 只输出修改后的整篇Markdown文本，不需要解释，不要加无关前后缀
- 保持语种和原文一致（原文是中文就全中文）

转录文本：
{transcript}

请开始整理：`;

// 中文数字转阿拉伯数字
function chineseToNumber(str) {
    const chineseNum = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    };
    
    // 处理"第X课"、"第X节"等格式
    const pattern = /第([零一二三四五六七八九十百千万]+)/g;
    
    return str.replace(pattern, (match, chinese) => {
        let result = 0;
        let temp = 0;
        let unit = 1;
        
        // 特殊处理"十"开头的情况（如"十一"表示11）
        if (chinese[0] === '十') {
            result = 10;
            chinese = chinese.substring(1);
        }
        
        for (let i = chinese.length - 1; i >= 0; i--) {
            const char = chinese[i];
            const num = chineseNum[char];
            
            if (num >= 10) {
                unit = num;
                if (temp === 0) temp = 1;
                result += temp * unit;
                temp = 0;
            } else {
                temp = num;
            }
        }
        result += temp;
        
        // 返回补齐的数字，确保排序正确
        return '第' + String(result).padStart(4, '0');
    });
}

// 自然排序函数，正确处理文件名中的数字
function naturalSort(a, b) {
    // 先转换中文数字
    const aConverted = chineseToNumber(a);
    const bConverted = chineseToNumber(b);
    
    // 使用正则表达式分离阿拉伯数字和非数字部分
    const regex = /(\d+)/g;
    
    // 替换数字为带前导零的格式
    const normalize = (str) => {
        return str.replace(regex, (match) => {
            return match.padStart(10, '0');
        });
    };
    
    const aNorm = normalize(aConverted);
    const bNorm = normalize(bConverted);
    
    // 使用中文locale进行比较
    return aNorm.localeCompare(bNorm, 'zh-CN', { numeric: true, sensitivity: 'base' });
}

// 页面加载时从多模型配置加载模型列表
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // 加载提示词
        const configResponse = await fetch('/api/get_config');
        if (configResponse.ok) {
            const config = await configResponse.json();
            customPromptText = config.default_system_prompt || DEFAULT_PROMPT;
        } else {
            customPromptText = DEFAULT_PROMPT;
        }
        
        // 加载多模型配置列表
        const modelsResponse = await fetch('/api/models/list');
        if (modelsResponse.ok) {
            const modelsData = await modelsResponse.json();
            if (modelsData.success && modelsData.models.length > 0) {
                const aiModelSelect = document.getElementById('aiModel');
                if (aiModelSelect) {
                    // 清空现有选项
                    aiModelSelect.innerHTML = '';
                    
                    // 添加所有配置的模型
                    modelsData.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.alias;
                        option.textContent = `${model.alias} - ${model.model_name}`;
                        option.dataset.modelName = model.model_name;
                        
                        // 如果是活动模型，设为选中
                        if (model.alias === modelsData.active_model) {
                            option.selected = true;
                        }
                        
                        aiModelSelect.appendChild(option);
                    });
                }
            }
        }
    } catch (error) {
        console.error('加载配置失败:', error);
        customPromptText = DEFAULT_PROMPT;
    }
});

const dropZone = document.getElementById('dropZone');
const videoInput = document.getElementById('videoInput');
const videoList = document.getElementById('videoList');
const videoCount = document.getElementById('videoCount');
const processBtn = document.getElementById('processBtn');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const transcriptResult = document.getElementById('transcriptResult');
const summarySection = document.getElementById('summarySection');
const summaryResult = document.getElementById('summaryResult');

dropZone.addEventListener('click', () => videoInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-indigo-500', 'bg-indigo-50');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
});

dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
    
    const items = e.dataTransfer.items;
    const files = [];
    
    if (items) {
        for (let i = 0; i < items.length; i++) {
            const item = items[i].webkitGetAsEntry();
            if (item) {
                if (item.isDirectory) {
                    folderName = item.name;
                    await readDirectory(item, files);
                } else if (item.isFile) {
                    const file = items[i].getAsFile();
                    if (file) files.push(file);
                }
            }
        }
    } else {
        files.push(...Array.from(e.dataTransfer.files));
    }
    
    if (files.length > 0) {
        files.sort((a, b) => naturalSort(a.name, b.name));
        handleFiles(files);
    }
});

async function readDirectory(directory, files) {
    const reader = directory.createReader();
    
    return new Promise((resolve) => {
        const readEntries = () => {
            reader.readEntries(async (entries) => {
                if (entries.length === 0) {
                    resolve();
                    return;
                }
                
                for (const entry of entries) {
                    if (entry.isFile) {
                        const file = await getFileFromEntry(entry);
                        if (file && isVideoFile(file.name)) {
                            files.push(file);
                        }
                    } else if (entry.isDirectory) {
                        await readDirectory(entry, files);
                    }
                }
                
                readEntries();
            });
        };
        
        readEntries();
    });
}

function getFileFromEntry(entry) {
    return new Promise((resolve) => {
        entry.file(resolve, () => resolve(null));
    });
}

function isVideoFile(filename) {
    const allowedExtensions = [
        // 视频格式
        'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', 'webm',
        // 音频格式
        'mp3', 'wav', 'aac', 'm4a', 'flac', 'ogg', 'wma', 'opus'
    ];
    const ext = filename.split('.').pop().toLowerCase();
    return allowedExtensions.includes(ext);
}

videoInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
});

async function handleFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('videos', file);
    });
    
    if (folderName) {
        formData.append('folder_name', folderName);
    }
    
    try {
        const response = await fetch('/upload_batch', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            uploadedFiles = uploadedFiles.concat(data.files);
            uploadedFiles.sort((a, b) => naturalSort(a.name, b.name));
            renderVideoList();
            videoInput.value = '';
        } else {
            alert('上传失败: ' + data.error);
        }
    } catch (error) {
        alert('上传出错: ' + error.message);
    }
}

function renderVideoList() {
    if (uploadedFiles.length === 0) {
        videoList.innerHTML = '<p class="text-gray-400 text-center py-8">暂无视频，请上传</p>';
        videoCount.textContent = '(0个)';
        return;
    }
    
    videoCount.textContent = `(${uploadedFiles.length}个)`;
    
    videoList.innerHTML = uploadedFiles.map((file, index) => `
        <div class="video-item bg-gray-50 rounded-lg p-4 flex items-center justify-between border border-gray-200" data-id="${file.id}">
            <div class="flex items-center flex-1">
                <i class="fas fa-grip-vertical drag-handle text-gray-400 mr-3 text-xl"></i>
                <div class="flex items-center space-x-3 flex-1">
                    <div class="bg-indigo-100 text-indigo-600 rounded-full w-8 h-8 flex items-center justify-center font-semibold">
                        ${index + 1}
                    </div>
                    <div class="flex-1">
                        <p class="font-medium text-gray-800">${file.name}</p>
                        <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                    </div>
                </div>
            </div>
            <button onclick="removeVideo('${file.id}')" class="text-red-500 hover:text-red-700 ml-4">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
    
    initSortable();
}

function initSortable() {
    new Sortable(videoList, {
        animation: 150,
        handle: '.drag-handle',
        ghostClass: 'sortable-ghost',
        onEnd: function(evt) {
            const item = uploadedFiles.splice(evt.oldIndex, 1)[0];
            uploadedFiles.splice(evt.newIndex, 0, item);
            renderVideoList();
        }
    });
}

function removeVideo(id) {
    uploadedFiles = uploadedFiles.filter(f => f.id !== id);
    renderVideoList();
}

function clearAll() {
    if (uploadedFiles.length === 0) return;
    if (confirm('确定要清空所有视频吗？')) {
        uploadedFiles = [];
        renderVideoList();
    }
}

async function startProcessing() {
    if (uploadedFiles.length === 0) {
        alert('请先上传视频文件');
        return;
    }
    
    processBtn.disabled = true;
    resultSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    
    // 设置处理状态并禁用导航
    isProcessing = true;
    setNavigationEnabled(false);
    
    // 连接日志流
    connectLogStream();
    
    // 启动计时器
    startTimer();
    
    const videoIds = uploadedFiles.map(f => f.id);
    const modelSize = document.getElementById('modelSize').value;
    const whisperLanguage = document.getElementById('whisperLanguage').value;
    const modelAlias = document.getElementById('aiModel').value;
    const enableAI = document.getElementById('enableAI').checked;
    const totalVideos = uploadedFiles.length;
    
    try {
        // 阶段1: 准备处理 (0-5%)
        updateProgress(
            2, 
            '🔧 准备处理环境', 
            '初始化 Whisper 模型和 API 连接...',
            `准备处理 ${totalVideos} 个视频文件`
        );
        
        await new Promise(resolve => setTimeout(resolve, 300));
        
        updateProgress(
            5, 
            '✓ 环境准备完成', 
            '开始处理视频文件...',
            `共 ${totalVideos} 个文件待处理`
        );
        
        // 显示处理中状态
        updateProgress(
            10,
            `🎤 正在处理视频`,
            `处理中，请查看右侧日志窗口...`,
            `共 ${totalVideos} 个视频`
        );
        
        // 发送处理请求
        const response = await fetch('/process_batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_ids: videoIds,
                model_size: modelSize,
                whisper_language: whisperLanguage,
                model_alias: modelAlias,
                custom_prompt: customPromptText,
                enable_ai_summary: enableAI
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 阶段4: 转录完成 (70-75%)
            addLog('✓ 所有视频转录完成', 'success');
            addLog(`   转录文本长度: ${data.combined_transcript.length} 字符`, 'success');
            
            updateProgress(
                72,
                '✓ 转录完成',
                '所有视频转录已完成，正在合并结果...',
                `成功处理 ${totalVideos} 个视频`
            );
            
            combinedTranscript = data.combined_transcript;
            transcriptResult.textContent = combinedTranscript;
            
            if (enableAI && data.ai_summary) {
                // 阶段5: AI 整理 (75-95%)
                addLog('═'.repeat(50), 'header');
                addLog('🤖 开始 AI 智能整理', 'header');
                addLog(`   模型: ${modelAlias}`, 'info');
                
                updateProgress(
                    75,
                    '🤖 AI 智能整理',
                    `使用 ${modelAlias} 模型生成摘要...`,
                    '正在分析转录内容并生成结构化文档'
                );
                
                addLog('📡 正在调用 AI API...', 'info');
                await new Promise(resolve => setTimeout(resolve, 500));
                
                updateProgress(
                    85,
                    '🤖 AI 处理中',
                    '生成章节标题和要点提取...',
                    '优化文档结构和格式'
                );
                
                aiSummary = data.ai_summary;
                summaryResult.innerHTML = marked.parse(aiSummary);
                summarySection.classList.remove('hidden');
                
                addLog('✓ AI 摘要生成完成', 'success');
                addLog(`   摘要长度: ${data.ai_summary.length} 字符`, 'success');
                
                updateProgress(
                    95,
                    '✓ AI 摘要完成',
                    '文档整理和格式化已完成',
                    '准备展示结果'
                );
            } else {
                summarySection.classList.add('hidden');
                updateProgress(
                    90,
                    '⏭️ 跳过 AI 整理',
                    '已禁用 AI 摘要功能',
                    '准备展示转录结果'
                );
            }
            
            // 阶段6: 保存结果 (95-100%)
            updateProgress(
                98,
                '💾 保存结果',
                '生成下载文件...',
                '处理即将完成'
            );
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            updateProgress(
                100,
                '🎉 处理完成！',
                `成功处理 ${totalVideos} 个视频，总用时 ${document.getElementById('elapsedTime').textContent}`,
                '所有任务已完成'
            );
            
            // 添加完成日志
            addLog('═'.repeat(50), 'header');
            addLog('🎉 所有任务完成！', 'success');
            addLog(`✓ 成功处理 ${totalVideos} 个视频`, 'success');
            addLog(`✓ 总用时: ${document.getElementById('elapsedTime').textContent}`, 'success');
            addLog('═'.repeat(50), 'header');
            
            // 停止计时器
            stopTimer();
            
            setTimeout(() => {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');
                
                // 断开日志流
                disconnectLogStream();
                
                // 恢复导航
                isProcessing = false;
                setNavigationEnabled(true);
            }, 1500);
        } else {
            stopTimer();
            alert('处理失败: ' + (data.error || '未知错误'));
            progressSection.classList.add('hidden');
            
            // 断开日志流
            disconnectLogStream();
            
            // 恢复导航
            isProcessing = false;
            setNavigationEnabled(true);
        }
        
    } catch (error) {
        stopTimer();
        alert('处理出错: ' + error.message);
        progressSection.classList.add('hidden');
        
        // 断开日志流
        disconnectLogStream();
        
        // 恢复导航
        isProcessing = false;
        setNavigationEnabled(true);
    } finally {
        processBtn.disabled = false;
    }
}

let startTime = null;
let timerInterval = null;
let isProcessing = false; // 处理状态标记
let eventSource = null; // SSE 连接

// 连接到后端日志流
function connectLogStream() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource('/stream_logs');
    
    eventSource.onmessage = function(event) {
        const log = JSON.parse(event.data);
        addLog(log.message, log.type);
    };
    
    eventSource.onerror = function(error) {
        console.error('SSE连接错误:', error);
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    };
}

// 断开日志流
function disconnectLogStream() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

// 日志管理
function addLog(message, type = 'info') {
    const logConsole = document.getElementById('logConsole');
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    
    // 创建日志行
    const logLine = document.createElement('div');
    logLine.className = 'mb-1';
    
    // 根据类型设置颜色
    let color = 'text-green-400';
    let icon = '●';
    if (type === 'success') {
        color = 'text-green-500';
        icon = '✓';
    } else if (type === 'error') {
        color = 'text-red-500';
        icon = '✗';
    } else if (type === 'warning') {
        color = 'text-yellow-500';
        icon = '⚠';
    } else if (type === 'header') {
        color = 'text-cyan-400 font-bold';
        icon = '━';
    }
    
    logLine.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> <span class="${color}">${icon}</span> ${message}`;
    
    // 如果是第一条日志，清空初始提示
    if (logConsole.querySelector('.text-gray-500')?.textContent === '等待处理开始...') {
        logConsole.innerHTML = '';
    }
    
    logConsole.appendChild(logLine);
    
    // 自动滚动到底部
    logConsole.scrollTop = logConsole.scrollHeight;
}

function clearLogs() {
    const logConsole = document.getElementById('logConsole');
    logConsole.innerHTML = '<div class="text-gray-500">日志已清空</div>';
}

// 禁用/启用导航链接
function setNavigationEnabled(enabled) {
    const modelsLink = document.getElementById('modelsLink');
    const settingsLink = document.getElementById('settingsLink');
    
    if (!enabled) {
        // 禁用导航
        modelsLink.classList.add('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
        settingsLink.classList.add('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
        
        // 添加离开页面警告
        window.onbeforeunload = function() {
            return "正在处理视频，离开页面将丢失进度。确定要离开吗？";
        };
    } else {
        // 启用导航
        modelsLink.classList.remove('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
        settingsLink.classList.remove('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
        
        // 移除离开页面警告
        window.onbeforeunload = null;
    }
}

function updateProgress(percent, step, detail = '', currentVideo = '') {
    // 更新进度条
    progressBar.style.width = percent + '%';
    
    // 更新百分比
    document.getElementById('progressPercentage').textContent = Math.round(percent) + '%';
    
    // 更新当前步骤
    document.getElementById('progressStep').textContent = step;
    
    // 更新详细信息
    if (detail) {
        document.getElementById('progressDetail').textContent = detail;
    }
    
    // 更新当前处理的视频
    if (currentVideo) {
        document.getElementById('currentVideo').textContent = currentVideo;
    }
}

function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const timeStr = minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;
        document.getElementById('elapsedTime').textContent = `已用时: ${timeStr}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function downloadText(type) {
    const content = type === 'transcript' ? combinedTranscript : aiSummary;
    const filename = type === 'transcript' ? '完整转录.txt' : 'AI摘要.md';
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

async function copyText(type, event) {
    const content = type === 'transcript' ? combinedTranscript : aiSummary;
    
    if (!content || content.trim() === '') {
        alert('没有可复制的内容');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(content);
        
        const button = event.target.closest('button');
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check mr-1"></i>已复制';
        button.classList.add('text-green-600');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('text-green-600');
        }, 2000);
    } catch (err) {
        console.error('复制失败:', err);
        alert('复制失败，请手动复制');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function toggleApiSettings() {
    const modal = document.getElementById('apiModal');
    modal.classList.toggle('hidden');
    
    if (!modal.classList.contains('hidden')) {
        loadApiSettings();
    }
}

async function loadApiSettings() {
    try {
        const response = await fetch('/api/get_config');
        const data = await response.json();
        
        document.getElementById('apiKey').value = data.api_key || '';
        document.getElementById('baseUrl').value = data.base_url || '';
        document.getElementById('defaultModel').value = data.model_name || 'gpt-4o';
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

async function saveApiSettings() {
    const apiKey = document.getElementById('apiKey').value;
    const baseUrl = document.getElementById('baseUrl').value;
    const defaultModel = document.getElementById('defaultModel').value;
    
    try {
        const response = await fetch('/api/save_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: apiKey || undefined,
                base_url: baseUrl,
                model_name: defaultModel
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('设置已保存');
            toggleApiSettings();
            
            // 更新主页面的AI模型选择
            if (defaultModel) {
                const aiModelSelect = document.getElementById('aiModel');
                if (aiModelSelect) {
                    // 检查模型是否在下拉列表中
                    const modelExists = Array.from(aiModelSelect.options).some(option => option.value === defaultModel);
                    
                    if (modelExists) {
                        aiModelSelect.value = defaultModel;
                    } else {
                        // 如果模型不在列表中，添加一个新选项
                        const newOption = document.createElement('option');
                        newOption.value = defaultModel;
                        newOption.textContent = defaultModel;
                        newOption.selected = true;
                        aiModelSelect.appendChild(newOption);
                    }
                }
            }
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

document.getElementById('enableAI').addEventListener('change', (e) => {
    const aiSettings = document.getElementById('aiSettings');
    if (e.target.checked) {
        aiSettings.classList.remove('hidden');
    } else {
        aiSettings.classList.add('hidden');
    }
});
