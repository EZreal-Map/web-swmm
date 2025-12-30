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
    你是一个SWMM有关的智能体的工具调度规划者，负责把用户诉求拆解为可执行的工具链。请仔细阅读用户问题并围绕下述原则生成计划。

    【待处理问题】
    {user_query}

    【工具简介】
    1. backend_tools：用于SWMM模型实体（节点，出口，子汇水区）的属性数据查询、创建、更新、删除或结果查询，还有SWMM实体的计算结果查询。
    2. frontend_tools：用于前端可视化交互（地图跳转、实体高亮、界面刷新等）。只读查询若直接回复给用户且无需界面变化，可以不调用frontend_tools；一旦执行新增、更新、删除或其他会影响前端展示的操作，必须在计划中追加相应的frontend_tools同步界面状态。
    3. Human-in-the-loop工具：用于存在不确定参数，问题参数不够的时候，需要补充信息的时候。
    4. 禁止列出无法通过工具落地的动作。若当前信息不足以调用后续工具，先插入信息补全部署。

    【规划要求】
    - 只输出严格依赖顺序的工具步骤，每步包含易懂描述 + 具体工具名和JSON参数。
    - 对每个实体变更，先确保输入参数完整，再安排后续动作，最后按需刷新前端。
    - 若无法为该问题生成任何可执行的步骤，回复“很抱歉，该问题我还无法生成计划”。

    【格式模板】
    **步骤1** [简洁描述这一动作的目的]
    `调用[工具名]，参数为{{具体参数的JSON格式}}`

    **步骤2** [简洁描述]
    `调用[工具名]，参数为{{具体参数的JSON格式}}`

    ...

    示例：

    **步骤1** 获取创建节点J100所需的缺失参数（至少经度和纬度）
    `调用[human_info_completion_tool]，参数为{{"input_title":"创建节点J100所需参数补充：请提供必要参数：经度(lon)、纬度(lat)；可选参数：高程(elevation)、初始水深(depth_init)"}}`

    **步骤2** 使用收集到的参数在SWMM模型中创建节点J100
    `调用[create_junction_tool]，参数为{{"name":"J100","lon":"<步骤1返回的lon>","lat":"<步骤1返回的lat>","elevation":"<若步骤1提供则使用该值否则0.0>"}}`

    **步骤3** 通知前端刷新并重新加载所有实体以更新渲染
    `调用[init_entities_tool]，参数为{{}}`

    请严格按照以上格式输出，不需要其他说明或总结。
    """
    else:
        await ChatMessageSendHandler.send_step(
            state.get("client_id", ""),
            "[计划制定中] 正在根据用户问题和错误反馈重新生成计划...",
            state.get("mode"),
        )
        planner_prompt = f"""
    你是一个SWMM有关的计划纠错与重新规划专家，需要在已有执行痕迹基础上给出可以继续推进的工具链方案。

    【用户问题】
    {user_query}

    【上一版计划全文】
    {state.get("plans")}

    【最近执行记录（含失败原因）】
    {recent_exec_records}

    【工具简介】
    1. backend_tools：用于SWMM模型实体（节点，出口，子汇水区）的属性数据查询、创建、更新、删除或结果查询，还有SWMM实体的计算结果查询。
    2. frontend_tools：用于前端可视化交互（地图跳转、实体高亮、界面刷新等）。只读查询若直接回复给用户且无需界面变化，可以不调用frontend_tools；一旦执行新增、更新、删除或其他会影响前端展示的操作，必须在计划中追加相应的frontend_tools同步界面状态。
    3. Human-in-the-loop工具：用于存在不确定参数，问题参数不够的时候，需要补充信息的时候。
    4. 禁止列出无法通过工具落地的动作。若当前信息不足以调用后续工具，先插入信息补全部署。

    【重新规划要求】
    1. 诊断失败节点原因，只重跑必要步骤，对已完成且无依赖的步骤不要重复安排。
    2. 针对缺参或校验失败的动作，先补充检查/信息采集，再进行核心操作。
    3. 若需要回滚、清理或恢复前端状态，必须写入计划。
    4. 仍需输出严格的依赖顺序，每步包含用户友好描述 + 具体工具及JSON参数。
    5. 执行完涉及数据变更的步骤后，补充前端同步，保持界面与数据一致。

    【格式模板】
    **步骤1** [简洁描述该步骤目的]
    `调用[工具名]，参数为{{具体参数的JSON格式}}`

    **步骤2** [简洁描述]
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
