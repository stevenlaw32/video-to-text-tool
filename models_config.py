"""
多模型配置管理模块
支持预设多个API模型配置，方便快速切换
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional


class ModelsConfig:
    """多模型配置管理类"""
    
    def __init__(self, config_file: str = "models.json"):
        """
        初始化多模型配置
        
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
                print(f"加载配置文件失败: {e}")
                return self._get_default_config()
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "models": [],
            "active_model": None
        }
    
    def _save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_all_models(self) -> List[Dict]:
        """获取所有模型配置"""
        return self.config.get("models", [])
    
    def get_model_by_alias(self, alias: str) -> Optional[Dict]:
        """
        根据别名获取模型配置
        
        Args:
            alias: 模型别名
            
        Returns:
            模型配置字典，如果不存在返回None
        """
        for model in self.config.get("models", []):
            if model.get("alias") == alias:
                return model
        return None
    
    def add_model(self, alias: str, api_key: str, base_url: str, 
                  model_provider: str, model_name: str, custom_prompt: str = '',
                  max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> bool:
        """
        添加新的模型配置
        
        Args:
            alias: 模型别名
            api_key: API密钥
            base_url: API基础URL
            model_provider: 模型提供商
            model_name: 模型名称
            custom_prompt: 自定义提示词（可选）
            max_tokens: 最大生成长度（可选）
            temperature: 生成温度（可选）
            
        Returns:
            是否添加成功
        """
        # 检查别名是否已存在
        if self.get_model_by_alias(alias):
            return False
        
        new_model = {
            "alias": alias,
            "api_key": api_key,
            "base_url": base_url,
            "model_provider": model_provider,
            "model_name": model_name,
            "custom_prompt": custom_prompt
        }
        if max_tokens is not None:
            new_model["max_tokens"] = max_tokens
        if temperature is not None:
            new_model["temperature"] = temperature
        
        self.config["models"].append(new_model)
        
        # 如果是第一个模型，设置为活动模型
        if len(self.config["models"]) == 1:
            self.config["active_model"] = alias
        
        return self._save_config()
    
    def update_model(self, alias: str, api_key: Optional[str] = None, 
                     base_url: Optional[str] = None, 
                     model_provider: Optional[str] = None,
                     model_name: Optional[str] = None,
                     custom_prompt: Optional[str] = None,
                     max_tokens: Optional[int] = None,
                     temperature: Optional[float] = None) -> bool:
        """
        更新模型配置
        
        Args:
            alias: 模型别名
            api_key: API密钥（可选）
            base_url: API基础URL（可选）
            model_provider: 模型提供商（可选）
            model_name: 模型名称（可选）
            custom_prompt: 自定义提示词（可选）
            max_tokens: 最大生成长度（可选）
            temperature: 生成温度（可选）
            
        Returns:
            是否更新成功
        """
        model = self.get_model_by_alias(alias)
        if not model:
            return False
        
        if api_key is not None:
            model["api_key"] = api_key
        if base_url is not None:
            model["base_url"] = base_url
        if model_provider is not None:
            model["model_provider"] = model_provider
        if model_name is not None:
            model["model_name"] = model_name
        if custom_prompt is not None:
            model["custom_prompt"] = custom_prompt
        if max_tokens is not None:
            model["max_tokens"] = max_tokens
        if temperature is not None:
            model["temperature"] = temperature
        
        return self._save_config()
    
    def rename_model(self, old_alias: str, new_alias: str,
                     api_key: Optional[str] = None,
                     base_url: Optional[str] = None,
                     model_provider: Optional[str] = None,
                     model_name: Optional[str] = None,
                     custom_prompt: Optional[str] = None,
                     max_tokens: Optional[int] = None,
                     temperature: Optional[float] = None) -> bool:
        """
        重命名模型并更新配置
        
        Args:
            old_alias: 原始别名
            new_alias: 新别名
            api_key: API密钥（可选）
            base_url: API基础URL（可选）
            model_provider: 模型提供商（可选）
            model_name: 模型名称（可选）
            custom_prompt: 自定义提示词（可选）
            max_tokens: 最大生成长度（可选）
            temperature: 生成温度（可选）
            
        Returns:
            是否重命名成功
        """
        # 检查原始模型是否存在
        old_model = self.get_model_by_alias(old_alias)
        if not old_model:
            return False
        
        # 检查新别名是否已被使用（除非新旧别名相同）
        if old_alias != new_alias and self.get_model_by_alias(new_alias):
            return False
        
        # 更新别名
        old_model["alias"] = new_alias
        
        # 更新其他字段
        if api_key is not None:
            old_model["api_key"] = api_key
        if base_url is not None:
            old_model["base_url"] = base_url
        if model_provider is not None:
            old_model["model_provider"] = model_provider
        if model_name is not None:
            old_model["model_name"] = model_name
        if custom_prompt is not None:
            old_model["custom_prompt"] = custom_prompt
        if max_tokens is not None:
            old_model["max_tokens"] = max_tokens
        if temperature is not None:
            old_model["temperature"] = temperature
        
        # 如果重命名的是活动模型，也要更新活动模型的别名
        if self.config.get("active_model") == old_alias:
            self.config["active_model"] = new_alias
        
        return self._save_config()
    
    def delete_model(self, alias: str) -> bool:
        """
        删除模型配置
        
        Args:
            alias: 模型别名
            
        Returns:
            是否删除成功
        """
        models = self.config.get("models", [])
        original_length = len(models)
        
        self.config["models"] = [m for m in models if m.get("alias") != alias]
        
        # 如果删除的是活动模型，切换到第一个模型
        if self.config.get("active_model") == alias:
            if self.config["models"]:
                self.config["active_model"] = self.config["models"][0]["alias"]
            else:
                self.config["active_model"] = None
        
        if len(self.config["models"]) < original_length:
            return self._save_config()
        
        return False
    
    def set_active_model(self, alias: str) -> bool:
        """
        设置活动模型
        
        Args:
            alias: 模型别名
            
        Returns:
            是否设置成功
        """
        if self.get_model_by_alias(alias):
            self.config["active_model"] = alias
            return self._save_config()
        return False
    
    def get_active_model(self) -> Optional[Dict]:
        """获取当前活动的模型配置"""
        active_alias = self.config.get("active_model")
        if active_alias:
            return self.get_model_by_alias(active_alias)
        return None
    
    def get_models_list(self) -> List[Dict[str, str]]:
        """
        获取模型列表（用于下拉框显示）
        
        Returns:
            包含 alias 和 display_name 的列表
        """
        models = []
        for model in self.config.get("models", []):
            models.append({
                "alias": model["alias"],
                "display_name": f"{model['alias']} - {model['model_name']}"
            })
        return models
