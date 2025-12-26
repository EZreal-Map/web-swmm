from langgraph.graph import StateGraph, START, END
from utils.logger import agent_logger
from utils.agent.async_store_manager import AsyncStoreManager
from schemas.agent.state import PlanModeState
from typing_extensions import TypedDict
from utils.agent.websocket_manager import ChatMessageSendHandler
from pydantic import Field
from utils.agent.node.tool.backend_tools import backend_tools
from utils.agent.node.tool.frontend_tools import frontend_tools
from typing import Literal


class PlansOutput(TypedDict):
    plans: list[str] = Field(
        description="根据用户问题生成的详细计划列表,每个计划步骤为一个字符串。"
    )


class PlanCheckOutput(TypedDict):
    next_step: Literal["tool_execution", "planner", "summary"] = Field(
        description="下一步流程: tool_execution-继续执行工具, planner-重新规划, summary-总结回复"
    )
    current_step: int = Field(
        description="下一步要执行的步骤号。继续执行则加1,重复执行保持不变,回到某步骤则为该步骤号"
    )
    reason: str = Field(
        description="简要说明决策原因。如果是重新执行计划或回到某一步骤,特别说明原因"
    )


def build_plan_graph() -> StateGraph:
    async def planner_node(state: PlanModeState) -> dict:
        """计划节点: 生成解决问题的计划"""
        from utils.agent.llm_manager import LLMRegistry
        from utils.agent.message_manager import get_recent_messages_by_type
        from langchain_core.messages import AIMessage, HumanMessage

        tools = backend_tools + frontend_tools

        recent_human_msgs = get_recent_messages_by_type(
            state.get("messages", []), n=4, msg_type=HumanMessage
        )
        # 获取当前query
        user_query = recent_human_msgs[-1].content
        planner_llm = LLMRegistry.get("tools_llm")
        if not planner_llm:
            llm = LLMRegistry.get("llm")
            planner_llm = llm.bind_tools(tools=tools)
            LLMRegistry.register("tools_llm", planner_llm)

        planner_prompt = f"""
你是一个工具调用规划者。你的任务是根据用户的问题，生成一个可执行的工具调用步骤列表。

问题：{user_query}

要求：
1. 只生成具体的工具调用步骤，每一步必须对应一个可用的工具
2. 每个步骤要明确指出调用哪个工具、传入什么参数
3. 步骤之间要有清晰的执行顺序和依赖关系
4. 不要包含任何无法通过工具执行的内容（如人工判断、手动操作等）
5. 在更新、添加、删除操作之后，要考虑是否调用前端工具，用来更新结果渲染
6. 如果发现某个步骤参数不足以执行的时候，一定要在此步骤之前，安排步骤调用信息补全工具，用来获取更多信息

输出格式要求：
每个步骤分为两个部分：
第一部分：用户友好的步骤描述（简洁、通俗易懂，说明这一步要做什么）
第二部分：详细的技术实现（具体的工具调用和参数细节）

格式模板：
**步骤1** [简洁的步骤描述，说明目的和意图]

`调用[工具名]，参数为{{具体参数的JSON格式}}`

**步骤2** [简洁的步骤描述]

`调用[工具名]，参数为{{具体参数的JSON格式}}`

...
```

示例：

**步骤1** 获取创建节点J100所需的缺失参数（至少经度和纬度）

`调用[human_info_completion_tool]，参数为{{"input_title":"创建节点J100所需参数补充：请提供必要参数：经度(lon)、纬度(lat)；可选参数（可不输入，系统将使用默认值）：高程(elevation)、初始水深(depth_init)"}}`

**步骤2** 使用收集到的参数在SWMM模型中创建节点J100

`调用[create_junction_tool]，参数为{{"name":"J100","lon":"<从步骤1返回的lon>","lat":"<从步骤1返回的lat>","elevation":"<若步骤1提供则使用该值否则0.0>"}}`

**步骤3** 通知前端刷新并重新加载所有实体以更新渲染

`调用[init_entities_tool]，参数为{{}}`

请严格按照以上格式输出，不需要其他说明或总结。

"""

        response = await planner_llm.ainvoke(planner_prompt)
        agent_logger.debug(f"{state.get('client_id')} - 计划节点生成的计划: {response}")

        return {
            "plans": response.content,
            "query": user_query,
            "current_step": 1,
        }

    async def tool_execution_node(state: PlanModeState) -> dict:
        """工具执行节点: 根据计划执行工具"""
        from utils.agent.llm_manager import LLMRegistry
        from utils.agent.message_manager import get_recent_messages_by_type
        from langchain_core.messages import ToolMessage
        from utils.agent.serial_tool_node import SerialToolNode
        from langgraph.prebuilt import ToolNode
        from utils.agent.node.tool.backend_tools import HIL_backend_tools_name
        from utils.agent.node.tool.frontend_tools import HIL_frontend_tools_name

        tools = backend_tools + frontend_tools
        HIL_tools_name = HIL_backend_tools_name + HIL_frontend_tools_name

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
"""
        response = await tools_llm.ainvoke(tool_execution_prompt)
        # TODO:这里增加检查如果没有tool_calls则不执行
        if not response.tool_calls:
            raise ValueError("工具执行节点没有生成任何工具调用")
        tool_call_name = response.tool_calls[0].get("name")
        args = response.tool_calls[0].get("args", {})
        if tool_call_name in HIL_tools_name:
            backend_execution = SerialToolNode(tools=tools)
            tool_state = {
                "messages": [response],
                "client_id": state.get("client_id"),
                "mode": state.get("mode"),
            }
        else:
            backend_execution = ToolNode(tools=tools)
            tool_state = {
                "messages": [response],
                "client_id": state.get("client_id"),
                "mode": state.get("mode"),
            }
        result = await backend_execution.ainvoke(tool_state)
        # 给前端发送工具执行结果消息
        # await ChatMessageSendHandler.send_tool_message(
        #     state.get("client_id"), result["messages"][0], state.get("mode")
        # )
        agent_logger.debug(f"{state.get('client_id')} - 工具执行节点执行结果: {result}")
        # ChatMessageSendHandler.send_complete(state["client_id"])
        executed_tool_record = f"""
