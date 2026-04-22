#!/usr/bin/env python3
"""
简化的抖音解析器
使用yt-dlp作为后端（支持抖音、小红书等多个平台）
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SimpleDouyinParser:
    """简化的视频解析器 - 使用yt-dlp"""
    
    def __init__(self):
        """初始化解析器"""
        self.check_ytdlp()
    
    def check_ytdlp(self) -> bool:
        """检查yt-dlp是否安装"""
        try:
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✓ yt-dlp 版本: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            logger.warning("⚠️  yt-dlp 未安装")
            logger.info("安装命令: pip install yt-dlp")
        except Exception as e:
            logger.error(f"检查yt-dlp失败: {e}")
        
        return False
    
    def parse(self, url: str, use_cookies: bool = True) -> Dict:
        """
        解析视频链接
        
        Args:
            url: 视频链接
            use_cookies: 是否使用浏览器Cookie
            
        Returns:
            解析结果
        """
        try:
            # 使用yt-dlp获取视频信息
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
            ]
            
            # 尝试使用浏览器Cookie
            if use_cookies:
                # 尝试多个浏览器
                for browser in ['chrome', 'edge', 'safari', 'firefox']:
                    cmd.extend(['--cookies-from-browser', browser])
                    break  # 只使用第一个
            
            cmd.append(url)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"yt-dlp错误: {error_msg}")
                return {
                    'success': False,
                    'error': f'解析失败: {error_msg[:200]}'
                }
            
            # 解析JSON输出
            info = json.loads(result.stdout)
            
            # 提取关键信息
            return {
                'success': True,
                'platform': info.get('extractor_key', 'unknown').lower(),
                'title': info.get('title', '未知标题'),
                'author': info.get('uploader', info.get('channel', '未知作者')),
                'video_url': info.get('url', ''),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'description': info.get('description', ''),
                'video_id': info.get('id', ''),
                'formats': info.get('formats', [])
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '解析超时'
            }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'JSON解析失败: {str(e)}'
            }
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download(self, url: str, output_path: str) -> Dict:
        """
        下载视频
        
        Args:
            url: 视频链接
            output_path: 输出路径
            
        Returns:
            下载结果
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'yt-dlp',
                '-o', str(output_path),
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"下载失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg[:200]
                }
            
            return {
                'success': True,
                'file_path': str(output_path),
                'message': '下载成功'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '下载超时'
            }
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    parser = SimpleDouyinParser()
    
    # 测试链接
    test_url = "https://v.douyin.com/TRz0nvN5xwQ/"
    
    print(f"\n测试解析: {test_url}\n")
    result = parser.parse(test_url)
    
    print("=" * 60)
    if result.get('success'):
        print("✅ 解析成功！")
        print(f"标题: {result.get('title')}")
        print(f"作者: {result.get('author')}")
        print(f"平台: {result.get('platform')}")
        print(f"时长: {result.get('duration')}秒")
    else:
        print("❌ 解析失败")
        print(f"错误: {result.get('error')}")
    print("=" * 60)
