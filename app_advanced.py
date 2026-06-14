from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from video_transcriber import VideoTranscriber
try:
    from simple_ocr import SimpleOCR
    HAS_VIDEO_OCR = True
    print("✓ 使用简化版 OCR（云端 API）")
except ImportError:
    HAS_VIDEO_OCR = False
    print("⚠️  OCR 模块未安装，OCR 功能将不可用")
from ai_summarizer_v2 import AISummarizerV2
import tempfile
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from api_routes import api_bp
from models_routes import models_bp
from audio_routes import audio_bp
from ocr_routes import ocr_bp
from text_summary_routes import text_summary_bp
from models_config import ModelsConfig
from log_stream import log_stream

# 尝试导入视频链接解析路由
try:
    from video_link_routes import video_link_bp
    HAS_VIDEO_LINK = True
except (ImportError, RuntimeError) as e:
    HAS_VIDEO_LINK = False
    print(f"⚠️  视频链接解析功能不可用: {e}")

load_dotenv()

app = Flask(__name__)
app.register_blueprint(api_bp)
app.register_blueprint(models_bp)
app.register_blueprint(audio_bp)
app.register_blueprint(ocr_bp)
app.register_blueprint(text_summary_bp)
if HAS_VIDEO_LINK:
    app.register_blueprint(video_link_bp)
app.config['MAX_CONTENT_LENGTH'] = 5000 * 1024 * 1024  # 5GB
app.config['UPLOAD_FOLDER'] = Path(tempfile.gettempdir()) / 'video_uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'error': '文件过大，超出上传限制（最大 5GB）',
        'success': False
    }), 413

ALLOWED_EXTENSIONS = {
    # 视频格式
    'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', 'webm',
    # 音频格式
    'mp3', 'wav', 'aac', 'm4a', 'flac', 'ogg', 'wma', 'opus'
}

uploaded_videos = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index_advanced.html')


@app.route('/settings')
def settings():
    return render_template('api_settings.html')


@app.route('/models')
def models_settings():
    return render_template('models_settings.html')


@app.route('/audio')
def audio_extract():
    return render_template('audio_extract.html')


@app.route('/ocr')
def ocr_settings():
    return render_template('ocr_settings.html')


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """停止服务器"""
    print("\n" + "=" * 70)
    print("🛑 收到停止服务器请求")
    print("=" * 70)
    
    def shutdown_server():
        import time
        time.sleep(1)  # 等待响应发送完成
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)
    
    # 在后台线程中停止服务器
    import threading
    threading.Thread(target=shutdown_server).start()
    
    return jsonify({'success': True, 'message': '服务器正在关闭...'})


@app.route('/stream_logs')
def stream_logs():
    """SSE 端点 - 实时推送处理日志到前端"""
    def generate():
        for log in log_stream.get_logs():
            yield f"data: {json.dumps(log)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/upload', methods=['POST'])
def upload_single():
    """单文件上传（用于音频提取）"""
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if file and allowed_file(file.filename):
        original_filename = file.filename
        safe_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        unique_filename = f"{timestamp}_{safe_filename}"
        video_path = app.config['UPLOAD_FOLDER'] / unique_filename
        file.save(video_path)
        
        return jsonify({
            'success': True,
            'file_path': str(video_path),
            'filename': original_filename,
            'size': video_path.stat().st_size
        })
    else:
        return jsonify({'error': '不支持的文件格式'}), 400


@app.route('/api/video_path/<file_id>')
def get_video_path(file_id):
    """获取已上传视频的文件路径"""
    if file_id in uploaded_videos:
        return jsonify({
            'success': True,
            'path': uploaded_videos[file_id]['path'],
            'name': uploaded_videos[file_id]['original_name']
        })
    else:
        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404


@app.route('/upload_batch', methods=['POST'])
def upload_batch():
    if 'videos' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    files = request.files.getlist('videos')
    folder_name = request.form.get('folder_name', '')
    uploaded_files = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_filename = file.filename
            safe_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            unique_filename = f"{timestamp}_{safe_filename}"
            video_path = app.config['UPLOAD_FOLDER'] / unique_filename
            file.save(video_path)
            
            file_id = unique_filename
            uploaded_videos[file_id] = {
                'path': str(video_path),
                'original_name': original_filename,
                'size': video_path.stat().st_size,
                'folder_name': folder_name
            }
            
            uploaded_files.append({
                'id': file_id,
                'name': original_filename,
                'size': video_path.stat().st_size
            })
    
    return jsonify({
        'success': True,
        'files': uploaded_files,
        'folder_name': folder_name
    })


