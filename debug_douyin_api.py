#!/usr/bin/env python3
"""
调试抖音API响应
"""

import asyncio
import httpx
import json

async def debug_api():
    """调试API"""
    video_id = "7630354436925191034"
    url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
    
    # 加载Cookie
    with open('parsers/config.json', 'r') as f:
        config = json.load(f)
    cookie = config['douyin']['cookie']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.douyin.com/video/{video_id}',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cookie': cookie
    }
    
    print(f"请求URL: {url}")
    print(f"Cookie长度: {len(cookie)}")
    print(f"\n发送请求...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        
        print(f"\n状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"\n响应内容（前1000字符）:")
        print(response.text[:1000])
        
        # 尝试解析JSON
        try:
            data = response.json()
            print(f"\n✓ JSON解析成功")
            print(f"数据结构: {list(data.keys())}")
        except:
            print(f"\n✗ JSON解析失败")
            print(f"内容类型: {response.headers.get('content-type')}")

if __name__ == '__main__':
    asyncio.run(debug_api())
