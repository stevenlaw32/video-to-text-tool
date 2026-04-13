"""
通用 API 客户端模块
支持调用各种第三方 AI 模型 API，如 OpenAI、Claude、通义千问等
"""

from openai import OpenAI
from typing import Optional, List, Dict, Any
from api_config import APIConfig


class UniversalAPIClient:
    """通用 API 客户端类"""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        初始化 API 客户端
        
        Args:
            config: API 配置对象，如果不提供则使用默认配置
        """
        self.config = config or APIConfig()
        
        # 验证配置
        is_valid, error_msg = self.config.validate_config()
        if not is_valid:
            raise ValueError(f"API 配置无效: {error_msg}")
        
        # 初始化 OpenAI 客户端（兼容 OpenAI API 格式的服务）
        self.client = OpenAI(
            api_key=self.config.get_api_key(),
            base_url=self.config.get_base_url()
        )
        
        self.model_name = self.config.get_model_name()
        self.temperature = self.config.get_temperature()
        self.max_tokens = self.config.get_max_tokens()
        self.default_system_prompt = self.config.get_default_system_prompt()
    
    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        messages_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        发送聊天请求
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词，如果不提供则使用默认值
            temperature: 温度参数，如果不提供则使用配置中的值
            max_tokens: 最大 token 数，如果不提供则使用配置中的值
            model: 模型名称，如果不提供则使用配置中的值
            messages_history: 历史消息列表，格式为 [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            str: AI 回复内容
        """
        try:
            # 构建消息列表
            messages = []
            
            # 添加系统提示词
            system_content = system_prompt or self.default_system_prompt
            if system_content:
                messages.append({"role": "system", "content": system_content})
            
            # 添加历史消息
            if messages_history:
                messages.extend(messages_history)
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": user_message})
            
            # 构建请求参数
            request_params = {
                'model': model or self.model_name,
                'messages': messages
            }
            
            # 只在有值时才添加temperature和max_tokens
            temp_value = temperature if temperature is not None else self.temperature
            if temp_value is not None:
                request_params['temperature'] = temp_value
            
            tokens_value = max_tokens or self.max_tokens
            if tokens_value is not None:
                request_params['max_tokens'] = tokens_value
            
            # 发送请求
            response = self.client.chat.completions.create(**request_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"API 调用失败: {str(e)}")
    
    def summarize(
        self,
        text: str,
        style: str = "summary",
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        文本摘要/整理
        
        Args:
            text: 要处理的文本
            style: 整理风格，可选值：summary（摘要）、tutorial（教程）、notes（笔记）
            custom_prompt: 自定义提示词，如果提供则忽略 style 参数
            model: 模型名称，如果不提供则使用配置中的值
        
        Returns:
            str: 整理后的文本
        """
        if custom_prompt:
            prompt = custom_prompt.replace('{text}', text)
        else:
            prompts = {
                "summary": """请对以下文本进行总结。要求：

1. 概括主要内容（3-5句话）
2. 列出关键要点（5-10条）
3. 提取重要结论
4. 使用Markdown格式

文本内容：
{text}

请开始总结：""",
                
                "tutorial": """请将以下文本整理成结构化的教程文档。要求：

1. 提取主题和核心内容
2. 按逻辑顺序组织成章节
3. 列出关键要点和步骤
4. 如有代码或命令，单独列出
5. 使用Markdown格式
6. 保持专业和易读

文本内容：
{text}

请开始整理：""",
                
                "notes": """请将以下文本整理成学习笔记。要求：

1. 使用清晰的标题和子标题
2. 提取核心概念和定义
3. 列出重要示例
4. 标注需要注意的要点
5. 使用Markdown格式，适当使用列表和引用

文本内容：
{text}

请开始整理："""
            }
            
            prompt = prompts.get(style, prompts["summary"]).format(text=text)
        
        return self.chat(
            user_message=prompt,
            system_prompt="你是一个专业的内容整理助手，擅长将文本整理成结构化的文档。",
            model=model
        )
    
    def analyze(
        self,
        text: str,
        analysis_type: str = "general",
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        文本分析
        
        Args:
            text: 要分析的文本
            analysis_type: 分析类型，可选值：general（通用）、sentiment（情感）、keywords（关键词）
            custom_prompt: 自定义提示词，如果提供则忽略 analysis_type 参数
            model: 模型名称，如果不提供则使用配置中的值
        
        Returns:
            str: 分析结果
        """
        if custom_prompt:
            prompt = custom_prompt.replace('{text}', text)
        else:
            prompts = {
                "general": """请对以下文本进行全面分析，包括：
1. 主题和内容概述
2. 关键信息提取
3. 逻辑结构分析
4. 重要观点总结

文本内容：
{text}

请开始分析：""",
                
                "sentiment": """请对以下文本进行情感分析，包括：
1. 整体情感倾向（积极/消极/中性）
2. 情感强度
3. 关键情感词汇
4. 情感变化趋势（如果有）

文本内容：
{text}

请开始分析：""",
                
                "keywords": """请从以下文本中提取关键词和关键短语，要求：
1. 按重要性排序
2. 标注词频
3. 分类整理（如：主题词、专业术语、人名地名等）

文本内容：
{text}

请开始提取："""
            }
            
            prompt = prompts.get(analysis_type, prompts["general"]).format(text=text)
        
        return self.chat(
            user_message=prompt,
            system_prompt="你是一个专业的文本分析助手，擅长从文本中提取有价值的信息。",
            model=model
        )
    
    def translate(
        self,
        text: str,
        target_language: str = "中文",
        source_language: str = "自动检测",
        model: Optional[str] = None
    ) -> str:
        """
        文本翻译
        
        Args:
            text: 要翻译的文本
            target_language: 目标语言
            source_language: 源语言，默认自动检测
            model: 模型名称，如果不提供则使用配置中的值
        
        Returns:
            str: 翻译结果
        """
        prompt = f"""请将以下文本从{source_language}翻译成{target_language}。
要求：
1. 保持原文的语气和风格
2. 确保翻译准确、流畅
3. 专业术语需要准确翻译
4. 只输出翻译结果，不要添加任何解释

原文：
{text}

翻译："""
        
        return self.chat(
            user_message=prompt,
            system_prompt="你是一个专业的翻译助手，擅长多语言翻译。",
            model=model
        )
    
    def batch_process(
        self,
        texts: List[str],
        process_func: str = "summarize",
        **kwargs
    ) -> List[str]:
        """
        批量处理文本
        
        Args:
            texts: 文本列表
            process_func: 处理函数名称，可选值：summarize、analyze、translate
            **kwargs: 传递给处理函数的其他参数
        
        Returns:
            List[str]: 处理结果列表
        """
        results = []
        func_map = {
            "summarize": self.summarize,
            "analyze": self.analyze,
            "translate": self.translate
        }
        
        if process_func not in func_map:
            raise ValueError(f"不支持的处理函数: {process_func}")
        
        func = func_map[process_func]
        
        for i, text in enumerate(texts, 1):
            print(f"处理第 {i}/{len(texts)} 个文本...")
            result = func(text, **kwargs)
            results.append(result)
        
        return results
    
    def stream_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        messages_history: Optional[List[Dict[str, str]]] = None
    ):
        """
        流式聊天请求（生成器）
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            model: 模型名称
            messages_history: 历史消息列表
        
        Yields:
            str: 流式返回的文本片段
        """
        try:
            messages = []
            
            system_content = system_prompt or self.default_system_prompt
            if system_content:
                messages.append({"role": "system", "content": system_content})
            
            if messages_history:
                messages.extend(messages_history)
            
            messages.append({"role": "user", "content": user_message})
            
            stream = self.client.chat.completions.create(
                model=model or self.model_name,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise Exception(f"流式 API 调用失败: {str(e)}")
