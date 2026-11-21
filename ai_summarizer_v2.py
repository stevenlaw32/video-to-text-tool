from openai import OpenAI
from dotenv import load_dotenv
import os
from openai_compat import complete_text

load_dotenv()


class AISummarizerV2:
    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model = model or os.getenv('MODEL_NAME', 'gpt-4o')
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def summarize(self, text, style='tutorial', custom_prompt=None):
        if custom_prompt:
            prompt = custom_prompt
        else:
            style_prompts = {
                'tutorial': '请将以下内容整理成结构化的教程格式，包含章节、步骤和要点。',
                'summary': '请对以下内容进行简洁的摘要，提取核心要点。',
                'notes': '请将以下内容整理成学习笔记格式，便于复习和记忆。'
            }
            prompt = style_prompts.get(style, style_prompts['tutorial'])
        
        return complete_text(
            self.client,
            model=self.model,
            user_message=f"{prompt}\n\n{text}",
            developer_prompt="你是一个专业的内容整理助手。",
            temperature=0.7,
            api_mode=os.getenv('OPENAI_API_MODE', 'auto'),
            reasoning_effort=os.getenv('REASONING_EFFORT', 'auto'),
            prompt_cache_ttl=os.getenv('PROMPT_CACHE_TTL', 'auto'),
            service_tier=os.getenv('SERVICE_TIER', 'auto')
        )
    
    def save_summary(self, summary, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary)
