from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from langchain_core.messages import HumanMessage
from utils.logger import agent_logger
from utils.agent.message_manager import (
    get_recent_messages_by_type,
    get_split_dialogue_rounds,
)
from utils.agent.llm_manager import create_openai_llm

llm = create_openai_llm()
summary_llm = llm  # 纯聊天用的LLM


# 4. 最终总结节点
async def summary_response_node(state: State) -> dict:
    """最终总结节点:基于所有执行结果生成总结回答"""
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""),
        f"[总结回答] AI正在为你整理最终回答...",
    )
    agent_logger.info(f"{state.get('client_id')} - 进入总结节点")
    user_query = state.get("query", "")

    # 基于最近一轮消息生成总结 (包含用户问题和所有工具执行结果)
    recent_dialogue_round = get_split_dialogue_rounds(state.get("messages", []), 1)

    recent_human_msgs = get_recent_messages_by_type(
        state.get("messages", []), n=4, msg_type=HumanMessage
    )
    recent_human_msgs = recent_human_msgs[:-1]  # 去掉最后一条用户消息
    # 添加总结提示
    summary_prompt = f"""
    请基于以上的工具执行结果,为用户问题"{user_query}"生成一个清晰、完整的回答。
    
    要求:
    1. 总结工具调用的执行结果和未能完成的任务。
    2. 回答用户的原始问题,如果需要更多信息才能完成任务,一定在最后提出来,需要哪些数据和信息。
    3. 如果有数据查询结果,请清晰展示,如果数据过长请进行适当的截断,除非用户要求保留完整和精确的数据。
    4. 浮点数小数位如果过长,可以适当截取,比如经纬度,适当截取保留5位就差不多了,除非用户要求保留完整和精确的数据。
    6. 如果执行结果中(success_message)有表明以用前端组件展示数据,请相信这个结果,不用再用文字输出该已展示的数据了。
    5. 尽量使用markdown格式回答,如果有多组同样格式数据,可以适当使用表格,确保信息清晰可读。

    用户最近3条上下文信息：
    {recent_human_msgs if recent_human_msgs else '无'}
    """
    # TODO: 优化总结上下文管理
    summary_messages = recent_dialogue_round + [HumanMessage(content=summary_prompt)]

    # 使用纯聊天LLM生成总结
    response = await summary_llm.ainvoke(summary_messages)
    agent_logger.info(f"{state.get('client_id')} - 总结节点LLM响应: {response}")
    await ChatMessageSendHandler.send_complete(state["client_id"])
    return {"messages": [response]}
