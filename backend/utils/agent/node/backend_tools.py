from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.agent.message_manager import get_split_dialogue_rounds
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm

from tools.junction import (
    get_junctions_tool,
    batch_get_junctions_by_ids_tool,
    create_junction_tool,
    delete_junction_tool,
    update_junction_tool,
)
from tools.outfall import (
    get_outfalls_tool,
    update_outfall_tool,
    create_outfall_tool,
    delete_outfall_tool,
)
from tools.conduit import (
    get_conduits_tool,
    update_conduit_tool,
    create_conduit_tool,
    delete_conduit_tool,
    batch_get_conduits_by_ids_tool,
)
from tools.subcatchment import (
    get_subcatchments_tool,
    batch_get_subcatchments_by_names_tool,
    update_subcatchment_tool,
    create_subcatchment_tool,
    delete_subcatchment_tool,
)
from tools.calculate import query_calculate_result_tool
from tools.webui import human_info_completion_tool

# 定义工具
# 1.1 普通后端工具
normal_backend_tools = [
    get_junctions_tool,
    create_junction_tool,
    batch_get_junctions_by_ids_tool,
    update_junction_tool,
    get_outfalls_tool,
    update_outfall_tool,
    create_outfall_tool,
    delete_outfall_tool,
    get_conduits_tool,
    update_conduit_tool,
    create_conduit_tool,
    delete_conduit_tool,
    batch_get_conduits_by_ids_tool,
    get_subcatchments_tool,
    update_subcatchment_tool,
    create_subcatchment_tool,
    batch_get_subcatchments_by_names_tool,
]
# 1.2 Human in the loop后端工具(人类反馈工具)
HIL_backend_tools = [
    delete_junction_tool,
    delete_outfall_tool,
    delete_conduit_tool,
    delete_subcatchment_tool,
    query_calculate_result_tool,
    human_info_completion_tool,
]
HIL_backend_tools_name = [
    tool.name for tool in HIL_backend_tools
]  # HIL后端工具名字变量
# 1.3 后端工具集合
backend_tools = normal_backend_tools + HIL_backend_tools

llm = create_openai_llm()
backend_llm = llm.bind_tools(tools=backend_tools)


# 2. 后端工具节点:根据标记决定是否执行
async def backend_tools_node(state: State) -> dict:
    """后端工具节点:根据need_backend标记决定是否执行"""
    need_backend = state.get("need_backend", False)
    user_query = state.get("query", "")
    agent_logger.info(
        f"{state.get('client_id')} - 进入后端工具节点: need_backend:{need_backend}, user_query: {user_query}"
    )
    # 如果不需要后端工具,直接返回原状态
    if not need_backend:
        agent_logger.info(f"{state.get('client_id')} - 不需要后端工具,跳过后端工具节点")
        return {}

    if not user_query:
        agent_logger.warning(
            f"{state.get('client_id')} - 用户问题为空,后端工具节点没有收到用户问题"
        )
        return {}
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""), "[后端决策] 正在分析后端工具调用..."
    )
    # 获取最后一轮消息
    recent_dialogue_round = get_split_dialogue_rounds(state.get("messages", []), 1)
    # TODO:这里需要更改,根据之后处理 memory 引入数据库后,更加优雅的处理
    # 将历史消息与意图prompt结合
    # 构建后端专用的消息,让后端LLM分析问题 (参考下面的frontend_messages节点的分析)
    retry_count = state.get("retry_count", 3)
    backend_prompt = f"""你是一个SWMM智能助手，请根据用户问题和最近一次工具执行结果，智能决定如何调用后端工具。

    - 用户问题: {user_query}
    - 最近一轮对话和工具执行结果: {recent_dialogue_round}
    - 当前重试次数: {retry_count}

    【要求】
    1. 如果信息充足，直接生成合适的工具调用。
    2. 如果你发现和上一次错误完全一样，尝试使用不同的参数或方法，或者调用human_info_completion_tool工具。
    3. 输出内容要简洁明了，避免重复无效尝试，主要是通过调用工具来解决问题，除非没有合适的工具可以调用的时候，回复说明。
    """

    # 后端LLM生成工具调用
    backend_response = await backend_llm.ainvoke(backend_prompt)
    agent_logger.info(
        f"{state.get('client_id')} - 后端工具节点LLM响应: {backend_response}"
    )
    # 屏蔽 astream 自动发送 tool_calls(因为有bug,此时的args为空),手动发送,因为此时content='',需要使用强制发送参数
    await ChatMessageSendHandler.send_ai_message(
        state.get("client_id"), backend_response, True
    )
    # 返回包含工具调用的AI消息
    return {"messages": [backend_response], "retry_count": retry_count}
