let uploadedFiles = [];
let combinedTranscript = '';
let aiSummary = '';
let folderName = '';
let customPromptText = ''; // 从 API配置中加载
let mergeOutput = true; // 输出方式：合并 or 分开
window.linkDownloadedVideos = window.linkDownloadedVideos || {};

// 输出方式切换
function setOutputMode(mode) {
    mergeOutput = (mode === 'merge');
    const mergeBtn = document.getElementById('mergeBtn');
    const splitBtn = document.getElementById('splitBtn');
    if (mergeOutput) {
        mergeBtn.className = 'flex-1 py-2 font-medium bg-indigo-600 text-white transition-colors';
        splitBtn.className = 'flex-1 py-2 font-medium bg-white text-gray-700 hover:bg-gray-50 transition-colors';
    } else {
        mergeBtn.className = 'flex-1 py-2 font-medium bg-white text-gray-700 hover:bg-gray-50 transition-colors';
        splitBtn.className = 'flex-1 py-2 font-medium bg-indigo-600 text-white transition-colors';
    }
}

// 处理模式切换
function toggleProcessingMode() {
    const mode = document.getElementById('processingMode').value;
    const whisperSettings = document.getElementById('whisperSettings');
    const ocrSettings = document.getElementById('ocrSettings');
    const hybridSettings = document.getElementById('hybridSettings');

    // 先全部隐藏
    whisperSettings.classList.add('hidden');
    ocrSettings.classList.add('hidden');
    hybridSettings.classList.add('hidden');

    if (mode === 'ocr') {
        ocrSettings.classList.remove('hidden');
    } else if (mode === 'hybrid') {
        // 混合模式：显示 Whisper 设置（可调模型/语言）+ 混合说明
        whisperSettings.classList.remove('hidden');
        hybridSettings.classList.remove('hidden');
    } else {
        // auto / whisper
        whisperSettings.classList.remove('hidden');
    }
}