@app.route('/process_batch', methods=['POST'])
def process_batch():
    data = request.json
    video_ids = data.get('video_ids', [])
    processing_mode = data.get('processing_mode', 'auto')  # auto, whisper, ocr, hybrid
    model_size = data.get('model_size', 'base')
    whisper_language = data.get('whisper_language', 'zh')
    model_alias = data.get('model_alias', '')  # 模型别名
    custom_prompt = data.get('custom_prompt', '')
    enable_ai_summary = data.get('enable_ai_summary', True)
    merge_output = data.get('merge_output', True)  # True=合并, False=分开
    
    if not video_ids:
        return jsonify({'error': '没有选择视频'}), 400
    
    try:
        # 启动日志流
        log_stream.start()
        
        print("\n" + "=" * 70)
        print("🚀 开始批量处理视频")
        print("=" * 70)
        log_stream.add_log("开始批量处理视频", "header")
        mode_text = {'auto': '自动检测', 'whisper': 'Whisper 音频转录', 'ocr': 'OCR 画面文字', 'hybrid': '🔀 混合模式（音频+画面）'}
        print(f"📊 任务信息:")
        print(f"   - 处理模式: {mode_text.get(processing_mode, processing_mode)}")
        print(f"   - 视频数量: {len(video_ids)} 个")
        print(f"   - Whisper 模型: {model_size}")
        print(f"   - 识别语言: {whisper_language}")
        print(f"   - AI 模型: {model_alias}")
        print(f"   - AI 摘要: {'启用' if enable_ai_summary else '禁用'}")
        print("=" * 70 + "\n")
        
        log_stream.add_log(f"📊 任务信息:", "info")
        log_stream.add_log(f"   处理模式: {mode_text.get(processing_mode, processing_mode)}", "info")
        log_stream.add_log(f"   视频数量: {len(video_ids)} 个", "info")
        log_stream.add_log(f"   Whisper 模型: {model_size}", "info")
        log_stream.add_log(f"   识别语言: {whisper_language}", "info")
        log_stream.add_log(f"   AI 模型: {model_alias}", "info")
        log_stream.add_log(f"   AI 摘要: {'启用' if enable_ai_summary else '禁用'}", "info")
        
        # 只在需要时初始化 Whisper
        transcriber = None
        if processing_mode != 'ocr':
            transcriber = VideoTranscriber(model_size=model_size)

        # 混合模式：同时需要 OCR 处理器
        hybrid_ocr_processor = None
        hybrid_ocr_config = None
        hybrid_ocr_provider = None
        if processing_mode == 'hybrid':
            try:
                from ocr_config import OCRConfig
                _ocr_cfg = OCRConfig()
                hybrid_ocr_provider = _ocr_cfg.get_active_provider()
                hybrid_ocr_config = _ocr_cfg.get_provider_config(hybrid_ocr_provider)
                if hybrid_ocr_provider in ['baidu', 'tencent', 'aliyun']:
                    hybrid_ocr_processor = SimpleOCR()
                    log_stream.add_log(f"✓ OCR 引擎就绪: {hybrid_ocr_config['name']}", "info")
                else:
                    log_stream.add_log("⚠️  混合模式需配置云端 OCR（百度/腾讯/阿里云），将仅使用 Whisper", "warning")
            except Exception as e:
                log_stream.add_log(f"⚠️  OCR 初始化失败: {e}，将仅使用 Whisper", "warning")
        
        all_transcripts = []
        results = []
        
        for i, video_id in enumerate(video_ids):
            if video_id not in uploaded_videos:
                continue
            
            video_info = uploaded_videos[video_id]
            video_path = video_info['path']
            
            print(f"\n{'─' * 70}")
            print(f"📹 处理视频 [{i + 1}/{len(video_ids)}]")
            print(f"{'─' * 70}")
            print(f"   文件名: {video_info['original_name']}")
            print(f"   大小: {video_info['size'] / 1024 / 1024:.2f} MB")
            print(f"{'─' * 70}\n")
            
            log_stream.add_log("─" * 50, "info")
            log_stream.add_log(f"📹 处理视频 [{i + 1}/{len(video_ids)}]", "info")
            log_stream.add_log(f"文件名: {video_info['original_name']}", "info")
            log_stream.add_log(f"大小: {video_info['size'] / 1024 / 1024:.2f} MB", "info")
            
            # ──────────────────────────────────────────────
            # 混合模式：Whisper + OCR 同时跑，各取各的内容
            # ──────────────────────────────────────────────
            if processing_mode == 'hybrid':
                # 1. Whisper 音频转录
                audio_text = ""
                try:
                    log_stream.add_log("🎤 [混合] 开始音频转录...", "info")
                    whisper_result = transcriber.process_video(video_path, language=whisper_language)
                    audio_text = whisper_result.get('text', '').strip()
                    log_stream.add_log(f"✓ 音频转录完成：{len(audio_text)} 字符", "success")
                except Exception as e:
                    log_stream.add_log(f"⚠️  音频转录失败: {e}", "warning")

                # 2. OCR 画面文字提取
                ocr_text = ""
                if hybrid_ocr_processor:
                    try:
                        log_stream.add_log("🖼️  [混合] 开始 OCR 画面识别...", "info")
                        ocr_result = hybrid_ocr_processor.process_video(
                            video_path,
                            interval=1.0,
                            cloud_provider=hybrid_ocr_provider,
                            cloud_config=hybrid_ocr_config
                        )
                        ocr_text = ocr_result.get('text', '').strip()
                        log_stream.add_log(f"✓ OCR 识别完成：{len(ocr_text)} 字符，{ocr_result.get('frame_count', 0)} 帧", "success")
                    except Exception as e:
                        log_stream.add_log(f"⚠️  OCR 提取失败: {e}", "warning")

                # 3. 打包成结构化输入，交给 AI 整合
                # 若只有一路有内容，直接透传（不加双路标头，避免 AI 当作"融合任务"而压缩信息）
                if audio_text and ocr_text:
                    transcript = (
                        f"## 音频转录内容（语音识别）\n\n{audio_text}\n\n"
                        f"---\n\n"
                        f"## 画面文字内容（OCR 识别）\n\n{ocr_text}"
                    )
                    log_stream.add_log(f"🔀 双路内容已合并（音频+OCR）：共 {len(transcript)} 字符", "info")
                elif audio_text:
                    transcript = audio_text
                    log_stream.add_log(f"⚠️  OCR 无内容，仅使用音频转录：{len(transcript)} 字符", "warning")
                elif ocr_text:
                    transcript = ocr_text
                    log_stream.add_log(f"⚠️  音频无内容，仅使用 OCR 结果：{len(transcript)} 字符", "warning")
                else:
                    transcript = ""

            # ──────────────────────────────────────────────
            # 普通模式
            # ──────────────────────────────────────────────
            elif processing_mode == 'ocr':
                # 强制使用 OCR 模式
                transcript = ""  # 跳过 Whisper，直接使用 OCR
            else:
                # Whisper 或 Auto 模式
                result = transcriber.process_video(video_path, language=whisper_language)
                transcript = result['text']
            
            # 检查是否需要使用 OCR（仅限非 hybrid 模式）
            should_use_ocr = (
                processing_mode != 'hybrid' and (
                    processing_mode == 'ocr' or  # 强制 OCR 模式
                    (processing_mode == 'auto' and (not transcript or len(transcript.strip()) == 0))  # 自动模式且转录为空
                )
            )
            
            if should_use_ocr:
                print(f"\n⚠️  检测到音频转录结果为空")
                print(f"   可能原因：视频无音频或音频为静音")
                print(f"   正在尝试使用 OCR 提取画面文字...\n")
                
                log_stream.add_log("⚠️  音频转录结果为空", "warning")
                log_stream.add_log("正在尝试 OCR 提取画面文字...", "info")
                
                try:
                    # 检查 OCR 模块是否可用
                    if not HAS_VIDEO_OCR:
                        raise ImportError("OCR 模块未安装，请运行: pip install opencv-python pillow surya-ocr")
                    
                    from ocr_config import OCRConfig
                    
                    # 获取 OCR 配置
                    ocr_config = OCRConfig()
                    active_provider = ocr_config.get_active_provider()
                    provider_config = ocr_config.get_provider_config(active_provider)
                    
                    print(f"   使用 OCR 引擎: {provider_config['name']}")
                    log_stream.add_log(f"使用: {provider_config['name']}", "info")
                    
                    # 初始化 OCR（仅在需要时）
                    if 'ocr_processor' not in locals():
                        ocr_processor = SimpleOCR()
                    
                    # 检查是否配置了云端 OCR
                    if active_provider not in ['baidu', 'tencent', 'aliyun']:
                        raise ValueError(f"简化版 OCR 仅支持云端 API。请访问 /ocr 配置百度/腾讯/阿里云 OCR，并切换激活提供商。")
                    
                    # 使用云端 OCR
                    ocr_result = ocr_processor.process_video(
                        video_path,
                        interval=1.0,
                        cloud_provider=active_provider,
                        cloud_config=provider_config
                    )
                    
                    transcript = ocr_result['text']
                    
                    print(f"\n✓ OCR 提取完成")
                    print(f"   提取文本长度: {len(transcript)} 字符")
                    print(f"   处理帧数: {ocr_result['frame_count']}\n")
                    
                    log_stream.add_log(f"✓ OCR 提取完成", "success")
                    log_stream.add_log(f"提取文本: {len(transcript)} 字符", "success")
                    
                except Exception as e:
                    error_msg = f"OCR 提取失败: {str(e)}"
                    print(f"❌ {error_msg}")
                    log_stream.add_log(f"❌ {error_msg}", "error")
                    log_stream.add_log("提示：检查 OCR 配置或安装依赖", "warning")
                    # OCR 失败时保持空文本
                    transcript = ""
            
            print(f"\n✓ 视频 [{i + 1}/{len(video_ids)}] 处理完成")
            print(f"   文本长度: {len(transcript)} 字符\n")
            
            log_stream.add_log(f"✓ 视频 [{i + 1}/{len(video_ids)}] 处理完成", "success")
            
            all_transcripts.append({
                'order': i + 1,
                'name': video_info['original_name'],
                'text': transcript
            })
            
            results.append({
                'id': video_id,
                'name': video_info['original_name'],
                'transcript': transcript
            })
        
        folder_name = None
        for video_id in video_ids:
            if video_id in uploaded_videos:
                folder_name = uploaded_videos[video_id].get('folder_name', '')
                if folder_name:
                    break
        
        combined_transcript = "\n\n".join([
            f"## {item['name']}\n\n{item['text']}" 
            for item in all_transcripts
        ])
        
        print(f"\n{'=' * 70}")
        print(f"📝 合并转录结果")
        print(f"{'=' * 70}")
        print(f"   转录条目数: {len(all_transcripts)}")
        print(f"   合并文本长度: {len(combined_transcript)} 字符")
        print(f"{'=' * 70}\n")
        
        log_stream.add_log(f"📝 转录条目数: {len(all_transcripts)}", "info")
        log_stream.add_log(f"📝 合并文本长度: {len(combined_transcript)} 字符", "info")
        
        ai_summary = None
        individual_results = None

        if enable_ai_summary and all_transcripts:
            try:
                print("\n" + "=" * 70)
                print("🤖 开始 AI 智能整理")
                print("=" * 70)
                log_stream.add_log("═" * 50, "header")
                log_stream.add_log("🤖 开始 AI 智能整理", "header")
                log_stream.add_log("═" * 50, "header")

                # ── 初始化 AI 客户端（仅一次）──
                models_config = ModelsConfig()
                model_config = models_config.get_model_by_alias(model_alias)
                if not model_config:
                    print(f"   使用环境变量配置")
                    client = OpenAI(
                        api_key=os.getenv('OPENAI_API_KEY'),
                        base_url=os.getenv('OPENAI_BASE_URL')
                    )
                    ai_model = os.getenv('MODEL_NAME', 'gpt-4o')
                    model_custom_prompt = custom_prompt
                    ai_max_tokens = None
                    ai_temperature = 0.7
                else:
                    print(f"   模型别名: {model_alias} / {model_config['model_name']}")
                    client = OpenAI(
                        api_key=model_config['api_key'],
                        base_url=model_config['base_url']
                    )
                    ai_model = model_config['model_name']
                    model_custom_prompt = model_config.get('custom_prompt') or custom_prompt
                    ai_max_tokens = model_config.get('max_tokens')
                    ai_temperature = model_config.get('temperature', 0.7)

                print(f"   使用{'自定义' if model_custom_prompt else '默认'}提示词")
                print(f"   输出方式: {'合并' if merge_output else '分开'}")
                print("=" * 70 + "\n")

                def _build_prompt(transcript_text, video_title):
                    t = video_title or folder_name or "视频内容"
                    if model_custom_prompt:
                        tpl = model_custom_prompt
                    else:
                        tpl = f"""# 标题：{t}

# Processing Logic (Adaptive)
请根据输入视频的内容类型，自动选择最适合的组织逻辑进行重组：

1. **若为【实操/教学类】（如摄影、软件操作）**：
   按"准备工作 -> 核心操作步骤 -> 关键细节/避坑指南 -> 效果复盘"逻辑整理。
2. **若为【理论/知识类】（如AI原理、科学普及）**：
   按"核心概念定义 -> 运行机制/原理分析 -> 实际应用场景 -> 未来展望/局限性"逻辑整理。
3. **若为【人文/社会类】（如心理学、社会现象）**：
   按"现象观察 -> 核心观点/理论解释 -> 案例论证 -> 对个人或社会的启示"逻辑整理。

# Content Requirements (Strict)
- **不流于表面**：保留视频中所有的核心论点、实验数据、具体的摄影参数或代码逻辑，确保文档深度。
- **灵活标题**：严禁全篇只有一级标题。根据内容的复杂度，自主划分为"## 模块"和"### 细分点"。
- **提炼话术**：在每一个【二级标题】模块的末尾，必须包含一个加粗的总结块：
  > **💡 本段要义：** [用一句话提炼该章节的核心价值或金句]
"""
                    # 混合模式且确实有双路内容时才加前缀；单路降级后直接走普通整理
                    is_dual_source = (
                        processing_mode == 'hybrid' and
                        '## 音频转录内容' in transcript_text and
                        '## 画面文字内容' in transcript_text
                    )
                    if is_dual_source:
                        hybrid_prefix = (
                            "你收到的内容来自同一视频的两路提取：\n"
                            "- **音频转录**（语音识别）：口述内容，可能因语速过快而有所遗漏\n"
                            "- **画面文字**（OCR 识别）：视频画面中的文字，通常更完整准确\n\n"
                            "融合规则（严格执行）：\n"
                            "1. **两路内容同等重要**，任意一路中出现的信息都必须保留在最终笔记中\n"
                            "2. **不得因音频未提及而遗漏 OCR 内容**——音频可能因语速过快或识别误差而有缺漏，OCR 是补充音频的关键依据\n"
                            "3. 两路都提到同一内容时，合并为一条，以 OCR 的精确文字（名称、地址、数据）为准\n"
                            "4. 音频负责提供叙述语气和上下文逻辑，OCR 负责提供精确的专有名词和数字\n\n"
                            "请将两路内容完整融合后，按以下要求整理笔记：\n\n---\n\n"
                        )
                        tpl = hybrid_prefix + tpl
                    if '{transcript}' in tpl:
                        return tpl.replace('{transcript}', transcript_text)
                    return tpl + '\n\n---\n\n转录内容：\n' + transcript_text

                def _call_ai(prompt_text):
                    import time
                    t0 = time.time()
                    req_params = {
                        'model': ai_model,
                        'messages': [
                            {"role": "system", "content": "你是一个专业的内容整理助手，擅长将视频转录文本整理成结构化的文档。"},
                            {"role": "user", "content": prompt_text}
                        ],
                        'temperature': ai_temperature
                    }
                    if ai_max_tokens:
                        req_params['max_tokens'] = ai_max_tokens
                    resp = client.chat.completions.create(**req_params)
                    elapsed = time.time() - t0
                    text = resp.choices[0].message.content
                    print(f"   ✓ AI 完成，用时 {elapsed:.2f}s，输出 {len(text)} 字符")
                    return text

                if merge_output:
                    # ── 合并模式：一次 AI 调用 ──
                    log_stream.add_log("📡 合并模式：调用 AI...", "info")
                    prompt = _build_prompt(combined_transcript, folder_name)
                    ai_summary = _call_ai(prompt)
                    log_stream.add_log(f"✓ AI 整理完成：{len(ai_summary)} 字符", "success")
                else:
                    # ── 分开模式：每个视频独立调用 AI ──
                    individual_results = []
                    for idx, item in enumerate(all_transcripts):
                        log_stream.add_log(f"📡 [{idx+1}/{len(all_transcripts)}] {item['name']}", "info")
                        print(f"   [{idx+1}/{len(all_transcripts)}] AI 处理：{item['name']}")
                        try:
                            prompt = _build_prompt(item['text'], item['name'])
                            summary = _call_ai(prompt)
                            log_stream.add_log(f"✓ [{idx+1}] 完成：{len(summary)} 字符", "success")
                        except Exception as e_item:
                            summary = f"AI处理失败: {e_item}"
                            log_stream.add_log(f"⚠️  [{idx+1}] 失败: {e_item}", "warning")
                        individual_results.append({
                            'name': item['name'],
                            'transcript': item['text'],
                            'ai_summary': summary
                        })
                    log_stream.add_log(f"✓ 全部 {len(individual_results)} 份摘要生成完成", "success")

            except Exception as e:
                print(f"\n❌ AI 处理失败: {str(e)}\n")
                ai_summary = f"AI处理失败: {str(e)}"

        print("\n" + "=" * 70)
        print("🎉 所有任务完成！")
        print("=" * 70)
        print(f"✓ 成功处理 {len(video_ids)} 个视频")
        print(f"✓ 总转录文本: {len(combined_transcript)} 字符")
        if ai_summary:
            print(f"✓ AI 摘要: {len(ai_summary)} 字符")
        if individual_results:
            print(f"✓ 分开摘要: {len(individual_results)} 份")
        print("=" * 70 + "\n")

        log_stream.add_log("═" * 50, "header")
        log_stream.add_log("🎉 所有任务完成！", "success")
        log_stream.add_log(f"✓ 成功处理 {len(video_ids)} 个视频", "success")
        log_stream.add_log(f"✓ 总转录文本: {len(combined_transcript)} 字符", "success")
        log_stream.add_log("═" * 50, "header")

        for video_id in video_ids:
            if video_id in uploaded_videos:
                video_path = uploaded_videos[video_id]['path']
                if os.path.exists(video_path):
                    os.remove(video_path)
                del uploaded_videos[video_id]

        log_stream.stop()

        return jsonify({
            'success': True,
            'results': results,
            'combined_transcript': combined_transcript,
            'merge_output': merge_output,
            'ai_summary': ai_summary,
            'individual_results': individual_results
        })
    except Exception as e:
        print(f"处理出错: {str(e)}")
        import traceback
        traceback.print_exc()
        log_stream.stop()
        return jsonify({'error': str(e)}), 500


