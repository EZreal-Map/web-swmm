from schemas.agent.state import ToolModeState
from utils.logger import agent_logger
from utils.agent.serial_tool_node import SerialToolNode
from langgraph.prebuilt import ToolNode
from utils.agent.node.tool.frontend_tools import frontend_tools


# 3.2 前端工具执行节点
# Send 到这个节点,分为并行(toolnode)(自动执行)和 (serialtoolnode)(人类参与)
# (重点:这里用同步,异步会导致human in the loop问题)
async def frontend_tool_execution_node(send_state: ToolModeState) -> dict:
    """前端工具执行节点:实际执行前端工具"""
    if send_state.get("human_in_the_loop", False):
        agent_logger.debug(
            f"{send_state.get('client_id')} - 开始执行前端工具(人类参与): messages: {send_state.get('messages', [])}"
        )
        frontend_tool_node = SerialToolNode(tools=frontend_tools)
        result = await frontend_tool_node.ainvoke(send_state)
        agent_logger.debug(
            f"{send_state.get('client_id')} - 前端工具(人类参与)执行结果: {result}"
        )
        return result
    else:
        agent_logger.debug(
            f"{send_state.get('client_id')} -  开始执行前端工具(自动执行): messages: {send_state.get('messages', [])}"
        )
        frontend_tool_node = ToolNode(tools=frontend_tools)
        result = await frontend_tool_node.ainvoke(send_state)
        agent_logger.debug(
            f"{send_state.get('client_id')} - 前端工具(自动执行)执行结果: {result}"
        )
        return result