// 默认提示词（仅用于后端，前端从API配置读取）
// 注意：不含 {transcript} 占位符，后端会自动追加转录内容
const DEFAULT_PROMPT = `# Role
你是一位精通多领域知识建模的"深度内容架构师"。你的任务是将视频转录文本（ASR）加工成一份逻辑严密、细节丰满、且具备极高可读性的 Markdown 深度笔记。

# Core Objective
**信息无损还原**：让从未看过原视频的读者，通过阅读本文档，能完全掌握视频中的核心逻辑、具体方法论、生动案例以及所有的关键细节，严禁过度简化。

# Task Goals
1. **拒绝干条目**：不仅记录结论，更要保留得出结论的推导过程、背景原因、以及博主使用的类比和例子。
2. **场景与细节复刻**：保留视频中提及的具体参数（如数值、设置）、具体话术（如交友/职场沟通）、以及具体的合规/避坑细节。
3. **结构化重组**：打破零散的口语顺序，按照最符合认知逻辑的结构重新组织内容。

# Processing Logic (Adaptive)
请根据输入内容的本质属性，自动匹配最佳逻辑框架：

1. **【决策/合规/策略类】（侧重逻辑与方案）**：
   - 框架：背景趋势 -> 核心痛点/风险分析 -> 深度解决方案（分点详述） -> 实施建议/风险规避。
2. **【理论/体系/心理类】（侧重概念与理解）**：
   - 框架：核心概念界定 -> 底层原理/逻辑拆解（保留生动类比） -> 现实应用场景 -> 认知升级/延伸思考。
3. **【技能/实操/方法类】（侧重动作与流程）**：
   - 框架：目标设定 -> 详细分步拆解（含操作要点） -> 关键细节/常见错误 -> 进阶技巧/复盘建议。
4. **【观点/启发/思维类】（侧重洞察与改变）**：
   - 框架：现状观察/痛点挖掘 -> 核心思维转折点 -> 行动指南/具体建议 -> 价值升华/金句提炼。

# Content Requirements (Rich & Descriptive)
- **多级标题**：严禁结构扁平。必须根据内容复杂度灵活使用 \`##\`, \`###\`, 甚至 \`####\` 来构建知识索引。
- **案例扩充**：若视频中提到案例、实验或故事，请详细描述其过程、转折和结论，使其具备"故事性"和"说服力"。
- **解释性写作**：保留博主对专业术语的通俗化解释，确保文档对"门外汉"友好。
- **模块化总结**：在每一个二级标题（##）的末尾，添加一个引用块：
  > **💡 核心萃取：** [用一句话提炼本章节的底层逻辑或核心价值，必须具备启发性]

# Tone & Style
- 风格：客观、详尽、富有条理。
- 目标：将"碎片化的口语"转化为"系统化的书面知识体系"。`;

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
    const processingMode = document.getElementById('processingMode').value;
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
                processing_mode: processingMode,
                model_size: modelSize,
                whisper_language: whisperLanguage,
                model_alias: modelAlias,
                custom_prompt: customPromptText,
                enable_ai_summary: enableAI,
                merge_output: mergeOutput
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

            const splitSummarySection = document.getElementById('splitSummarySection');

            if (enableAI && (data.ai_summary || data.individual_results)) {
                addLog('═'.repeat(50), 'header');
                addLog('🤖 AI 整理完成', 'header');

                updateProgress(75, '🤖 AI 智能整理', `使用 ${modelAlias} 模型生成摘要...`, '正在分析转录内容');
                await new Promise(resolve => setTimeout(resolve, 500));
                updateProgress(85, '🤖 AI 处理中', '生成章节标题和要点提取...', '优化文档结构和格式');

                if (data.individual_results) {
                    // 分开模式：渲染多张摘要卡片
                    summarySection.classList.add('hidden');
                    splitSummarySection.innerHTML = data.individual_results.map((item, idx) => `
                        <div class="bg-white rounded-2xl shadow-xl p-6">
                            <div class="flex justify-between items-center mb-3">
                                <h3 class="text-base font-semibold text-gray-800">
                                    <i class="fas fa-film mr-2 text-indigo-500"></i>
                                    <span class="text-indigo-600 mr-2">[${idx + 1}]</span>${item.name}
                                </h3>
                                <div class="flex space-x-2">
                                    <button onclick="copySplitSummary(${idx}, event)" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                                        <i class="fas fa-copy mr-1"></i>复制
                                    </button>
                                    <button onclick="downloadSplitSummary(${idx}, '${item.name}')" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                                        <i class="fas fa-download mr-1"></i>下载
                                    </button>
                                </div>
                            </div>
                            <div class="prose max-w-none bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto split-summary-content">
                                ${marked.parse(item.ai_summary || '\u65e0内容')}
                            </div>
                        </div>
                    `).join('');
                    splitSummarySection.classList.remove('hidden');
                    // 保存到全局以供复制/下载使用
                    window._splitResults = data.individual_results;
                    addLog(`✓ ${data.individual_results.length} 个视频摄要分别生成完成`, 'success');
                } else {
                    // 合并模式：单一摘要
                    splitSummarySection.classList.add('hidden');
                    aiSummary = data.ai_summary;
                    summaryResult.innerHTML = marked.parse(aiSummary);
                    summarySection.classList.remove('hidden');
                    addLog(`✓ AI 摘要生成完成，共 ${data.ai_summary.length} 字符`, 'success');
                }

                updateProgress(95, '✓ AI 摘要完成', '文档整理和格式化已完成', '准备展示结果');
            } else {
                summarySection.classList.add('hidden');
                splitSummarySection.classList.add('hidden');
                updateProgress(90, '⏭️ 跳过 AI 整理', '已禁用 AI 摘要功能', '准备展示转录结果');
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

function downloadSplitSummary(idx, name) {
    const results = window._splitResults;
    if (!results || !results[idx]) return;
    const content = results[idx].ai_summary || '';
    const safeName = name.replace(/[\\/:*?"<>|]/g, '_').replace(/\.[^.]+$/, '');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AI摘要_${safeName}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

async function copySplitSummary(idx, event) {
    const results = window._splitResults;
    if (!results || !results[idx]) return;
    const content = results[idx].ai_summary || '';
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
        alert('复制失败，请手动复制');
    }
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
        // 获取当前选中的AI模型
        const currentModel = document.getElementById('aiModel').value;
        
        // 从多模型配置中查找该模型
        const modelsResponse = await fetch('/api/models/list');
        const modelsData = await modelsResponse.json();
        
        if (modelsData.success && modelsData.models) {
            // 尝试找到匹配的模型配置（通过model_name匹配）
            const matchedModel = modelsData.models.find(m => m.model_name === currentModel);
            
            if (matchedModel) {
                // 使用找到的模型配置
                document.getElementById('apiKey').value = matchedModel.api_key || '';
                document.getElementById('baseUrl').value = matchedModel.base_url || '';
                // 显示模型名称（model_name字段）
                document.getElementById('defaultModel').value = matchedModel.model_name || currentModel;
            } else {
                // 如果没找到，使用默认API配置
                const response = await fetch('/api/get_config');
                const data = await response.json();
                
                document.getElementById('apiKey').value = data.api_key || '';
                document.getElementById('baseUrl').value = data.base_url || '';
                document.getElementById('defaultModel').value = data.model_name || currentModel;
            }
        } else {
            // 如果多模型配置加载失败，使用默认API配置
            const response = await fetch('/api/get_config');
            const data = await response.json();
            
            document.getElementById('apiKey').value = data.api_key || '';
            document.getElementById('baseUrl').value = data.base_url || '';
            document.getElementById('defaultModel').value = data.model_name || currentModel;
        }
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

// 隐藏测试结果
function hideTestResult() {
    document.getElementById('connectionTestResult').classList.add('hidden');
}

// 显示测试结果
function showTestResult(message, isSuccess) {
    const resultDiv = document.getElementById('connectionTestResult');
    const resultText = document.getElementById('testResultText');
    const resultIcon = document.getElementById('testResultIcon');
    const container = resultDiv.querySelector('div');
    
    resultText.textContent = message;
    
    // 重置样式
    container.className = 'p-4 rounded-lg border-l-4 flex items-center justify-between';
    resultIcon.className = 'fas mr-3 text-xl';
    
    if (isSuccess) {
        container.classList.add('bg-green-50', 'border-green-500', 'text-green-800');
        resultIcon.classList.add('fa-check-circle', 'text-green-600');
    } else {
        container.classList.add('bg-red-50', 'border-red-500', 'text-red-800');
        resultIcon.classList.add('fa-exclamation-circle', 'text-red-600');
    }
    
    resultDiv.classList.remove('hidden');
}

// 连通性测试函数
async function testApiConnection() {
    const testBtn = document.getElementById('testConnectionBtn');
    const originalHTML = testBtn.innerHTML;
    
    // 隐藏之前的测试结果
    hideTestResult();
    
    // 显示加载状态
    testBtn.disabled = true;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>测试中...';
    
    try {
        const response = await fetch('/api/test_connection');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showTestResult(
                `✓ 连接测试成功！Base URL: ${data.base_url} | 模型: ${data.model}`,
                true
            );
        } else {
            showTestResult(`✗ 连接测试失败：${data.error}`, false);
        }
    } catch (error) {
        console.error('连接测试错误:', error);
        showTestResult(`✗ 连接测试失败：${error.message}`, false);
    } finally {
        // 恢复按钮状态
        testBtn.disabled = false;
        testBtn.innerHTML = originalHTML;
    }
}

// 停止服务器
async function shutdownServer() {
    if (!confirm('确定要停止服务器吗？\n\n停止后需要重新启动才能使用。')) {
        return;
    }
    
    try {
        const response = await fetch('/shutdown', {
            method: 'POST'
        });
        
        if (response.ok) {
            // 显示提示信息
            alert('服务器正在关闭...\n\n页面将在3秒后自动关闭');
            
            // 3秒后关闭页面
            setTimeout(() => {
                window.close();
                // 如果无法关闭窗口，显示提示
                setTimeout(() => {
                    document.body.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: linear-gradient(to br, #EEF2FF, #E0E7FF);">
                            <div style="text-align: center; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);">
                                <i class="fas fa-check-circle" style="font-size: 64px; color: #10B981; margin-bottom: 20px;"></i>
                                <h1 style="font-size: 24px; color: #1F2937; margin-bottom: 10px;">服务器已停止</h1>
                                <p style="color: #6B7280; margin-bottom: 20px;">您可以关闭此页面了</p>
                                <p style="color: #9CA3AF; font-size: 14px;">要重新启动，请双击"启动服务（后台）.command"</p>
                            </div>
                        </div>
                    `;
                }, 100);
            }, 3000);
        } else {
            alert('停止服务器失败');
        }
    } catch (error) {
        console.error('停止服务器错误:', error);
        alert('停止服务器失败：' + error.message);
    }
}

// ==================== 文本总结功能 ====================
let docFiles = [];          // 上传的原始 File 对象
let docExtracted = [];      // [{name, text, charCount, status, error}]
let docMergeMode = true;
let docSummaryText = '';    // 合并模式的结果
let docSplitSummaries = []; // 分开模式的结果 [{name, summary}]
let docProcessing = false;

// 初始化文档上传区
document.addEventListener('DOMContentLoaded', function() {
    const docDrop = document.getElementById('docDropZone');
    const docInput = document.getElementById('docFileInput');
    if (!docDrop || !docInput) return;

    docDrop.addEventListener('click', () => docInput.click());
    docInput.addEventListener('change', (e) => handleDocFiles(Array.from(e.target.files)));

    docDrop.addEventListener('dragover', (e) => {
        e.preventDefault();
        docDrop.classList.add('border-indigo-500', 'bg-indigo-50');
    });
    docDrop.addEventListener('dragleave', () => {
        docDrop.classList.remove('border-indigo-500', 'bg-indigo-50');
    });
    docDrop.addEventListener('drop', (e) => {
        e.preventDefault();
        docDrop.classList.remove('border-indigo-500', 'bg-indigo-50');
        handleDocFiles(Array.from(e.dataTransfer.files));
    });

    // 加载模型列表到 docAiModel
    loadDocModelList();
});

async function loadDocModelList() {
    try {
        const resp = await fetch('/api/models/list');
        if (!resp.ok) return;
        const data = await resp.json();
        const sel = document.getElementById('docAiModel');
        if (!sel || !data.models) return;
        data.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.alias;
            opt.textContent = `${m.alias} (${m.model_name})`;
            sel.appendChild(opt);
        });
    } catch(e) { console.error('加载模型列表失败:', e); }
}

function handleDocFiles(files) {
    const allowedExts = ['pdf', 'doc', 'docx', 'md', 'txt'];
    files.forEach(f => {
        const ext = f.name.split('.').pop().toLowerCase();
        if (allowedExts.includes(ext)) docFiles.push(f);
    });
    updateDocFileList();
    updateDocStats();
    document.getElementById('docSummaryBtn').disabled = docFiles.length === 0;
}

function getDocIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    switch(ext) {
        case 'pdf': return '<i class="fas fa-file-pdf text-red-500"></i>';
        case 'doc': case 'docx': return '<i class="fas fa-file-word text-blue-500"></i>';
        case 'md': return '<i class="fab fa-markdown text-gray-600"></i>';
        default: return '<i class="fas fa-file-alt text-gray-500"></i>';
    }
}

function updateDocFileList() {
    const list = document.getElementById('docFileList');
    const count = document.getElementById('docFileCount');
    count.textContent = `(${docFiles.length} \u4e2a\u6587\u4ef6)`;

    if (docFiles.length === 0) {
        list.innerHTML = '<div class="text-center py-8 text-gray-400"><i class="fas fa-inbox text-4xl mb-2"></i><p class="text-sm">\u6682\u65e0\u6587\u6863\uff0c\u8bf7\u4e0a\u4f20\u6587\u4ef6</p></div>';
        return;
    }

    list.innerHTML = docFiles.map((file, idx) => {
        const ex = docExtracted.find(d => d.fileIndex === idx);
        const status = ex ? ex.status : 'pending';
        let statusIcon = '<i class="fas fa-clock text-gray-400"></i>';
        let bg = 'bg-gray-50';
        if (status === 'extracted') { statusIcon = '<i class="fas fa-check-circle text-green-500"></i>'; bg = 'bg-green-50 border border-green-200'; }
        else if (status === 'failed') { statusIcon = '<i class="fas fa-exclamation-circle text-red-500"></i>'; bg = 'bg-red-50 border border-red-200'; }
        else if (status === 'summarizing') { statusIcon = '<i class="fas fa-spinner fa-spin text-blue-500"></i>'; bg = 'bg-blue-50 border border-blue-200'; }

        let errorHtml = (status === 'failed' && ex && ex.error) ? `<p class="text-xs text-red-500 mt-1 truncate" title="${ex.error}">${ex.error}</p>` : '';
        let charInfo = (ex && ex.charCount) ? `<span class="text-xs text-green-600 ml-2">${ex.charCount} \u5b57\u7b26</span>` : '';
        let removeBtn = !docProcessing ? `<button onclick="removeDocFile(${idx})" class="ml-2 text-red-500 hover:text-red-700" title="\u5220\u9664"><i class="fas fa-times"></i></button>` : '';

        return `<div class="flex items-center justify-between p-3 ${bg} rounded-lg transition-colors">
            <div class="flex items-center flex-1 min-w-0">
                <span class="mr-3 text-lg flex-shrink-0">${statusIcon}</span>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-800 truncate">${getDocIcon(file.name)} ${file.name} ${charInfo}</p>
                    <p class="text-xs text-gray-500">${(file.size / 1024).toFixed(1)} KB</p>
                    ${errorHtml}
                </div>
            </div>
            <div class="flex items-center flex-shrink-0">${removeBtn}</div>
        </div>`;
    }).join('');
}

function removeDocFile(idx) {
    const exIdx = docExtracted.findIndex(d => d.fileIndex === idx);
    if (exIdx !== -1) docExtracted.splice(exIdx, 1);
    docFiles.splice(idx, 1);
    docExtracted.forEach(d => { if (d.fileIndex > idx) d.fileIndex--; });
    updateDocFileList();
    updateDocStats();
    document.getElementById('docSummaryBtn').disabled = docFiles.length === 0;
}

function clearAllDocs() {
    if (docFiles.length === 0) return;
    if (!confirm('\u786e\u5b9a\u8981\u6e05\u7a7a\u6240\u6709\u6587\u6863\u5417\uff1f')) return;
    docFiles = [];
    docExtracted = [];
    docSummaryText = '';
    docSplitSummaries = [];
    updateDocFileList();
    updateDocStats();
    document.getElementById('docSummaryBtn').disabled = true;
    document.getElementById('docResultSection').classList.add('hidden');
}

function setDocOutputMode(mode) {
    docMergeMode = (mode === 'merge');
    const mb = document.getElementById('docMergeBtn');
    const sb = document.getElementById('docSplitBtn');
    if (docMergeMode) {
        mb.className = 'flex-1 py-2 font-medium bg-indigo-600 text-white transition-colors text-sm';
        sb.className = 'flex-1 py-2 font-medium bg-white text-gray-700 hover:bg-gray-50 transition-colors text-sm';
    } else {
        mb.className = 'flex-1 py-2 font-medium bg-white text-gray-700 hover:bg-gray-50 transition-colors text-sm';
        sb.className = 'flex-1 py-2 font-medium bg-indigo-600 text-white transition-colors text-sm';
    }
}

function updateDocStats() {
    const total = docFiles.length;
    const extracted = docExtracted.filter(d => d.status === 'extracted').length;
    const failed = docExtracted.filter(d => d.status === 'failed').length;
    const chars = docExtracted.filter(d => d.status === 'extracted').reduce((s, d) => s + (d.charCount || 0), 0);

    document.getElementById('docStatTotal').textContent = total;
    document.getElementById('docStatExtracted').textContent = extracted;
    document.getElementById('docStatChars').textContent = chars.toLocaleString();
    document.getElementById('docStatFailed').textContent = failed;

    const bar = document.getElementById('docProgressBar');
    const txt = document.getElementById('docProgressText');
    if (bar && total > 0) {
        const pct = Math.round(((extracted + failed) / total) * 100);
        bar.style.width = pct + '%';
        bar.className = 'h-full rounded-full transition-all duration-300 ' +
            (failed > 0 && extracted === 0 ? 'bg-red-500' : failed > 0 ? 'bg-yellow-500' : 'bg-green-500');
        if (txt) txt.textContent = `${extracted + failed} / ${total}` + (failed > 0 ? ` (${failed} \u5931\u8d25)` : '');
    } else if (bar) {
        bar.style.width = '0%';
        if (txt) txt.textContent = '';
    }
}

// ── 文档日志 SSE ──
let docEventSource = null;

function connectDocLogStream() {
    if (docEventSource) docEventSource.close();
    const logSection = document.getElementById('docLogSection');
    logSection.classList.remove('hidden');

    docEventSource = new EventSource('/api/text_summary/stream_logs');
    docEventSource.onmessage = function(event) {
        const log = JSON.parse(event.data);
        addDocLog(log.message, log.type);
    };
    docEventSource.onerror = function() {
        if (docEventSource) { docEventSource.close(); docEventSource = null; }
    };
}

function disconnectDocLogStream() {
    if (docEventSource) { docEventSource.close(); docEventSource = null; }
}

function addDocLog(message, type) {
    const container = document.getElementById('docLogContainer');
    const line = document.createElement('div');
    line.className = 'py-0.5';

    const colors = {
        'header': 'text-yellow-400 font-bold',
        'success': 'text-green-400',
        'error': 'text-red-400',
        'warning': 'text-yellow-300',
        'info': 'text-gray-300'
    };
    line.innerHTML = `<span class="${colors[type] || colors.info}">${message}</span>`;
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
}

function clearDocLog() {
    document.getElementById('docLogContainer').innerHTML = '';
}

async function startDocSummary() {
    if (docFiles.length === 0) return;

    docProcessing = true;
    const btn = document.getElementById('docSummaryBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>\u4e0a\u4f20\u6587\u6863\u4e2d...';

    // Show & clear log
    clearDocLog();
    document.getElementById('docLogSection').classList.remove('hidden');

    // Step 1: Upload all files to extract text
    const extractMode = document.getElementById('docExtractMode').value;
    addDocLog(`\u{1F4E4} \u5F00\u59CB\u4E0A\u4F20\u6587\u6863... (\u63D0\u53D6\u65B9\u5F0F: ${extractMode})`, 'info');
    const formData = new FormData();
    docFiles.forEach(f => formData.append('files', f));
    formData.append('extract_mode', extractMode);

    try {
        const uploadResp = await fetch('/api/text_summary/upload', {
            method: 'POST',
            body: formData
        });
        const uploadData = await uploadResp.json();
        if (!uploadData.success) {
            addDocLog('\u274C \u4E0A\u4F20\u5931\u8D25: ' + (uploadData.error || ''), 'error');
            alert('\u4e0a\u4f20\u5931\u8d25: ' + (uploadData.error || '\u672a\u77e5\u9519\u8bef'));
            resetDocBtn();
            return;
        }

        // Update extracted status
        docExtracted = [];
        uploadData.files.forEach((f, i) => {
            docExtracted.push({
                fileIndex: i,
                name: f.name,
                text: f.text || '',
                charCount: f.char_count || 0,
                status: f.success ? 'extracted' : 'failed',
                error: f.error || null
            });
            if (f.success) {
                addDocLog(`\u2713 ${f.name} \u2014 ${f.char_count} \u5B57\u7B26`, 'success');
            } else {
                addDocLog(`\u274C ${f.name} \u2014 ${f.error || '\u63D0\u53D6\u5931\u8D25'}`, 'error');
            }
        });
        addDocLog(`\u{1F4CA} \u6587\u672C\u63D0\u53D6\u5B8C\u6210\uFF1A\u6210\u529F ${uploadData.succeeded} / \u5931\u8D25 ${uploadData.failed}`, 'info');
        updateDocFileList();
        updateDocStats();

        const successDocs = docExtracted.filter(d => d.status === 'extracted');
        if (successDocs.length === 0) {
            addDocLog('\u274C \u6240\u6709\u6587\u6863\u63D0\u53D6\u5931\u8D25\uFF0C\u65E0\u6CD5\u7EE7\u7EED', 'error');
            alert('\u6240\u6709\u6587\u6863\u63d0\u53d6\u5931\u8d25\uff0c\u65e0\u6cd5\u7ee7\u7eed');
            resetDocBtn();
            return;
        }

        // Step 2: Connect log stream, then call AI
        btn.innerHTML = '<i class="fas fa-brain fa-spin mr-2"></i>AI \u6574\u7406\u4e2d...';
        connectDocLogStream();

        const modelAlias = document.getElementById('docAiModel').value;
        const sumResp = await fetch('/api/text_summary/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                documents: successDocs.map(d => ({ name: d.name, text: d.text })),
                model_alias: modelAlias,
                custom_prompt: customPromptText,
                merge: docMergeMode
            })
        });
        const sumData = await sumResp.json();
        disconnectDocLogStream();

        if (!sumData.success) {
            addDocLog('\u274C AI \u5904\u7406\u5931\u8D25: ' + (sumData.error || ''), 'error');
            alert('AI \u5904\u7406\u5931\u8d25: ' + (sumData.error || '\u672a\u77e5\u9519\u8bef'));
            resetDocBtn();
            return;
        }

        // Step 3: Show results
        const resultSection = document.getElementById('docResultSection');
        const mergedDiv = document.getElementById('docMergedResult');
        const splitDiv = document.getElementById('docSplitResults');

        resultSection.classList.remove('hidden');

        if (sumData.mode === 'merge') {
            docSummaryText = sumData.summary;
            document.getElementById('docMergedContent').innerHTML = marked.parse(docSummaryText);
            mergedDiv.classList.remove('hidden');
            splitDiv.classList.add('hidden');
        } else {
            docSplitSummaries = sumData.results;
            mergedDiv.classList.add('hidden');
            splitDiv.innerHTML = sumData.results.map((item, idx) => `
                <div class="bg-white rounded-2xl shadow-xl p-6">
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="text-base font-semibold text-gray-800">
                            <i class="fas fa-file-alt mr-2 text-indigo-500"></i>
                            <span class="text-indigo-600 mr-2">[${idx+1}]</span>${item.name}
                        </h3>
                        <div class="flex space-x-2">
                            <button onclick="copyDocSplitSummary(${idx}, event)" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                                <i class="fas fa-copy mr-1"></i>\u590d\u5236
                            </button>
                            <button onclick="downloadDocSplitSummary(${idx})" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                                <i class="fas fa-download mr-1"></i>\u4e0b\u8f7d
                            </button>
                        </div>
                    </div>
                    <div class="prose max-w-none bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto text-sm">
                        ${item.success ? marked.parse(item.summary) : '<p class="text-red-500">\u5904\u7406\u5931\u8d25: ' + (item.error || '') + '</p>'}
                    </div>
                </div>
            `).join('');
            splitDiv.classList.remove('hidden');
        }

        // Update progress to 100%
        const bar = document.getElementById('docProgressBar');
        bar.style.width = '100%';
        bar.className = 'h-full rounded-full transition-all duration-300 bg-green-500';
        document.getElementById('docProgressText').textContent = '\u5b8c\u6210';

    } catch (error) {
        disconnectDocLogStream();
        console.error('\u6587\u672c\u603b\u7ed3\u5931\u8d25:', error);
        addDocLog('\u274C \u5904\u7406\u5931\u8D25: ' + error.message, 'error');
        alert('\u5904\u7406\u5931\u8d25: ' + error.message);
    }

    resetDocBtn();
}

function resetDocBtn() {
    docProcessing = false;
    const btn = document.getElementById('docSummaryBtn');
    btn.disabled = docFiles.length === 0;
    btn.innerHTML = '<i class="fas fa-brain mr-2"></i>\u5f00\u59cb\u603b\u7ed3';
}

async function copyDocSummary(event) {
    if (!docSummaryText) return;
    try {
        await navigator.clipboard.writeText(docSummaryText);
        const button = event.target.closest('button');
        const orig = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check mr-1"></i>\u5df2\u590d\u5236';
        button.classList.add('text-green-600');
        setTimeout(() => { button.innerHTML = orig; button.classList.remove('text-green-600'); }, 2000);
    } catch(e) { alert('\u590d\u5236\u5931\u8d25'); }
}

function downloadDocSummary() {
    if (!docSummaryText) return;
    const blob = new Blob([docSummaryText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'AI\u6587\u6863\u603b\u7ed3.md';
    a.click();
    URL.revokeObjectURL(url);
}

async function copyDocSplitSummary(idx, event) {
    if (!docSplitSummaries[idx] || !docSplitSummaries[idx].summary) return;
    try {
        await navigator.clipboard.writeText(docSplitSummaries[idx].summary);
        const button = event.target.closest('button');
        const orig = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check mr-1"></i>\u5df2\u590d\u5236';
        button.classList.add('text-green-600');
        setTimeout(() => { button.innerHTML = orig; button.classList.remove('text-green-600'); }, 2000);
    } catch(e) { alert('\u590d\u5236\u5931\u8d25'); }
}

function downloadDocSplitSummary(idx) {
    if (!docSplitSummaries[idx] || !docSplitSummaries[idx].summary) return;
    const item = docSplitSummaries[idx];
    const safeName = item.name.replace(/[\\/:*?"<>|]/g, '_').replace(/\.[^.]+$/, '');
    const blob = new Blob([item.summary], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AI\u603b\u7ed3_${safeName}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

// ==================== TAB 切换功能 ====================
function switchTab(tabName) {
    const videoTab = document.getElementById('videoTab');
    const audioTab = document.getElementById('audioTab');
    const linkTab = document.getElementById('linkTab');
    const textSummaryTab = document.getElementById('textSummaryTab');
    const videoContent = document.getElementById('videoTabContent');
    const audioContent = document.getElementById('audioTabContent');
    const linkContent = document.getElementById('linkTabContent');
    const textSummaryContent = document.getElementById('textSummaryTabContent');

    // 重置所有TAB样式
    [videoTab, audioTab, linkTab, textSummaryTab].forEach(tab => {
        tab.classList.remove('border-indigo-600', 'text-indigo-600');
        tab.classList.add('border-transparent', 'text-gray-600');
    });

    // 隐藏所有内容
    [videoContent, audioContent, linkContent, textSummaryContent].forEach(content => {
        content.classList.add('hidden');
    });

    // 激活选中的TAB
    if (tabName === 'video') {
        videoTab.classList.add('border-indigo-600', 'text-indigo-600');
        videoTab.classList.remove('border-transparent', 'text-gray-600');
        videoContent.classList.remove('hidden');
    } else if (tabName === 'audio') {
        audioTab.classList.add('border-indigo-600', 'text-indigo-600');
        audioTab.classList.remove('border-transparent', 'text-gray-600');
        audioContent.classList.remove('hidden');
    } else if (tabName === 'link') {
        linkTab.classList.add('border-indigo-600', 'text-indigo-600');
        linkTab.classList.remove('border-transparent', 'text-gray-600');
        linkContent.classList.remove('hidden');
    } else if (tabName === 'textSummary') {
        textSummaryTab.classList.add('border-indigo-600', 'text-indigo-600');
        textSummaryTab.classList.remove('border-transparent', 'text-gray-600');
        textSummaryContent.classList.remove('hidden');
    }
}

// ==================== 音频提取功能 ====================
let audioFiles = [];
let extractedAudioFiles = [];
let audioExtractionRunning = false;

// 初始化音频提取功能
document.addEventListener('DOMContentLoaded', function() {
    const audioDropZone = document.getElementById('audioDropZone');
    const audioFileInput = document.getElementById('audioFileInput');
    
    if (audioDropZone && audioFileInput) {
        // 点击上传
        audioDropZone.addEventListener('click', () => audioFileInput.click());
        
        // 文件选择
        audioFileInput.addEventListener('change', (e) => {
            handleAudioFiles(Array.from(e.target.files));
        });
        
        // 拖拽上传
        audioDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            audioDropZone.classList.add('border-indigo-500', 'bg-indigo-50');
        });
        
        audioDropZone.addEventListener('dragleave', () => {
            audioDropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
        });
        
        audioDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            audioDropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
            handleAudioFiles(Array.from(e.dataTransfer.files));
        });
    }
});

function handleAudioFiles(files) {
    const videoExtensions = ['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', 'webm'];
    
    files.forEach(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (videoExtensions.includes(ext)) {
            audioFiles.push(file);
        }
    });
    
    updateAudioFileList();
    updateAudioStats();
}

function getStatusIcon(status) {
    switch (status) {
        case 'pending': return '<i class="fas fa-clock text-gray-400"></i>';
        case 'processing': return '<i class="fas fa-spinner fa-spin text-blue-500"></i>';
        case 'completed': return '<i class="fas fa-check-circle text-green-500"></i>';
        case 'failed': return '<i class="fas fa-exclamation-circle text-red-500"></i>';
        default: return '<i class="fas fa-file-video text-indigo-600"></i>';
    }
}

function getStatusBg(status) {
    switch (status) {
        case 'processing': return 'bg-blue-50 border border-blue-200';
        case 'completed': return 'bg-green-50 border border-green-200';
        case 'failed': return 'bg-red-50 border border-red-200';
        default: return 'bg-gray-50';
    }
}

function updateAudioFileList() {
    const fileList = document.getElementById('audioFileList');
    const fileCount = document.getElementById('audioFileCount');
    
    fileCount.textContent = `(${audioFiles.length} \u4e2a\u6587\u4ef6)`;
    
    if (audioFiles.length === 0) {
        fileList.innerHTML = `
            <div class="text-center py-8 text-gray-400">
                <i class="fas fa-inbox text-4xl mb-2"></i>
                <p class="text-sm">\u6682\u65e0\u6587\u4ef6\uff0c\u8bf7\u4e0a\u4f20\u89c6\u9891</p>
            </div>
        `;
        return;
    }
    
    fileList.innerHTML = audioFiles.map((file, index) => {
        const extracted = extractedAudioFiles.find(f => f.fileIndex === index);
        const status = extracted ? extracted.status : 'pending';
        const statusIcon = getStatusIcon(extracted ? status : null);
        const statusBg = extracted ? getStatusBg(status) : 'bg-gray-50';
        
        let actionBtn = '';
        if (!audioExtractionRunning) {
            if (status === 'failed') {
                actionBtn = `<button onclick="retryAudioFile(${index})" class="ml-2 text-orange-500 hover:text-orange-700 text-xs px-2 py-1 rounded bg-orange-50 hover:bg-orange-100" title="\u91cd\u8bd5"><i class="fas fa-redo"></i></button>`;
            }
            if (!extracted || status === 'failed') {
                actionBtn += `<button onclick="removeAudioFile(${index})" class="ml-2 text-red-500 hover:text-red-700" title="\u5220\u9664"><i class="fas fa-times"></i></button>`;
            }
        }
        
        let errorMsg = '';
        if (status === 'failed' && extracted && extracted.error) {
            errorMsg = `<p class="text-xs text-red-500 mt-1 truncate" title="${extracted.error}">${extracted.error}</p>`;
        }
        
        return `
        <div class="flex items-center justify-between p-3 ${statusBg} rounded-lg transition-colors">
            <div class="flex items-center flex-1 min-w-0">
                <span class="mr-3 text-lg flex-shrink-0">${statusIcon}</span>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-800 truncate">${file.name}</p>
                    <p class="text-xs text-gray-500">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    ${errorMsg}
                </div>
            </div>
            <div class="flex items-center flex-shrink-0">
                ${actionBtn}
            </div>
        </div>`;
    }).join('');
}

function removeAudioFile(index) {
    const extractedIdx = extractedAudioFiles.findIndex(f => f.fileIndex === index);
    if (extractedIdx !== -1) {
        extractedAudioFiles.splice(extractedIdx, 1);
    }
    audioFiles.splice(index, 1);
    // reindex extractedAudioFiles
    extractedAudioFiles.forEach(f => {
        if (f.fileIndex > index) f.fileIndex--;
    });
    updateAudioFileList();
    updateAudioStats();
    updateOutputFilesList();
}

function clearAllAudioFiles() {
    if (audioFiles.length === 0) return;
    if (confirm('\u786e\u5b9a\u8981\u6e05\u7a7a\u6240\u6709\u6587\u4ef6\u5417\uff1f')) {
        audioFiles = [];
        extractedAudioFiles = [];
        updateAudioFileList();
        updateAudioStats();
        updateOutputFilesList();
        document.getElementById('downloadAllBtn').disabled = true;
    }
}

function updateAudioStats() {
    document.getElementById('statTotal').textContent = audioFiles.length;
    const completed = extractedAudioFiles.filter(f => f.status === 'completed').length;
    const processing = extractedAudioFiles.filter(f => f.status === 'processing').length;
    const failed = extractedAudioFiles.filter(f => f.status === 'failed').length;
    const pending = audioFiles.length - extractedAudioFiles.length + extractedAudioFiles.filter(f => f.status === 'pending').length;
    
    document.getElementById('statCompleted').textContent = completed;
    document.getElementById('statProcessing').textContent = processing;
    document.getElementById('statFailed').textContent = failed;
    
    // 更新进度条
    const progressBar = document.getElementById('audioProgressBar');
    const progressText = document.getElementById('audioProgressText');
    if (progressBar && audioFiles.length > 0) {
        const percent = Math.round(((completed + failed) / audioFiles.length) * 100);
        progressBar.style.width = percent + '%';
        progressBar.className = 'h-full rounded-full transition-all duration-300 ' + 
            (failed > 0 && completed === 0 ? 'bg-red-500' : 
             failed > 0 ? 'bg-yellow-500' : 'bg-green-500');
        if (progressText) {
            progressText.textContent = `${completed + failed} / ${audioFiles.length}` + 
                (failed > 0 ? ` (${failed} \u5931\u8d25)` : '');
        }
    } else if (progressBar) {
        progressBar.style.width = '0%';
        if (progressText) progressText.textContent = '';
    }
}

async function extractSingleFile(fileIndex) {
    const file = audioFiles[fileIndex];
    const format = document.getElementById('outputFormat').value;
    const bitrate = document.getElementById('bitrate').value;
    const sampleRate = document.getElementById('sampleRate').value;
    
    let fileInfo = extractedAudioFiles.find(f => f.fileIndex === fileIndex);
    if (!fileInfo) {
        fileInfo = {
            fileIndex: fileIndex,
            name: file.name,
            status: 'processing',
            outputUrl: null,
            outputName: null,
            error: null
        };
        extractedAudioFiles.push(fileInfo);
    } else {
        fileInfo.status = 'processing';
        fileInfo.error = null;
    }
    
    updateAudioFileList();
    updateAudioStats();
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', format);
        formData.append('bitrate', bitrate);
        formData.append('sample_rate', sampleRate);
        
        const response = await fetch('/api/audio/extract_file', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                fileInfo.status = 'completed';
                fileInfo.outputUrl = data.download_url;
                fileInfo.outputName = data.filename;
            } else {
                fileInfo.status = 'failed';
                fileInfo.error = data.error || '\u63d0\u53d6\u5931\u8d25';
            }
        } else {
            let errMsg = `HTTP ${response.status}`;
            try {
                const errData = await response.json();
                errMsg = errData.error || errMsg;
            } catch(e) {}
            fileInfo.status = 'failed';
            fileInfo.error = errMsg;
        }
    } catch (error) {
        console.error('\u63d0\u53d6\u5931\u8d25:', error);
        fileInfo.status = 'failed';
        fileInfo.error = error.message || '\u7f51\u7edc\u9519\u8bef';
    }
    
    updateAudioFileList();
    updateAudioStats();
    updateOutputFilesList();
}

async function startAudioExtraction() {
    if (audioFiles.length === 0) {
        alert('\u8bf7\u5148\u4e0a\u4f20\u89c6\u9891\u6587\u4ef6');
        return;
    }
    
    audioExtractionRunning = true;
    const extractBtn = document.getElementById('extractBtn');
    extractBtn.disabled = true;
    extractBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>\u5904\u7406\u4e2d...';
    document.getElementById('downloadAllBtn').disabled = true;
    
    // 找出需要处理的文件（未处理或失败的）
    const toProcess = [];
    for (let i = 0; i < audioFiles.length; i++) {
        const existing = extractedAudioFiles.find(f => f.fileIndex === i);
        if (!existing || existing.status === 'failed') {
            toProcess.push(i);
        }
    }
    
    for (let j = 0; j < toProcess.length; j++) {
        extractBtn.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>${j + 1} / ${toProcess.length}`;
        await extractSingleFile(toProcess[j]);
    }
    
    audioExtractionRunning = false;
    extractBtn.disabled = false;
    
    const failed = extractedAudioFiles.filter(f => f.status === 'failed').length;
    const completed = extractedAudioFiles.filter(f => f.status === 'completed').length;
    
    if (failed > 0) {
        extractBtn.innerHTML = `<i class="fas fa-redo mr-2"></i>\u91cd\u8bd5\u5931\u8d25\u9879 (${failed})`;
    } else {
        extractBtn.innerHTML = '<i class="fas fa-play mr-2"></i>\u5f00\u59cb\u63d0\u53d6';
    }
    
    document.getElementById('downloadAllBtn').disabled = completed === 0;
}

async function retryAudioFile(fileIndex) {
    audioExtractionRunning = true;
    const extractBtn = document.getElementById('extractBtn');
    extractBtn.disabled = true;
    extractBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>\u91cd\u8bd5\u4e2d...';
    
    await extractSingleFile(fileIndex);
    
    audioExtractionRunning = false;
    extractBtn.disabled = false;
    
    const failed = extractedAudioFiles.filter(f => f.status === 'failed').length;
    const completed = extractedAudioFiles.filter(f => f.status === 'completed').length;
    
    if (failed > 0) {
        extractBtn.innerHTML = `<i class="fas fa-redo mr-2"></i>\u91cd\u8bd5\u5931\u8d25\u9879 (${failed})`;
    } else {
        extractBtn.innerHTML = '<i class="fas fa-play mr-2"></i>\u5f00\u59cb\u63d0\u53d6';
    }
    document.getElementById('downloadAllBtn').disabled = completed === 0;
}

function updateOutputFilesList() {
    const outputList = document.getElementById('outputFilesList');
    const completed = extractedAudioFiles.filter(f => f.status === 'completed');
    
    if (completed.length === 0) {
        outputList.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">\u6682\u65e0\u8f93\u51fa\u6587\u4ef6</p>';
        return;
    }
    
    outputList.innerHTML = completed.map(file => `
        <div class="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100">
            <div class="flex items-center flex-1 min-w-0">
                <i class="fas fa-file-audio text-green-600 mr-2"></i>
                <span class="text-sm text-gray-700 truncate">${file.outputName}</span>
            </div>
            <a href="${file.outputUrl}" download class="ml-2 text-indigo-600 hover:text-indigo-800">
                <i class="fas fa-download"></i>
            </a>
        </div>
    `).join('');
}

async function downloadAllAudio() {
    const completed = extractedAudioFiles.filter(f => f.status === 'completed');
    if (completed.length === 0) {
        alert('\u6ca1\u6709\u53ef\u4e0b\u8f7d\u7684\u6587\u4ef6');
        return;
    }
    
    const btn = document.getElementById('downloadAllBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>\u6253\u5305\u4e2d...';
    
    try {
        const filenames = completed.map(f => f.outputName);
        const response = await fetch('/api/audio/download_zip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filenames })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'audio_files.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else {
            let errMsg = '\u4e0b\u8f7d\u5931\u8d25';
            try { const d = await response.json(); errMsg = d.error || errMsg; } catch(e) {}
            alert(errMsg);
        }
    } catch (error) {
        console.error('\u6279\u91cf\u4e0b\u8f7d\u5931\u8d25:', error);
        alert('\u6279\u91cf\u4e0b\u8f7d\u5931\u8d25: ' + error.message);
    }
    
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-download mr-2"></i>\u6279\u91cf\u4e0b\u8f7d';
}

// ==================== 视频链接解析功能 ====================

// 清空链接输入
function clearLinkInput() {
    document.getElementById('videoLinkInput').value = '';
    document.getElementById('batchLinksInput').value = '';
    document.getElementById('linkResultsArea').classList.add('hidden');
    document.getElementById('linkResults').innerHTML = '';
}

// 从文本中提取URL
function extractUrl(text) {
    text = text.trim();
    
    // 尝试匹配URL模式
    const urlPattern = /(https?:\/\/[^\s]+)/i;
    const match = text.match(urlPattern);
    
    if (match) {
        return match[1];
    }
    
    // 如果没有找到完整URL，尝试查找域名
    const domainPattern = /((?:v\.douyin\.com|www\.douyin\.com|douyin\.com|xiaohongshu\.com|xhslink\.com|kuaishou\.com|ksurl\.cn)[^\s]*)/i;
    const domainMatch = text.match(domainPattern);
    
    if (domainMatch) {
        return 'https://' + domainMatch[1];
    }
    
    return text;
}

// 修复URL协议
function fixUrlProtocol(url) {
    // 先提取纯URL
    url = extractUrl(url);
    url = url.trim();
    
    // 移除可能的尾部标点符号
    url = url.replace(/[，。！？、；：""''（）《》【】\s]+$/, '');
    
    // 如果URL不包含协议，添加https://
    if (!url.match(/^https?:\/\//i)) {
        // 如果以//开头，添加https:
        if (url.startsWith('//')) {
            return 'https:' + url;
        }
        // 否则添加https://
        return 'https://' + url;
    }
    return url;
}

// 开始链接解析
async function startLinkParsing() {
    const singleLink = document.getElementById('videoLinkInput').value.trim();
    const batchLinks = document.getElementById('batchLinksInput').value.trim();
    
    // 收集所有链接
    let urls = [];
    if (singleLink) {
        urls.push(fixUrlProtocol(singleLink));
    }
    if (batchLinks) {
        const lines = batchLinks.split('\n').map(line => line.trim()).filter(line => line);
        urls.push(...lines.map(fixUrlProtocol));
    }
    
    if (urls.length === 0) {
        alert('请输入至少一个视频链接');
        return;
    }
    
    // 获取处理模式和设置
    const processMode = document.getElementById('linkProcessMode').value;
    const whisperModel = document.getElementById('linkWhisperModel').value;
    const language = document.getElementById('linkLanguage').value;
    const enableAI = document.getElementById('linkEnableAI').checked;
    
    // 显示结果区域
    const resultsArea = document.getElementById('linkResultsArea');
    const resultsDiv = document.getElementById('linkResults');
    resultsArea.classList.remove('hidden');
    resultsDiv.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin mr-2"></i>处理中...</div>';
    
    try {
        if (processMode === 'download') {
            // 仅下载模式
            await downloadVideosOnly(urls);
        } else {
            // 下载并转录模式
            await downloadAndTranscribe(urls, whisperModel, language, enableAI);
        }
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p class="text-red-800"><i class="fas fa-exclamation-circle mr-2"></i>处理失败: ${error.message}</p>
            </div>
        `;
    }
}

// 仅下载视频
async function downloadVideosOnly(urls) {
    const resultsDiv = document.getElementById('linkResults');
    resultsDiv.innerHTML = '';
    
    for (let i = 0; i < urls.length; i++) {
        const url = urls[i];
        const resultId = `link-result-${i}`;
        
        // 添加处理项
        resultsDiv.innerHTML += `
            <div id="${resultId}" class="p-4 border border-gray-200 rounded-lg">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <p class="text-sm text-gray-600 mb-1">链接 ${i + 1}/${urls.length}</p>
                        <p class="text-xs text-gray-500 truncate">${url}</p>
                    </div>
                    <div class="ml-4">
                        <i class="fas fa-spinner fa-spin text-indigo-600"></i>
                    </div>
                </div>
                <div class="mt-2 text-sm text-gray-600">
                    <i class="fas fa-info-circle mr-1"></i>解析中...
                </div>
            </div>
        `;
        
        try {
            // 调用后端 API，用 yt-dlp 在服务端完成下载
            const response = await fetch('/api/video-link/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url })
            });
            
            const result = await response.json();
            
            if (result.success) {
                const title = result.title || '视频';
                const author = result.author || '未知';
                const platform = result.platform || 'video';
                const downloadUrl = result.download_url;
                window.linkDownloadedVideos[resultId] = {
                    filename: result.download_filename,
                    title,
                    author,
                    platform,
                    source_url: result.source_url || url
                };
                
                document.getElementById(resultId).innerHTML = `
                    <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div class="flex items-center justify-between mb-3">
                            <div class="flex-1">
                                <p class="font-semibold text-gray-800">${title}</p>
                                <p class="text-sm text-gray-600 mt-1">作者: ${author} | 平台: ${platform}</p>
                            </div>
                            <div class="ml-4">
                                <i class="fas fa-check-circle text-green-600 text-2xl"></i>
                            </div>
                        </div>
                        <div class="mt-2 text-sm text-green-600">
                            <i class="fas fa-check mr-1"></i>视频已下载，可继续转录或保存到本机
                        </div>
                        <div class="mt-3 flex flex-wrap gap-2">
                            <button onclick="transcribeDownloadedVideo('${resultId}')" class="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
                                <i class="fas fa-file-alt mr-1"></i>转录文本
                            </button>
                            ${downloadUrl ? `
                                <a href="${downloadUrl}" download class="inline-flex items-center px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700">
                                    <i class="fas fa-download mr-1"></i>保存到本机
                                </a>
                            ` : ''}
                        </div>
                    </div>
                `;
                
            } else {
                const errorMsg = result.error || '解析失败';
                
                document.getElementById(resultId).innerHTML = `
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <p class="text-sm text-gray-600 truncate">${url}</p>
                        </div>
                        <div class="ml-4">
                            <i class="fas fa-times-circle text-red-600"></i>
                        </div>
                    </div>
                    <div class="mt-2 text-sm text-red-600">
                        <i class="fas fa-exclamation-circle mr-1"></i>${errorMsg}
                    </div>
                `;
            }
        } catch (error) {
            document.getElementById(resultId).innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <p class="text-sm text-gray-600 truncate">${url}</p>
                    </div>
                    <div class="ml-4">
                        <i class="fas fa-times-circle text-red-600"></i>
                    </div>
                </div>
                <div class="mt-2 text-sm text-red-600">
                    <i class="fas fa-exclamation-circle mr-1"></i>网络错误: ${error.message}
                </div>
            `;
        }
        
        // 添加延迟，避免请求过快
        if (i < urls.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}

// 对“仅下载”模式的结果继续转录
async function transcribeDownloadedVideo(resultId) {
    const item = window.linkDownloadedVideos[resultId];
    if (!item || !item.filename) {
        alert('未找到已下载的视频文件，请重新下载');
        return;
    }

    const whisperModel = document.getElementById('linkWhisperModel')?.value || 'base';
    const language = document.getElementById('linkLanguage')?.value || 'zh';
    const enableAI = document.getElementById('linkEnableAI')?.checked ?? true;
    const resultEl = document.getElementById(resultId);

    resultEl.innerHTML = `
        <div class="p-4 border border-blue-200 bg-blue-50 rounded-lg">
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <p class="font-semibold text-gray-800">${item.title}</p>
                    <p class="text-sm text-gray-600 mt-1">作者: ${item.author} | 平台: ${item.platform}</p>
                </div>
                <div class="ml-4">
                    <i class="fas fa-spinner fa-spin text-blue-600 text-2xl"></i>
                </div>
            </div>
            <div class="mt-3 text-sm text-blue-700">
                <i class="fas fa-circle-notch fa-spin mr-1"></i>
                正在转录${enableAI ? '并进行 AI 整理' : ''}...
            </div>
        </div>
    `;

    try {
        const response = await fetch('/api/video-link/transcribe-downloaded', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filename: item.filename,
                title: item.title,
                author: item.author,
                platform: item.platform,
                source_url: item.source_url,
                whisper_model: whisperModel,
                language,
                enable_ai: enableAI
            })
        });

        const result = await response.json();
        if (result.success) {
            renderLinkTranscribeResult(resultId, result);
        } else {
            resultEl.innerHTML = `
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <p class="font-semibold text-gray-800">${item.title}</p>
                        </div>
                        <div class="ml-4">
                            <i class="fas fa-times-circle text-red-600 text-2xl"></i>
                        </div>
                    </div>
                    <div class="mt-2 text-sm text-red-600">
                        <i class="fas fa-exclamation-circle mr-1"></i>${result.error || '转录失败'}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        resultEl.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <p class="text-red-800"><i class="fas fa-exclamation-circle mr-2"></i>网络错误: ${error.message}</p>
            </div>
        `;
    }
}

function renderLinkTranscribeResult(resultId, result) {
    const title = result.title || '视频';
    const author = result.author || '未知';
    const platform = result.platform || 'video';
    const transcriptUrl = result.transcript_download_url || result.transcript_file;
    const summaryUrl = result.ai_summary_download_url || result.ai_summary_file;
    const videoUrl = result.video_download_url || result.video_file;

    document.getElementById(resultId).innerHTML = `
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="flex items-center justify-between mb-3">
                <div class="flex-1">
                    <p class="font-semibold text-gray-800">${title}</p>
                    <p class="text-sm text-gray-600 mt-1">作者: ${author} | 平台: ${platform}</p>
                </div>
                <div class="ml-4">
                    <i class="fas fa-check-circle text-green-600 text-2xl"></i>
                </div>
            </div>
            <div class="flex flex-wrap gap-2">
                ${transcriptUrl ? `
                    <a href="${transcriptUrl}" target="_blank" class="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
                        <i class="fas fa-file-alt mr-1"></i>转录文本
                    </a>
                ` : ''}
                ${summaryUrl ? `
                    <a href="${summaryUrl}" target="_blank" class="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700">
                        <i class="fas fa-brain mr-1"></i>AI 摘要
                    </a>
                ` : ''}
                ${videoUrl ? `
                    <a href="${videoUrl}" download class="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700">
                        <i class="fas fa-download mr-1"></i>保存到本机
                    </a>
                ` : ''}
            </div>
            ${result.ai_summary_error ? `
                <div class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                    <i class="fas fa-exclamation-triangle mr-1"></i>
                    转录已完成，但 AI 整理失败：${result.ai_summary_error}
                </div>
            ` : ''}
        </div>
    `;
}

// 下载并转录
async function downloadAndTranscribe(urls, whisperModel, language, enableAI) {
    const resultsDiv = document.getElementById('linkResults');
    resultsDiv.innerHTML = '';
    
    for (let i = 0; i < urls.length; i++) {
        const url = urls[i];
        const resultId = `link-result-${i}`;
        
        // 添加处理项
        resultsDiv.innerHTML += `
            <div id="${resultId}" class="p-4 border border-gray-200 rounded-lg">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <p class="text-sm text-gray-600 mb-1">链接 ${i + 1}/${urls.length}</p>
                        <p class="text-xs text-gray-500 truncate">${url}</p>
                    </div>
                    <div class="ml-4">
                        <i class="fas fa-spinner fa-spin text-indigo-600"></i>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="text-sm text-gray-600">
                        <i class="fas fa-circle-notch fa-spin mr-1"></i>步骤 1/4: 解析链接...
                    </div>
                    <div class="mt-2 w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-indigo-600 h-2 rounded-full transition-all" style="width: 25%"></div>
                    </div>
                </div>
            </div>
        `;
        
        try {
            // 调用后端API进行完整处理
            const response = await fetch('/api/video-link/parse-and-transcribe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: url,
                    whisper_model: whisperModel,
                    language: language,
                    enable_ai: enableAI
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                renderLinkTranscribeResult(resultId, result);
            } else {
                // 处理失败
                document.getElementById(resultId).innerHTML = `
                    <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                        <div class="flex items-center justify-between">
                            <div class="flex-1">
                                <p class="text-sm text-gray-600 truncate">${url}</p>
                            </div>
                            <div class="ml-4">
                                <i class="fas fa-times-circle text-red-600 text-2xl"></i>
                            </div>
                        </div>
                        <div class="mt-2 text-sm text-red-600">
                            <i class="fas fa-exclamation-circle mr-1"></i>${result.error || '处理失败'}
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            document.getElementById(resultId).innerHTML = `
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <p class="text-sm text-gray-600 truncate">${url}</p>
                        </div>
                        <div class="ml-4">
                            <i class="fas fa-times-circle text-red-600 text-2xl"></i>
                        </div>
                    </div>
                    <div class="mt-2 text-sm text-red-600">
                        <i class="fas fa-exclamation-circle mr-1"></i>网络错误: ${error.message}
                    </div>
                </div>
            `;
        }
        
        // 添加延迟
        if (i < urls.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
}

// 监听处理模式变化，显示/隐藏 Whisper 设置
document.getElementById('linkProcessMode')?.addEventListener('change', function() {
    const whisperSettings = document.getElementById('linkWhisperSettings');
    whisperSettings.classList.remove('hidden');
});
