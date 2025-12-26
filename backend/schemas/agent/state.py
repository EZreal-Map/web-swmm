from typing import Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


# 定义工具模式状态
class ToolModeState(TypedDict):
    messages: Annotated[
        list, add_messages
    ]  # 消息记录（HumanMessage, AIMessage，ToolMessage）
    client_id: Optional[str]  # 客户端连接ID
    mode: Optional[str]  # 代理模式
    query: Optional[str]  # 当前要解决的问题
    need_backend: Optional[bool]  # 是否需要执行后端工具
    need_frontend: Optional[bool]  # 是否需要执行前端工具
    retry_count: Optional[int]  # 工具重试次数
    next_step: Optional[str]  # 下一步执行节点名称


# 定义计划模式状态
class PlanModeState(TypedDict):
    messages: Annotated[
        list, add_messages
    ]  # 消息记录（HumanMessage, AIMessage，ToolMessage）
    client_id: Optional[str]  # 客户端连接ID
    mode: Optional[str]  # 代理模式
    query: Optional[str]  # 当前要解决的问题
    plans: Optional[str]  # 生成的计划内容
    current_step: Optional[int]  # 当前计划步骤索引
    executed_tools: Annotated[list, add_messages]  # 已执行的计划步骤
