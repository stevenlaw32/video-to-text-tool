#!/usr/bin/env python3
"""
测试抖音分享链接解析
"""

import asyncio
import httpx
import re
import json
from pathlib import Path

async def parse_share_link(share_url: str):
    """
    解析抖音分享链接
    
    Args:
        share_url: 分享链接（如 https://v.douyin.com/xxxxx/）
    """
    print(f"🔍 正在解析分享链接: {share_url}\n")
    
    # 加载Cookie
    config_path = Path('parsers/config.json')
    cookie = ''
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
            cookie = config.get('douyin', {}).get('cookie', '')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    
    if cookie:
        headers['Cookie'] = cookie
        print(f"✓ 使用Cookie（{len(cookie)} 字符）\n")
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        # 步骤1: 访问短链接，获取重定向后的完整URL
        print("步骤1: 访问短链接...")
        response = await client.get(share_url, headers=headers)
        final_url = str(response.url)
        
        print(f"✓ 重定向后的URL: {final_url}\n")
        
        # 从URL中提取视频ID
        video_id_match = re.search(r'/video/(\d+)', final_url)
        if not video_id_match:
            print("❌ 无法从URL中提取视频ID")
            return None
        
        video_id = video_id_match.group(1)
        print(f"✓ 视频ID: {video_id}\n")
        
        # 步骤2: 从页面HTML中提取视频信息
        print("步骤2: 解析页面内容...")
        html = response.text
        
        # 尝试从HTML中提取JSON数据
        # 抖音会在页面中嵌入一个包含视频信息的script标签
        json_match = re.search(r'<script id="RENDER_DATA" type="application/json">(.+?)</script>', html)
        
        if json_match:
            try:
                import urllib.parse
                json_str = urllib.parse.unquote(json_match.group(1))
                data = json.loads(json_str)
                
                print(f"✓ 成功提取页面数据\n")
                
                # 解析视频信息
                # 数据结构可能是: data -> video -> aweme_detail
                if isinstance(data, dict):
                    # 尝试多种可能的数据路径
                    aweme_detail = None
                    
                    # 路径1: 直接在根级别
                    for key in data.keys():
                        if 'detail' in key.lower() or 'aweme' in key.lower():
                            aweme_detail = data[key]
                            break
                    
                    # 路径2: 在某个子键中
                    if not aweme_detail:
                        for key, value in data.items():
                            if isinstance(value, dict):
                                for subkey, subvalue in value.items():
                                    if 'detail' in subkey.lower() or 'aweme' in subkey.lower():
                                        aweme_detail = subvalue
                                        break
                    
                    if aweme_detail:
                        print("✓ 找到视频详情数据\n")
                        
                        # 提取基本信息
                        desc = aweme_detail.get('desc', '未知标题')
                        author_info = aweme_detail.get('author', {})
                        author_name = author_info.get('nickname', '未知作者')
                        
                        # 提取视频信息
                        video_info = aweme_detail.get('video', {})
                        play_addr = video_info.get('play_addr', {})
                        
                        # 获取视频URL
                        video_url = ''
                        if 'url_list' in play_addr and play_addr['url_list']:
                            video_url = play_addr['url_list'][0]
                        
                        # 获取封面
                        cover_url = ''
                        if 'cover' in video_info:
                            cover_info = video_info['cover']
                            if 'url_list' in cover_info and cover_info['url_list']:
                                cover_url = cover_info['url_list'][0]
                        
                        # 获取时长
                        duration = video_info.get('duration', 0) / 1000  # 毫秒转秒
                        
                        result = {
                            'success': True,
                            'video_id': video_id,
                            'title': desc,
                            'author': author_name,
                            'video_url': video_url,
                            'cover_url': cover_url,
                            'duration': duration,
                            'platform': 'douyin'
                        }
                        
                        print("=" * 60)
                        print("✅ 解析成功!")
                        print("=" * 60)
                        print(f"📝 标题: {desc}")
                        print(f"👤 作者: {author_name}")
                        print(f"🎬 视频ID: {video_id}")
                        print(f"⏱️  时长: {duration:.1f}秒")
                        print(f"")
                        if video_url:
                            print(f"🔗 视频地址: {video_url[:80]}...")
                        else:
                            print(f"⚠️  未获取到视频下载地址")
                        print(f"")
                        if cover_url:
                            print(f"🖼️  封面地址: {cover_url[:80]}...")
                        print("=" * 60)
                        
                        return result
                    else:
                        print("⚠️  未找到视频详情数据")
                        print(f"数据键: {list(data.keys())[:10]}")
                
            except Exception as e:
                print(f"❌ 解析JSON失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️  未找到RENDER_DATA")
            
            # 尝试其他方法：查找视频标签
            print("\n尝试从HTML中提取视频标签...")
            video_match = re.search(r'<video[^>]*src="([^"]+)"', html)
            if video_match:
                video_url = video_match.group(1)
                print(f"✓ 找到视频URL: {video_url[:80]}...")
                
                return {
                    'success': True,
                    'video_id': video_id,
                    'video_url': video_url,
                    'platform': 'douyin'
                }
        
        return {
            'success': False,
            'error': '无法提取视频信息'
        }

async def main():
    """主函数"""
    # 测试链接
    share_url = "https://v.douyin.com/TRz0nvN5xwQ/"
    
    result = await parse_share_link(share_url)
    
    if not result or not result.get('success'):
        print("\n❌ 解析失败")
        if result:
            print(f"错误: {result.get('error', '未知错误')}")

if __name__ == '__main__':
    asyncio.run(main())
