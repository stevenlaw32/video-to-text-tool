"""
视频链接解析路由模块
提供视频链接解析和下载的 API 接口
"""

from flask import Blueprint, request, jsonify
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from local_video_parser import LocalVideoParser
from video_transcriber import VideoTranscriber
from api_client import UniversalAPIClient

logger = logging.getLogger(__name__)

video_link_bp = Blueprint('video_link', __name__, url_prefix='/api/video-link')

# 初始化解析器
parser = LocalVideoParser()
transcriber = VideoTranscriber()


@video_link_bp.route('/parse', methods=['POST'])
def parse_video_link():
    """
    解析视频链接
    
    请求参数:
        - url: 视频链接（必需）
    
    返回:
        视频信息（标题、作者、下载地址等）
    """
    try:
        data = request.json
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: url'
            }), 400
        
        url = data.get('url')
        
        # 使用本地解析器解析
        result = asyncio.run(parser.parse(url))
        
        return jsonify(result), 200 if result.get('success') else 400
            
    except Exception as e:
        logger.error(f"解析视频链接失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_link_bp.route('/parse-and-transcribe', methods=['POST'])
def parse_and_transcribe():
    """
    视频解析 + 转录的完整流程
    
    请求参数:
        - url: 视频链接（必需）
        - whisper_model: Whisper 模型（可选，默认 'base'）
        - language: 语言（可选，默认 'zh'）
        - enable_ai: 是否启用 AI 整理（可选，默认 True）
    
    返回:
        完整的处理结果
    """
    try:
        data = request.json
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: url'
            }), 400
        
        url = data.get('url')
        whisper_model = data.get('whisper_model', 'base')
        language = data.get('language', 'zh')
        enable_ai = data.get('enable_ai', True)
        
        # 步骤 1: 解析视频链接
        logger.info(f"步骤 1/4: 解析视频链接...")
        parse_result = asyncio.run(parser.parse(url))
        
        if not parse_result.get('success'):
            return jsonify(parse_result), 400
        
        platform = parse_result['platform']
        title = parse_result.get('title', 'untitled')
        author = parse_result.get('author', 'unknown')
        video_url = parse_result.get('video_url', '')
        
        if not video_url:
            return jsonify({
                'success': False,
                'error': '未获取到视频下载地址'
            }), 400
        
        # 步骤 2: 下载视频
        logger.info(f"步骤 2/4: 下载视频...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = _safe_filename(title)
        video_filename = f"{platform}_{safe_title}_{timestamp}.mp4"
        
        temp_dir = Path('temp_videos')
        temp_dir.mkdir(exist_ok=True)
        video_path = temp_dir / video_filename
        
        download_result = asyncio.run(parser.download_video(video_url, str(video_path)))
        
        if not download_result.get('success'):
            return jsonify({
                'success': False,
                'error': f"下载失败: {download_result.get('error')}"
            }), 400
        
        # 步骤 3: 转录视频
        logger.info(f"步骤 3/4: 转录视频...")
        transcript_result = transcriber.transcribe(
            str(video_path),
            model=whisper_model,
            language=language
        )
        
        if not transcript_result.get('text'):
            return jsonify({
                'success': False,
                'error': '转录失败'
            }), 400
        
        transcript_text = transcript_result['text']
        
        # 保存转录文本
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        transcript_file = output_dir / f"{safe_title}_transcript.txt"
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"标题: {title}\n")
            f.write(f"作者: {author}\n")
            f.write(f"平台: {platform}\n")
            f.write(f"链接: {url}\n")
            f.write(f"\n{'='*50}\n\n")
            f.write(transcript_text)
        
        result = {
            'success': True,
            'title': title,
            'author': author,
            'platform': platform,
            'video_file': str(video_path),
            'transcript_file': str(transcript_file),
            'transcript': transcript_text
        }
        
        # 步骤 4: AI 整理（可选）
        if enable_ai:
            logger.info(f"步骤 4/4: AI 整理...")
            try:
                api_client = UniversalAPIClient()
                
                prompt = f"""请将以下视频转录内容整理成结构化的文档。

视频信息：
- 标题：{title}
- 作者：{author}
- 平台：{platform}

转录内容：
{transcript_text}

请整理成以下格式：
1. 内容概述
2. 主要内容（分点列出）
3. 重点总结
"""
                
                ai_result = api_client.chat(prompt)
                
                # 保存 AI 整理结果
                ai_file = output_dir / f"{safe_title}_summary.md"
                with open(ai_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {title}\n\n")
                    f.write(f"**作者**: {author}  \n")
                    f.write(f"**平台**: {platform}  \n")
                    f.write(f"**链接**: {url}  \n\n")
                    f.write("---\n\n")
                    f.write(ai_result)
                
                result['ai_summary_file'] = str(ai_file)
                logger.info(f"✓ AI 整理完成")
                
            except Exception as e:
                logger.warning(f"AI 整理失败: {e}")
        
        return jsonify(result), 200
            
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _safe_filename(filename: str, max_length: int = 50) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
        
    Returns:
        安全的文件名
    """
    # 移除不安全字符
    safe_chars = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '中'))
    safe_chars = safe_chars.strip()
    
    # 限制长度
    if len(safe_chars) > max_length:
        safe_chars = safe_chars[:max_length]
    
    return safe_chars or 'untitled'
