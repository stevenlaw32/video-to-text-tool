"""
简化版 OCR 模块 - 仅支持云端 OCR
不依赖 Surya，避免编译问题
"""
import os
import cv2
import numpy as np
from typing import List, Dict
from cloud_ocr import CloudOCRProcessor


class SimpleOCR:
    """简化版 OCR - 仅支持云端 API"""
    
    def __init__(self):
        """初始化"""
        print("初始化简化版 OCR（仅云端 API）")
    
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
    
    def merge_texts(self, texts: List[str]) -> str:
        """
        合并和去重文字结果
        
        Args:
            texts: 文字列表
            
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
        
        # 去重（保持顺序）
        seen = set()
        unique_texts = []
        for text in texts:
            if text and text not in seen:
                seen.add(text)
                unique_texts.append(text)
        
        # 合并文本
        merged_text = '\n'.join(unique_texts)
        
        print(f"统计信息:")
        print(f"   原始文本行数: {len(texts)}")
        print(f"   去重后行数: {len(unique_texts)}")
        print(f"   总字符数: {len(merged_text)}")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log(f"去重后: {len(unique_texts)} 行", "info")
            log_stream.add_log(f"总字符数: {len(merged_text)}", "success")
        
        return merged_text
    
    def process_video(self, video_path: str, interval: float = 1.0,
                     cloud_provider: str = None, cloud_config: Dict = None) -> Dict:
        """
        处理视频，使用云端 OCR 提取画面文字
        
        Args:
            video_path: 视频文件路径
            interval: 帧提取间隔（秒）
            cloud_provider: 云端 OCR 提供商 (baidu, tencent, aliyun)
            cloud_config: 云端 OCR 配置
            
        Returns:
            包含文本的字典
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        if not cloud_provider or not cloud_config:
            raise ValueError("简化版 OCR 仅支持云端 API，请配置云端 OCR 提供商")
        
        # 提取帧
        frames = self.extract_frames(video_path, interval)
        
        if len(frames) == 0:
            raise ValueError("未能从视频中提取任何帧")
        
        # 使用云端 OCR
        processor = CloudOCRProcessor(cloud_provider, cloud_config)
        all_texts = processor.process_frames(frames)
        
        # 合并文本
        merged_text = self.merge_texts(all_texts)
        
        return {
            'text': merged_text,
            'frame_count': len(frames)
        }
