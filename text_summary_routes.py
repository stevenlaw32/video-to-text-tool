"""
文本总结路由模块
支持上传 PDF / Word / Markdown 文档，提取文本后调用大模型整理
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from openai import OpenAI
from models_config import ModelsConfig
import os
import json
import time
import queue
import tempfile
import logging
import threading

logger = logging.getLogger(__name__)

text_summary_bp = Blueprint('text_summary', __name__, url_prefix='/api/text_summary')

ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'md', 'txt'}


# ── 独立的文档日志流（不复用视频的单例 LogStream）──
class DocLogStream:
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
                log = self.log_queue.get(timeout=timeout)
                yield log
            except queue.Empty:
                if not self.active:
                    break
                if time.time() - last_heartbeat > 30:
                    yield {'message': '处理中...', 'type': 'info'}
                    last_heartbeat = time.time()
                continue

doc_log = DocLogStream()


def allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS


def extract_text_from_file(file_path, extract_mode='auto'):
    """根据文件类型提取文本
    
    Args:
        file_path: 文件路径
        extract_mode: 提取模式 - auto / markitdown / ocr / pdfplumber
    """
    ext = file_path.rsplit('.', 1)[-1].lower()

    if ext == 'md' or ext == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # ── 强制模式 ──
    if extract_mode == 'markitdown':
        logger.info(f"强制使用 MarkItDown 提取")
        text = _extract_markitdown(file_path)
        if text and text.strip():
            logger.info(f"MarkItDown 提取成功: {len(text)} 字符")
            return text
        raise ValueError('MarkItDown 无法提取有效文本（文件可能是纯图片）')

    if extract_mode == 'ocr':
        logger.info(f"强制使用 OCR 提取")
        if ext == 'pdf':
            text = _extract_pdf_ocr(file_path)
            if text and text.strip():
                logger.info(f"OCR 提取成功: {len(text)} 字符")
                return text
            raise ValueError('OCR 无法提取有效文本（请检查 OCR 配置）')
        raise ValueError(f'OCR 模式仅支持 PDF 文件，当前文件类型: .{ext}')

    if extract_mode == 'pdfplumber':
        logger.info(f"强制使用 pdfplumber 提取")
        if ext == 'pdf':
            text = _extract_pdf_plumber(file_path)
            if text and text.strip():
                logger.info(f"pdfplumber 提取成功: {len(text)} 字符")
                return text
            raise ValueError('pdfplumber 无法提取有效文本（文件可能是纯图片）')
        raise ValueError(f'pdfplumber 仅支持 PDF 文件，当前文件类型: .{ext}')

    # ── 自动模式（三级降级策略）──
    # 第一级：markitdown（支持 PDF / DOCX / PPTX 等）
    text = _extract_markitdown(file_path)
    if text and len(text.strip()) > 50:
        logger.info(f"markitdown 提取成功: {len(text)} 字符")
        return text

    # 第二级：针对 PDF 使用 pdfplumber
    if ext == 'pdf':
        text = _extract_pdf_plumber(file_path)
        if text and len(text.strip()) > 50:
            logger.info(f"pdfplumber 提取成功: {len(text)} 字符")
            return text

    # 第三级：针对 PDF 图片型文档，转图片后 OCR
    if ext == 'pdf':
        text = _extract_pdf_ocr(file_path)
        if text and len(text.strip()) > 10:
            logger.info(f"PDF OCR 提取成功: {len(text)} 字符")
            return text

    # 针对 DOCX 的回退
    if ext in ('doc', 'docx'):
        text = _extract_docx(file_path)
        if text:
            return text

    if text:
        return text
    raise ValueError(f'无法从文件中提取有效文本（可能是纯图片文档且未配置 OCR）')


def _extract_markitdown(file_path):
    """使用微软 markitdown 提取文档内容"""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content if result and result.text_content else ''
    except Exception as e:
        logger.warning(f"markitdown 提取失败: {e}")
        return ''


def _extract_pdf_plumber(file_path):
    """使用 pdfplumber 提取 PDF 文本"""
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
        return '\n\n'.join(texts)
    except Exception as e:
        logger.warning(f"pdfplumber 提取失败: {e}")
        return ''


def _extract_pdf_ocr(file_path):
    """将 PDF 页面渲染为图片，然后使用已配置的云端 OCR 识别"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF 未安装，无法对图片型 PDF 进行 OCR")
        return ''

    # 获取 OCR 配置
    try:
        from ocr_config import OCRConfig
        ocr_config = OCRConfig()
        provider = ocr_config.get_active_provider()
        provider_config = ocr_config.get_provider_config(provider)
        if provider not in ('baidu', 'tencent', 'aliyun'):
            logger.warning(f"当前 OCR 提供商 '{provider}' 不支持，图片型 PDF 需配置百度/腾讯/阿里云 OCR")
            return ''
    except Exception as e:
        logger.warning(f"OCR 配置加载失败: {e}，无法识别图片型 PDF")
        return ''

    try:
        from cloud_ocr import CloudOCRProcessor
        import cv2
        import numpy as np

        processor = CloudOCRProcessor(provider, provider_config)
        doc = fitz.open(file_path)
        all_texts = []

        logger.info(f"PDF OCR: 共 {len(doc)} 页，使用 {provider_config.get('name', provider)} 识别")

        for i, page in enumerate(doc):
            # 渲染页面为图片 (2x 缩放以提高 OCR 精度)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None:
                continue

            try:
                texts = processor.ocr.recognize_image(img)
                page_text = '\n'.join(texts) if texts else ''
                if page_text.strip():
                    all_texts.append(f"[第{i+1}页]\n{page_text}")
                    logger.info(f"  第 {i+1}/{len(doc)} 页: {len(page_text)} 字符")
            except Exception as e:
                logger.warning(f"  第 {i+1} 页 OCR 失败: {e}")

        doc.close()
        return '\n\n'.join(all_texts)

    except Exception as e:
        logger.warning(f"PDF OCR 处理失败: {e}")
        return ''


