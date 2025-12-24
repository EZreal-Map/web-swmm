from schemas.agent.state import ToolModeSate
from utils.logger import agent_logger
from utils.agent.serial_tool_node import SerialToolNode
from langgraph.prebuilt import ToolNode
from utils.agent.node.tool.backend_tools import backend_tools


async def backend_tool_execution_node(send_state: ToolModeSate) -> dict:
    """后端工具执行节点:实际执行后端工具"""
    if send_state.get("human_in_the_loop", False):
        agent_logger.debug(
            f"{send_state.get('client_id')} - 开始执行后端工具(人类参与): messages: {send_state.get('messages', [])}"
        )
        backend_tool_node = SerialToolNode(tools=backend_tools)
        result = backend_tool_node.invoke(send_state)
        agent_logger.debug(
            f"{send_state.get('client_id')} - 后端工具(人类参与)执行结果: {result}"
        )
        return result
    else:
        agent_logger.debug(
            f"{send_state.get('client_id')} -  开始执行后端工具(自动执行): messages: {send_state.get('messages', [])}"
        )
        backend_tool_node = ToolNode(tools=backend_tools)
        result = await backend_tool_node.ainvoke(send_state)
        agent_logger.debug(
            f"{send_state.get('client_id')} - 后端工具(自动执行)执行结果: {result}"
        )
        return result
