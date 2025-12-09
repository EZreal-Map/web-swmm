from langchain_core.tools import tool
from pydantic import Field
from langgraph.types import interrupt
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
from langgraph.errors import GraphInterrupt
from utils.agent.websocket_manager import ChatMessageSendHandler
import asyncio


# 人类信息补充工具
@tool
def human_info_completion_tool(
    input_title: str = Field(
        description="补充信息的标题提示信息，标题提示信息要求尽量详细，参数信息可以分为必要参数信息和可选参数信息。可选参数可以不用强制输入，可以跳过，系统会使用默认值。例如：创建节点J100所需参数补充：请继续提供节点的必要参数：经度、纬度；可选参数：高程、初始水深、最大水深等（可选参数可不输入，系统将使用默认值）。"
    ),
    client_id: Annotated[str, InjectedState("client_id")] = Field(
        description="前端客户端ID，自动注入"
    ),
) -> str:
    """
    1. 仅用于在**创建、新增**实体的时候，信息不全时,向用户请求补充信息。
    2. 除了**创建、新增**需要补充**必要参数**的时候，其他情况不需要调用该工具补充信息。
    不要和其他工具一起调用，因为如果需要调用这个工具，意味着当前上下文信息不足以支持其他工具的正常工作。
    """
    try:
        # 'message' =
        # '(104.213708,28.936575)'
        # 'type' =
        # <RequestMessageType.FEEDBACK: 'feedback'>
        # 'success' =
        # True
        resume_value = interrupt({"input_title": input_title})
        return resume_value
    except GraphInterrupt:
        asyncio.run(
            ChatMessageSendHandler.send_function_call(
                client_id=client_id,
                function_name="showHumanInfoUITool",
                args={"input_title": input_title},
                is_direct_feedback=False,
            )
        )
        raise
