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
- current_step = {state.get("current_step")}（这是刚执行完的步骤编号）
- 最近5次执行记录：{state.get("executed_tools", [])[-5:]}

【判定规则-严格遵守】
1. **首先解析完整计划,提取所有步骤编号(如:步骤1、步骤2、步骤3)**,确定计划总步骤数。
2. **查看最近执行记录的最后一条**,确认current_step对应的步骤是否执行成功:
   - 如果记录中明确包含"步骤{state.get("current_step")}"且显示success=true或执行成功 → 该步骤已完成
   - 如果记录显示失败或错误 → 该步骤失败
3. **根据执行结果决定next_step**:
   - 若步骤{state.get("current_step")}执行成功 且 还有后续步骤 → next_step = {state.get("current_step")} + 1
   - 若步骤{state.get("current_step")}执行成功 且 已是最后一步(计划中已没有步骤{state.get("current_step") + 1}) → next_node="summary", next_step = {state.get("current_step")} + 1
   - 若步骤{state.get("current_step")}失败但可重试 → next_step = {state.get("current_step")}(保持不变)
   - 若多次失败或用户取消 → next_node="summary", next_step = 总计划步骤数 + 1
   - 若需重新规划 → next_node="planner", next_step = 0

4. **防止循环执行**:如果最近5条记录中有3条以上都是执行同一步骤且都成功,说明陷入循环,应强制推进到下一步或进入summary。

【输出要求】
- next_node: "tool_execution"、"planner" 或 "summary"
- next_step: 下一步要执行的计划编号(必须是整数)
- reason: 明确说明:步骤X执行[成功/失败],下一步执行步骤Y,原因是...
    """
    response = await observerllm.ainvoke(observer_prompt)
    if response.get("reason"):
        state.get("executed_tools").append(response["reason"])
        state["current_step"] = response["next_step"]
    if response["next_node"] in ["tool_execution", "planner", "summary"]:
        return Send(response["next_node"], state)
    return Send("summary", state)
