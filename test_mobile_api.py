#!/usr/bin/env python3
"""
使用移动端API解析抖音视频
"""

import asyncio
import httpx
import re
import json
from pathlib import Path

async def parse_douyin_mobile(share_url: str):
    """
    使用移动端方式解析抖音视频
    """
    print(f"🔍 正在解析: {share_url}\n")
    
    # 加载Cookie
    config_path = Path('parsers/config.json')
    cookie = ''
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
            cookie = config.get('douyin', {}).get('cookie', '')
    
    # 模拟移动端浏览器
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.douyin.com/',
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        # 步骤1: 获取重定向后的URL
        print("步骤1: 访问分享链接...")
        response = await client.get(share_url, headers=headers)
        final_url = str(response.url)
        
        print(f"✓ 最终URL: {final_url}\n")
        
        # 提取视频ID
        video_id_match = re.search(r'/video/(\d+)', final_url)
        if not video_id_match:
            video_id_match = re.search(r'video_id=(\d+)', final_url)
        
        if not video_id_match:
            print("❌ 无法提取视频ID")
            return None
        
        video_id = video_id_match.group(1)
        print(f"✓ 视频ID: {video_id}\n")
        
        # 步骤2: 使用移动端API
        print("步骤2: 调用移动端API...")
        
        # 尝试多个可能的API端点
        api_urls = [
            f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}",
            f"https://m.douyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}",
        ]
        
        for api_url in api_urls:
            try:
                print(f"尝试: {api_url}")
                api_response = await client.get(api_url, headers=headers)
                
                if api_response.status_code == 200:
                    try:
                        data = api_response.json()
                        
                        if data.get('status_code') == 0 and 'item_list' in data:
                            items = data['item_list']
                            if items and len(items) > 0:
                                aweme = items[0]
                                
                                # 提取信息
                                desc = aweme.get('desc', '未知标题')
                                author_info = aweme.get('author', {})
                                author_name = author_info.get('nickname', '未知作者')
                                
                                # 视频信息
                                video_info = aweme.get('video', {})
                                play_addr = video_info.get('play_addr', {})
                                
                                video_url = ''
                                if 'url_list' in play_addr and play_addr['url_list']:
                                    video_url = play_addr['url_list'][0]
                                
                                # 封面
                                cover_url = ''
                                cover_info = video_info.get('cover', {})
                                if 'url_list' in cover_info and cover_info['url_list']:
                                    cover_url = cover_info['url_list'][0]
                                
                                # 时长
                                duration = video_info.get('duration', 0) / 1000
                                
                                print("\n" + "=" * 60)
                                print("✅ 解析成功!")
                                print("=" * 60)
                                print(f"📝 标题: {desc}")
                                print(f"👤 作者: {author_name}")
                                print(f"🎬 视频ID: {video_id}")
                                print(f"⏱️  时长: {duration:.1f}秒")
                                print()
                                
                                if video_url:
                                    print(f"🔗 视频地址:")
                                    print(f"   {video_url}")
                                else:
                                    print(f"⚠️  未获取到视频下载地址")
                                
                                print()
                                if cover_url:
                                    print(f"🖼️  封面地址:")
                                    print(f"   {cover_url[:80]}...")
                                
                                print("=" * 60)
                                
                                return {
                                    'success': True,
                                    'video_id': video_id,
                                    'title': desc,
                                    'author': author_name,
                                    'video_url': video_url,
                                    'cover_url': cover_url,
                                    'duration': duration,
                                    'platform': 'douyin'
                                }
                    except json.JSONDecodeError:
                        print(f"  ✗ JSON解析失败")
                        continue
                else:
                    print(f"  ✗ 状态码: {api_response.status_code}")
            except Exception as e:
                print(f"  ✗ 请求失败: {e}")
                continue
        
        print("\n❌ 所有API尝试均失败")
        return {
            'success': False,
            'error': '无法获取视频信息'
        }

async def main():
    """主函数"""
    share_url = "https://v.douyin.com/TRz0nvN5xwQ/"
    
    result = await parse_douyin_mobile(share_url)
    
    if result and result.get('success'):
        print("\n✅ 测试成功！可以开始下载视频了")
    else:
        print("\n❌ 测试失败")

if __name__ == '__main__':
    asyncio.run(main())
