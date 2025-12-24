from typing import Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


# 定义聊天机器人的状态
class ToolModeSate(TypedDict):
    messages: Annotated[
        list, add_messages
    ]  # 消息记录（HumanMessage, AIMessage，ToolMessage）
    client_id: Optional[str]  # 客户端连接ID
    query: Optional[str]  # 当前要解决的问题
    need_backend: Optional[bool]  # 是否需要执行后端工具
    need_frontend: Optional[bool]  # 是否需要执行前端工具
    retry_count: Optional[int]  # 工具重试次数
    next_step: Optional[str]  # 下一步执行节点名称
    mode: Optional[str]  # 代理模式