def _extract_docx(file_path):
    """从 Word 文档提取文本"""
    try:
        from docx import Document
        doc = Document(file_path)
        texts = [para.text for para in doc.paragraphs if para.text.strip()]
        return '\n\n'.join(texts)
    except ImportError:
        raise ImportError('需要安装 Word 解析库：pip install python-docx')


def _get_ai_client(model_alias):
    """根据模型别名获取 AI 客户端配置，返回 (client, model_name, custom_prompt, max_tokens, temperature)"""
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
        temperature = model_config.get('temperature', 0.7)
    else:
        client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL')
        )
        model_name = os.getenv('MODEL_NAME', 'gpt-4o')
        custom_prompt = ''
        max_tokens = None
        temperature = 0.7

    return client, model_name, custom_prompt, max_tokens, temperature


def _build_prompt(text, title, custom_prompt=None):
    """构建提示词"""
    t = title or '文档内容'
    if custom_prompt:
        tpl = custom_prompt
    else:
        tpl = f"""# 标题：{t}

# Role
你是一位精通多领域知识建模的"深度内容架构师"。你的任务是将文档内容加工成一份逻辑严密、细节丰满、且具备极高可读性的 Markdown 深度笔记。

# Core Objective
**信息无损还原**：让从未阅读过原文档的读者，通过阅读本文档，能完全掌握其中的核心逻辑、具体方法论、生动案例以及所有的关键细节，严禁过度简化。

# Task Goals
1. **拒绝干条目**：不仅记录结论，更要保留得出结论的推导过程、背景原因、以及作者使用的类比和例子。
2. **场景与细节复刻**：保留文档中提及的具体参数（如数值、设置）、具体话术（如交友/职场沟通）、以及具体的合规/避坑细节。
3. **结构化重组**：打破零散的文字顺序，按照最符合认知逻辑的结构重新组织内容。

# Processing Logic (Adaptive)
请根据输入内容的本质属性，自动匹配最佳逻辑框架：

1. **【决策/合规/策略类】（侧重逻辑与方案）**：
   - 框架：背景趋势 -> 核心痛点/风险分析 -> 深度解决方案（分点详述） -> 实施建议/风险规避。
2. **【理论/体系/心理类】（侧重概念与理解）**：
   - 框架：核心概念界定 -> 底层原理/逻辑拆解（保留生动类比） -> 现实应用场景 -> 认知升级/延伸思考。
3. **【技能/实操/方法类】（侧重动作与流程）**：
   - 框架：目标设定 -> 详细分步拆解（含操作要点） -> 关键细节/常见错误 -> 进阶技巧/复盘建议。
4. **【观点/启发/思维类】（侧重洞察与改变）**：
   - 框架：现状观察/痛点挖掘 -> 核心思维转折点 -> 行动指南/具体建议 -> 价值升华/金句提炼。

# Content Requirements (Rich & Descriptive)
- **多级标题**：严禁结构扁平。必须根据内容复杂度灵活使用 `##`, `###`, 甚至 `####` 来构建知识索引。
- **案例扩充**：若文档中提到案例、实验或故事，请详细描述其过程、转折和结论，使其具备"故事性"和"说服力"。
- **解释性写作**：保留作者对专业术语的通俗化解释，确保文档对"门外汉"友好。
- **模块化总结**：在每一个二级标题（##）的末尾，添加一个引用块：
  > **💡 核心萃取：** [用一句话提炼本章节的底层逻辑或核心价值，必须具备启发性]

# Tone & Style
- 风格：客观、详尽、富有条理。
- 目标：将"碎片化的文字"转化为"系统化的书面知识体系"。
"""
    if '{transcript}' in tpl:
        return tpl.replace('{transcript}', text)
    return tpl + '\n\n---\n\n文档内容：\n' + text