@app.route('/get_settings', methods=['GET'])
def get_settings():
    api_key = os.getenv('OPENAI_API_KEY', '')
    return jsonify({
        'api_key': api_key,
        'base_url': os.getenv('OPENAI_BASE_URL', ''),
        'model_name': os.getenv('MODEL_NAME', 'gpt-4o')
    })


@app.route('/save_settings', methods=['POST'])
def save_settings():
    data = request.json
    
    env_path = Path('.env')
    env_content = {}
    
    # 读取现有的.env文件
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # 更新设置（只更新非空值）
    if data.get('api_key'):
        env_content['OPENAI_API_KEY'] = data.get('api_key')
    if data.get('base_url'):
        env_content['OPENAI_BASE_URL'] = data.get('base_url')
    if data.get('model_name'):
        env_content['MODEL_NAME'] = data.get('model_name')
    
    # 写回.env文件
    with open(env_path, 'w', encoding='utf-8') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")
    
    # 重新加载环境变量
    load_dotenv(override=True)
    
    return jsonify({'success': True})


@app.route('/download_result', methods=['POST'])
def download_result():
    data = request.json
    content = data.get('content', '')
    filename = data.get('filename', 'result.txt')
    
    temp_file = Path(tempfile.gettempdir()) / filename
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return send_file(temp_file, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    import webbrowser
    import threading
    
    # 读取版本号
    version = "1.0.0"
    try:
        with open(os.path.join(os.path.dirname(__file__), 'VERSION'), 'r') as f:
            version = f.read().strip()
    except:
        pass
    
    print("\n" + "="*60)
    print(f"视频转文字工具 - 增强版客户端 v{version}")
    print("="*60)
    print("\n功能特性：")
    print("  ✓ 批量拖拽上传视频")
    print("  ✓ 手动调整处理顺序")
    print("  ✓ 自动衔接转录结果")
    print("  ✓ 自定义AI模型")
    print("  ✓ 自定义AI提示词")
    print("\n访问地址: http://localhost:5001")
    print("\n按 Ctrl+C 停止服务器\n")
    
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://localhost:5001')
    
    threading.Thread(target=open_browser).start()
    app.run(debug=False, host='0.0.0.0', port=5001)
