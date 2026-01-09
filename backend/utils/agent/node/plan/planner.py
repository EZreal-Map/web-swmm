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
     你是一个SWMM水力模型系统的智能规划助手，负责将用户关于SWMM模型的诉求拆解为可执行的工具调用计划。

     【重要】系统业务领域
     本系统专注于SWMM（Storm Water Management Model）水力模型管理，包括：
     - 节点（Junction）：水力模型中的交汇点
     - 渠道（Conduit）：连接节点的管道
     - 出口（Outfall）：排水出口
     - 子汇水区（Subcatchment）：雨水汇集区域
     - 计算结果查询：模拟运行后的水力计算数据

     **只处理与SWMM模型相关的问题，不要联想到Kubernetes、数据库、云平台等无关系统。**

     【待处理问题】
     {user_query}

     【可用工具】
     1. backend_tools：用于SWMM模型实体的CRUD操作
         - 查询（优先级规则：有名字时优先批量查询→批量查询失败尝试全部查询找相似匹配→无名字时直接全部查询）：
             · 节点查询：get_junctions_tool, batch_get_junctions_by_ids_tool
             · 渠道查询：get_conduits_tool, batch_get_conduits_by_ids_tool
             · 出口查询：get_outfalls_tool, batch_get_outfalls_by_ids_tool
             · 子汇水区查询：get_subcatchments_tool, batch_get_subcatchments_by_names_tool
             · 计算结果查询：query_calculate_result_tool
         - 创建：create_junction_tool, create_conduit_tool, create_outfall_tool, create_subcatchment_tool
         - 更新：update_junction_tool, update_conduit_tool, update_outfall_tool, update_subcatchment_tool
         - 删除：delete_junction_tool, delete_conduit_tool, delete_outfall_tool, delete_subcatchment_tool
     2. frontend_tools：用于前端WebGIS交互
         - fly_to_entity_by_name_tool：地图跳转到指定实体
         - init_entities_tool：刷新前端实体显示
     3. Human-in-the-loop工具：当必要参数缺失时使用
         - human_info_completion_tool：向用户请求补充信息

     【规划原则】
     1. 查询类问题（如“查询所有节点”、“查看渠道信息”等）可以直接生成计划，无需额外信息。
     2. 创建/更新操作必须先确保所有必填参数齐全，缺参数时先调用human_info_completion_tool。
     3. 删除操作可直接生成计划，工具内部会处理确认流程。
     4. 数据变更后要调用init_entities_tool刷新前端显示。
     5. 单个实体定位可使用fly_to_entity_by_name_tool跳转到地图位置。
     6. 只输出严格依赖顺序的工具步骤，每步包含描述 + 工具名 + JSON参数。
     7. 除非确实无法处理（如请求与SWMM无关），否则应生成计划；若无法生成计划，回复“很抱歉，该问题我还无法生成计划”。

     【格式模板】
     **步骤1** [简洁描述这一动作的目的]
     `调用[工具名]，参数为{{具体参数的JSON格式}}`

     **步骤2** [简洁描述]
     `调用[工具名]，参数为{{具体参数的JSON格式}}`

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
     你是一个SWMM水力模型系统的计划纠错与重新规划专家，需要在已有执行痕迹基础上给出可继续推进的工具链方案。

     【重要】系统业务领域
     本系统专注于SWMM（Storm Water Management Model）水力模型管理，包括：
     - 节点（Junction）：水力模型中的交汇点
     - 渠道（Conduit）：连接节点的管道
     - 出口（Outfall）：排水出口
     - 子汇水区（Subcatchment）：雨水汇集区域
     - 计算结果查询：模拟运行后的水力计算数据

     【用户问题】
     {user_query}

     【上一版计划全文】
     {state.get("plans")}

     【最近执行记录（含失败原因）】
     {recent_exec_records}

     【可用工具】
     1. backend_tools：用于SWMM模型实体的CRUD操作
         - 查询（优先级规则：有名字时优先批量查询→批量查询失败尝试全部查询找相似匹配→无名字时直接全部查询）：
             · 节点查询：get_junctions_tool, batch_get_junctions_by_ids_tool
             · 渠道查询：get_conduits_tool, batch_get_conduits_by_ids_tool
             · 出口查询：get_outfalls_tool, batch_get_outfalls_by_ids_tool
             · 子汇水区查询：get_subcatchments_tool, batch_get_subcatchments_by_names_tool
             · 计算结果查询：query_calculate_result_tool
         - 创建：create_junction_tool, create_conduit_tool, create_outfall_tool, create_subcatchment_tool
         - 更新：update_junction_tool, update_conduit_tool, update_outfall_tool, update_subcatchment_tool
         - 删除：delete_junction_tool, delete_conduit_tool, delete_outfall_tool, delete_subcatchment_tool
     2. frontend_tools：用于前端WebGIS交互
         - fly_to_entity_by_name_tool：地图跳转到指定实体
         - init_entities_tool：刷新前端实体显示
     3. Human-in-the-loop工具：当必要参数缺失时使用
         - human_info_completion_tool：向用户请求补充信息

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

     输出格式保持一致：每个步骤包含一条用户友好描述 + 一条具体工具调用（JSON参数）的技术说明。
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
