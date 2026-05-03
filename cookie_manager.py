"""
Cookie管理器 - 自动从浏览器获取Cookie
支持Chrome、Safari、Edge、Firefox等主流浏览器
"""

import json
import os
import sys
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

try:
    import browser_cookie3
    HAS_BROWSER_COOKIE = True
except ImportError:
    HAS_BROWSER_COOKIE = False
    logger.warning("browser_cookie3 未安装，无法自动获取浏览器Cookie")


class CookieManager:
    """Cookie管理器"""
    
    def __init__(self, config_path: str = 'parsers/config.json'):
        """
        初始化Cookie管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config_dir = Path(config_path).parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_chrome_cookies(self, domain: str) -> Dict[str, str]:
        """
        从Chrome浏览器获取指定域名的Cookie
        
        Args:
            domain: 域名（如 'douyin.com'）
            
        Returns:
            Cookie字典
        """
        if not HAS_BROWSER_COOKIE:
            return {}
        
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            return cookie_dict
        except Exception as e:
            logger.error(f"从Chrome获取Cookie失败: {e}")
            return {}
    
    def get_safari_cookies(self, domain: str) -> Dict[str, str]:
        """
        从Safari浏览器获取指定域名的Cookie
        
        Args:
            domain: 域名
            
        Returns:
            Cookie字典
        """
        if not HAS_BROWSER_COOKIE:
            return {}
        
        try:
            cookies = browser_cookie3.safari(domain_name=domain)
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            return cookie_dict
        except Exception as e:
            logger.error(f"从Safari获取Cookie失败: {e}")
            return {}
    
    def get_edge_cookies(self, domain: str) -> Dict[str, str]:
        """
        从Edge浏览器获取指定域名的Cookie
        
        Args:
            domain: 域名
            
        Returns:
            Cookie字典
        """
        if not HAS_BROWSER_COOKIE:
            return {}
        
        try:
            cookies = browser_cookie3.edge(domain_name=domain)
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            return cookie_dict
        except Exception as e:
            logger.error(f"从Edge获取Cookie失败: {e}")
            return {}
    
    def get_firefox_cookies(self, domain: str) -> Dict[str, str]:
        """
        从Firefox浏览器获取指定域名的Cookie
        
        Args:
            domain: 域名
            
        Returns:
            Cookie字典
        """
        if not HAS_BROWSER_COOKIE:
            return {}
        
        try:
            cookies = browser_cookie3.firefox(domain_name=domain)
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            return cookie_dict
        except Exception as e:
            logger.error(f"从Firefox获取Cookie失败: {e}")
            return {}
    
    def get_all_browsers_cookies(self, domain: str) -> Dict[str, str]:
        """
        尝试从所有浏览器获取Cookie
        
        Args:
            domain: 域名
            
        Returns:
            Cookie字典（优先级：Chrome > Safari > Edge > Firefox）
        """
        browsers = [
            ('Chrome', self.get_chrome_cookies),
            ('Safari', self.get_safari_cookies),
            ('Edge', self.get_edge_cookies),
            ('Firefox', self.get_firefox_cookies)
        ]
        
        for browser_name, get_func in browsers:
            try:
                cookies = get_func(domain)
                if cookies:
                    logger.info(f"✓ 从 {browser_name} 获取到Cookie")
                    return cookies
            except Exception as e:
                logger.debug(f"从 {browser_name} 获取Cookie失败: {e}")
                continue
        
        return {}
    
    def cookies_dict_to_string(self, cookies: Dict[str, str]) -> str:
        """
        将Cookie字典转换为字符串格式
        
        Args:
            cookies: Cookie字典
            
        Returns:
            Cookie字符串
        """
        return '; '.join([f"{k}={v}" for k, v in cookies.items()])
    
    def auto_update_douyin_cookie(self) -> bool:
        """
        自动更新抖音Cookie
        
        Returns:
            是否成功
        """
        logger.info("正在从浏览器获取抖音Cookie...")
        
        cookies = self.get_all_browsers_cookies('douyin.com')
        
        if not cookies:
            logger.warning("未能从任何浏览器获取到抖音Cookie")
            return False
        
        cookie_string = self.cookies_dict_to_string(cookies)
        
        # 更新配置文件
        config = self._load_config()
        config['douyin']['cookie'] = cookie_string
        self._save_config(config)
        
        logger.info(f"✓ 抖音Cookie已更新（{len(cookie_string)} 字符）")
        return True
    
    def auto_update_xiaohongshu_cookie(self) -> bool:
        """
        自动更新小红书Cookie
        
        Returns:
            是否成功
        """
        logger.info("正在从浏览器获取小红书Cookie...")
        
        cookies = self.get_all_browsers_cookies('xiaohongshu.com')
        
        if not cookies:
            logger.warning("未能从任何浏览器获取到小红书Cookie")
            return False
        
        cookie_string = self.cookies_dict_to_string(cookies)
        
        # 更新配置文件
        config = self._load_config()
        config['xiaohongshu']['cookie'] = cookie_string
        self._save_config(config)
        
        logger.info(f"✓ 小红书Cookie已更新（{len(cookie_string)} 字符）")
        return True
    
    def auto_update_all_cookies(self) -> Dict[str, bool]:
        """
        自动更新所有平台的Cookie
        
        Returns:
            更新结果字典
        """
        results = {
            'douyin': self.auto_update_douyin_cookie(),
            'xiaohongshu': self.auto_update_xiaohongshu_cookie()
        }
        return results
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        
        # 返回默认配置
        return {
            'douyin': {'cookie': ''},
            'xiaohongshu': {'cookie': ''}
        }
    
    def _save_config(self, config: Dict):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def show_cookie_status(self):
        """显示当前Cookie状态"""
        config = self._load_config()
        
        print("\n" + "=" * 60)
        print("Cookie 状态")
        print("=" * 60)
        
        for platform, data in config.items():
            cookie = data.get('cookie', '')
            if cookie:
                print(f"✓ {platform:15s} 已配置 ({len(cookie)} 字符)")
            else:
                print(f"✗ {platform:15s} 未配置")
        
        print("=" * 60 + "\n")


def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cookie管理工具')
    parser.add_argument('--update', '-u', action='store_true', help='自动更新所有Cookie')
    parser.add_argument('--douyin', '-d', action='store_true', help='只更新抖音Cookie')
    parser.add_argument('--xiaohongshu', '-x', action='store_true', help='只更新小红书Cookie')
    parser.add_argument('--status', '-s', action='store_true', help='显示Cookie状态')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    if not HAS_BROWSER_COOKIE:
        print("\n❌ 缺少依赖库 browser_cookie3")
        print("\n请运行以下命令安装：")
        print("  pip install browser-cookie3")
        print("\n或者使用国内镜像：")
        print("  pip install browser-cookie3 -i https://pypi.tuna.tsinghua.edu.cn/simple")
        return
    
    manager = CookieManager()
    
    if args.status:
        manager.show_cookie_status()
        return
    
    if args.douyin:
        print("\n🔄 更新抖音Cookie...")
        success = manager.auto_update_douyin_cookie()
        if success:
            print("✅ 抖音Cookie更新成功！")
        else:
            print("❌ 抖音Cookie更新失败")
            print("\n💡 提示：")
            print("  1. 请先在浏览器中登录抖音网页版")
            print("  2. 确保浏览器已关闭（某些浏览器需要）")
            print("  3. 重新运行此命令")
        return
    
    if args.xiaohongshu:
        print("\n🔄 更新小红书Cookie...")
        success = manager.auto_update_xiaohongshu_cookie()
        if success:
            print("✅ 小红书Cookie更新成功！")
        else:
            print("❌ 小红书Cookie更新失败")
            print("\n💡 提示：")
            print("  1. 请先在浏览器中登录小红书网页版")
            print("  2. 确保浏览器已关闭（某些浏览器需要）")
            print("  3. 重新运行此命令")
        return
    
    if args.update:
        print("\n🔄 自动更新所有Cookie...")
        results = manager.auto_update_all_cookies()
        
        print("\n" + "=" * 60)
        print("更新结果")
        print("=" * 60)
        for platform, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"{platform:15s} {status}")
        print("=" * 60)
        
        if not any(results.values()):
            print("\n💡 提示：")
            print("  1. 请先在浏览器中登录对应网站")
            print("  2. 确保浏览器已关闭（某些浏览器需要）")
            print("  3. 重新运行此命令")
        else:
            print("\n✅ Cookie已更新！现在可以使用视频解析功能了")
        
        return
    
    # 默认显示帮助
    parser.print_help()


if __name__ == '__main__':
    main()
