#!/usr/bin/env python3
"""
测试抖音链接解析
"""

import asyncio
import logging
from local_video_parser import LocalVideoParser

logging.basicConfig(level=logging.INFO)

async def test_parse():
    """测试解析抖音链接"""
    parser = LocalVideoParser()
    
    # 测试链接
    url = "https://www.douyin.com/video/7630354436925191034"
    
    print(f"🔍 正在解析链接: {url}\n")
    
    result = await parser.parse(url)
    
    print("=" * 60)
    print("解析结果:")
    print("=" * 60)
    
    if result.get('success'):
        print(f"✅ 解析成功!")
        print(f"")
        print(f"📱 平台: {result.get('platform', 'N/A')}")
        print(f"📝 标题: {result.get('title', 'N/A')}")
        print(f"👤 作者: {result.get('author', 'N/A')}")
        print(f"🎬 视频ID: {result.get('video_id', 'N/A')}")
        print(f"⏱️  时长: {result.get('duration', 0):.1f}秒")
        print(f"")
        print(f"🔗 视频下载地址:")
        video_url = result.get('video_url', '')
        if video_url:
            print(f"   {video_url[:100]}...")
        else:
            print(f"   ⚠️  未获取到下载地址")
        print(f"")
        print(f"🖼️  封面地址:")
        cover_url = result.get('cover_url', '')
        if cover_url:
            print(f"   {cover_url[:100]}...")
        else:
            print(f"   ⚠️  未获取到封面")
    else:
        print(f"❌ 解析失败")
        print(f"错误: {result.get('error', '未知错误')}")
    
    print("=" * 60)
    
    return result

if __name__ == '__main__':
    asyncio.run(test_parse())