# ── SSE 日志流端点 ──
@text_summary_bp.route('/stream_logs')
def stream_doc_logs():
    def generate():
        for log in doc_log.get_logs():
            yield f"data: {json.dumps(log)}\n\n"
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@text_summary_bp.route('/upload', methods=['POST'])
def upload_docs():
    """上传文档并提取文本"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': '缺少文件'}), 400

        files = request.files.getlist('files')
        extract_mode = request.form.get('extract_mode', 'auto')
        logger.info(f"文本提取模式: {extract_mode}")
        results = []

        for file in files:
            if not file or not file.filename:
                continue
            if not allowed_doc(file.filename):
                results.append({
                    'name': file.filename,
                    'success': False,
                    'error': f'不支持的格式，仅支持: {", ".join(ALLOWED_DOC_EXTENSIONS)}'
                })
                continue

            safe_name = secure_filename(file.filename)
            tmp_dir = tempfile.mkdtemp()
            tmp_path = os.path.join(tmp_dir, safe_name)
            file.save(tmp_path)

            try:
                text = extract_text_from_file(tmp_path, extract_mode=extract_mode)
                results.append({
                    'name': file.filename,
                    'success': True,
                    'text': text,
                    'char_count': len(text)
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
        logger.error(f"文档上传错误: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@text_summary_bp.route('/summarize', methods=['POST'])
def summarize():
    """调用大模型对文档文本进行总结"""
    try:
        data = request.json
        if not data or not data.get('documents'):
            return jsonify({'success': False, 'error': '缺少文档内容'}), 400

        documents = data['documents']
        model_alias = data.get('model_alias', '')
        user_prompt = data.get('custom_prompt', '')
        merge = data.get('merge', True)

        client, model_name, model_prompt, max_tokens, temperature = _get_ai_client(model_alias)
        effective_prompt = user_prompt or model_prompt or None

        doc_log.start()
        doc_log.add_log("═" * 40, "header")
        doc_log.add_log(f"🚀 开始文本总结任务", "header")
        doc_log.add_log(f"📄 文档数: {len(documents)}  |  模型: {model_name}", "info")
        params_info = f"📋 模式: {'合并成一份' if merge else '分开处理'}  |  温度: {temperature}"
        if max_tokens:
            params_info += f"  |  max_tokens: {max_tokens}"
        doc_log.add_log(params_info, "info")
        doc_log.add_log("═" * 40, "header")

        def _call_ai(prompt_text, label=""):
            t0 = time.time()
            if label:
                doc_log.add_log(f"📡 调用 AI: {label}", "info")
            request_params = {
                'model': model_name,
                'messages': [
                    {"role": "system", "content": "你是一个专业的内容整理助手，擅长将文档内容整理成结构化的笔记。"},
                    {"role": "user", "content": prompt_text}
                ],
                'temperature': temperature
            }
            if max_tokens:
                request_params['max_tokens'] = max_tokens
            resp = client.chat.completions.create(**request_params)
            elapsed = time.time() - t0
            text = resp.choices[0].message.content
            doc_log.add_log(f"✓ 完成，用时 {elapsed:.1f}s，输出 {len(text)} 字符", "success")
            return text

        if merge:
            doc_log.add_log("📝 合并模式：将所有文档合并后一次性调用 AI...", "info")
            combined = '\n\n'.join([
                f"## {doc['name']}\n\n{doc['text']}"
                for doc in documents
            ])
            doc_log.add_log(f"📊 合并文本总长: {len(combined)} 字符", "info")
            prompt = _build_prompt(combined, '多文档合并', effective_prompt)
            summary = _call_ai(prompt, "合并总结")

            doc_log.add_log("═" * 40, "header")
            doc_log.add_log("🎉 文本总结完成！", "success")
            doc_log.add_log("═" * 40, "header")
            doc_log.stop()

            return jsonify({
                'success': True,
                'mode': 'merge',
                'summary': summary
            })
        else:
            results = []
            total = len(documents)
            for i, doc in enumerate(documents):
                doc_log.add_log("─" * 30, "info")
                doc_log.add_log(f"📄 [{i+1}/{total}] {doc['name']}", "info")
                doc_log.add_log(f"   文本长度: {len(doc['text'])} 字符", "info")
                try:
                    prompt = _build_prompt(doc['text'], doc['name'], effective_prompt)
                    summary = _call_ai(prompt, doc['name'])
                    results.append({
                        'name': doc['name'],
                        'success': True,
                        'summary': summary
                    })
                except Exception as e:
                    doc_log.add_log(f"❌ 失败: {e}", "error")
                    results.append({
                        'name': doc['name'],
                        'success': False,
                        'error': str(e)
                    })

            succeeded = sum(1 for r in results if r['success'])
            failed = total - succeeded
            doc_log.add_log("═" * 40, "header")
            doc_log.add_log(f"🎉 全部完成！成功 {succeeded} / 失败 {failed} / 共 {total}", "success")
            doc_log.add_log("═" * 40, "header")
            doc_log.stop()

            return jsonify({
                'success': True,
                'mode': 'split',
                'results': results
            })

    except Exception as e:
        logger.error(f"文本总结错误: {str(e)}")
        doc_log.add_log(f"❌ 严重错误: {str(e)}", "error")
        doc_log.stop()
        return jsonify({'success': False, 'error': str(e)}), 500
