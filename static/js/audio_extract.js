// 音频提取前端逻辑

let selectedFiles = [];
let processedFiles = [];

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initializeDropZone();
    loadOutputFiles();
});

// 初始化拖拽区域
function initializeDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    // 点击上传
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    // 文件选择
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // 拖拽事件
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

// 处理选择的文件
function handleFiles(files) {
    const videoExtensions = ['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', 'webm'];
    
    for (let file of files) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (videoExtensions.includes(ext)) {
            // 检查是否已存在
            if (!selectedFiles.find(f => f.name === file.name)) {
                selectedFiles.push({
                    file: file,
                    name: file.name,
                    size: file.size,
                    status: 'pending',
                    progress: 0
                });
            }
        } else {
            showNotification(`不支持的文件格式: ${file.name}`, 'error');
        }
    }
    
    updateFileList();
    updateStatistics();
}

// 更新文件列表显示
function updateFileList() {
    const fileList = document.getElementById('fileList');
    const fileCount = document.getElementById('fileCount');
    
    fileCount.textContent = `(${selectedFiles.length} 个文件)`;
    
    if (selectedFiles.length === 0) {
        fileList.innerHTML = `
            <div class="text-center py-8 text-gray-400">
                <i class="fas fa-inbox text-4xl mb-2"></i>
                <p class="text-sm">暂无文件，请上传视频</p>
            </div>
        `;
        document.getElementById('extractBtn').disabled = true;
        return;
    }
    
    document.getElementById('extractBtn').disabled = false;
    
    fileList.innerHTML = selectedFiles.map((item, index) => {
        const statusIcons = {
            'pending': '<i class="fas fa-clock text-gray-400"></i>',
            'processing': '<i class="fas fa-spinner fa-spin text-blue-500"></i>',
            'completed': '<i class="fas fa-check-circle text-green-500"></i>',
            'error': '<i class="fas fa-exclamation-circle text-red-500"></i>'
        };
        
        const statusTexts = {
            'pending': '等待中',
            'processing': '处理中...',
            'completed': '已完成',
            'error': '失败'
        };
        
        return `
            <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-3 flex-1 min-w-0">
                        ${statusIcons[item.status]}
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium text-gray-900 truncate">${item.name}</p>
                            <p class="text-xs text-gray-500">${formatFileSize(item.size)}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-medium ${getStatusColor(item.status)}">${statusTexts[item.status]}</span>
                        ${item.status === 'completed' && item.outputPath ? 
                            `<button onclick="downloadFile('${item.outputFilename}')" class="text-indigo-600 hover:text-indigo-800">
                                <i class="fas fa-download"></i>
                            </button>` : ''}
                        <button onclick="removeFile(${index})" class="text-red-600 hover:text-red-800">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                ${item.status === 'processing' ? `
                    <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div class="progress-bar bg-indigo-600 h-2 rounded-full" style="width: ${item.progress}%"></div>
                    </div>
                ` : ''}
                ${item.error ? `
                    <p class="text-xs text-red-600 mt-2">${item.error}</p>
                ` : ''}
            </div>
        `;
    }).join('');
}

// 获取状态颜色
function getStatusColor(status) {
    const colors = {
        'pending': 'text-gray-500',
        'processing': 'text-blue-600',
        'completed': 'text-green-600',
        'error': 'text-red-600'
    };
    return colors[status] || 'text-gray-500';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// 移除文件
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
    updateStatistics();
}

// 清空所有文件
function clearAllFiles() {
    if (selectedFiles.length === 0) return;
    
    if (confirm('确定要清空所有文件吗？')) {
        selectedFiles = [];
        updateFileList();
        updateStatistics();
    }
}

