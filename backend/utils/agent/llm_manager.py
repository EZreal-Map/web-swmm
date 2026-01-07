import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from utils.logger import agent_logger


# 默认参数
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MODEL = "qwen-plus"

# 默认模型列表,用于前端下拉等
SELECTED_MODEL = DEFAULT_MODEL

# Qwen模型前缀,用于判断是否是Qwen模型
QWEN_MODEL_PREFIXES = ["qwen"]


class LLMRegistry:
    _llms: Dict[str, ChatOpenAI] = {}
    SELECTED_MODEL_NAME: str = DEFAULT_MODEL

    @classmethod
    def register(cls, name: str, llm: ChatOpenAI):
        cls._llms[name] = llm
        agent_logger.info(f"LLM 注册成功: name={name}")

    @classmethod
    def get(cls, name: str) -> Optional[ChatOpenAI]:
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
        available_models = get_available_models()
        if model_name not in available_models:
            raise ValueError(f"不支持的模型: {model_name}")
        cls.SELECTED_MODEL_NAME = model_name


def _is_qwen_model(model: str) -> bool:
    """判断是否是Qwen模型"""
    return any(model.startswith(prefix) for prefix in QWEN_MODEL_PREFIXES)


def create_openai_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
) -> ChatOpenAI:
    """快速创建 OpenAI/Qwen LLM 实例,根据模型名称自动选择提供商"""
    load_dotenv()

    # 如果没有指定模型,使用默认模型
    if not model:
        model = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)

    # 根据模型名称判断是OpenAI还是Qwen
    is_qwen = _is_qwen_model(model)

    # 根据提供商选择对应的配置
    if is_qwen:
        # Qwen配置
        if not api_key:
            api_key = os.getenv("QWEN_API_KEY")
        if not base_url:
            base_url = os.getenv("QWEN_BASE_URL")
        provider_name = "Qwen"
    else:
        # OpenAI配置
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not base_url:
            base_url = os.getenv("OPENAI_BASE_URL")
        provider_name = "OpenAI"

    if temperature is None:
        temperature = DEFAULT_TEMPERATURE

    if not api_key:
        error_msg = f"{provider_name} API_KEY未设置,请检查环境变量"
        agent_logger.error(error_msg)
        raise ValueError(error_msg)

    agent_logger.info(
        f"创建{provider_name} LLM实例: model={model}, base_url={base_url}, temperature={temperature}"
    )
    init_params = {"model": model, "api_key": api_key, "temperature": temperature}
    LLMRegistry.set_selected_model_name(model)
    if base_url:
        init_params["base_url"] = base_url

    return ChatOpenAI(**init_params)


def get_available_models() -> List[str]:
    """从 .env 读取可用模型列表(OpenAI + Qwen),未配置则返回默认列表"""
    load_dotenv(override=True)

    # 获取OpenAI模型列表
    openai_raw = os.getenv("OPENAI_MODELS")
    openai_models: List[str] = []
    if openai_raw:
        for item in openai_raw.split(","):
            name = item.strip()
            if name:
                openai_models.append(name)

    # 获取Qwen模型列表
    qwen_raw = os.getenv("QWEN_MODELS")
    qwen_models: List[str] = []
    if qwen_raw:
        for item in qwen_raw.split(","):
            name = item.strip()
            if name:
                qwen_models.append(name)

    # 合并两个列表
    return openai_models + qwen_models


if __name__ == "__main__":
    llm = create_openai_llm()
    print(f"LLM实例已创建: {llm.model_name}")
