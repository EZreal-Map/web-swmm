from langgraph.types import Send
from utils.logger import agent_logger
from schemas.agent.state import PlanModeState
from utils.agent.llm_manager import LLMRegistry
from utils.agent.node.tool.backend_tools import backend_tools
from utils.agent.node.tool.frontend_tools import frontend_tools
from utils.agent.websocket_manager import ChatMessageSendHandler


async def tool_execution_node(state: PlanModeState) -> dict:
    """工具执行节点: 根据计划执行工具"""
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""),
        f"[步骤执行中] 正在根据计划执行步骤{state.get('current_step','')}...",
        state.get("mode"),
    )

    tools = backend_tools + frontend_tools
    tools_llm = LLMRegistry.get("tools_llm")
    if not tools_llm:
        llm = LLMRegistry.get("llm")
        tools_llm = llm.bind_tools(tools=tools)
        LLMRegistry.register("tools_llm", tools_llm)

    tool_execution_prompt = f"""
你是一个工具调用执行者。根据用户的问题和生成的计划，逐步调用相应的工具来解决问题。
问题：{state.get("query")}
计划：{state.get("plans")}
已经执行到步骤：{state.get("current_step")}
已经执行的工具记录：{state.get("executed_tools", [])}
要求：
1. 每次只从计划中执行当前需要执行的步骤(即当前执行步骤所对应的工具调用)
2. 调用工具时，确保传入正确的参数
3. 如果没有计划，就不执行任何工具，直接返回
"""
    response = await tools_llm.ainvoke(tool_execution_prompt)
    if not response.tool_calls:
        no_tool_calls_record = f"**步骤{state.get('current_step')}** 无法解析出工具调用,跳过执行该步骤,请检查计划内容是否正确"
        state.get("executed_tools").append(no_tool_calls_record)
        agent_logger.info(no_tool_calls_record)
        return Send("summary", state)
    tool_state = {
        "messages": [response],
        "client_id": state.get("client_id"),
        "mode": state.get("mode"),
    }
    return Send("executor", tool_state)