// 开始提取
async function startExtraction() {
    const extractBtn = document.getElementById('extractBtn');
    const outputFormat = document.getElementById('outputFormat').value;
    const bitrate = document.getElementById('bitrate').value;
    const sampleRate = document.getElementById('sampleRate').value;
    
    // 过滤出未完成的文件
    const pendingFiles = selectedFiles.filter(f => f.status !== 'completed');
    
    if (pendingFiles.length === 0) {
        showNotification('没有需要处理的文件', 'warning');
        return;
    }
    
    extractBtn.disabled = true;
    
    try {
        // 第一步：批量上传文件
        const formData = new FormData();
        pendingFiles.forEach(item => {
            formData.append('videos', item.file);
        });
        formData.append('folder_name', 'audio_extract');
        
        // 标记所有文件为处理中
        pendingFiles.forEach(item => {
            item.status = 'processing';
            item.progress = 10;
        });
        updateFileList();
        updateStatistics();
        
        const uploadResponse = await fetch('/upload_batch', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('批量上传失败');
        }
        
        const uploadData = await uploadResponse.json();
        
        if (!uploadData.success) {
            throw new Error('批量上传失败');
        }
        
        // 更新进度
        pendingFiles.forEach(item => {
            item.progress = 30;
        });
        updateFileList();
        
        // 第二步：逐个提取音频（保持进度可见）
        for (let i = 0; i < pendingFiles.length; i++) {
            const item = pendingFiles[i];
            const uploadedFile = uploadData.files[i];
            
            if (!uploadedFile) {
                item.status = 'error';
                item.error = '文件上传失败';
                updateFileList();
                updateStatistics();
                continue;
            }
            
            try {
                item.progress = 50;
                updateFileList();
                
                // 获取视频文件路径（通过API获取）
                const pathResponse = await fetch(`/api/video_path/${uploadedFile.id}`);
                let videoPath;
                
                if (pathResponse.ok) {
                    const pathData = await pathResponse.json();
                    videoPath = pathData.path;
                } else {
                    // 如果API不存在，使用默认路径构建
                    videoPath = `/tmp/video_uploads/${uploadedFile.id}`;
                }
                
                const extractResponse = await fetch('/api/audio/extract', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        video_path: videoPath,
                        format: outputFormat,
                        bitrate: bitrate,
                        sample_rate: parseInt(sampleRate)
                    })
                });
                
                const extractData = await extractResponse.json();
                
                if (extractData.success) {
                    item.status = 'completed';
                    item.progress = 100;
                    item.outputPath = extractData.output_path;
                    item.outputFilename = extractData.output_filename;
                    item.fileSize = extractData.file_size;
                    
                    processedFiles.push(item);
                    showNotification(`✓ ${item.name} 提取成功`, 'success');
                } else {
                    throw new Error(extractData.error || '提取失败');
                }
                
            } catch (error) {
                item.status = 'error';
                item.error = error.message;
                showNotification(`✗ ${item.name} 提取失败: ${error.message}`, 'error');
            }
            
            updateFileList();
            updateStatistics();
        }
        
    } catch (error) {
        showNotification(`批量处理失败: ${error.message}`, 'error');
        // 标记所有处理中的文件为失败
        pendingFiles.forEach(item => {
            if (item.status === 'processing') {
                item.status = 'error';
                item.error = error.message;
            }
        });
    } finally {
        extractBtn.disabled = false;
        document.getElementById('downloadAllBtn').disabled = processedFiles.length === 0;
        updateFileList();
        updateStatistics();
        loadOutputFiles();
    }
}

// 下载文件
function downloadFile(filename) {
    window.location.href = `/api/audio/download/${filename}`;
}

// 批量下载
function downloadAll() {
    const completedFiles = selectedFiles.filter(f => f.status === 'completed');
    
    if (completedFiles.length === 0) {
        showNotification('没有可下载的文件', 'warning');
        return;
    }
    
    completedFiles.forEach(item => {
        if (item.outputFilename) {
            setTimeout(() => {
                downloadFile(item.outputFilename);
            }, 100);
        }
    });
}

// 更新统计信息
function updateStatistics() {
    document.getElementById('statTotal').textContent = selectedFiles.length;
    document.getElementById('statCompleted').textContent = selectedFiles.filter(f => f.status === 'completed').length;
    document.getElementById('statProcessing').textContent = selectedFiles.filter(f => f.status === 'processing').length;
    document.getElementById('statFailed').textContent = selectedFiles.filter(f => f.status === 'error').length;
}

// 加载输出文件列表
async function loadOutputFiles() {
    try {
        const response = await fetch('/api/audio/list');
        const data = await response.json();
        
        if (data.success && data.files.length > 0) {
            const outputFilesList = document.getElementById('outputFilesList');
            outputFilesList.innerHTML = data.files.map(file => `
                <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-900 truncate">${file.filename}</p>
                        <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="downloadFile('${file.filename}')" class="text-indigo-600 hover:text-indigo-800">
                            <i class="fas fa-download"></i>
                        </button>
                        <button onclick="deleteOutputFile('${file.filename}')" class="text-red-600 hover:text-red-800">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('加载输出文件失败:', error);
    }
}

// 删除输出文件
async function deleteOutputFile(filename) {
    if (!confirm(`确定要删除 ${filename} 吗？`)) return;
    
    try {
        const response = await fetch(`/api/audio/delete/${filename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('文件已删除', 'success');
            loadOutputFiles();
        } else {
            showNotification('删除失败: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    const colors = {
        'success': 'bg-green-500',
        'error': 'bg-red-500',
        'warning': 'bg-yellow-500',
        'info': 'bg-blue-500'
    };
    
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animate-fade-in {
        animation: fade-in 0.3s ease-out;
    }
`;
document.head.appendChild(style);
