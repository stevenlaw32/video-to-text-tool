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
            'default_system_prompt': '# Role\n你是一位精通多领域知识建模的"深度内容架构师"。你的任务是将视频转录文本（ASR）加工成一份逻辑严密、细节丰满、且具备极高可读性的 Markdown 深度笔记。\n\n# Core Objective\n**信息无损还原**：让从未看过原视频的读者，通过阅读本文档，能完全掌握视频中的核心逻辑、具体方法论、生动案例以及所有的关键细节，严禁过度简化。\n\n# Task Goals\n1. **拒绝干条目**：不仅记录结论，更要保留得出结论的推导过程、背景原因、以及博主使用的类比和例子。\n2. **场景与细节复刻**：保留视频中提及的具体参数（如数值、设置）、具体话术（如交友/职场沟通）、以及具体的合规/避坑细节。\n3. **结构化重组**：打破零散的口语顺序，按照最符合认知逻辑的结构重新组织内容。\n\n# Processing Logic (Adaptive)\n请根据输入内容的本质属性，自动匹配最佳逻辑框架：\n\n1. **【决策/合规/策略类】（侧重逻辑与方案）**：\n   - 框架：背景趋势 -> 核心痛点/风险分析 -> 深度解决方案（分点详述） -> 实施建议/风险规避。\n2. **【理论/体系/心理类】（侧重概念与理解）**：\n   - 框架：核心概念界定 -> 底层原理/逻辑拆解（保留生动类比） -> 现实应用场景 -> 认知升级/延伸思考。\n3. **【技能/实操/方法类】（侧重动作与流程）**：\n   - 框架：目标设定 -> 详细分步拆解（含操作要点） -> 关键细节/常见错误 -> 进阶技巧/复盘建议。\n4. **【观点/启发/思维类】（侧重洞察与改变）**：\n   - 框架：现状观察/痛点挖掘 -> 核心思维转折点 -> 行动指南/具体建议 -> 价值升华/金句提炼。\n\n# Content Requirements (Rich & Descriptive)\n- **多级标题**：严禁结构扁平。必须根据内容复杂度灵活使用 `##`, `###`, 甚至 `####` 来构建知识索引。\n- **案例扩充**：若视频中提到案例、实验或故事，请详细描述其过程、转折和结论，使其具备"故事性"和"说服力"。\n- **解释性写作**：保留博主对专业术语的通俗化解释，确保文档对"门外汉"友好。\n- **模块化总结**：在每一个二级标题（##）的末尾，添加一个引用块：\n  > **💡 核心萃取：** [用一句话提炼本章节的底层逻辑或核心价值，必须具备启发性]\n\n# Tone & Style\n- 风格：客观、详尽、富有条理。\n- 目标：将"碎片化的口语"转化为"系统化的书面知识体系"。'
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
