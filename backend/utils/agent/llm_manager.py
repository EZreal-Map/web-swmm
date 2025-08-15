import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from utils.logger import agent_logger

# 默认参数
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MODEL = "gpt-4o-mini"


def create_openai_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
) -> ChatOpenAI:
    """快速创建 OpenAI LLM 实例"""
    # 读取环境变量
    load_dotenv()
    if not model:
        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not base_url:
        base_url = os.getenv("OPENAI_BASE_URL")
    if temperature is None:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", DEFAULT_TEMPERATURE))

    if not api_key:
        agent_logger.error("API_KEY未设置,请检查环境变量OPENAI_API_KEY")
        raise ValueError("API_KEY未设置,请检查环境变量OPENAI_API_KEY")

    # 初始化参数
    init_params = {"model": model, "api_key": api_key, "temperature": temperature}

    if base_url:
        init_params["base_url"] = base_url

    return ChatOpenAI(**init_params)


if __name__ == "__main__":
    # 测试创建 LLM 实例
    llm = create_openai_llm()
    print(f"LLM实例已创建: {llm.model_name}")
