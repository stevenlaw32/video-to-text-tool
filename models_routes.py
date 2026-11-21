"""
多模型配置管理的API路由
"""

from urllib.parse import urlsplit, urlunsplit

import requests
from flask import Blueprint, request, jsonify
from models_config import ModelsConfig
from prompt_presets import DEFAULT_PRESET_ID, list_presets
from openai import OpenAI

models_bp = Blueprint('models', __name__, url_prefix='/api/models')


def _build_model_list_urls(base_url):
    """根据用户填写的 Base URL 生成模型列表候选地址。"""
    parsed = urlsplit((base_url or '').strip())
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError('Base URL 必须是有效的 HTTP/HTTPS 地址')

    normalized_path = parsed.path.rstrip('/')
    normalized_base = urlunsplit((
        parsed.scheme,
        parsed.netloc,
        normalized_path,
        '',
        ''
    )).rstrip('/')

    urls = [f'{normalized_base}/models']
    if not normalized_path.endswith('/v1'):
        urls.append(f'{normalized_base}/v1/models')
    return list(dict.fromkeys(urls))


def _normalize_available_models(payload, model_provider):
    """兼容 OpenAI、Anthropic 以及常见代理商的模型列表格式。"""
    if isinstance(payload, list):
        raw_models = payload
    elif isinstance(payload, dict):
        raw_models = payload.get('data')
        if not isinstance(raw_models, list):
            raw_models = payload.get('models')
    else:
        raw_models = None

    if not isinstance(raw_models, list):
        raise ValueError('服务端返回的模型列表格式无法识别')

    models = []
    seen_ids = set()
    for item in raw_models:
        if isinstance(item, str):
            model_id = item
            owned_by = model_provider
        elif isinstance(item, dict):
            model_id = (
                item.get('id')
                or item.get('model')
                or item.get('model_id')
                or item.get('name')
            )
            owned_by = item.get('owned_by') or item.get('provider') or model_provider
        else:
            continue

        if not model_id or model_id in seen_ids:
            continue
        seen_ids.add(model_id)
        models.append({'id': str(model_id), 'owned_by': str(owned_by or '')})

    return sorted(models, key=lambda model: model['id'].lower())


@models_bp.route('/prompt_presets', methods=['GET'])
def get_prompt_presets():
    """返回内置默认提示词模板：整理重排、尊重原文。"""
    return jsonify({
        'success': True,
        'default_id': DEFAULT_PRESET_ID,
        'presets': list_presets()
    })


