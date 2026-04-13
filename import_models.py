#!/usr/bin/env python3
"""
一次性导入脚本 - 从 YAML 文件批量导入模型配置
仅用于本地操作，不会包含在项目代码中

智能识别 YAML 结构：
- alias: 模型别名
- model_id: 模型名称
- api_key: API密钥
- base_url: API基础URL
- api: API类型（openai-completions等）
"""

import yaml
import requests
import re

# YAML 文件路径
YAML_FILE = "/Users/apple/开发/DevOps/ModelAPIKey.yaml"

# API 端点
BASE_URL = "http://localhost:5000"

def extract_models_from_yaml():
    """智能提取 YAML 文件中的所有模型配置"""
    with open(YAML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 只读取到结束标记之前的内容
    end_marker = "# ==================API kEY 清单到此结束"
    if end_marker in content:
        content = content.split(end_marker)[0]
    
    # 解析 YAML
    try:
        data = yaml.safe_load(content)
    except Exception as e:
        print(f"YAML 解析错误: {e}")
        return []
    
    if not data:
        return []
    
    models = []
    
    # 遍历所有键值对，找出模型配置
    for key, value in data.items():
        # 跳过非字典类型的值
        if not isinstance(value, dict):
            continue
        
        # 检查是否包含模型配置的必要字段
        if 'alias' in value and 'api_key' in value and 'base_url' in value:
            model_info = {
                'yaml_key': key,
                'alias': value.get('alias', key),
                'model_name': value.get('model_id', ''),
                'api_key': value.get('api_key', ''),
                'base_url': value.get('base_url', ''),
                'api_type': value.get('api', 'openai-completions')
            }
            
            # 只添加有效的配置（必须有 API Key 和 Base URL）
            if model_info['api_key'] and model_info['base_url']:
                models.append(model_info)
    
    return models

def determine_provider(api_type, base_url):
    """根据 API 类型和 Base URL 判断 provider"""
    if 'openai' in api_type.lower():
        return 'openai-completion'
    elif 'anthropic' in base_url.lower() or 'claude' in base_url.lower():
        return 'anthropic'
    else:
        return 'custom'

def import_model(model_info):
    """导入单个模型配置"""
    
    alias = model_info['alias']
    
    # 准备数据
    config = {
        "alias": alias,
        "api_key": model_info['api_key'],
        "base_url": model_info['base_url'],
        "model_provider": determine_provider(model_info['api_type'], model_info['base_url']),
        "model_name": model_info['model_name'],
        "custom_prompt": ""
    }
    
    print(f"\n导入模型: {alias}")
    print(f"  - 模型名称: {config['model_name']}")
    print(f"  - Base URL: {config['base_url']}")
    print(f"  - Provider: {config['model_provider']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/models/add",
            json=config,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        result = response.json()
        
        if result.get("success"):
            print(f"  ✓ 成功导入")
            return True
        else:
            error_msg = result.get('error', '未知错误')
            if '已存在' in error_msg:
                print(f"  ⊙ 已存在，跳过")
                return True
            else:
                print(f"  ✗ 导入失败: {error_msg}")
                return False
            
    except requests.exceptions.ConnectionError:
        print(f"  ✗ 连接失败: 请确保服务器运行在 {BASE_URL}")
        return False
    except Exception as e:
        print(f"  ✗ 导入出错: {str(e)}")
        return False

def main():
    print("=" * 70)
    print(" " * 20 + "批量导入模型配置")
    print("=" * 70)
    
    # 提取模型配置
    print("\n📖 正在读取 YAML 配置文件...")
    models = extract_models_from_yaml()
    
    if not models:
        print("✗ 未找到有效的模型配置")
        return
    
    print(f"✓ 找到 {len(models)} 个模型配置\n")
    
    # 显示将要导入的模型列表
    print("📋 待导入的模型:")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model['alias']} ({model['model_name']})")
    
    # 确认导入
    print("\n" + "=" * 70)
    confirm = input("是否继续导入？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("已取消导入")
        return
    
    # 导入所有模型
    print("\n🚀 开始导入...")
    success_count = 0
    fail_count = 0
    
    for model in models:
        if import_model(model):
            success_count += 1
        else:
            fail_count += 1
    
    # 总结
    print("\n" + "=" * 70)
    print("📊 导入完成！")
    print("=" * 70)
    print(f"✓ 成功: {success_count} 个")
    print(f"✗ 失败: {fail_count} 个")
    print(f"📦 总计: {len(models)} 个")
    
    if success_count > 0:
        print("\n🎉 现在可以访问以下地址查看导入的模型:")
        print(f"   {BASE_URL}/models")
        print("\n💡 提示: 您可以在多模型配置页面为每个模型设置专属提示词")

if __name__ == "__main__":
    main()
