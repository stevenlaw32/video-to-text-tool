"""
音频提取模块
从视频文件中提取音频并转换为指定格式
"""

import subprocess
import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AudioExtractor:
    """音频提取器"""
    
    def __init__(self, output_dir='audio_output'):
        """
        初始化音频提取器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"音频提取器初始化，输出目录: {output_dir}")
    
    def extract_audio(self, video_path, output_format='mp3', 
                     bitrate='192k', sample_rate=44100, 
                     custom_filename=None):
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_format: 输出格式 (mp3, wav, aac, flac, ogg)
            bitrate: 比特率 (128k, 192k, 320k)
            sample_rate: 采样率 (44100, 48000)
            custom_filename: 自定义输出文件名（不含扩展名）
        
        Returns:
            dict: 包含成功状态、输出路径、文件大小等信息
        """
        try:
            # 验证输入文件
            if not os.path.exists(video_path):
                return {
                    'success': False,
                    'error': f'视频文件不存在: {video_path}'
                }
            
            # 生成输出文件名
            if custom_filename:
                base_name = custom_filename
            else:
                base_name = Path(video_path).stem
            
            output_filename = f"{base_name}.{output_format}"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # 如果文件名已存在，加时间戳后缀避免覆盖
            if os.path.exists(output_path):
                ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                output_filename = f"{base_name}_-_{ts}.{output_format}"
                output_path = os.path.join(self.output_dir, output_filename)
                logger.info(f"文件名冲突，已加时间戳: {output_filename}")
            
            # 根据格式选择编码器
            codec_map = {
                'mp3': 'libmp3lame',
                'wav': 'pcm_s16le',
                'aac': 'aac',
                'flac': 'flac',
                'ogg': 'libvorbis'
            }
            
            codec = codec_map.get(output_format, 'libmp3lame')
            
            # 构建FFmpeg命令
            command = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # 不处理视频流
                '-acodec', codec,
                '-y',  # 覆盖已存在的文件
            ]
            
            # 添加比特率（某些格式不支持）
            if output_format in ['mp3', 'aac', 'ogg']:
                command.extend(['-ab', bitrate])
            
            # 添加采样率
            command.extend(['-ar', str(sample_rate)])
            
            # 添加输出路径
            command.append(output_path)
            
            logger.info(f"开始提取音频: {video_path} -> {output_path}")
            logger.debug(f"FFmpeg命令: {' '.join(command)}")
            
            # 执行FFmpeg命令
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )
            
            # 获取文件信息
            file_size = os.path.getsize(output_path)
            
            logger.info(f"音频提取成功: {output_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'output_path': output_path,
                'output_filename': output_filename,
                'file_size': file_size,
                'format': output_format,
                'bitrate': bitrate,
                'sample_rate': sample_rate
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg执行失败: {e.stderr}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"音频提取失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_audio_info(self, audio_path):
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            dict: 音频信息（时长、码率、采样率等）
        """
        try:
            command = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                audio_path
            ]
            
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )
            
            import json
            info = json.loads(result.stdout)
            
            # 提取音频流信息
            audio_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                return {'success': False, 'error': '未找到音频流'}
            
            format_info = info.get('format', {})
            
            return {
                'success': True,
                'duration': float(format_info.get('duration', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': audio_stream.get('channels', 0),
                'codec': audio_stream.get('codec_name', ''),
                'file_size': int(format_info.get('size', 0))
            }
            
        except Exception as e:
            logger.error(f"获取音频信息失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def batch_extract(self, video_paths, **kwargs):
        """
        批量提取音频
        
        Args:
            video_paths: 视频文件路径列表
            **kwargs: 传递给extract_audio的参数
        
        Returns:
            list: 每个文件的提取结果
        """
        results = []
        for video_path in video_paths:
            result = self.extract_audio(video_path, **kwargs)
            results.append({
                'video_path': video_path,
                **result
            })
        return results
    
    def list_output_files(self):
        """
        列出输出目录中的所有音频文件
        
        Returns:
            list: 文件信息列表
        """
        files = []
        if os.path.exists(self.output_dir):
            for filename in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'filename': filename,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': os.path.getmtime(file_path)
                    })
        return files
    
    def delete_output_file(self, filename):
        """
        删除输出文件
        
        Args:
            filename: 文件名
        
        Returns:
            bool: 是否成功删除
        """
        try:
            file_path = os.path.join(self.output_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除文件: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False
