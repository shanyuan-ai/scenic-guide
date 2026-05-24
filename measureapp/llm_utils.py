# measureapp/llm_utils.py
from volcenginesdkarkruntime import Ark
from django.conf import settings
import os
import requests


class BaseAI:
    def __init__(self):
        self.system_prompt = settings.SYSTEM_PROMPT

    def chat(self, user_input, context):
        raise NotImplementedError


class DoubaoAI(BaseAI):
    def __init__(self):
        super().__init__()
        self.client = Ark(api_key=settings.DOUBAO_API_KEY)
        self.model = settings.DOUBAO_MODEL
        self.max_tokens = settings.DOUBAO_MAX_TOKENS

    def chat(self, user_input, context):
        system_prompt = self.system_prompt
        if context:
            system_prompt += f"\n\n参考资料：\n{context}\n请根据参考资料回答用户问题。"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )
            return completion.choices[0].message.content
        except Exception as e:
            return "抱歉，AI 服务暂时不可用，请稍后再试。"


class OpenAICompatibleAI(BaseAI):
    def __init__(self, api_key=None, base_url=None, model=None):
        super().__init__()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

    def chat(self, user_input, context):
        system_prompt = self.system_prompt
        if context:
            system_prompt += f"\n\n参考资料：\n{context}\n请根据参考资料回答用户问题。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "max_tokens": 500
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            )
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception:
            return "抱歉，AI 服务暂时不可用。"


class LocalOllamaAI(BaseAI):
    def __init__(self, base_url="http://localhost:11434", model="qwen:7b"):
        super().__init__()
        self.base_url = base_url
        self.model = model

    def chat(self, user_input, context):
        system_prompt = self.system_prompt
        if context:
            system_prompt += f"\n\n参考资料：\n{context}\n请根据参考资料回答用户问题。"

        full_prompt = f"{system_prompt}\n\n用户：{user_input}\n助手："

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=30
            )
            return response.json()['response']
        except Exception:
            return "本地模型未启动，请检查 Ollama 服务。"


def call_ai_model(user_input, context="", model_type="doubao"):
    models = {
        'doubao': DoubaoAI,
        'openai': lambda: OpenAICompatibleAI(model='gpt-3.5-turbo'),
        'gpt4': lambda: OpenAICompatibleAI(model='gpt-4'),
        'deepseek': lambda: OpenAICompatibleAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat"
        ),
        'qwen': lambda: OpenAICompatibleAI(
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus"
        ),
        'local': LocalOllamaAI,
    }

    if model_type not in models:
        model_type = 'doubao'

    ai_instance = models[model_type]
    if callable(ai_instance) and not isinstance(ai_instance, type):
        ai_instance = ai_instance()
    else:
        ai_instance = ai_instance()

    return ai_instance.chat(user_input, context)


def call_doubao(user_input, context=""):
    return call_ai_model(user_input, context, "doubao")