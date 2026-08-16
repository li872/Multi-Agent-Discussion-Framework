# 云端大模型客户端：统一从 settings 读 key / base / model
# 从 .env 读配置，创建 ChatOpenAI

from langchain_openai import ChatOpenAI

from backend.config import settings


def get_chat_llm(*, temperature: float = 0.7, timeout: float = 30) -> ChatOpenAI:
    if not settings.llm_api_key or settings.llm_api_key.startswith("xxxx"):
        raise RuntimeError(
            "LLM_API_KEY 未配置。请在项目根目录 .env 里填真实 key。"
        )
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base or None,
        temperature=temperature,
        timeout=timeout,
        stream_usage=True,
    )