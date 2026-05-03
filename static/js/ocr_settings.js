// OCR 配置管理脚本

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadProviders();
    loadActiveProvider();
});

// 加载所有提供商配置
async function loadProviders() {
    try {
        const response = await fetch('/api/ocr/providers');
        const data = await response.json();
        
        if (data.success) {
            // 填充激活提供商下拉框
            populateActiveProviderSelect(data.providers, data.active_provider);
            
            // 加载各个提供商的配置
            loadProviderConfigs(data.providers);
        }
    } catch (error) {
        console.error('加载 OCR 配置失败:', error);
        alert('加载配置失败: ' + error.message);
    }
}

// 填充激活提供商下拉框
function populateActiveProviderSelect(providers, activeProvider) {
    const select = document.getElementById('activeProvider');
    select.innerHTML = '';
    
    for (const [key, config] of Object.entries(providers)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = config.name;
        option.selected = key === activeProvider;
        select.appendChild(option);
    }
}

// 加载各个提供商的配置
function loadProviderConfigs(providers) {
    // 百度
    if (providers.baidu) {
        document.getElementById('baiduApiKey').value = providers.baidu.api_key || '';
        document.getElementById('baiduSecretKey').value = providers.baidu.secret_key || '';
    }
    
    // 腾讯云
    if (providers.tencent) {
        document.getElementById('tencentSecretId').value = providers.tencent.secret_id || '';
        document.getElementById('tencentSecretKey').value = providers.tencent.secret_key || '';
        document.getElementById('tencentRegion').value = providers.tencent.region || 'ap-guangzhou';
    }
    
    // 阿里云
    if (providers.aliyun) {
        document.getElementById('aliyunAccessKeyId').value = providers.aliyun.access_key_id || '';
        document.getElementById('aliyunAccessKeySecret').value = providers.aliyun.access_key_secret || '';
        document.getElementById('aliyunRegion').value = providers.aliyun.region || 'cn-shanghai';
    }
}

// 加载当前激活的提供商
async function loadActiveProvider() {
    try {
        const response = await fetch('/api/ocr/active');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('activeProvider').value = data.active_provider;
        }
    } catch (error) {
        console.error('加载激活提供商失败:', error);
    }
}

// 设置激活的提供商
async function setActiveProvider() {
    const provider = document.getElementById('activeProvider').value;
    
    try {
        const response = await fetch('/api/ocr/active', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ provider })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ 已切换到 ' + provider);
        } else {
            alert('切换失败: ' + data.error);
        }
    } catch (error) {
        alert('切换失败: ' + error.message);
    }
}

// 保存百度配置
async function saveBaiduConfig() {
    const apiKey = document.getElementById('baiduApiKey').value.trim();
    const secretKey = document.getElementById('baiduSecretKey').value.trim();
    
    if (!apiKey || !secretKey) {
        alert('请填写完整的 API Key 和 Secret Key');
        return;
    }
    
    try {
        const response = await fetch('/api/ocr/providers/baidu', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: apiKey,
                secret_key: secretKey,
                enabled: true
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ 百度 OCR 配置已保存');
            loadProviders();
        } else {
            alert('保存失败: ' + data.error);
        }
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

// 保存腾讯云配置
async function saveTencentConfig() {
    const secretId = document.getElementById('tencentSecretId').value.trim();
    const secretKey = document.getElementById('tencentSecretKey').value.trim();
    const region = document.getElementById('tencentRegion').value;
    
    if (!secretId || !secretKey) {
        alert('请填写完整的 Secret ID 和 Secret Key');
        return;
    }
    
    try {
        const response = await fetch('/api/ocr/providers/tencent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                secret_id: secretId,
                secret_key: secretKey,
                region: region,
                enabled: true
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ 腾讯云 OCR 配置已保存');
            loadProviders();
        } else {
            alert('保存失败: ' + data.error);
        }
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

// 保存阿里云配置
async function saveAliyunConfig() {
    const accessKeyId = document.getElementById('aliyunAccessKeyId').value.trim();
    const accessKeySecret = document.getElementById('aliyunAccessKeySecret').value.trim();
    const region = document.getElementById('aliyunRegion').value;
    
    if (!accessKeyId || !accessKeySecret) {
        alert('请填写完整的 Access Key ID 和 Access Key Secret');
        return;
    }
    
    try {
        const response = await fetch('/api/ocr/providers/aliyun', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                access_key_id: accessKeyId,
                access_key_secret: accessKeySecret,
                region: region,
                enabled: true
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ 阿里云 OCR 配置已保存');
            loadProviders();
        } else {
            alert('保存失败: ' + data.error);
        }
    } catch (error) {
        alert('保存失败: ' + error.message);
    }
}

// 测试提供商连接
async function testProvider(provider) {
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;
    
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>测试中...';
    
    try {
        const response = await fetch(`/api/ocr/test/${provider}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ ' + data.message);
        } else {
            alert('✗ ' + data.error);
        }
    } catch (error) {
        alert('测试失败: ' + error.message);
    } finally {
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}
