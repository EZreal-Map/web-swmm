import os
from typing import Optional, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from utils.logger import agent_logger

# 默认参数
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MODEL = "gpt-4o-mini"

# 默认模型列表,用于前端下拉等
DEFAULT_MODELS: List[str] = ["gpt-4o-mini", "gpt-4o"]
SELECTED_MODEL = DEFAULT_MODEL


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

    agent_logger.info(
        f"创建OpenAI LLM实例: model={model}, base_url={base_url}, temperature={temperature}"
    )
    # 初始化参数
    init_params = {"model": model, "api_key": api_key, "temperature": temperature}
    # 保存选择的模型名称
    LLMRegistry.set_selected_model_name(model)
    if base_url:
        init_params["base_url"] = base_url

    return ChatOpenAI(**init_params)


class LLMRegistry:
    _llms: dict[str, ChatOpenAI] = {}
    SELECTED_MODEL_NAME: str = DEFAULT_MODEL

    @classmethod
    def register(cls, name: str, llm: ChatOpenAI):
        cls._llms[name] = llm
        agent_logger.info(f"LLM 注册成功: name={name}")

    @classmethod
    def get(cls, name: str) -> ChatOpenAI:
        if name not in cls._llms:
            return None
        return cls._llms[name]

    @classmethod
    def exists(cls, name: str) -> bool:
        return name in cls._llms

    @classmethod
    def clear(cls):
        cls._llms.clear()

    @classmethod
    def get_selected_model_name(cls) -> str:
        """获取当前选择的模型名称"""
        return cls.SELECTED_MODEL_NAME

    @classmethod
    def set_selected_model_name(cls, model_name: str):
        """设置当前选择的模型名称"""
        avaiable_models = get_available_models()
        if model_name not in avaiable_models:
            raise ValueError(f"不支持的模型: {model_name}")
        cls.SELECTED_MODEL_NAME = model_name


def get_available_models() -> List[str]:
    """从 .env 读取可用模型列表,未配置则返回默认列表。
    .env 示例:
    OPENAI_MODELS=gpt-4o-mini,gpt-4o
    """
    # 热加载环境变量，覆盖已有变量
    load_dotenv(override=True)
    raw = os.getenv("OPENAI_MODELS")
    if not raw:
        return DEFAULT_MODELS

    models: List[str] = []
    for item in raw.split(","):
        name = item.strip()
        if name:
            models.append(name)

    return models or DEFAULT_MODELS


if __name__ == "__main__":
    # 测试创建 LLM 实例
    llm = create_openai_llm()
    print(f"LLM实例已创建: {llm.model_name}")
