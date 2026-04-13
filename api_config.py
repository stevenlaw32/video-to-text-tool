"""
API 配置管理模块
用于管理第三方 API 的配置信息，支持从环境变量或数据库读取配置
"""

import os
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv, set_key, find_dotenv
import json


class APIConfig:
    """API 配置管理类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化 API 配置
        
        Args:
            config_file: 配置文件路径，默认使用 .env 文件
        """
        self.config_file = config_file or find_dotenv() or '.env'
        load_dotenv(self.config_file)
        
        # 默认配置
        self.default_config = {
            'base_url': 'https://api.openai.com/v1',
            'model_provider': 'openai',
            'model_name': 'gpt-4o',
            'temperature': 0.7,
            'max_tokens': 4000,
            'default_system_prompt': '你是一个专业的文档助手，擅长将会议录音转录、视频内容等文本整理成结构化的文档。你特别擅长生成会议纪要、课程笔记和内容摘要。'
        }
    
    def get_api_key(self) -> str:
        """获取 API Key"""
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("未设置 OPENAI_API_KEY，请先配置 API Key")
        return api_key
    
    def get_base_url(self) -> str:
        """获取 Base URL"""
        return os.getenv('OPENAI_BASE_URL', self.default_config['base_url'])
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return os.getenv('MODEL_NAME', self.default_config['model_name'])
    
    def get_model_provider(self) -> str:
        """获取模型提供商"""
        return os.getenv('MODEL_PROVIDER', self.default_config['model_provider'])
    
    def get_temperature(self) -> Optional[float]:
        """获取温度参数，如果未设置返回None使用API默认值"""
        temp_str = os.getenv('TEMPERATURE', '')
        if temp_str and temp_str.lower() != 'none':
            try:
                return float(temp_str)
            except ValueError:
                return None
        return None
    
    def get_max_tokens(self) -> Optional[int]:
        """获取最大 token 数，如果未设置返回None使用API默认值"""
        tokens_str = os.getenv('MAX_TOKENS', '')
        if tokens_str and tokens_str.lower() != 'none':
            try:
                return int(tokens_str)
            except ValueError:
                return None
        return None
    
    def get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        return os.getenv('DEFAULT_SYSTEM_PROMPT', self.default_config['default_system_prompt'])
    
    def get_all_config(self) -> Dict[str, any]:
        """获取所有配置"""
        return {
            'api_key': self.get_api_key(),
            'base_url': self.get_base_url(),
            'model_name': self.get_model_name(),
            'model_provider': self.get_model_provider(),
            'temperature': self.get_temperature(),
            'max_tokens': self.get_max_tokens(),
            'default_system_prompt': self.get_default_system_prompt()
        }
    
    def update_config(self, **kwargs) -> bool:
        """
        更新配置
        
        Args:
            **kwargs: 配置项，支持的键：
                - api_key: API Key
                - base_url: Base URL
                - model_name: 模型名称
                - model_provider: 模型提供商
                - temperature: 温度参数
                - max_tokens: 最大 token 数
                - default_system_prompt: 默认系统提示词
        
        Returns:
            bool: 是否更新成功
        """
        try:
            env_path = Path(self.config_file)
            
            # 确保 .env 文件存在
            if not env_path.exists():
                env_path.touch()
            
            # 映射配置键到环境变量名
            key_mapping = {
                'api_key': 'OPENAI_API_KEY',
                'base_url': 'OPENAI_BASE_URL',
                'model_name': 'MODEL_NAME',
                'model_provider': 'MODEL_PROVIDER',
                'temperature': 'TEMPERATURE',
                'max_tokens': 'MAX_TOKENS',
                'default_system_prompt': 'DEFAULT_SYSTEM_PROMPT'
            }
            
            # 更新配置
            for key, value in kwargs.items():
                if key in key_mapping:
                    env_key = key_mapping[key]
                    if value is None:
                        # 如果值为None，设置为空字符串表示使用默认值
                        set_key(str(env_path), env_key, '')
                    else:
                        set_key(str(env_path), env_key, str(value))
            
            # 重新加载环境变量
            load_dotenv(self.config_file, override=True)
            
            return True
        except Exception as e:
            print(f"更新配置失败: {str(e)}")
            return False
    
    def validate_config(self) -> tuple[bool, str]:
        """
        验证配置是否完整
        
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            api_key = self.get_api_key()
            if not api_key:
                return False, "API Key 未设置"
            
            base_url = self.get_base_url()
            if not base_url:
                return False, "Base URL 未设置"
            
            model_name = self.get_model_name()
            if not model_name:
                return False, "模型名称未设置"
            
            return True, "配置验证成功"
        except Exception as e:
            return False, str(e)
    
    def export_config(self, output_file: str) -> bool:
        """
        导出配置到 JSON 文件（不包含敏感信息）
        
        Args:
            output_file: 输出文件路径
        
        Returns:
            bool: 是否导出成功
        """
        try:
            config = {
                'base_url': self.get_base_url(),
                'model_name': self.get_model_name(),
                'model_provider': self.get_model_provider(),
                'temperature': self.get_temperature(),
                'max_tokens': self.get_max_tokens(),
                'default_system_prompt': self.get_default_system_prompt()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"导出配置失败: {str(e)}")
            return False
