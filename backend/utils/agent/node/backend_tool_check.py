from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from langchain_core.messages import HumanMessage
from utils.agent.message_manager import get_split_dialogue_rounds
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm
from typing_extensions import TypedDict
from typing import Literal
from pydantic import Field


class CheckOutput(TypedDict):
    query: str = Field(
        description="若有补充信息则返回合并后的结果，或问题可以进一步完善，否则保持 original_query 不变。"
    )
    next_step: Literal["backend_tools", "frontend_tools", "summary_response"] = Field(
        description="下一步流程跳转指令节点名"
    )
    reason: str = Field(description="简明解释为何更新 query 以及为何选择该 next_step")
    retry_count: int = Field(description="工具重试次数")


llm = create_openai_llm()
backend_tool_check_llm = llm.with_structured_output(CheckOutput)


# 2.3 后端工具检查节点
async def backend_tool_check_node(
    state: State,
) -> dict:
    """后端工具检查节点:检查后端工具执行状态"""
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""),
        f"[工具检查] AI正在检查后端工具执行状态...",
    )
    agent_logger.debug(
        f"{state.get('client_id')} - 后端工具检查节点: messages: {state.get('messages', [])}"
    )

    user_query = state.get("query", "")
    # 获取最后一轮消息
    recent_dialogue_round = get_split_dialogue_rounds(state.get("messages", []), 1)
    # 构造 prompt
    check_prompt = f"""
你是智能流程控制助手，请基于最近一次对话轮次（recent_dialogue_round）返回的工具调用与回复，结合下列已知信息，判断 query 是否需要更新，并决定下一步流程。

【提供的信息】
- original_query: "{user_query}"
- need_backend: {state.get("need_backend")}
- need_frontend: {state.get("need_frontend")}
- recent_dialogue_round: {recent_dialogue_round}
- retry_count: {state.get("retry_count", 3)}

【任务一：处理 query】
1. 检查 recent_dialogue_round 是否包含 human_info_completion_tool 的调用及其有效补充内容。
2. 若存在有效补充，则将补充内容与 original_query 合并为新的完整 query，并准备在 retry_count < 3 的前提下再次进入 backend_tools。
3. 若存在无效补充，如“人工取消填写”或补充信息为空，则停止尝试重新执行后端工具，即使retry_count未达上限。
4. 若未检测到该工具或补充信息无效，则保持 original_query 不变。
5. 或执行错误，可以上下文信息进行修正，完善 query，只是合理完善问题，不要无端改变。
6. 如果 retry_count 已达上限 >= 5，停止尝试重新执行后端工具，检查每次运行的错误原因，合理完善 query，避免无限循环。

【任务二：决定 next_step】
1. 继续阅读 recent_dialogue_round，结合 need_backend / need_frontend / retry_count，判断下一步：
     - backend_tools：需要继续或重新执行后端工具（如刚获得补充信息、需要重试、或仍未完成数据操作），如果“人工取消填写”或补充信息为空，则停止尝试重新执行后端工具，即使retry_count未达上限。
     - frontend_tools：后端数据已满足或无需更改，但需要前端联动展示/跳转。
     - summary_response：已完成所有必要操作或无法继续执行，应该直接总结回复。
2. 说明选择原因，包括是否因为补充信息、错误重试上限、或前端展示需求等。

【输出字段说明】
- query: 若有补充信息则返回合并后的结果，或问题可以进一步完善，否则保持 original_query 不变。
- next_step: backend_tools / frontend_tools / summary_response
- reason: 简明解释为何更新 query 以及为何选择该 next_step
- retry_count: 工具重试次数，即 state 中的 retry_count 值
"""
    # 用结构化输出 LLM 获取判断结果
    check_result = await backend_tool_check_llm.ainvoke(
        [HumanMessage(content=check_prompt)]
    )
    agent_logger.info(f"后端工具检查节点LLM响应: {check_result}")

    next_step = check_result.get("next_step")
    if next_step == "backend_tools":
        state["retry_count"] = state.get("retry_count", 0) + 1
    return {
        "query": check_result.get("query", user_query),
        "next_step": next_step,
        "retry_count": state.get("retry_count", 0),
    }
