import time
from collections.abc import Iterator


class EchoLLMProvider:
    """开发模式模型，不调用外部 API，只回显检索上下文。"""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        preview = user_prompt.strip().replace("\n", " ")[:500]
        return (
            "当前没有配置 OPENAI_API_KEY，已回退到开发模式 echo，未调用真实大模型。\n\n"
            f"检索上下文预览：{preview}\n\n"
            "请在 .env 中填写 OPENAI_API_KEY，然后重启服务并重新摄取文档。"
        )

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """把完整回答切成小块模拟流式输出。"""
        answer = self.generate(system_prompt, user_prompt)
        step = 18
        for index in range(0, len(answer), step):
            yield answer[index : index + step]
            time.sleep(0.03)
