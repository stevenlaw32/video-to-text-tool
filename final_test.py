#!/usr/bin/env python3
"""
最终测试 - 使用Python 3.11环境
"""

import asyncio
from local_video_parser import LocalVideoParser

async def main():
    """测试抖音分享链接"""
    parser = LocalVideoParser()
    
    # 你提供的分享链接
    url = "https://v.douyin.com/TRz0nvN5xwQ/"
    
    print("=" * 70)
    print("🎯 Python 3.11 环境 - 抖音视频解析测试")
    print("=" * 70)
    print(f"\n🔗 测试链接: {url}\n")
    
    print("开始解析...\n")
    result = await parser.parse(url)
    
    print("=" * 70)
    if result.get('success'):
        print("✅ 解析成功！")
        print("=" * 70)
        print(f"📱 平台: {result.get('platform', 'N/A')}")
        print(f"📝 标题: {result.get('title', 'N/A')}")
        print(f"👤 作者: {result.get('author', 'N/A')}")
        print(f"🎬 视频ID: {result.get('video_id', 'N/A')}")
        
        duration = result.get('duration', 0)
        if duration:
            print(f"⏱️  时长: {duration:.1f}秒")
        
        video_url = result.get('video_url', '')
        if video_url:
            print(f"\n🎥 视频下载地址:")
            print(f"   {video_url[:100]}...")
        else:
            print(f"\n⚠️  未获取到视频下载地址")
        
        cover_url = result.get('cover_url', '')
        if cover_url:
            print(f"\n🖼️  封面地址:")
            print(f"   {cover_url[:100]}...")
        
        print("=" * 70)
        print("\n🎉 测试完成！可以开始使用视频解析功能了！")
        
    else:
        print("❌ 解析失败")
        print("=" * 70)
        print(f"错误信息: {result.get('error', '未知错误')}")
        print("\n💡 提示:")
        print("  - 抖音有严格的反爬虫机制")
        print("  - 建议使用Web界面进行测试")
        print("  - 或者尝试其他平台（小红书）")
        print("=" * 70)

if __name__ == '__main__':
    asyncio.run(main())
