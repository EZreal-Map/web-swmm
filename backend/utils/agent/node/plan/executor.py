from langgraph.prebuilt import ToolNode

from schemas.agent.state import PlanModeState
from utils.agent.node.tool.backend_tools import (
    HIL_backend_tools_name,
    backend_tools,
)
from utils.agent.node.tool.frontend_tools import (
    HIL_frontend_tools_name,
    frontend_tools,
)
from utils.agent.serial_tool_node import SerialToolNode
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.logger import agent_logger


async def executor_node(state: PlanModeState) -> dict:
    """执行者节点: 根据计划步骤调用相应工具"""
    tools = backend_tools + frontend_tools

    HIL_tools_name = HIL_backend_tools_name + HIL_frontend_tools_name
    tool_message = state.get("messages")[0]
    tool_call_name = tool_message.tool_calls[0].get("name")
    args = tool_message.tool_calls[0].get("args", {})
    tool_state = {
        "messages": [tool_message],
        "client_id": state.get("client_id"),
        "mode": state.get("mode"),
    }
    if tool_call_name in HIL_tools_name:
        backend_execution = SerialToolNode(tools=tools)
        result = await backend_execution.ainvoke(tool_state)
    else:
        backend_execution = ToolNode(tools=tools)
        result = await backend_execution.ainvoke(tool_state)

    await ChatMessageSendHandler.send_tool_message(
        state.get("client_id"), result["messages"][0], state.get("mode")
    )
    agent_logger.debug(f"{state.get('client_id')} - 工具执行节点执行结果: {result}")
    executed_tool_record = f"""
**步骤{state.get("current_step")}** 执行工具 {tool_call_name}
`参数为{args}`
执行结果：{result}
"""
    return {"executed_tools": executed_tool_record}
