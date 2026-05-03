"""
OCR API 配置路由
"""
from flask import Blueprint, request, jsonify
from ocr_config import OCRConfig

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api/ocr')

# 全局配置实例
ocr_config = OCRConfig()


@ocr_bp.route('/providers', methods=['GET'])
def get_providers():
    """获取所有 OCR 提供商配置"""
    try:
        providers = ocr_config.get_all_providers()
        active = ocr_config.get_active_provider()
        
        return jsonify({
            'success': True,
            'providers': providers,
            'active_provider': active
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/providers/available', methods=['GET'])
def get_available_providers():
    """获取所有可用的（已配置的）提供商"""
    try:
        available = ocr_config.get_available_providers()
        return jsonify({
            'success': True,
            'providers': available
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/providers/<provider>', methods=['GET'])
def get_provider(provider):
    """获取指定提供商的配置"""
    try:
        config = ocr_config.get_provider_config(provider)
        if config:
            # 隐藏敏感信息
            safe_config = config.copy()
            for key in ['api_key', 'secret_key', 'secret_id', 'access_key_id', 'access_key_secret']:
                if key in safe_config and safe_config[key]:
                    # 只显示前4位和后4位
                    value = safe_config[key]
                    if len(value) > 8:
                        safe_config[key] = value[:4] + '*' * (len(value) - 8) + value[-4:]
                    else:
                        safe_config[key] = '*' * len(value)
            
            return jsonify({
                'success': True,
                'provider': provider,
                'config': safe_config
            })
        else:
            return jsonify({
                'success': False,
                'error': '提供商不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/providers/<provider>', methods=['POST'])
def update_provider(provider):
    """更新提供商配置"""
    try:
        data = request.json
        
        # 验证必填字段
        if provider == "baidu":
            if not data.get('api_key') or not data.get('secret_key'):
                return jsonify({
                    'success': False,
                    'error': '百度 OCR 需要提供 api_key 和 secret_key'
                }), 400
        elif provider == "tencent":
            if not data.get('secret_id') or not data.get('secret_key'):
                return jsonify({
                    'success': False,
                    'error': '腾讯云 OCR 需要提供 secret_id 和 secret_key'
                }), 400
        elif provider == "aliyun":
            if not data.get('access_key_id') or not data.get('access_key_secret'):
                return jsonify({
                    'success': False,
                    'error': '阿里云 OCR 需要提供 access_key_id 和 access_key_secret'
                }), 400
        
        # 更新配置
        success = ocr_config.update_provider_config(provider, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{provider} 配置已更新'
            })
        else:
            return jsonify({
                'success': False,
                'error': '更新配置失败'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/active', methods=['GET'])
def get_active():
    """获取当前激活的提供商"""
    try:
        active = ocr_config.get_active_provider()
        config = ocr_config.get_provider_config(active)
        
        return jsonify({
            'success': True,
            'active_provider': active,
            'provider_name': config.get('name', '') if config else ''
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/active', methods=['POST'])
def set_active():
    """设置激活的提供商"""
    try:
        data = request.json
        provider = data.get('provider')
        
        if not provider:
            return jsonify({
                'success': False,
                'error': '请指定提供商'
            }), 400
        
        # 检查是否已配置
        if not ocr_config.is_provider_configured(provider):
            return jsonify({
                'success': False,
                'error': f'{provider} 尚未配置，请先配置 API 密钥'
            }), 400
        
        success = ocr_config.set_active_provider(provider)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'已切换到 {provider}'
            })
        else:
            return jsonify({
                'success': False,
                'error': '切换失败'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ocr_bp.route('/test/<provider>', methods=['POST'])
def test_provider(provider):
    """测试 OCR API 连接"""
    try:
        import cv2
        import numpy as np
        from cloud_ocr import CloudOCRProcessor
        
        # 获取配置
        config = ocr_config.get_provider_config(provider)
        if not config:
            return jsonify({
                'success': False,
                'error': '提供商不存在'
            }), 404
        
        if provider == "surya":
            return jsonify({
                'success': True,
                'message': 'Surya OCR 是本地模型，无需测试连接'
            })
        
        # 检查是否已配置
        if not ocr_config.is_provider_configured(provider):
            return jsonify({
                'success': False,
                'error': f'{provider} 尚未配置完整'
            }), 400
        
        # 创建测试图像（包含文字 "测试"）
        test_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
        cv2.putText(test_image, "Test OCR", (20, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # 测试 OCR
        processor = CloudOCRProcessor(provider, config)
        result = processor.ocr.recognize_image(test_image)
        
        return jsonify({
            'success': True,
            'message': f'{config["name"]} 连接成功',
            'test_result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'连接失败: {str(e)}'
        }), 500
