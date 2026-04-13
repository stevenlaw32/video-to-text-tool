import os
from pathlib import Path
from typing import Optional
import tempfile
import ffmpeg
import torch
import whisper
import sys
from io import StringIO


class VideoTranscriber:
    def __init__(self, model_size: str = "base"):
        # 检测可用的设备
        self.device = self._get_device()
        
        print(f"加载 Whisper {model_size} 模型...")
        print(f"推荐模型：tiny(最快) | base(推荐) | small(更准确)")
        print(f"你的配置适合：base 或 small 模型")
        print(f"使用设备: {self.device}")
        
        # 加载模型到指定设备
        self.model = whisper.load_model(model_size, device=self.device)
        print("模型加载完成！")
        
    def _get_device(self):
        """自动检测并返回最佳可用设备"""
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
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "temp_audio.wav")
        
        print(f"正在提取音频: {video_path}")
        try:
            # 使用 ffmpeg 提取音频
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"音频已提取到: {output_path}")
            return output_path
        except ffmpeg.Error as e:
            raise Exception(f"音频提取失败: {e.stderr.decode() if e.stderr else str(e)}")
    
    def transcribe(self, audio_path: str, language: str = "zh") -> dict:
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        print(f"\n{'=' * 70}")
        print(f"🎤 Whisper 语音识别")
        print(f"{'=' * 70}")
        print(f"   音频文件: {os.path.basename(audio_path)}")
        print(f"   模型大小: {self.model.__class__.__name__}")
        print(f"   识别语言: {language}")
        print(f"{'=' * 70}")
        print(f"\n💡 提示: 首次运行会自动下载模型，请耐心等待...\n")
        print(f"{'─' * 70}")
        print(f"开始转录 (Whisper 详细日志如下):")
        print(f"{'─' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log("🎤 Whisper 语音识别开始", "header")
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log(f"音频文件: {os.path.basename(audio_path)}", "info")
            log_stream.add_log(f"模型: Whisper {self.model.__class__.__name__}", "info")
            log_stream.add_log(f"语言: {language}", "info")
            log_stream.add_log("正在转录... (详细日志请查看终端)", "info")
        
        # 使用 openai-whisper 进行转录，启用进度显示
        # verbose=True 会在终端显示每个音频片段的转录进度
        result = self.model.transcribe(
            audio_path,
            language=language,
            initial_prompt="以下是普通话的句子。",
            verbose=True  # 显示转录进度：[00:00.000 --> 00:03.000] 文本内容
        )
        
        print(f"\n{'─' * 70}")
        print(f"✓ Whisper 转录完成！")
        print(f"   转录文本长度: {len(result['text'])} 字符")
        print(f"   检测到的语言: {result.get('language', 'unknown')}")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("─" * 50, "info")
            log_stream.add_log("✓ Whisper 转录完成！", "success")
            log_stream.add_log(f"转录文本长度: {len(result['text'])} 字符", "success")
            log_stream.add_log(f"检测到的语言: {result.get('language', 'unknown')}", "success")
            log_stream.add_log("═" * 50, "header")
        
        return result
    
    def process_video(self, video_path: str, language: str = "zh") -> dict:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        audio_path = self.extract_audio(video_path)
        
        try:
            result = self.transcribe(audio_path, language)
            return result
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
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
