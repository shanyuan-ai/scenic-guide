# app/agent/llm.py
"""轻量 LLM 客户端,基于 OpenAI-compatible API (DashScope qwen3.5-flash 等)。

用途:后台智能任务(报单关键词提取、分组、摘要生成等),不用于用户直接对话。
"""
import json
import logging

from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> OpenAI:
    """懒初始化 OpenAI 客户端(避免无 key 时启动报错)。"""
    global _client
    if _client is None:
        if not LLM_API_KEY:
            logger.warning('LLM_API_KEY 未配置,LLM 功能不可用')
            return None
        _client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=30.0,
            max_retries=1,
        )
    return _client


def llm_chat(
    prompt: str,
    system_prompt: str = '',
    model: str = '',
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str | None:
    """调用 LLM 获取文本回复。

    Returns:
        模型回复文本;失败返回 None(调用方负责降级处理)。
    """
    client = _get_client()
    if client is None:
        logger.warning('LLM 客户端未初始化,跳过调用')
        return None

    model = model or LLM_MODEL
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            # qwen3 系列默认开 thinking 模式,对结构化输出会思考很久(15s+),
            # 关掉后降到 <1s。后台整合任务不需要深度推理,直接关。
            extra_body={'enable_thinking': False},
        )
        text = resp.choices[0].message.content
        if text is None:
            return None
        return text.strip()

    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as exc:
        logger.warning('LLM 调用失败: %s', exc)
        return None
    except Exception as exc:
        logger.warning('LLM 未知错误: %s', exc)
        return None


def llm_chat_json(
    prompt: str,
    system_prompt: str = '',
    model: str = '',
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> dict | list | None:
    """调用 LLM 并解析 JSON 回复。

    Returns:
        解析后的 dict/list;失败返回 None。
    """
    text = llm_chat(prompt, system_prompt, model, temperature, max_tokens)
    if text is None:
        return None

    # 尝试从回复中提取 JSON(qwen 可能带 markdown 包裹)
    json_str = text
    if '```json' in json_str:
        json_str = json_str.split('```json')[1].split('```')[0]
    elif '```' in json_str:
        json_str = json_str.split('```')[1].split('```')[0]

    try:
        return json.loads(json_str.strip())
    except json.JSONDecodeError:
        logger.warning('LLM 回复 JSON 解析失败: %s', text[:200])
        return None
