import os
from pathlib import Path
from typing import Optional
import tempfile
import ffmpeg
import sys
from io import StringIO

# MLX-Whisper：Apple Silicon 原生加速引擎（优先使用）
try:
    import mlx_whisper
    HAS_MLX_WHISPER = True
except ImportError:
    HAS_MLX_WHISPER = False

# openai-whisper：通用回退引擎
try:
    import torch
    import whisper
    HAS_OPENAI_WHISPER = True
except ImportError:
    HAS_OPENAI_WHISPER = False

# MLX 模型映射：model_size -> HuggingFace repo
_MLX_MODEL_MAP = {
    "tiny":    "mlx-community/whisper-tiny-mlx",
    "base":    "mlx-community/whisper-base-mlx",
    "small":   "mlx-community/whisper-small-mlx",
    "medium":  "mlx-community/whisper-medium-mlx",
    "large":   "mlx-community/whisper-large-v3-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "turbo":   "mlx-community/whisper-large-v3-turbo",
}


class VideoTranscriber:
    def __init__(self, model_size: str = "base"):
        self._use_mlx = False
        self.model = None
        self.device = None
        self.model_size = model_size

        if HAS_MLX_WHISPER:
            self._init_mlx(model_size)
        elif HAS_OPENAI_WHISPER:
            self.device = self._get_device()
            self._init_openai_whisper(model_size)
        else:
            raise ImportError("未找到可用的 Whisper 引擎，请安装 mlx-whisper 或 openai-whisper")

    def _init_mlx(self, model_size: str):
        """初始化 MLX-Whisper（Apple Silicon 原生加速）"""
        self._use_mlx = True
        self._mlx_repo = _MLX_MODEL_MAP.get(model_size, f"mlx-community/whisper-{model_size}-mlx")
        print(f"🚀 使用 MLX-Whisper 引擎（Apple Silicon 原生 GPU 加速）")
        print(f"   模型: {model_size}  →  {self._mlx_repo}")
        print(f"   💡 首次运行将自动下载模型（base 约 140MB）")
        print(f"✓ MLX-Whisper 就绪！")

    def _init_openai_whisper(self, model_size: str):
        """初始化 openai-whisper（回退引擎）"""
        print(f"加载 Whisper {model_size} 模型...")
        print(f"推荐模型：tiny(最快) | base(推荐) | small(更准确)")
        print(f"你的配置适合：base 或 small 模型")
        print(f"使用设备: {self.device}")
        self.model = whisper.load_model(model_size, device=self.device)
        print("模型加载完成！")

    def _get_device(self):
        """自动检测并返回最佳可用设备（仅用于 openai-whisper 回退）"""
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✓ 检测到 NVIDIA GPU: {gpu_name}")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # MPS 在某些 Whisper 操作上有兼容性问题，暂时使用 CPU
            device = "cpu"
            print(f"ℹ️  检测到 Apple Silicon GPU (MPS)")
            print(f"⚠️  由于 Whisper 与 MPS 的兼容性问题，暂时使用 CPU")
            print(f"💡 提示：使用 tiny 或 base 模型可获得最佳性能")
        else:
            device = "cpu"
            print(f"⚠ 未检测到 GPU，使用 CPU")
        return device
    
    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
            
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "temp_audio.wav")
        
        print(f"正在提取音频: {video_path}")
        if has_log_stream:
            log_stream.add_log(f"🎵 提取音频: {os.path.basename(video_path)}", "info")

        # 先探测视频流，无音频轨道时提前返回 None（触发 OCR 回退）
        try:
            probe = ffmpeg.probe(video_path)
            has_audio = any(s.get('codec_type') == 'audio' for s in probe.get('streams', []))
            if not has_audio:
                msg = "视频无音频轨道，将跳过语音转录（自动切换 OCR 模式）"
                print(f"⚠️  {msg}")
                if has_log_stream:
                    log_stream.add_log(f"⚠️  {msg}", "warning")
                return None
        except Exception:
            pass  # 探测失败则继续尝试提取

        try:
            # 使用 ffmpeg 提取音频
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
            # 检查音频文件大小
            audio_size = os.path.getsize(output_path)
            print(f"音频已提取到: {output_path}")
            print(f"音频文件大小: {audio_size / 1024:.2f} KB")
            
            if has_log_stream:
                log_stream.add_log(f"✓ 音频提取完成 ({audio_size / 1024:.2f} KB)", "success")
            
            # 如果音频文件太小，可能没有有效音频
            if audio_size < 1000:  # 小于 1KB
                warning_msg = f"⚠️  警告：音频文件很小 ({audio_size} bytes)，视频可能没有音频轨道"
                print(warning_msg)
                if has_log_stream:
                    log_stream.add_log(warning_msg, "warning")
            
            return output_path
        except ffmpeg.Error as e:
            stderr_full = e.stderr.decode(errors='replace') if e.stderr else str(e)
            # ffmpeg stderr 包含版本头，只取最后几行（实际错误信息）
            stderr_lines = [l for l in stderr_full.splitlines() if l.strip()]
            stderr_brief = '\n'.join(stderr_lines[-4:]) if stderr_lines else stderr_full
            print(f"❌ ffmpeg 完整错误:\n{stderr_full}")  # 终端输出完整日志
            error_msg = f"音频提取失败: {stderr_brief}"
            if has_log_stream:
                log_stream.add_log(f"❌ {error_msg}", "error")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"音频提取异常: {str(e)}"
            print(f"❌ {error_msg}")
            if has_log_stream:
                log_stream.add_log(f"❌ {error_msg}", "error")
            raise
    
    def transcribe(self, audio_path: str, language: str = "zh") -> dict:
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False

        engine_label = "MLX-Whisper (Apple Silicon)" if self._use_mlx else "Whisper (CPU)"
        print(f"\n{'=' * 70}")
        print(f"🎤 语音识别 [{engine_label}]")
        print(f"{'=' * 70}")
        print(f"   音频文件: {os.path.basename(audio_path)}")
        print(f"   模型大小: {self.model_size}")
        print(f"   识别语言: {language}")
        print(f"{'=' * 70}")
        print(f"\n💡 提示: 首次运行会自动下载模型，请耐心等待...\n")
        print(f"{'─' * 70}")
        print(f"开始转录 (详细日志如下):")
        print(f"{'─' * 70}\n")

        if has_log_stream:
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log(f"🎤 语音识别开始 [{engine_label}]", "header")
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log(f"音频文件: {os.path.basename(audio_path)}", "info")
            log_stream.add_log(f"模型: {self.model_size}", "info")
            log_stream.add_log(f"语言: {language}", "info")
            log_stream.add_log("正在转录... (详细日志请查看终端)", "info")

        if self._use_mlx:
            # MLX-Whisper：Apple Silicon 原生加速，返回格式与 openai-whisper 兼容
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=self._mlx_repo,
                language=language,
                initial_prompt="以下是普通话的句子。",
                verbose=True,
            )
        else:
            # openai-whisper 回退
            # verbose=True 会在终端显示每个音频片段的转录进度
            result = self.model.transcribe(
                audio_path,
                language=language,
                initial_prompt="以下是普通话的句子。",
                verbose=True,
            )

        print(f"\n{'─' * 70}")
        print(f"✓ 转录完成！")
        print(f"   转录文本长度: {len(result['text'])} 字符")
        print(f"   检测到的语言: {result.get('language', 'unknown')}")
        print(f"{'=' * 70}\n")

        if has_log_stream:
            log_stream.add_log("─" * 50, "info")
            log_stream.add_log("✓ 转录完成！", "success")
            log_stream.add_log(f"转录文本长度: {len(result['text'])} 字符", "success")
            log_stream.add_log(f"检测到的语言: {result.get('language', 'unknown')}", "success")
            log_stream.add_log("═" * 50, "header")

        return result
    
    def process_video(self, video_path: str, language: str = "zh") -> dict:
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
            
        if not os.path.exists(video_path):
            error_msg = f"视频文件不存在: {video_path}"
            print(f"❌ {error_msg}")
            if has_log_stream:
                log_stream.add_log(f"❌ {error_msg}", "error")
            raise FileNotFoundError(error_msg)
        
        audio_path = None
        try:
            audio_path = self.extract_audio(video_path)
            if audio_path is None:
                # 无音频轨道，返回空结果以触发 OCR 回退
                return {'text': '', 'segments': [], 'language': 'unknown'}
            result = self.transcribe(audio_path, language)
            return result
        except Exception as e:
            error_msg = f"视频处理失败: {str(e)}"
            print(f"❌ {error_msg}")
            if has_log_stream:
                log_stream.add_log(f"❌ {error_msg}", "error")
            raise
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"已清理临时音频文件: {audio_path}")
                except Exception as e:
                    print(f"⚠️  清理临时文件失败: {e}")
    
    def save_transcript(self, result: dict, output_path: str, format: str = "txt"):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if format == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['text'])
        elif format == "srt":
            self._save_as_srt(result, output_path)
        elif format == "segments":
            with open(output_path, 'w', encoding='utf-8') as f:
                for segment in result['segments']:
                    f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]\n")
                    f.write(f"{segment['text']}\n\n")
        
        print(f"转录文本已保存到: {output_path}")
    
    def _save_as_srt(self, result: dict, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(result['segments'], 1):
                start_time = self._format_timestamp(segment['start'])
                end_time = self._format_timestamp(segment['end'])
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n\n")
    
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