**步骤{state.get("current_step")}** 执行工具 {tool_call_name}
`参数为{args}`
执行结果：{result}
"""
        return {"executed_tools": executed_tool_record}

    async def observer_node(state: PlanModeState) -> dict:
        """观察者节点: 监控工具执行状态，决定是否继续执行或结束"""
        from utils.agent.llm_manager import LLMRegistry
        from langgraph.types import Send

        observerllm = LLMRegistry.get("observerllm")
        if not observerllm:
            llm = LLMRegistry.get("llm")
            observerllm = llm.with_structured_output(PlanCheckOutput)
            LLMRegistry.register("observerllm", observerllm)

        observer_prompt = f"""
你是一个工具执行观察者。你的任务是监控工具的执行状态，决定是否继续执行、重新规划或结束整个过程。

【当前状态信息】
- 用户问题：{state.get("query")}
- 完整计划：{state.get("plans")}
- 当前已执行到第 {state.get("current_step")} 步
- 最近5次执行记录：{state.get("executed_tools", [])[-5:]}

【决策要求】

**第一步：判断计划总步骤数**
- 仔细阅读"完整计划"，统计总共有多少个步骤（如 **步骤1**、**步骤2** 等）
- 记录总步骤数为 N

**第二步：判断执行状态**
- 检查最近一次工具执行是否成功
- 如果执行失败：分析失败原因
  * 参数错误或信息不足 → 考虑回到 planner 重新规划
  * 临时性错误 → 可以重试当前步骤（current_step 不变）
  * 严重错误无法修复 → 进入 summary 总结回复

**第三步：决定 next_step**
- 如果 current_step == N 且当前步骤成功（已执行完所有步骤）：
  ✓ **必须返回 next_step = "summary"**，不要继续执行
  ✓ current_step 保持为 N

- 如果 current_step < N（还有步骤未执行）且当前步骤成功：
  ✓ next_step = "tool_execution"
  ✓ current_step = current_step + 1（执行下一步）

- 如果需要重试当前步骤：
  ✓ next_step = "tool_execution"
  ✓ current_step 保持不变

- 如果需要重新规划：
  ✓ next_step = "planner"
  ✓ current_step = 1

【输出格式】
- next_step: 必须是 "tool_execution"、"planner" 或 "summary" 之一
- current_step: 整数，下一步要执行的步骤号
- reason: 简要说明决策原因，特别注意：
  * 如果选择 summary，说明原因（如"所有 N 个步骤已完成"）
  * 如果选择重试或回退，说明具体原因

【关键提示】
⚠️ 观察执行记录，避免重复错误执行，循环执行！，如有发现问题实在解决不了，可以停止执行，直接进入总结回复节点。
"""
        response = await observerllm.ainvoke(observer_prompt)
        if response.get("reason", None):
            state.get("executed_tools").append(response["reason"])
            state["current_step"] = response["current_step"]
        if response["next_step"] in ["tool_execution", "planner", "summary"]:
            return Send(response["next_step"], state)
        else:
            return Send("summary", state)

    async def summary_node(state: PlanModeState) -> dict:
        """总结节点: 汇总整个过程，生成最终回复"""
        from utils.agent.llm_manager import LLMRegistry

        summary_llm = LLMRegistry.get("llm")

        summary_prompt = f"""
你是一个智能助手。你的任务是基于用户的问题和整个工具执行过程，生成一个清晰、完整的最终回复。
问题：{state.get("query")}
计划：{state.get("plans")}
最近5次执行记录：{state.get("executed_tools", [])[-5:]}
要求：
1. 总结工具调用的执行结果和未能完成的任务。
2. 回答用户的原始问题,如果需要更多信息才能完成任务,一定在最后提出来,需要哪些数据和信息。
3. 如果有数据查询结果,请清晰展示,如果数据过长请进行适当的截断,除非用户要求保留完整和精确的数据。
4. 浮点数小数位如果过长,可以适当截取,比如经纬度,适当截取保留5位就差不多了,除非用户要求保留完整和精确的数据。
6. 如果执行结果中(success_message)有表明以用前端组件展示数据,请相信这个结果,不用再用文字输出该已展示的数据了。
5. 尽量使用markdown格式回答,如果有多组同样格式数据,可以适当使用表格,确保信息清晰可读。
"""
        response = await summary_llm.ainvoke(summary_prompt)
        agent_logger.debug(f"{state.get('client_id')} - 总结节点生成的回复: {response}")
        await ChatMessageSendHandler.send_complete(state["client_id"])
        return {}

    # 构建graph
    graph_builder = StateGraph(PlanModeState)
    # 构建图结构
    graph_builder.add_node("planner", planner_node)
    graph_builder.add_node("tool_execution", tool_execution_node)
    graph_builder.add_node("observer", observer_node)
    graph_builder.add_node("summary", summary_node)
    # 添加边
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "tool_execution")
    graph_builder.add_edge("tool_execution", "observer")
    graph_builder.add_edge("observer", "summary")
    graph_builder.add_edge("summary", END)

    # === 持久化存储 ===
    checkpointer = AsyncStoreManager.checkpointer
    store = AsyncStoreManager.store
    # TODO：计划模式：待完成
    agent_logger.info("Graph 创建成功 (计划模式：待完成)")
    return graph_builder.compile(checkpointer=checkpointer, store=store)
