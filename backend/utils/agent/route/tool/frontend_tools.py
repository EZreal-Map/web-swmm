from schemas.agent.state import ToolModeState
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.agent.message_manager import split_ai_message_by_tool_names
from utils.logger import agent_logger
from typing import Literal
from langgraph.types import Send
from utils.agent.node.tool.frontend_tools import HIL_frontend_tools_name


# 3.1 路由函数:决定是否执行前端工具
async def frontend_tools_route(
    state: ToolModeState,
) -> Literal["frontend_tool_execution", "summary_response"]:
    """
    根据最后上一个节点的消息决定是否执行工具:执行工具或跳转到下一个节点(summary_response)
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        agent_logger.warning("没有找到消息用于工具路由")
        return Send("summary_response", state)

    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        agent_logger.debug(
            f"{state.get('client_id')} - 检测到前端工具调用,执行前端工具"
        )
        # 发送步骤消息：正在执行前端工具 {工具集合}
        tool_calls = ai_message.tool_calls
        tool_names = []
        for tool_call in tool_calls:
            tool_names.append(tool_call.get("name"))
        await ChatMessageSendHandler.send_step(
            state.get("client_id", ""),
            f"[前端执行] AI正在执行前端工具...",
            mode=state.get("mode"),
        )
        # 2.前端有工具调用
        # 记录 Send 返回结果
        send_list = []
        split_messages = split_ai_message_by_tool_names(
            ai_message, HIL_frontend_tools_name
        )
        # 2.1 分割后第一个消息为普通工具调用消息
        if split_messages[0]:
            send_list.append(
                Send(
                    "frontend_tool_execution",
                    {
                        "messages": [split_messages[0]],
                        "client_id": state["client_id"],
                        "query": state["query"],
                        "human_in_the_loop": False,
                        "mode": state.get("mode"),
                    },
                )
            )
        # 2.2 分割后第二个消息为人类参与的工具调用消息
        if split_messages[1]:
            send_list.append(
                Send(
                    "frontend_tool_execution",
                    {
                        "messages": [split_messages[1]],
                        "client_id": state["client_id"],
                        "query": state["query"],
                        "human_in_the_loop": True,
                        "mode": state.get("mode"),
                    },
                )
            )
        # 返回调用下一个节点执行工具
        return send_list
    else:
        # 前端LLM没有生成工具调用,跳转到总结节点
        return Send("summary_response", state)
