"""
视频链接解析路由模块
提供视频链接解析和下载的 API 接口
"""

from flask import Blueprint, request, jsonify, send_file
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from local_video_parser import LocalVideoParser
from video_transcriber import VideoTranscriber
from api_client import UniversalAPIClient

logger = logging.getLogger(__name__)

video_link_bp = Blueprint('video_link', __name__, url_prefix='/api/video-link')

# 初始化解析器
parser = LocalVideoParser()
transcriber = VideoTranscriber()
DOWNLOAD_DIR = Path('temp_videos/link_downloads')
ARTIFACT_ROOTS = {
    'downloads': DOWNLOAD_DIR,
    'temp': Path('temp_videos'),
    'output': Path('output'),
}


def _artifact_url(kind: str, file_path: Path) -> str:
    return f"/api/video-link/artifact/{kind}/{quote(file_path.name)}"


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


@video_link_bp.route('/download', methods=['POST'])
def download_video_link():
    """
    使用本地下载器下载视频链接到本地，并返回可点击的下载地址。
    """
    try:
        data = request.json

        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: url'
            }), 400

        result = asyncio.run(parser.download(data.get('url'), str(DOWNLOAD_DIR)))
        if not result.get('success'):
            return jsonify(result), 400

        file_path = Path(result['file_path'])
        result['download_url'] = _artifact_url('downloads', file_path)
        result['download_filename'] = file_path.name
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"下载视频链接失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_link_bp.route('/artifact/<kind>/<path:filename>', methods=['GET'])
def download_artifact(kind, filename):
    """下载链接处理过程中生成的视频、转录文本或摘要文件。"""
    try:
        if kind not in ARTIFACT_ROOTS:
            return jsonify({
                'success': False,
                'error': '未知文件类型'
            }), 404

        base = ARTIFACT_ROOTS[kind].resolve()
        requested = (base / Path(filename).name).resolve()

        try:
            requested.relative_to(base)
        except ValueError:
            return jsonify({
                'success': False,
                'error': '非法文件路径'
            }), 400

        if not requested.exists():
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

        return send_file(requested, as_attachment=True, download_name=requested.name)
    except Exception as e:
        logger.error(f"发送文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_link_bp.route('/transcribe-downloaded', methods=['POST'])
def transcribe_downloaded_video():
    """
    对“仅下载”模式已经下载好的视频继续做转录和可选 AI 整理。
    """
    try:
        data = request.json

        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: filename'
            }), 400

        base = DOWNLOAD_DIR.resolve()
        video_path = (base / Path(data.get('filename')).name).resolve()
        try:
            video_path.relative_to(base)
        except ValueError:
            return jsonify({
                'success': False,
                'error': '非法文件路径'
            }), 400

        if not video_path.exists():
            return jsonify({
                'success': False,
                'error': '视频文件不存在，请重新下载'
            }), 404

        result = _transcribe_and_summarize(
            video_path=video_path,
            source_url=data.get('source_url', ''),
            title=data.get('title') or video_path.stem,
            author=data.get('author') or 'unknown',
            platform=data.get('platform') or 'video',
            whisper_model=data.get('whisper_model', 'base'),
            language=data.get('language', 'zh'),
            enable_ai=data.get('enable_ai', True),
            video_kind='downloads',
        )
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"转录已下载视频失败: {str(e)}")
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
        
        # 步骤 1: 下载视频（抖音专用路径，其它平台走 yt-dlp）
        logger.info(f"步骤 1/3: 下载视频...")
        temp_dir = Path('temp_videos')
        temp_dir.mkdir(exist_ok=True)
        
        download_result = asyncio.run(parser.download(url, str(temp_dir)))
        
        if not download_result.get('success'):
            return jsonify({
                'success': False,
                'error': f"下载失败: {download_result.get('error')}"
            }), 400

        platform = download_result.get('platform', 'video')
        title = download_result.get('title', 'untitled')
        author = download_result.get('author', 'unknown')
        safe_title = _safe_filename(title)
        video_path = Path(download_result['file_path'])
        
        result = _transcribe_and_summarize(
            video_path=video_path,
            source_url=url,
            title=title,
            author=author,
            platform=platform,
            whisper_model=whisper_model,
            language=language,
            enable_ai=enable_ai,
            video_kind='temp',
        )
        
        return jsonify(result), 200
            
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _transcribe_and_summarize(
    video_path: Path,
    source_url: str,
    title: str,
    author: str,
    platform: str,
    whisper_model: str,
    language: str,
    enable_ai: bool,
    video_kind: str,
) -> dict:
    """执行视频转录，并在需要时调用大模型整理。"""
    safe_title = _safe_filename(title)

    logger.info("步骤 2/3: 转录视频...")
    active_transcriber = transcriber
    if getattr(active_transcriber, 'model_size', 'base') != whisper_model:
        active_transcriber = VideoTranscriber(model_size=whisper_model)

    transcript_result = active_transcriber.process_video(
        str(video_path),
        language=language
    )

    if not transcript_result.get('text'):
        raise RuntimeError('转录失败：没有识别到文本')

    transcript_text = transcript_result['text']

    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    transcript_file = output_dir / f"{safe_title}_transcript.txt"

    with open(transcript_file, 'w', encoding='utf-8') as f:
        f.write(f"标题: {title}\n")
        f.write(f"作者: {author}\n")
        f.write(f"平台: {platform}\n")
        f.write(f"链接: {source_url}\n")
        f.write(f"\n{'='*50}\n\n")
        f.write(transcript_text)

    result = {
        'success': True,
        'title': title,
        'author': author,
        'platform': platform,
        'video_file': str(video_path),
        'video_download_url': _artifact_url(video_kind, video_path),
        'transcript_file': str(transcript_file),
        'transcript_download_url': _artifact_url('output', transcript_file),
        'transcript': transcript_text,
    }

    if enable_ai:
        logger.info("步骤 3/3: AI 整理...")
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

            ai_file = output_dir / f"{safe_title}_summary.md"
            with open(ai_file, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**作者**: {author}  \n")
                f.write(f"**平台**: {platform}  \n")
                f.write(f"**链接**: {source_url}  \n\n")
                f.write("---\n\n")
                f.write(ai_result)

            result['ai_summary_file'] = str(ai_file)
            result['ai_summary_download_url'] = _artifact_url('output', ai_file)
            logger.info("✓ AI 整理完成")

        except Exception as e:
            logger.exception(f"AI 整理失败: {e}")
            result['ai_summary_error'] = str(e)

    return result


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
