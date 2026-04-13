"""
AI 摘要生成器 - 兼容版本
为了兼容 main.py，提供与 ai_summarizer_v2 相同的接口
"""

import os
from api_client import UniversalAPIClient
from api_config import APIConfig
from typing import Optional


class AISummarizer:
    def __init__(self, config: Optional[APIConfig] = None):
        """
        初始化 AI 摘要生成器
        
        Args:
            config: API 配置对象，如果不提供则使用默认配置
        """
        self.client = UniversalAPIClient(config)
    
    def summarize(self, transcript: str, style: str = "tutorial") -> str:
        """
        使用 AI 整理视频转录文本
        
        Args:
            transcript: 视频转录文本
            style: 整理风格，可选值：tutorial（教程）、summary（摘要）、notes（笔记）
        
        Returns:
            str: 整理后的文本
        """
        return self.client.summarize(transcript, style=style)
    
    def batch_summarize(self, transcripts: list[str], style: str = "tutorial") -> list[str]:
        """
        批量处理多个转录文本
        
        Args:
            transcripts: 转录文本列表
            style: 整理风格
        
        Returns:
            list[str]: 整理后的文本列表
        """
        return self.client.batch_process(transcripts, process_func="summarize", style=style)
    
    def save_summary(self, summary: str, output_path: str):
        """
        保存摘要到文件
        
        Args:
            summary: 摘要内容
            output_path: 输出文件路径
        """
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"总结已保存到: {output_path}")
