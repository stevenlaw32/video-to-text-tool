#!/usr/bin/env python3
"""
使用TikTokDownloader测试抖音链接解析
"""

import sys
import os
from pathlib import Path

# 添加TikTokDownloader到路径
tiktok_path = Path(__file__).parent / 'parsers' / 'douyin_parser'
if tiktok_path.exists():
    sys.path.insert(0, str(tiktok_path))
    print(f"✓ 已加载 TikTokDownloader: {tiktok_path}")
else:
    print(f"❌ 未找到 TikTokDownloader")
    sys.exit(1)

try:
    # 尝试导入TikTokDownloader的核心模块
    from src.tools import Extractor
    print("✓ 成功导入 Extractor")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("\n尝试查看可用模块...")
    import os
    src_path = tiktok_path / 'src'
    if src_path.exists():
        print(f"src目录内容: {os.listdir(src_path)}")
    sys.exit(1)

def test_parse():
    """测试解析"""
    url = "https://www.douyin.com/video/7630354436925191034"
    
    print(f"\n{'='*60}")
    print(f"测试链接: {url}")
    print(f"{'='*60}\n")
    
    try:
        # 创建提取器
        extractor = Extractor()
        
        # 提取视频信息
        print("正在解析...")
        result = extractor.run(url)
        
        print(f"\n解析结果:")
        print(f"类型: {type(result)}")
        print(f"内容: {result}")
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_parse()
