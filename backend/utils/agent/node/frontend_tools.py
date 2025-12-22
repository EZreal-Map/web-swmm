from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from langchain_core.messages import HumanMessage
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm
from tools.webgis import fly_to_entity_by_name_tool, init_entities_tool

# 2.1 普通前端工具
normal_frontend_tools = []
# 2.2 Human in the loop前端工具(人类反馈工具)
HIL_frontend_tools = [
    init_entities_tool,
    fly_to_entity_by_name_tool,
]
HIL_frontend_tools_name = [
    tool.name for tool in HIL_frontend_tools
]  # HIL前端工具名字变量
# 2.3 前端工具集合
frontend_tools = normal_frontend_tools + HIL_frontend_tools

llm = create_openai_llm()
frontend_llm = llm.bind_tools(tools=frontend_tools)


# 3. 前端工具节点:根据标记决定是否生成工具调用
async def frontend_tools_node(state: State) -> dict:
    """前端工具节点:根据need_frontend标记决定是否生成工具调用"""
    need_frontend = state.get("need_frontend", False)
    user_query = state.get("query", "")
    agent_logger.info(
        f"{state.get('client_id')} - 进入前端工具节点: need_frontend: {need_frontend}, user_query: {user_query}"
    )

    # 如果不需要前端工具,直接返回原状态
    if not need_frontend:
        agent_logger.info(f"{state.get('client_id')} - 不需要前端工具,跳过前端工具节点")
        return {}

    if not user_query:
        agent_logger.warning(
            f"{state.get('client_id')} - 用户问题为空,前端工具节点没有收到用户问题"
        )
        return {}

    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""), "[前端决策] 正在分析前端工具调用..."
    )

    # TODO:这里需要更改,根据之后处理 memory 引入数据库后,更加优雅的处理
    # 将历史消息与意图prompt结合 ,不能直接把 human_messages + frontend_messages
    # 因为会让这个并列,有时候就会回答之前的问题去了,要把放进promt里面,包裹关系
    # 还有一种办法,在graph最开始,有一个拼接上下文的llm,丰富问题上下文(这个更好)

    # human_messages = GraphInstance.get_recent_messages_by_type(
    #     state, n=3, msg_type=HumanMessage
    # )

    # 构建前端专用的消息,让前端LLM分析问题
    frontend_messages = [
        HumanMessage(
            content=f"""请根据以下问题一次性调用合适的前端工具:{user_query}
            前端工具调用**注意事项**:
            1.如果要调用**更新所有实体工具**,需要最先调用。
            2.如果涉及到**一次性更新单个实体**实体数据和**增加**实体数据,一定需要调用**更新所有实体工具**,最好再调用**跳转功能**。
            3.如果涉及一次性更新单个实体实体的**名字属性**的时候,尤其需要调用**跳转功能**,跳转到新的名字实体上。""",
        )
    ]
    # 前端LLM生成工具调用
    frontend_response = await frontend_llm.ainvoke(frontend_messages)
    agent_logger.info(
        f"{state.get('client_id')} - 前端工具LLM响应: {frontend_response}"
    )
    # 屏蔽 astream 自动发送 tool_calls(因为有bug,此时的args为空),手动发送,因为此时content='',需要使用强制发送参数
    await ChatMessageSendHandler.send_ai_message(
        state.get("client_id"), frontend_response, True
    )

    return {"messages": [frontend_response]}
