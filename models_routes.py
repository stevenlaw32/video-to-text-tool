"""
多模型配置管理的API路由
"""

from flask import Blueprint, request, jsonify
from models_config import ModelsConfig
from openai import OpenAI

models_bp = Blueprint('models', __name__, url_prefix='/api/models')


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
            custom_prompt=data.get('custom_prompt', '')
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
        
        success = config.update_model(
            alias=data.get('alias'),
            api_key=data.get('api_key'),
            base_url=data.get('base_url'),
            model_provider=data.get('model_provider'),
            model_name=data.get('model_name'),
            custom_prompt=data.get('custom_prompt')
        )
        
        if success:
            return jsonify({'success': True, 'message': '模型更新成功'})
        else:
            return jsonify({'success': False, 'error': '模型不存在'}), 404
            
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
