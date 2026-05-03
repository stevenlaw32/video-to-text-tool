let uploadedVideoPath = null;
let transcriptText = '';
let summaryText = '';

const dropZone = document.getElementById('dropZone');
const videoInput = document.getElementById('videoInput');
const fileInfo = document.getElementById('fileInfo');
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

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

videoInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

async function handleFileSelect(file) {
    const formData = new FormData();
    formData.append('video', file);
    
    fileInfo.textContent = `已选择: ${file.name} (${formatFileSize(file.size)})`;
    fileInfo.classList.remove('hidden');
    processBtn.disabled = false;
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            uploadedVideoPath = data.path;
        } else {
            alert('上传失败: ' + data.error);
        }
    } catch (error) {
        alert('上传出错: ' + error.message);
    }
}

processBtn.addEventListener('click', async () => {
    if (!uploadedVideoPath) {
        alert('请先上传视频文件');
        return;
    }
    
    processBtn.disabled = true;
    resultSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    
    updateProgress(10, '正在提取音频...');
    
    const modelSize = document.getElementById('modelSize').value;
    const aiStyle = document.getElementById('aiStyle').value;
    const skipAI = document.getElementById('skipAI').checked;
    
    try {
        updateProgress(30, '正在转录音频...');
        
        const response = await fetch('/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_path: uploadedVideoPath,
                model_size: modelSize,
                style: aiStyle,
                skip_ai: skipAI
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateProgress(70, '转录完成...');
            
            transcriptText = data.transcript;
            transcriptResult.textContent = transcriptText;
            
            if (!skipAI && data.summary) {
                updateProgress(90, 'AI整理中...');
                summaryText = data.summary;
                summaryResult.innerHTML = marked.parse(summaryText);
                summarySection.classList.remove('hidden');
            } else {
                summarySection.classList.add('hidden');
            }
            
            updateProgress(100, '处理完成！');
            
            setTimeout(() => {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');
            }, 1000);
            
        } else {
            alert('处理失败: ' + data.error);
            progressSection.classList.add('hidden');
        }
        
    } catch (error) {
        alert('处理出错: ' + error.message);
        progressSection.classList.add('hidden');
    } finally {
        processBtn.disabled = false;
    }
});

function updateProgress(percent, text) {
    progressBar.style.width = percent + '%';
    progressText.textContent = text;
}

function downloadText(type) {
    const content = type === 'transcript' ? transcriptText : summaryText;
    const filename = type === 'transcript' ? 'transcript.txt' : 'summary.md';
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
