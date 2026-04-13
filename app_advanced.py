from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from video_transcriber import VideoTranscriber
from ai_summarizer_v2 import AISummarizerV2
import tempfile
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from api_routes import api_bp
from models_routes import models_bp
from models_config import ModelsConfig
from log_stream import log_stream

load_dotenv()

app = Flask(__name__)
app.register_blueprint(api_bp)
app.register_blueprint(models_bp)
app.config['MAX_CONTENT_LENGTH'] = 2000 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = Path(tempfile.gettempdir()) / 'video_uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

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
    model_size = data.get('model_size', 'base')
    whisper_language = data.get('whisper_language', 'zh')
    model_alias = data.get('model_alias', '')  # 模型别名
    custom_prompt = data.get('custom_prompt', '')
    enable_ai_summary = data.get('enable_ai_summary', True)
    
    if not video_ids:
        return jsonify({'error': '没有选择视频'}), 400
    
    try:
        # 启动日志流
        log_stream.start()
        
        print("\n" + "=" * 70)
        print("🚀 开始批量处理视频")
        print("=" * 70)
        log_stream.add_log("开始批量处理视频", "header")
        print(f"📊 任务信息:")
        print(f"   - 视频数量: {len(video_ids)} 个")
        print(f"   - Whisper 模型: {model_size}")
        print(f"   - 识别语言: {whisper_language}")
        print(f"   - AI 模型: {model_alias}")
        print(f"   - AI 摘要: {'启用' if enable_ai_summary else '禁用'}")
        print("=" * 70 + "\n")
        
        log_stream.add_log(f"📊 任务信息:", "info")
        log_stream.add_log(f"   视频数量: {len(video_ids)} 个", "info")
        log_stream.add_log(f"   Whisper 模型: {model_size}", "info")
        log_stream.add_log(f"   识别语言: {whisper_language}", "info")
        log_stream.add_log(f"   AI 模型: {model_alias}", "info")
        log_stream.add_log(f"   AI 摘要: {'启用' if enable_ai_summary else '禁用'}", "info")
        
        transcriber = VideoTranscriber(model_size=model_size)
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
            
            result = transcriber.process_video(video_path, language=whisper_language)
            transcript = result['text']
            
            print(f"\n✓ 视频 [{i + 1}/{len(video_ids)}] 转录完成")
            print(f"   转录文本长度: {len(transcript)} 字符\n")
            
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
        
        ai_summary = None
        if enable_ai_summary and combined_transcript:
            try:
                print("\n" + "=" * 70)
                print("🤖 开始 AI 智能整理")
                print("=" * 70)
                
                log_stream.add_log("═" * 50, "header")
                log_stream.add_log("🤖 开始 AI 智能整理", "header")
                log_stream.add_log("═" * 50, "header")
                
                # 根据模型别名获取配置
                models_config = ModelsConfig()
                model_config = models_config.get_model_by_alias(model_alias)
                
                if not model_config:
                    # 如果没有找到模型配置，使用环境变量
                    print(f"   使用环境变量配置")
                    client = OpenAI(
                        api_key=os.getenv('OPENAI_API_KEY'),
                        base_url=os.getenv('OPENAI_BASE_URL')
                    )
                    ai_model = os.getenv('MODEL_NAME', 'gpt-4o')
                    model_custom_prompt = custom_prompt
                else:
                    # 使用模型配置
                    print(f"   模型别名: {model_alias}")
                    print(f"   模型名称: {model_config['model_name']}")
                    print(f"   Base URL: {model_config['base_url']}")
                    client = OpenAI(
                        api_key=model_config['api_key'],
                        base_url=model_config['base_url']
                    )
                    ai_model = model_config['model_name']
                    # 优先使用模型配置中的提示词，如果没有则使用传入的提示词
                    model_custom_prompt = model_config.get('custom_prompt') or custom_prompt
                
                print(f"   转录文本长度: {len(combined_transcript)} 字符")
                print(f"   使用{'自定义' if model_custom_prompt else '默认'}提示词")
                print("=" * 70 + "\n")
                
                if model_custom_prompt:
                    prompt = model_custom_prompt.replace('{transcript}', combined_transcript)
                else:
                    title = folder_name if folder_name else "视频内容"
                    
                    default_prompt = f"""请你扮演一名"课程笔记精简&排版编辑"，对我提供的 Markdown 课程文档进行重排、精简和结构优化。要求如下：

## 文档信息
标题：{title}

## 整体风格
- 保留所有核心观点和方法论，删除或压缩废话、营销语、重复说明
- 风格偏向知识笔记/复习大纲，而不是长篇教程文案
- 语言简洁、直接，句子能短就短

## 结构调整
用少量清晰的一级、二级标题组织内容，例如：
- 一、课程主题/正确认知
- 二、核心目标/根本目的
- 三、常见错误或禁忌
- 四、核心方法/技巧
- 五、练习与作业/实战

要求：
- 尽量合并重复或碎片化的小节，避免"第一节/第二节/第三节"式的细碎结构，如果内容相近就归为同一大块
- 保持目录层级不超过2-3级，避免过深的标题嵌套

## 内容精简方式
- 将能列表化的内容，尽量改成有条理的项目符号或编号列表
- 同一意思只保留一次表达：若原文在不同小节重复同一个观点，合并到一个地方，用1-2句说清
- 删除或压缩以下内容：
  - 过度铺陈、空话和情绪化语句（如"通过本课程你将能够……"之类）
  - 冗长的过渡句、赘述的"背景介绍"
  - 过多、类似的例子，只保留最典型1-2个

## 重点呈现方式
- 用粗体强调关键概念和步骤（例如：**发散性思维**、**平移思维**、**需求感过强**）
- 对"方法/技巧"类内容，用清晰的结构呈现：
  1. 定义
  2. 使用步骤
  3. 示例
  4. 适用场景/注意点（如果原文有）
- 对"禁忌/错误"类内容，整合成一个汇总列表，避免散落多处重复说

## 示例与比喻
- 保留有助理解的例子和比喻，但删除明显重复或价值不高的例子
- 示例尽量简短，能用1-2条对话或一个场景说明的，不拉长叙述

## 练习与作业部分
- 独立成一个"练习/作业/实战应用"模块
- 用列表列出具体要做的事情和频次（如"每天练习20个关键词"），方便执行和回顾

## 输出格式
- 只输出修改后的整篇Markdown文本，不需要解释，不要加无关前后缀
- 保持语种和原文一致（原文是中文就全中文）

转录文本：
{combined_transcript}

请开始整理："""
                    
                    prompt = default_prompt
                
                print("📡 正在调用 AI API...")
                print(f"   模型: {ai_model}")
                
                log_stream.add_log("📡 正在调用 AI API...", "info")
                log_stream.add_log(f"模型: {ai_model}", "info")
                
                import time
                start_time = time.time()
                
                response = client.chat.completions.create(
                    model=ai_model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的内容整理助手，擅长将视频转录文本整理成结构化的文档。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )
                
                elapsed_time = time.time() - start_time
                ai_summary = response.choices[0].message.content
                
                print(f"\n✓ AI 整理完成")
                print(f"   用时: {elapsed_time:.2f} 秒")
                print(f"   输出长度: {len(ai_summary)} 字符")
                if hasattr(response, 'usage') and response.usage:
                    print(f"   Token 使用: {response.usage.total_tokens}")
                print("=" * 70 + "\n")
                
                log_stream.add_log("✓ AI 整理完成", "success")
                log_stream.add_log(f"用时: {elapsed_time:.2f} 秒", "success")
                log_stream.add_log(f"输出长度: {len(ai_summary)} 字符", "success")
                
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
        print("=" * 70 + "\n")
        
        log_stream.add_log("═" * 50, "header")
        log_stream.add_log("🎉 所有任务完成！", "success")
        log_stream.add_log(f"✓ 成功处理 {len(video_ids)} 个视频", "success")
        log_stream.add_log(f"✓ 总转录文本: {len(combined_transcript)} 字符", "success")
        if ai_summary:
            log_stream.add_log(f"✓ AI 摘要: {len(ai_summary)} 字符", "success")
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
            'ai_summary': ai_summary
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
    print("\n访问地址: http://localhost:5000")
    print("\n按 Ctrl+C 停止服务器\n")
    
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://localhost:5000')
    
    threading.Thread(target=open_browser).start()
    app.run(debug=False, host='0.0.0.0', port=5000)
