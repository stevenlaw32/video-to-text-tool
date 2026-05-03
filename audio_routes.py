"""
音频提取路由模块
提供音频提取相关的API接口
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from audio_extractor import AudioExtractor
import os
import logging

logger = logging.getLogger(__name__)

audio_bp = Blueprint('audio', __name__, url_prefix='/api/audio')
extractor = AudioExtractor()


@audio_bp.route('/extract', methods=['POST'])
def extract_audio():
    """
    提取音频API
    
    请求参数:
        - video_path: 视频文件路径
        - format: 输出格式 (默认: mp3)
        - bitrate: 比特率 (默认: 192k)
        - sample_rate: 采样率 (默认: 44100)
    
    返回:
        JSON格式的提取结果
    """
    try:
        data = request.json
        
        if not data or 'video_path' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: video_path'
            }), 400
        
        video_path = data.get('video_path')
        output_format = data.get('format', 'mp3')
        bitrate = data.get('bitrate', '192k')
        sample_rate = int(data.get('sample_rate', 44100))
        custom_filename = data.get('custom_filename')
        
        logger.info(f"收到音频提取请求: {video_path}")
        
        result = extractor.extract_audio(
            video_path=video_path,
            output_format=output_format,
            bitrate=bitrate,
            sample_rate=sample_rate,
            custom_filename=custom_filename
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"音频提取API错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audio_bp.route('/batch_extract', methods=['POST'])
def batch_extract():
    """
    批量提取音频API
    
    请求参数:
        - video_paths: 视频文件路径列表
        - format: 输出格式
        - bitrate: 比特率
        - sample_rate: 采样率
    
    返回:
        JSON格式的批量提取结果
    """
    try:
        data = request.json
        
        if not data or 'video_paths' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: video_paths'
            }), 400
        
        video_paths = data.get('video_paths', [])
        output_format = data.get('format', 'mp3')
        bitrate = data.get('bitrate', '192k')
        sample_rate = int(data.get('sample_rate', 44100))
        
        logger.info(f"收到批量音频提取请求: {len(video_paths)} 个文件")
        
        results = extractor.batch_extract(
            video_paths=video_paths,
            output_format=output_format,
            bitrate=bitrate,
            sample_rate=sample_rate
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'succeeded': sum(1 for r in results if r.get('success')),
            'failed': sum(1 for r in results if not r.get('success'))
        })
        
    except Exception as e:
        logger.error(f"批量音频提取API错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audio_bp.route('/download/<filename>')
def download_audio(filename):
    """
    下载提取的音频文件
    
    参数:
        filename: 文件名
    
    返回:
        音频文件
    """
    try:
        # 安全处理文件名
        safe_filename = secure_filename(filename)
        file_path = os.path.join(extractor.output_dir, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        logger.info(f"下载音频文件: {safe_filename}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename
        )
        
    except Exception as e:
        logger.error(f"下载音频文件错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audio_bp.route('/info/<filename>')
def get_audio_info(filename):
    """
    获取音频文件信息
    
    参数:
        filename: 文件名
    
    返回:
        JSON格式的音频信息
    """
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(extractor.output_dir, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        info = extractor.get_audio_info(file_path)
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"获取音频信息错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audio_bp.route('/list')
def list_output_files():
    """
    列出所有输出的音频文件
    
    返回:
        JSON格式的文件列表
    """
    try:
        files = extractor.list_output_files()
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"列出文件错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audio_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """
    删除音频文件
    
    参数:
        filename: 文件名
    
    返回:
        JSON格式的删除结果
    """
    try:
        safe_filename = secure_filename(filename)
        success = extractor.delete_output_file(safe_filename)
        
        if success:
            return jsonify({
                'success': True,
                'message': '文件已删除'
            })
        else:
            return jsonify({
                'success': False,
                'error': '文件不存在或删除失败'
            }), 404
            
    except Exception as e:
        logger.error(f"删除文件错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
