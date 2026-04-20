"""
OCR API 配置管理模块
支持多个云服务商的 OCR API 配置
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class OCRConfig:
    def __init__(self, config_file: str = "ocr_apis.json"):
        """
        初始化 OCR 配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载 OCR 配置失败: {e}")
                return self._get_default_config()
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "active_provider": "surya",  # 默认使用本地 Surya OCR
            "providers": {
                "surya": {
                    "name": "Surya OCR (本地)",
                    "type": "local",
                    "enabled": True,
                    "description": "本地 OCR，无需 API，免费使用"
                },
                "baidu": {
                    "name": "百度 OCR",
                    "type": "cloud",
                    "enabled": False,
                    "api_key": "",
                    "secret_key": "",
                    "description": "百度智能云 OCR，免费额度 500次/天"
                },
                "tencent": {
                    "name": "腾讯云 OCR",
                    "type": "cloud",
                    "enabled": False,
                    "secret_id": "",
                    "secret_key": "",
                    "region": "ap-guangzhou",
                    "description": "腾讯云 OCR，免费额度 1000次/月"
                },
                "aliyun": {
                    "name": "阿里云 OCR",
                    "type": "cloud",
                    "enabled": False,
                    "access_key_id": "",
                    "access_key_secret": "",
                    "region": "cn-shanghai",
                    "description": "阿里云 OCR，按量付费"
                }
            }
        }
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存 OCR 配置失败: {e}")
            return False
    
    def get_all_providers(self) -> Dict:
        """获取所有 OCR 提供商配置"""
        return self.config.get("providers", {})
    
    def get_active_provider(self) -> str:
        """获取当前激活的 OCR 提供商"""
        return self.config.get("active_provider", "surya")
    
    def set_active_provider(self, provider: str) -> bool:
        """
        设置激活的 OCR 提供商
        
        Args:
            provider: 提供商名称 (surya, baidu, tencent, aliyun)
        """
        if provider in self.config["providers"]:
            self.config["active_provider"] = provider
            return self._save_config()
        return False
    
    def get_provider_config(self, provider: str) -> Optional[Dict]:
        """
        获取指定提供商的配置
        
        Args:
            provider: 提供商名称
        """
        return self.config["providers"].get(provider)
    
    def update_provider_config(self, provider: str, config: Dict) -> bool:
        """
        更新提供商配置
        
        Args:
            provider: 提供商名称
            config: 新的配置信息
        """
        if provider in self.config["providers"]:
            # 更新配置，保留原有字段
            for key, value in config.items():
                if key in self.config["providers"][provider]:
                    self.config["providers"][provider][key] = value
            return self._save_config()
        return False
    
    def add_provider(self, provider: str, config: Dict) -> bool:
        """
        添加新的 OCR 提供商
        
        Args:
            provider: 提供商名称
            config: 配置信息
        """
        self.config["providers"][provider] = config
        return self._save_config()
    
    def remove_provider(self, provider: str) -> bool:
        """
        删除 OCR 提供商
        
        Args:
            provider: 提供商名称
        """
        if provider in self.config["providers"] and provider != "surya":
            del self.config["providers"][provider]
            # 如果删除的是当前激活的，切换到 surya
            if self.config["active_provider"] == provider:
                self.config["active_provider"] = "surya"
            return self._save_config()
        return False
    
    def is_provider_configured(self, provider: str) -> bool:
        """
        检查提供商是否已配置
        
        Args:
            provider: 提供商名称
        """
        config = self.get_provider_config(provider)
        if not config:
            return False
        
        if provider == "surya":
            return True
        elif provider == "baidu":
            return bool(config.get("api_key") and config.get("secret_key"))
        elif provider == "tencent":
            return bool(config.get("secret_id") and config.get("secret_key"))
        elif provider == "aliyun":
            return bool(config.get("access_key_id") and config.get("access_key_secret"))
        
        return False
    
    def get_available_providers(self) -> List[Dict]:
        """获取所有可用的（已配置的）提供商列表"""
        available = []
        for provider, config in self.config["providers"].items():
            if self.is_provider_configured(provider):
                available.append({
                    "id": provider,
                    "name": config["name"],
                    "type": config["type"],
                    "description": config.get("description", ""),
                    "is_active": provider == self.config["active_provider"]
                })
        return available
