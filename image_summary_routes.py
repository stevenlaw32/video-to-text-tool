"""
图片识别总结路由模块
支持批量上传图片，使用已配置的云端 OCR 识别文字后调用大模型整理。
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from openai import OpenAI
from openai_compat import complete_text
from models_config import ModelsConfig
import json
import logging
import os
import queue
import tempfile
import time
from importlib.util import find_spec

logger = logging.getLogger(__name__)

image_summary_bp = Blueprint('image_summary', __name__, url_prefix='/api/image_summary')

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'}
ALLOWED_IMAGE_FORMATS = {'PNG', 'JPEG', 'BMP', 'WEBP', 'TIFF'}
MAX_IMAGE_FILES = 30
MAX_IMAGE_SIZE = 15 * 1024 * 1024
MAX_TOTAL_IMAGE_SIZE = 150 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_SIDE = 12000
MAX_MERGE_TEXT_CHARS = 60000


class ImageLogStream:
    def __init__(self):
        self.log_queue = queue.Queue()
        self.active = False

    def start(self):
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break
        self.active = True

    def stop(self):
        self.active = False

    def add_log(self, message, log_type='info'):
        if self.active:
            self.log_queue.put({'message': message, 'type': log_type})

    def get_logs(self, timeout=0.5, max_wait_time=600):
        start_wait = time.time()
        last_heartbeat = time.time()
        while not self.active:
            if time.time() - start_wait > max_wait_time:
                break
            if time.time() - last_heartbeat > 30:
                yield {'message': '等待处理开始...', 'type': 'info'}
                last_heartbeat = time.time()
            time.sleep(0.5)
        while self.active or not self.log_queue.empty():
            try:
                yield self.log_queue.get(timeout=timeout)
            except queue.Empty:
                if not self.active:
                    break
                if time.time() - last_heartbeat > 30:
                    yield {'message': '处理中...', 'type': 'info'}
                    last_heartbeat = time.time()


image_log = ImageLogStream()


def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _format_bytes(size):
    units = ['B', 'KB', 'MB', 'GB']
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != 'B' else f"{int(value)} B"
        value /= 1024


def _inspect_image_file(file_path):
    """校验真实图片格式和尺寸，避免伪装扩展名或超大图片拖垮 OCR。"""
    try:
        from PIL import Image
    except ImportError as e:
        raise ImportError('图片校验需要 Pillow，请先运行环境安装脚本或 pip install pillow') from e

    try:
        with Image.open(file_path) as image:
            image_format = image.format
            width, height = image.size
    except Exception as e:
        raise ValueError('无法读取图片元信息，请确认文件未损坏') from e

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValueError(f'不支持的图片格式: {image_format or "未知"}')

    pixels = width * height
    if pixels > MAX_IMAGE_PIXELS:
        raise ValueError(
            f'图片像素过大: {width}x{height}，上限约 {MAX_IMAGE_PIXELS // 1_000_000}MP'
        )
    if width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE:
        raise ValueError(
            f'图片边长过大: {width}x{height}，单边上限 {MAX_IMAGE_SIDE}px'
        )

    return {
        'format': image_format,
        'width': width,
        'height': height,
        'pixels': pixels
    }


def _get_ocr_processor():
    """读取当前 OCR 配置并返回云端 OCR 处理器。"""
    from ocr_config import OCRConfig

    ocr_config = OCRConfig()
    provider = ocr_config.get_active_provider()
    provider_config = ocr_config.get_provider_config(provider)

    if provider not in ('baidu', 'tencent', 'aliyun'):
        raise ValueError('图片识别当前使用云端 OCR，请在 OCR 配置中切换到百度、腾讯云或阿里云')
    if not ocr_config.is_provider_configured(provider):
        raise ValueError(f'{provider_config.get("name", provider)} 尚未配置完整，请先在 OCR 配置中填写密钥')
    if provider == 'aliyun' and not find_spec('alibabacloud_ocr_api20210707'):
        raise ImportError('阿里云 OCR SDK 未安装，请运行 pip install alibabacloud-ocr-api20210707 后再使用阿里云 OCR')

    try:
        from cloud_ocr import CloudOCRProcessor
    except ImportError as e:
        raise ImportError('云端 OCR 需要安装 opencv-python 和 numpy，请先运行环境安装脚本或 pip install opencv-python numpy') from e

    return CloudOCRProcessor(provider, provider_config), provider_config.get('name', provider)


def _extract_text_from_image(file_path, processor=None, provider_name=None):
    """使用 OpenCV 读取图片并调用云端 OCR。"""
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise ImportError('图片 OCR 需要安装 opencv-python 和 numpy，请先运行环境安装脚本或 pip install opencv-python numpy') from e

    if processor is None or provider_name is None:
        processor, provider_name = _get_ocr_processor()

    img_data = np.fromfile(file_path, dtype=np.uint8)
    image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('无法读取图片，请确认文件未损坏')

    texts = processor.ocr.recognize_image(image)
    lines = []
    for text in texts or []:
        normalized = text.strip()
        if normalized:
            lines.append(normalized)

    return {
        'text': '\n'.join(lines),
        'line_count': len(lines),
        'provider_name': provider_name
    }


def _get_ai_client(model_alias):
    models_config = ModelsConfig()
    model_config = models_config.get_model_by_alias(model_alias)

    if model_config:
        client = OpenAI(
            api_key=model_config['api_key'],
            base_url=model_config['base_url']
        )
        model_name = model_config['model_name']
        custom_prompt = model_config.get('custom_prompt', '')
        max_tokens = model_config.get('max_tokens')
        temperature = model_config.get('temperature')
        reasoning_effort = model_config.get('reasoning_effort')
        api_mode = model_config.get('api_mode', 'auto')
        prompt_cache_ttl = model_config.get('prompt_cache_ttl', 'auto')
        service_tier = model_config.get('service_tier', 'auto')
    else:
        client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL')
        )
        model_name = os.getenv('MODEL_NAME', 'gpt-4o')
        custom_prompt = ''
        max_tokens = None
        temperature = None
        reasoning_effort = os.getenv('REASONING_EFFORT', 'auto')
        api_mode = os.getenv('OPENAI_API_MODE', 'auto')
        prompt_cache_ttl = os.getenv('PROMPT_CACHE_TTL', 'auto')
        service_tier = os.getenv('SERVICE_TIER', 'auto')

    return (
        client, model_name, custom_prompt, max_tokens, temperature,
        reasoning_effort, api_mode, prompt_cache_ttl, service_tier
    )


def _build_image_prompt(text, title, custom_prompt=None):
    if custom_prompt:
        if '{transcript}' in custom_prompt:
            return custom_prompt.replace('{transcript}', text)
        return custom_prompt + '\n\n---\n\n图片 OCR 文字：\n' + text

    t = title or '图片内容'
    return f"""# 标题：{t}

