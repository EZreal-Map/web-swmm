from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.agent.message_manager import split_ai_message_by_tool_names
from utils.logger import agent_logger
from typing import Literal
from langgraph.types import Send
from utils.agent.node.backend_tools import HIL_backend_tools_name


# 2.1 路由函数:决定是否执行后端工具
async def backend_tools_route(
    state: State,
) -> Literal["backend_tool_execution", "check_node"]:
    """
    决定是否执行后端工具
    如果最后一条消息有tool_calls,则执行工具；否则跳过
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        agent_logger.warning(
            f"{state.get('client_id')} - state格式为空或者不正确,没有找到消息用于工具路由: state={state}"
        )
        # 后端LLM没有生成工具调用,跳转到检查节点
        return Send("check_node", state)

    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        agent_logger.debug(
            f"{state.get('client_id')} - 检测到后端工具调用,执行后端工具"
        )
        # 发送步骤消息：正在执行后端工具
        await ChatMessageSendHandler.send_step(
            state.get("client_id", ""),
            "[后端执行] AI正在执行后端工具...",
        )
        # 2.后端有工具调用
        # 记录 Send 返回结果
        send_list = []
        split_messages = split_ai_message_by_tool_names(
            ai_message, HIL_backend_tools_name
        )
        # 2.1 分割后第一个消息为普通工具调用消息
        if split_messages[0]:
            send_list.append(
                Send(
                    "backend_tool_execution",
                    {
                        "messages": [split_messages[0]],
                        "client_id": state["client_id"],
                        "query": state["query"],
                        "human_in_the_loop": False,
                    },
                )
            )
        # 2.2 分割后第二个消息为人类参与的工具调用消息
        if split_messages[1]:
            send_list.append(
                Send(
                    "backend_tool_execution",
                    {
                        "messages": [split_messages[1]],
                        "client_id": state["client_id"],
                        "query": state["query"],
                        "human_in_the_loop": True,
                    },
                )
            )
        # 返回调用下一个节点执行工具
        return send_list
    else:
        # 后端LLM没有生成工具调用,跳转到检查节点
        return Send("check_node", state)
