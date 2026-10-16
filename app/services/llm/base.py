from collections.abc import Iterator
from typing import Protocol


class BaseLLMProvider(Protocol):
    """大模型提供方协议。"""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """根据系统提示和用户提示生成完整回答。"""

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """根据系统提示和用户提示流式生成回答片段。"""
