"""
视频 OCR 模块 - 从视频帧中提取文字
使用 Surya OCR 进行文字识别
"""
import os
try:
    import cv2
except ImportError:
    raise ImportError("OpenCV 未安装。请运行: pip install opencv-python-headless")
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from collections import defaultdict


class VideoOCR:
    def __init__(self, ocr_engine: str = "surya"):
        """
        初始化 OCR 引擎
        
        Args:
            ocr_engine: OCR 引擎类型 ('surya', 'easyocr', 'tesseract')
        """
        self.ocr_engine = ocr_engine
        self.model = None
        self.processor = None
        
        print(f"初始化 {ocr_engine} OCR 引擎...")
        
        if ocr_engine == "surya":
            self._init_surya()
        elif ocr_engine == "easyocr":
            self._init_easyocr()
        elif ocr_engine == "tesseract":
            self._init_tesseract()
        else:
            raise ValueError(f"不支持的 OCR 引擎: {ocr_engine}")
        
        print("OCR 引擎初始化完成！")
    
    def _init_surya(self):
        """初始化 Surya OCR"""
        try:
            from surya.ocr import run_ocr
            from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
            from surya.model.recognition.model import load_model as load_rec_model
            from surya.model.recognition.processor import load_processor as load_rec_processor
            
            print("加载 Surya 检测模型...")
            self.det_model = load_det_model()
            self.det_processor = load_det_processor()
            
            print("加载 Surya 识别模型...")
            self.rec_model = load_rec_model()
            self.rec_processor = load_rec_processor()
            
            self.run_ocr = run_ocr
            print("✓ Surya OCR 加载成功")
            
        except ImportError:
            raise ImportError(
                "Surya OCR 未安装。请运行: pip install surya-ocr"
            )
    
    def _init_easyocr(self):
        """初始化 EasyOCR"""
        try:
            import easyocr
            print("加载 EasyOCR 模型（首次使用会下载模型）...")
            self.model = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            print("✓ EasyOCR 加载成功")
        except ImportError:
            raise ImportError(
                "EasyOCR 未安装。请运行: pip install easyocr"
            )
    
    def _init_tesseract(self):
        """初始化 Tesseract OCR"""
        try:
            import pytesseract
            self.model = pytesseract
            print("✓ Tesseract OCR 加载成功")
        except ImportError:
            raise ImportError(
                "Tesseract 未安装。请运行: brew install tesseract && pip install pytesseract"
            )
    
    def extract_frames(self, video_path: str, interval: float = 1.0) -> List[np.ndarray]:
        """
        从视频中提取关键帧
        
        Args:
            video_path: 视频文件路径
            interval: 提取间隔（秒）
            
        Returns:
            帧图像列表
        """
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        print(f"\n{'=' * 70}")
        print(f"📹 提取视频帧")
        print(f"{'=' * 70}")
        print(f"   视频文件: {os.path.basename(video_path)}")
        print(f"   提取间隔: {interval} 秒")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log("📹 开始提取视频帧", "header")
            log_stream.add_log(f"提取间隔: {interval} 秒", "info")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        frame_interval = int(fps * interval)
        frames = []
        frame_count = 0
        extracted_count = 0
        
        print(f"视频信息:")
        print(f"   FPS: {fps:.2f}")
        print(f"   总帧数: {total_frames}")
        print(f"   时长: {duration:.2f} 秒")
        print(f"   预计提取: {int(duration / interval)} 帧\n")
        
        if has_log_stream:
            log_stream.add_log(f"视频时长: {duration:.2f} 秒", "info")
            log_stream.add_log(f"预计提取: {int(duration / interval)} 帧", "info")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                frames.append(frame)
                extracted_count += 1
                if extracted_count % 10 == 0:
                    print(f"已提取 {extracted_count} 帧...")
                    if has_log_stream:
                        log_stream.add_log(f"已提取 {extracted_count} 帧", "info")
            
            frame_count += 1
        
        cap.release()
        
        print(f"\n✓ 帧提取完成")
        print(f"   共提取: {len(frames)} 帧\n")
        
        if has_log_stream:
            log_stream.add_log(f"✓ 共提取 {len(frames)} 帧", "success")
        
        return frames
    
    def recognize_text_surya(self, frames: List[np.ndarray], languages: List[str] = ["zh", "en"]) -> List[Dict]:
        """使用 Surya OCR 识别文字"""
        from PIL import Image
        
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        print(f"\n{'=' * 70}")
        print(f"🔍 Surya OCR 文字识别")
        print(f"{'=' * 70}")
        print(f"   待识别帧数: {len(frames)}")
        print(f"   识别语言: {', '.join(languages)}")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log("🔍 开始 OCR 文字识别", "header")
            log_stream.add_log(f"待识别: {len(frames)} 帧", "info")
        
        results = []
        
        for idx, frame in enumerate(frames):
            # 转换为 PIL Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # 运行 OCR
            predictions = self.run_ocr(
                [pil_image],
                [languages],
                self.det_model,
                self.det_processor,
                self.rec_model,
                self.rec_processor
            )
            
            # 提取文字
            texts = []
            if predictions and len(predictions) > 0:
                for text_line in predictions[0].text_lines:
                    if text_line.text.strip():
                        texts.append(text_line.text.strip())
            
            results.append({
                'frame_index': idx,
                'texts': texts
            })
            
            if (idx + 1) % 5 == 0:
                print(f"已识别 {idx + 1}/{len(frames)} 帧...")
                if has_log_stream:
                    log_stream.add_log(f"已识别 {idx + 1}/{len(frames)} 帧", "info")
        
        print(f"\n✓ OCR 识别完成\n")
        if has_log_stream:
            log_stream.add_log("✓ OCR 识别完成", "success")
        
        return results
    
    def recognize_text_easyocr(self, frames: List[np.ndarray]) -> List[Dict]:
        """使用 EasyOCR 识别文字"""
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        print(f"\n🔍 EasyOCR 文字识别 ({len(frames)} 帧)...\n")
        if has_log_stream:
            log_stream.add_log(f"🔍 EasyOCR 识别 {len(frames)} 帧", "info")
        
        results = []
        
        for idx, frame in enumerate(frames):
            ocr_results = self.model.readtext(frame)
            texts = [text for _, text, _ in ocr_results if text.strip()]
            
            results.append({
                'frame_index': idx,
                'texts': texts
            })
            
            if (idx + 1) % 5 == 0:
                print(f"已识别 {idx + 1}/{len(frames)} 帧...")
                if has_log_stream:
                    log_stream.add_log(f"已识别 {idx + 1}/{len(frames)} 帧", "info")
        
        print(f"\n✓ OCR 识别完成\n")
        if has_log_stream:
            log_stream.add_log("✓ OCR 识别完成", "success")
        
        return results
    
    def merge_texts(self, ocr_results: List[Dict]) -> str:
        """
        合并和去重文字结果
        
        Args:
            ocr_results: OCR 识别结果列表
            
        Returns:
            合并后的文本
        """
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        print(f"\n{'=' * 70}")
        print(f"📝 合并文字结果")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("📝 合并文字结果", "info")
        
        # 收集所有文本
        all_texts = []
        for result in ocr_results:
            all_texts.extend(result['texts'])
        
        # 去重（保持顺序）
        seen = set()
        unique_texts = []
        for text in all_texts:
            if text not in seen:
                seen.add(text)
                unique_texts.append(text)
        
        # 合并文本
        merged_text = '\n'.join(unique_texts)
        
        print(f"统计信息:")
        print(f"   原始文本行数: {len(all_texts)}")
        print(f"   去重后行数: {len(unique_texts)}")
        print(f"   总字符数: {len(merged_text)}")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log(f"去重后: {len(unique_texts)} 行", "info")
            log_stream.add_log(f"总字符数: {len(merged_text)}", "success")
        
        return merged_text
    
    def recognize_text_cloud(self, frames: List[np.ndarray], provider: str, config: Dict) -> List[Dict]:
        """使用云端 OCR 识别文字"""
        from cloud_ocr import CloudOCRProcessor
        
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        print(f"\n{'=' * 70}")
        print(f"🔍 {provider.upper()} 云端 OCR 识别")
        print(f"{'=' * 70}")
        print(f"   待识别帧数: {len(frames)}")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log(f"🔍 {provider.upper()} 云端 OCR", "header")
            log_stream.add_log(f"待识别: {len(frames)} 帧", "info")
        
        # 创建云端 OCR 处理器
        processor = CloudOCRProcessor(provider, config)
        
        # 处理所有帧
        all_texts = processor.process_frames(frames)
        
        # 转换为统一格式
        results = [{
            'frame_index': 0,
            'texts': all_texts
        }]
        
        print(f"\n✓ 云端 OCR 识别完成\n")
        if has_log_stream:
            log_stream.add_log("✓ 云端 OCR 完成", "success")
        
        return results
    
    def process_video(self, video_path: str, interval: float = 1.0, languages: List[str] = ["zh", "en"], 
                     cloud_provider: str = None, cloud_config: Dict = None) -> Dict:
        """
        处理视频，提取画面文字
        
        Args:
            video_path: 视频文件路径
            interval: 帧提取间隔（秒）
            languages: 识别语言列表
            cloud_provider: 云端 OCR 提供商 (baidu, tencent, aliyun)
            cloud_config: 云端 OCR 配置
            
        Returns:
            包含文本的字典
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 提取帧
        frames = self.extract_frames(video_path, interval)
        
        if len(frames) == 0:
            raise ValueError("未能从视频中提取任何帧")
        
        # OCR 识别
        if cloud_provider and cloud_config:
            # 使用云端 OCR
            ocr_results = self.recognize_text_cloud(frames, cloud_provider, cloud_config)
        elif self.ocr_engine == "surya":
            ocr_results = self.recognize_text_surya(frames, languages)
        elif self.ocr_engine == "easyocr":
            ocr_results = self.recognize_text_easyocr(frames)
        else:
            raise ValueError(f"不支持的 OCR 引擎: {self.ocr_engine}")
        
        # 合并文本
        merged_text = self.merge_texts(ocr_results)
        
        return {
            'text': merged_text,
            'frame_count': len(frames),
            'ocr_results': ocr_results
        }
