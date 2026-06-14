"""
音频提取路由模块
提供音频提取相关的API接口
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from audio_extractor import AudioExtractor
import os
import tempfile
import io
import zipfile
import logging

logger = logging.getLogger(__name__)

audio_bp = Blueprint('audio', __name__, url_prefix='/api/audio')
extractor = AudioExtractor()


@audio_bp.route('/extract_file', methods=['POST'])
def extract_audio_file():
    """
    通过上传文件提取音频API（FormData方式）
    
    请求参数 (multipart/form-data):
        - file: 视频文件
        - format: 输出格式 (默认: mp3)
        - bitrate: 比特率 (默认: 192k)
        - sample_rate: 采样率 (默认: 44100)
    
    返回:
        JSON格式的提取结果，含 download_url 和 filename
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '缺少文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400
        
        output_format = request.form.get('format', 'mp3')
        bitrate = request.form.get('bitrate', '192k')
        sample_rate = int(request.form.get('sample_rate', 44100))
        
        # 保存上传的文件到临时目录
        safe_name = secure_filename(file.filename)
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, safe_name)
        file.save(tmp_path)
        
        logger.info(f"收到文件上传提取请求: {safe_name}")
        
        result = extractor.extract_audio(
            video_path=tmp_path,
            output_format=output_format,
            bitrate=bitrate,
            sample_rate=sample_rate
        )
        
        # 清理临时文件
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass
        
        if result['success']:
            filename = result['output_filename']
            return jsonify({
                'success': True,
                'download_url': f'/api/audio/download/{filename}',
                'filename': filename,
                'file_size': result['file_size']
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"文件上传提取API错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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


@audio_bp.route('/download_zip', methods=['POST'])
def download_zip():
    """
    将指定的音频文件打包成ZIP下载
    
    请求参数:
        - filenames: 文件名列表（可选，为空则打包全部）
    
    返回:
        ZIP文件
    """
    try:
        data = request.json or {}
        filenames = data.get('filenames', [])
        
        # 如果没指定文件名，打包全部输出文件
        if not filenames:
            all_files = extractor.list_output_files()
            filenames = [f['filename'] for f in all_files]
        
        if not filenames:
            return jsonify({
                'success': False,
                'error': '没有可下载的文件'
            }), 400
        
        # 获取实际存在的文件列表（白名单）
        existing_files = {f['filename'] for f in extractor.list_output_files()}
        
        # 创建内存中的ZIP
        zip_buffer = io.BytesIO()
        added_count = 0
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in filenames:
                # 直接匹配磁盘上的文件名，不再二次 secure_filename
                if fname in existing_files:
                    file_path = os.path.join(extractor.output_dir, fname)
                    if os.path.exists(file_path):
                        zf.write(file_path, fname)
                        added_count += 1
                else:
                    logger.warning(f"ZIP打包跳过（文件不存在）: {fname}")
        
        if added_count == 0:
            return jsonify({
                'success': False,
                'error': '没有找到任何文件'
            }), 404
        
        zip_buffer.seek(0)
        logger.info(f"批量下载ZIP: {added_count} 个文件")
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='audio_files.zip'
        )
        
    except Exception as e:
        logger.error(f"ZIP下载错误: {str(e)}")
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
