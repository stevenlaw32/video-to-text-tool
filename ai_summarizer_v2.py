from openai import OpenAI
from dotenv import load_dotenv
import os

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
        
        messages = [
            {"role": "system", "content": "你是一个专业的内容整理助手。"},
            {"role": "user", "content": f"{prompt}\n\n{text}"}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    def save_summary(self, summary, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary)