# Role
你是一位擅长从图片资料中提取信息、还原上下文并整理知识的内容分析助手。

# Task
请根据下面的图片 OCR 文字，整理成一份结构清晰、信息密度高的 Markdown 笔记。

# Requirements
- 先判断图片的内容类型，例如截图、海报、课程页、PPT、表格、聊天记录、票据或网页片段。
- 保留关键数字、日期、名称、步骤、结论、限制条件和行动项。
- OCR 可能存在断行、错别字或顺序错乱，请在不编造原文没有的信息的前提下做合理校正和重组。
- 如果多张图片合并处理，请按图片来源组织内容，再给出总体提炼。
- 结尾输出“核心提炼”和“可执行事项”；如果信息不足，请明确说明不足点。

# 图片 OCR 文字
{text}
"""


@image_summary_bp.route('/stream_logs')
def stream_image_logs():
    def generate():
        for log in image_log.get_logs():
            yield f"data: {json.dumps(log)}\n\n"
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@image_summary_bp.route('/upload', methods=['POST'])
def upload_images():
    """上传图片并识别文字。"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': '缺少文件'}), 400

        files = request.files.getlist('files')
        if len(files) > MAX_IMAGE_FILES:
            return jsonify({
                'success': False,
                'error': f'一次最多上传 {MAX_IMAGE_FILES} 张图片'
            }), 400

        if request.content_length and request.content_length > MAX_TOTAL_IMAGE_SIZE:
            return jsonify({
                'success': False,
                'error': f'图片总大小超出限制，最多 {_format_bytes(MAX_TOTAL_IMAGE_SIZE)}'
            }), 400

        results = []
        total_saved_size = 0
        processor = None
        provider_name = None

        for file in files:
            if not file or not file.filename:
                continue
            if not allowed_image(file.filename):
                results.append({
                    'name': file.filename,
                    'success': False,
                    'error': f'不支持的格式，仅支持: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}'
                })
                continue

            if processor is None or provider_name is None:
                try:
                    processor, provider_name = _get_ocr_processor()
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)}), 400

            safe_name = secure_filename(file.filename)
            tmp_dir = tempfile.mkdtemp()
            tmp_path = os.path.join(tmp_dir, safe_name)
            file.save(tmp_path)

            try:
                file_size = os.path.getsize(tmp_path)
                total_saved_size += file_size
                if file_size > MAX_IMAGE_SIZE:
                    raise ValueError(f'图片过大: {_format_bytes(file_size)}，单张上限 {_format_bytes(MAX_IMAGE_SIZE)}')
                if total_saved_size > MAX_TOTAL_IMAGE_SIZE:
                    raise ValueError(f'图片总大小超出限制，最多 {_format_bytes(MAX_TOTAL_IMAGE_SIZE)}')

                image_info = _inspect_image_file(tmp_path)
                extracted = _extract_text_from_image(tmp_path, processor=processor, provider_name=provider_name)
                text = extracted['text']
                if not text.strip():
                    raise ValueError('未识别到有效文字')
                results.append({
                    'name': file.filename,
                    'success': True,
                    'text': text,
                    'char_count': len(text),
                    'line_count': extracted['line_count'],
                    'provider_name': extracted['provider_name'],
                    'width': image_info['width'],
                    'height': image_info['height']
                })
            except Exception as e:
                results.append({
                    'name': file.filename,
                    'success': False,
                    'error': str(e)
                })
            finally:
                try:
                    os.remove(tmp_path)
                    os.rmdir(tmp_dir)
                except OSError:
                    pass

        return jsonify({
            'success': True,
            'files': results,
            'total': len(results),
            'succeeded': sum(1 for r in results if r.get('success')),
            'failed': sum(1 for r in results if not r.get('success'))
        })

    except Exception as e:
        logger.error(f"图片上传识别错误: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@image_summary_bp.route('/summarize', methods=['POST'])
def summarize_images():
    """调用大模型对图片 OCR 文本进行总结。"""
    try:
        data = request.json
        if not data or not data.get('images'):
            return jsonify({'success': False, 'error': '缺少图片文字内容'}), 400

        images = data['images']
        model_alias = data.get('model_alias', '')
        user_prompt = data.get('custom_prompt', '')
        merge = data.get('merge', True)

        (
            client, model_name, model_prompt, max_tokens, temperature,
            reasoning_effort, api_mode, prompt_cache_ttl, service_tier
        ) = _get_ai_client(model_alias)
        effective_prompt = user_prompt or model_prompt or None

        image_log.start()
        image_log.add_log("═" * 40, "header")
        image_log.add_log("🚀 开始图片文字总结任务", "header")
        image_log.add_log(f"🖼️ 图片数: {len(images)}  |  模型: {model_name}", "info")
        temperature_label = temperature if temperature is not None else '模型默认'
        params_info = f"📋 模式: {'合并成一份' if merge else '分开处理'}  |  温度: {temperature_label}"
        if max_tokens:
            params_info += f"  |  max_tokens: {max_tokens}"
        image_log.add_log(params_info, "info")
        image_log.add_log("═" * 40, "header")

        def _call_ai(prompt_text, label=""):
            t0 = time.time()
            if label:
                image_log.add_log(f"📡 调用 AI: {label}", "info")
            text = complete_text(
                client,
                model=model_name,
                user_message=prompt_text,
                developer_prompt="你是一个专业的图片文字分析和内容整理助手。",
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_effort=reasoning_effort,
                api_mode=api_mode,
                prompt_cache_ttl=prompt_cache_ttl,
                service_tier=service_tier
            )
            elapsed = time.time() - t0
            image_log.add_log(f"✓ 完成，用时 {elapsed:.1f}s，输出 {len(text)} 字符", "success")
            return text

        if merge:
            image_log.add_log("📝 合并模式：将所有图片文字合并后一次性调用 AI...", "info")
            combined = '\n\n'.join([
                f"## {img['name']}\n\n{img['text']}"
                for img in images
            ])
            image_log.add_log(f"📊 合并文本总长: {len(combined)} 字符", "info")
            if len(combined) > MAX_MERGE_TEXT_CHARS:
                image_log.add_log(
                    f"⚠️ 合并文本超过 {MAX_MERGE_TEXT_CHARS} 字符，请切换为分开处理或减少图片数量",
                    "warning"
                )
                image_log.stop()
                return jsonify({
                    'success': False,
                    'error': f'合并文本过长（{len(combined)} 字符），请切换“分开处理”或减少图片数量后重试',
                    'code': 'merge_text_too_long',
                    'char_count': len(combined),
                    'max_chars': MAX_MERGE_TEXT_CHARS
                }), 400

            prompt = _build_image_prompt(combined, '多图片合并', effective_prompt)
            summary = _call_ai(prompt, "合并总结")

            image_log.add_log("═" * 40, "header")
            image_log.add_log("🎉 图片总结完成！", "success")
            image_log.add_log("═" * 40, "header")
            image_log.stop()

            return jsonify({
                'success': True,
                'mode': 'merge',
                'summary': summary
            })

        results = []
        total = len(images)
        for i, img in enumerate(images):
            image_log.add_log("─" * 30, "info")
            image_log.add_log(f"🖼️ [{i+1}/{total}] {img['name']}", "info")
            image_log.add_log(f"   文本长度: {len(img['text'])} 字符", "info")
            try:
                prompt = _build_image_prompt(img['text'], img['name'], effective_prompt)
                summary = _call_ai(prompt, img['name'])
                results.append({
                    'name': img['name'],
                    'success': True,
                    'summary': summary
                })
            except Exception as e:
                image_log.add_log(f"❌ 失败: {e}", "error")
                results.append({
                    'name': img['name'],
                    'success': False,
                    'error': str(e)
                })

        succeeded = sum(1 for r in results if r['success'])
        failed = total - succeeded
        image_log.add_log("═" * 40, "header")
        image_log.add_log(f"🎉 全部完成！成功 {succeeded} / 失败 {failed} / 共 {total}", "success")
        image_log.add_log("═" * 40, "header")
        image_log.stop()

        return jsonify({
            'success': True,
            'mode': 'split',
            'results': results
        })

    except Exception as e:
        logger.error(f"图片总结错误: {str(e)}")
        image_log.add_log(f"❌ 严重错误: {str(e)}", "error")
        image_log.stop()
        return jsonify({'success': False, 'error': str(e)}), 500
