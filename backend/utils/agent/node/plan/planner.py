from typing_extensions import TypedDict
from pydantic import Field
from langchain_core.messages import HumanMessage

from schemas.agent.state import PlanModeState
from utils.agent.llm_manager import LLMRegistry
from utils.agent.message_manager import get_recent_messages_by_type
from utils.agent.node.tool.backend_tools import backend_tools
from utils.agent.node.tool.frontend_tools import frontend_tools
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.logger import agent_logger


class PlansOutput(TypedDict):
    plans: list[str] = Field(
        description="根据用户问题生成的详细计划列表,每个计划步骤为一个字符串。"
    )


async def planner_node(state: PlanModeState) -> dict:
    """计划节点: 生成解决问题的计划"""
    tools = backend_tools + frontend_tools

    recent_human_msgs = get_recent_messages_by_type(
        state.get("messages", []), n=4, msg_type=HumanMessage
    )
    user_query = recent_human_msgs[-1].content
    planner_llm = LLMRegistry.get("planner_llm")
    if not planner_llm:
        llm = LLMRegistry.get("llm")
        planner_llm = llm.bind_tools(tools=tools, tool_choice="none")
        LLMRegistry.register("planner_llm", planner_llm)

    replan_mode = state.get("current_step") == 0 and state.get("plans")
    recent_exec_records = state.get("executed_tools", [])[-5:]
    if not replan_mode:
        await ChatMessageSendHandler.send_step(
            state.get("client_id", ""),
            "[计划制定中] 正在根据用户问题生成计划...",
            state.get("mode"),
        )
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

如果无法生成任何计划步骤，请严格回复“很抱歉，该问题我还无法生成计划”。
"""
    else:
        await ChatMessageSendHandler.send_step(
            state.get("client_id", ""),
            "[计划制定中] 正在根据用户问题和错误反馈重新生成计划...",
            state.get("mode"),
        )
        planner_prompt = f"""
你是一个计划纠错与重新规划专家。由于上一版计划在执行过程中出现问题，现在需要基于已有信息重新指定后续的工具执行方案。

【用户问题】
{user_query}

【上一版计划全文】
{state.get("plans")}

【最近执行记录（含失败原因）】
{recent_exec_records}

请明确指出失败节点可能的原因，重新生成一份可以继续执行的计划。要求：
1. 对已经成功完成的步骤仅在必要时复用，不要重复已完成且无需重跑的步骤。
2. 对失败或缺参的步骤，需补齐前置检查或信息采集工具，确保可以顺利调用。
3. 若需要回滚或清理之前的操作，也要写在新计划中。
4. 仍只允许列出具体可调用的工具和必要参数，保持步骤有严格的依赖顺序。
5. 结束时如需前端刷新或结果同步，同样写入计划。

格式模板：
**步骤1** [简洁的步骤描述，说明目的和意图]
`调用[工具名]，参数为{{具体参数的JSON格式}}`

**步骤2** [简洁的步骤描述]
`调用[工具名]，参数为{{具体参数的JSON格式}}`

输出格式保持不变：每个步骤包含一条用户友好描述 + 一条具体工具调用（JSON参数）的技术说明。
"""

    response = await planner_llm.ainvoke(planner_prompt)
    agent_logger.debug(f"{state.get('client_id')} - 计划节点生成的计划: {response}")

    return {
        "messages": response,
        "plans": response.content,
        "query": user_query,
        "current_step": 1,
        "executed_tools": [],
    }
