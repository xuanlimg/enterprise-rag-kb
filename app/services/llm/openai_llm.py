from collections.abc import Iterator


class OpenAILLMProvider:
    """OpenAI 兼容接口的大模型提供方。"""

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """调用支持流式输出的 Chat Completions 接口。"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
