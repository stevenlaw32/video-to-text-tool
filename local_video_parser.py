"""
本地视频解析器
集成 TikTokDownloader 和 XHS-Downloader
"""

import sys
import os
import json
import logging
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LocalVideoParser:
    """本地视频解析器 - 使用免费开源库"""
    
    def __init__(self, config_path: str = 'parsers/config.json'):
        """
        初始化本地解析器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_parsers()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        
        return {
            'douyin': {'cookie': ''},
            'xiaohongshu': {'cookie': ''}
        }
    
    def _setup_parsers(self):
        """设置解析器路径"""
        project_root = Path(__file__).parent
        douyin_path = project_root / 'parsers' / 'douyin_parser'
        xhs_path = project_root / 'parsers' / 'xhs_parser'
        
        if douyin_path.exists():
            sys.path.insert(0, str(douyin_path))
            logger.info(f"✓ 已加载抖音解析器")
        else:
            logger.warning(f"⚠️  抖音解析器未找到，请运行: ./安装视频解析库.sh")
        
        if xhs_path.exists():
            sys.path.insert(0, str(xhs_path))
            logger.info(f"✓ 已加载小红书解析器")
        else:
            logger.warning(f"⚠️  小红书解析器未找到，请运行: ./安装视频解析库.sh")
    
    async def parse_douyin(self, url: str) -> Dict:
        """
        解析抖音视频
        
        Args:
            url: 抖音视频链接
            
        Returns:
            解析结果
        """
        try:
            # 简化的解析逻辑 - 直接使用 httpx 获取重定向后的真实链接
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)
                real_url = str(response.url)
                
                # 从URL中提取视频ID
                import re
                video_id_match = re.search(r'/video/(\d+)', real_url)
                if not video_id_match:
                    return {
                        'success': False,
                        'error': '无法解析视频ID'
                    }
                
                video_id = video_id_match.group(1)
                
                # 构建API请求获取视频信息
                api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': f'https://www.douyin.com/video/{video_id}',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
                
                cookie = self.config.get('douyin', {}).get('cookie', '')
                if cookie:
                    headers['Cookie'] = cookie
                
                api_response = await client.get(api_url, headers=headers)
                
                # 检查响应
                if api_response.status_code != 200:
                    logger.error(f"API请求失败: {api_response.status_code}")
                    return {
                        'success': False,
                        'error': f'API请求失败: {api_response.status_code}'
                    }
                
                try:
                    data = api_response.json()
                except Exception as e:
                    logger.error(f"解析JSON失败: {e}")
                    logger.error(f"响应内容: {api_response.text[:500]}")
                    return {
                        'success': False,
                        'error': '解析失败，可能需要配置Cookie。请编辑 parsers/config.json 添加抖音Cookie'
                    }
                
                if data.get('status_code') == 0 and 'aweme_detail' in data:
                    aweme = data['aweme_detail']
                    video_info = aweme.get('video', {})
                    
                    # 获取视频下载地址
                    play_addr = video_info.get('play_addr', {})
                    video_url = ''
                    if 'url_list' in play_addr and play_addr['url_list']:
                        video_url = play_addr['url_list'][0]
                    
                    return {
                        'success': True,
                        'platform': 'douyin',
                        'title': aweme.get('desc', '抖音视频'),
                        'author': aweme.get('author', {}).get('nickname', '未知'),
                        'video_url': video_url,
                        'cover_url': video_info.get('cover', {}).get('url_list', [''])[0],
                        'duration': video_info.get('duration', 0) / 1000,
                        'video_id': video_id
                    }
                else:
                    return {
                        'success': False,
                        'error': '解析失败，请检查链接或配置Cookie'
                    }
                    
        except Exception as e:
            logger.error(f"解析抖音视频失败: {e}")
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    async def parse_xiaohongshu(self, url: str) -> Dict:
        """
        解析小红书笔记
        
        Args:
            url: 小红书链接
            
        Returns:
            解析结果
        """
        try:
            # 简化的解析逻辑
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url)
                real_url = str(response.url)
                
                # 从URL中提取笔记ID
                import re
                note_id_match = re.search(r'/explore/([a-zA-Z0-9]+)', real_url)
                if not note_id_match:
                    return {
                        'success': False,
                        'error': '无法解析笔记ID'
                    }
                
                note_id = note_id_match.group(1)
                
                # 构建API请求
                api_url = f"https://edith.xiaohongshu.com/api/sns/web/v1/feed"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Referer': 'https://www.xiaohongshu.com/'
                }
                
                cookie = self.config.get('xiaohongshu', {}).get('cookie', '')
                if cookie:
                    headers['Cookie'] = cookie
                
                params = {
                    'source_note_id': note_id
                }
                
                api_response = await client.get(api_url, headers=headers, params=params)
                data = api_response.json()
                
                if data.get('success'):
                    items = data.get('data', {}).get('items', [])
                    if items:
                        note = items[0].get('note_card', {})
                        
                        # 判断是视频还是图文
                        note_type = note.get('type', 'normal')
                        video_url = ''
                        
                        if note_type == 'video':
                            video_info = note.get('video', {})
                            if 'media' in video_info:
                                video_url = video_info['media'].get('stream', {}).get('h264', [{}])[0].get('master_url', '')
                        
                        return {
                            'success': True,
                            'platform': 'xiaohongshu',
                            'title': note.get('title', '小红书笔记'),
                            'author': note.get('user', {}).get('nickname', '未知'),
                            'video_url': video_url,
                            'cover_url': note.get('cover', {}).get('url', ''),
                            'note_type': note_type,
                            'note_id': note_id
                        }
                
                return {
                    'success': False,
                    'error': '解析失败，请检查链接或配置Cookie'
                }
                    
        except Exception as e:
            logger.error(f"解析小红书笔记失败: {e}")
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    async def parse(self, url: str) -> Dict:
        """
        自动识别并解析视频链接
        
        Args:
            url: 视频链接
            
        Returns:
            解析结果
        """
        # 检测平台
        if 'douyin.com' in url or 'iesdouyin.com' in url:
            return await self.parse_douyin(url)
        elif 'xiaohongshu.com' in url or 'xhslink.com' in url:
            return await self.parse_xiaohongshu(url)
        else:
            return {
                'success': False,
                'error': '不支持的平台或无效的链接'
            }
    
    async def download_video(self, video_url: str, save_path: str) -> Dict:
        """
        下载视频文件
        
        Args:
            video_url: 视频下载地址
            save_path: 保存路径
            
        Returns:
            下载结果
        """
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://www.douyin.com/'
            }
            
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                async with client.stream('GET', video_url, headers=headers) as response:
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(save_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if downloaded % (1024 * 1024) == 0:  # 每1MB打印一次
                                    logger.debug(f"下载进度: {progress:.1f}%")
            
            return {
                'success': True,
                'file_path': str(save_path),
                'file_size': downloaded
            }
            
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 使用示例
async def example():
    """使用示例"""
    parser = LocalVideoParser()
    
    # 解析抖音视频
    print("测试抖音解析...")
    result = await parser.parse("https://v.douyin.com/xxxxx/")
    print(result)
    
    # 解析小红书笔记
    print("\n测试小红书解析...")
    result = await parser.parse("https://www.xiaohongshu.com/explore/xxxxx")
    print(result)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example())