@models_bp.route('/list', methods=['GET'])
def get_models_list():
    """获取所有模型配置列表"""
    try:
        config = ModelsConfig()
        models = config.get_all_models()
        active_model = config.config.get("active_model")
        
        return jsonify({
            'success': True,
            'models': models,
            'active_model': active_model
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/providers', methods=['GET'])
def get_providers():
    """获取所有供应商配置"""
    try:
        config = ModelsConfig()
        return jsonify({
            'success': True,
            'providers': config.get_all_providers()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/fetch_available', methods=['POST'])
def fetch_available_models():
    """由本机后端代为请求上游模型列表，避免浏览器的 CORS 限制。"""
    data = request.get_json(silent=True) or {}
    api_key = (data.get('api_key') or '').strip()
    base_url = (data.get('base_url') or '').strip()
    model_provider = (data.get('model_provider') or 'openai').strip().lower()

    if not api_key or not base_url:
        return jsonify({
            'success': False,
            'error': '请先填写 API Key 和 Base URL'
        }), 400

    try:
        candidate_urls = _build_model_list_urls(base_url)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    if model_provider == 'anthropic':
        headers.update({
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        })
    elif model_provider in ('gemini', 'google'):
        headers['x-goog-api-key'] = api_key

    errors = []
    for models_url in candidate_urls:
        try:
            upstream = requests.get(
                models_url,
                headers=headers,
                timeout=(5, 20)
            )
        except requests.RequestException as exc:
            errors.append(f'{models_url}: 连接失败（{exc}）')
            continue

        if not upstream.ok:
            errors.append(f'{models_url}: HTTP {upstream.status_code}')
            continue

        try:
            models = _normalize_available_models(upstream.json(), model_provider)
        except (ValueError, requests.exceptions.JSONDecodeError) as exc:
            errors.append(f'{models_url}: {exc}')
            continue

        return jsonify({
            'success': True,
            'models': models,
            'source_url': models_url
        })

    detail = '；'.join(errors) if errors else '未获得有效响应'
    return jsonify({
        'success': False,
        'error': f'上游模型列表请求失败：{detail}'
    }), 502


@models_bp.route('/providers/save', methods=['POST'])
def save_provider():
    """新增或更新供应商配置"""
    try:
        data = request.json
        config = ModelsConfig()

        success = config.save_provider(
            alias=data.get('alias'),
            original_alias=data.get('original_alias'),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model_provider=data.get('model_provider', 'openai')
        )

        if success:
            return jsonify({'success': True, 'message': '供应商保存成功'})
        return jsonify({'success': False, 'error': '供应商别名已存在或参数不完整'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/providers/delete', methods=['POST'])
def delete_provider():
    """删除供应商，并删除该供应商下的模型配置"""
    try:
        data = request.json
        config = ModelsConfig()

        result = config.delete_provider(alias=data.get('alias'))

        if result is not None:
            return jsonify({
                'success': True,
                'message': '供应商删除成功',
                'deleted_models': result.get('deleted_models', 0)
            })
        return jsonify({'success': False, 'error': '供应商不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/add', methods=['POST'])
def add_model():
    """添加新的模型配置"""
    try:
        data = request.json
        config = ModelsConfig()
        
        success = config.add_model(
            alias=data.get('alias'),
            api_key=data.get('api_key'),
            base_url=data.get('base_url'),
            model_provider=data.get('model_provider'),
            model_name=data.get('model_name'),
            custom_prompt=data.get('custom_prompt', ''),
            max_tokens=data.get('max_tokens'),
            temperature=data.get('temperature'),
            provider_alias=data.get('provider_alias')
        )
        
        if success:
            return jsonify({'success': True, 'message': '模型添加成功'})
        else:
            return jsonify({'success': False, 'error': '模型别名已存在'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/update', methods=['POST'])
def update_model():
    """更新模型配置"""
    try:
        data = request.json
        config = ModelsConfig()
        
        original_alias = data.get('original_alias')
        new_alias = data.get('alias')
        
        # 如果别名被修改，需要重命名
        if original_alias != new_alias:
            success = config.rename_model(
                old_alias=original_alias,
                new_alias=new_alias,
                api_key=data.get('api_key'),
                base_url=data.get('base_url'),
                model_provider=data.get('model_provider'),
                model_name=data.get('model_name'),
                custom_prompt=data.get('custom_prompt'),
                max_tokens=data.get('max_tokens'),
                temperature=data.get('temperature'),
                provider_alias=data.get('provider_alias')
            )
        else:
            # 别名未改变，直接更新
            success = config.update_model(
                alias=new_alias,
                api_key=data.get('api_key'),
                base_url=data.get('base_url'),
                model_provider=data.get('model_provider'),
                model_name=data.get('model_name'),
                custom_prompt=data.get('custom_prompt'),
                max_tokens=data.get('max_tokens'),
                temperature=data.get('temperature'),
                provider_alias=data.get('provider_alias')
            )
        
        if success:
            return jsonify({'success': True, 'message': '模型更新成功'})
        else:
            return jsonify({'success': False, 'error': '模型不存在或新别名已被使用'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/delete', methods=['POST'])
def delete_model():
    """删除模型配置"""
    try:
        data = request.json
        config = ModelsConfig()
        
        success = config.delete_model(alias=data.get('alias'))
        
        if success:
            return jsonify({'success': True, 'message': '模型删除成功'})
        else:
            return jsonify({'success': False, 'error': '模型不存在'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/set_active', methods=['POST'])
def set_active_model():
    """设置活动模型"""
    try:
        data = request.json
        config = ModelsConfig()
        
        success = config.set_active_model(alias=data.get('alias'))
        
        if success:
            return jsonify({'success': True, 'message': '活动模型设置成功'})
        else:
            return jsonify({'success': False, 'error': '模型不存在'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/get/<alias>', methods=['GET'])
def get_model(alias):
    """获取指定模型的配置"""
    try:
        config = ModelsConfig()
        model = config.get_model_by_alias(alias)
        
        if model:
            return jsonify({'success': True, 'model': model})
        else:
            return jsonify({'success': False, 'error': '模型不存在'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/active', methods=['GET'])
def get_active_model():
    """获取当前活动的模型配置"""
    try:
        config = ModelsConfig()
        model = config.get_active_model()
        
        if model:
            return jsonify({'success': True, 'model': model})
        else:
            return jsonify({'success': False, 'error': '没有活动模型'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@models_bp.route('/test_connection', methods=['POST'])
def test_connection():
    """测试模型连接"""
    try:
        data = request.json
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=data.get('api_key'),
            base_url=data.get('base_url')
        )
        
        # 发送一个简单的测试请求
        response = client.chat.completions.create(
            model=data.get('model_name'),
            messages=[
                {"role": "user", "content": "Hello"}
            ],
            max_tokens=10
        )
        
        return jsonify({
            'success': True,
            'message': '连接测试成功！',
            'response': response.choices[0].message.content
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'连接测试失败: {str(e)}'
        }), 500
