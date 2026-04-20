"""
API 路由模块
提供 API 配置管理的 HTTP 接口
"""

from flask import Blueprint, request, jsonify
from api_config import APIConfig
from api_client import UniversalAPIClient

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/get_config', methods=['GET'])
def get_config():
    """获取当前 API 配置"""
    try:
        config = APIConfig()
        config_data = config.get_all_config()
        
        # 直接返回API Key，不加密
        return jsonify(config_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/save_config', methods=['POST'])
def save_config():
    """保存 API 配置"""
    try:
        data = request.json
        config = APIConfig()
        
        # 更新配置
        update_data = {}
        if data.get('api_key'):
            update_data['api_key'] = data['api_key']
        if data.get('base_url'):
            update_data['base_url'] = data['base_url']
        if data.get('model_provider'):
            update_data['model_provider'] = data['model_provider']
        if data.get('model_name'):
            update_data['model_name'] = data['model_name']
        if data.get('temperature') is not None:
            update_data['temperature'] = data['temperature']
        if data.get('max_tokens'):
            update_data['max_tokens'] = data['max_tokens']
        if data.get('default_system_prompt'):
            update_data['default_system_prompt'] = data['default_system_prompt']
        
        success = config.update_config(**update_data)
        
        if success:
            return jsonify({'success': True, 'message': '配置保存成功'})
        else:
            return jsonify({'success': False, 'error': '配置保存失败'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/test_connection', methods=['GET', 'POST'])
def test_connection():
    """测试 API 连接"""
    try:
        config = APIConfig()
        
        if request.method == 'POST':
            # POST方法：使用提交的临时配置
            data = request.json
            config.update_config(
                api_key=data.get('api_key'),
                base_url=data.get('base_url'),
                model_name=data.get('model_name')
            )
        # GET方法：使用当前保存的配置
        
        # 获取配置信息
        config_data = config.get_all_config()
        
        # 尝试创建客户端并发送测试请求
        client = UniversalAPIClient(config)
        
        # 发送一个简单的测试请求
        response = client.chat(
            user_message="Hello",
            max_tokens=10
        )
        
        return jsonify({
            'success': True,
            'message': '连接测试成功',
            'base_url': config_data.get('base_url'),
            'model': config_data.get('model_name'),
            'response': response
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/validate_config', methods=['GET'])
def validate_config():
    """验证当前配置是否有效"""
    try:
        config = APIConfig()
        is_valid, message = config.validate_config()
        
        return jsonify({
            'valid': is_valid,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': str(e)
        }), 500


@api_bp.route('/export_config', methods=['GET'])
def export_config():
    """导出配置（不包含敏感信息）"""
    try:
        config = APIConfig()
        import tempfile
        import os
        from flask import send_file
        
        # 创建临时文件
        temp_file = os.path.join(tempfile.gettempdir(), 'api_config.json')
        
        if config.export_config(temp_file):
            return send_file(
                temp_file,
                as_attachment=True,
                download_name='api_config.json',
                mimetype='application/json'
            )
        else:
            return jsonify({'error': '导出配置失败'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
