from volcenginesdkarkruntime import Ark
from django.conf import settings


def call_doubao(user_input, context=""):

    client = Ark(api_key=settings.DOUBAO_API_KEY)

    system_prompt = settings.SYSTEM_PROMPT
    if context:
        system_prompt += f"\n\n参考资料：\n{context}\n请根据参考资料回答用户问题。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    completion = client.chat.completions.create(
        model=settings.DOUBAO_MODEL,
        messages=messages,
        max_tokens=settings.DOUBAO_MAX_TOKENS
    )

    return completion.choices[0].message.content