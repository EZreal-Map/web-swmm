from typing import Literal

from pydantic import Field
from typing_extensions import TypedDict
from langgraph.types import Send

from schemas.agent.state import PlanModeState
from utils.agent.llm_manager import LLMRegistry
from utils.agent.websocket_manager import ChatMessageSendHandler


class PlanCheckOutput(TypedDict):
    next_node: Literal["tool_execution", "planner", "summary"] = Field(
        description="下一跳节点: tool_execution-继续执行工具, planner-重新规划, summary-总结回复"
    )
    next_step: int = Field(
        description="下一步要执行的计划编号。继续执行则加1,重复执行保持不变,回到开头则为1"
    )
    reason: str = Field(
        description="简要说明决策原因。如果是重新执行计划或回到某一步骤,特别说明原因"
    )


async def observer_node(state: PlanModeState) -> dict:
    """观察者节点: 监控工具执行状态，决定是否继续执行或结束"""
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""),
        "[观察反思中] 正在根据计划和步骤执行情况思考中...",
        state.get("mode"),
    )

    observerllm = LLMRegistry.get("observerllm")
    if not observerllm:
        llm = LLMRegistry.get("llm")
        observerllm = llm.with_structured_output(PlanCheckOutput)
        LLMRegistry.register("observerllm", observerllm)

    observer_prompt = f"""
你是工具执行观察者。根据以下信息判断下一跳节点和要执行的计划步骤：

【当前状态】
- 用户问题：{state.get("query")}
- 完整计划：{state.get("plans")}
- 当前已执行到第 {state.get("current_step")} 步（该值表示“最近完成的步骤编号”，判断其执行结果后再决定下一步）
- 最近5次执行记录：{state.get("executed_tools", [])[-5:]}

【判定规则】
1. 阅读完整计划，确认步骤总数与顺序。
2. 结合最近执行记录，判断最新一步是否成功以及对应的计划编号。
3. 若最新完成的步骤已经是计划中的最后一步，或 state.current_step 已等于/超过计划最大编号 → next_node = "summary"，next_step 设为 state.current_step。
4. 若还有步骤待执行：
    - 最新执行成功 → next_node = "tool_execution"，next_step = state.current_step + 1（继续下一计划步骤）。
    - 临时性失败且可重试 → next_node = "tool_execution"，next_step = state.current_step（重新执行同一步）。
    - 若最近执行记录/提示词表明该步骤由用户或人工手动取消（如“人为取消”“手动取消”等），直接进入总结，或者判断还能否执行下一步，不要重复执行该工具，也不应该重新回到规划计划。
    - 如果觉得把执行失败的信息补充上，有很大的概率能够继续执行成功，就重新生成计划（一定要有很大的成功概率才回到计划起点) → next_node = "planner"，next_step = 0（回到计划起点，重新生成计划）。

    - 多次失败或无法继续 → next_node = "summary"，next_step = state.current_step，并说明原因。

【输出要求】
- next_node: "tool_execution"、"planner" 或 "summary"。
- next_step: 下一步要执行的计划编号（遵循上面规则）。
- reason: 第几步骤执行成功还是失败，准备进入哪一步骤，及其理由，简要说明决策原因，尤其是重新计划，要特别说明原因和重新指定计划的建议，已便后续计划的生成。
    """
    response = await observerllm.ainvoke(observer_prompt)
    if response.get("reason"):
        state.get("executed_tools").append(response["reason"])
        state["current_step"] = response["next_step"]
    if response["next_node"] in ["tool_execution", "planner", "summary"]:
        return Send(response["next_node"], state)
    return Send("summary", state)
