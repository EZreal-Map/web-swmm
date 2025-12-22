from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from langchain_core.messages import AIMessage, HumanMessage
from utils.agent.message_manager import get_recent_messages_by_type
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm

llm = create_openai_llm()
question_rewrite_llm = llm


# 0. 问题改写节点:结合记忆补全用户问题
async def question_rewrite_node(state: State) -> dict:
    """
    问题改写节点：结合最近3次HumanMessage、最近1次AIMessage和当前query,补全用户问题。
    """
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""),
        f"[问题重写] AI正在为你问题重写...",
    )

    recent_human_msgs = get_recent_messages_by_type(
        state.get("messages", []), n=4, msg_type=HumanMessage
    )
    # 获取当前query
    user_query = recent_human_msgs[-1].content
    # 获取最近3次HumanMessage (除去最近一次)
    recent_human_msgs = recent_human_msgs[:-1]
    # 获取最近1次AIMessage
    recent_ai_msg = get_recent_messages_by_type(
        state.get("messages", []), n=1, msg_type=AIMessage
    )

    # 构建更智能的改写prompt
    rewrite_prompt = f"""
你是一个智能问题补全助手,目标是将用户的最新输入与历史上下文结合,生成**完整、独立、可直接执行**的问题。

你的任务分两步：
1. 判断最新用户输入是一个“问题”还是“陈述/补充信息/名词短语”。
   - 如果是“问题”,请检查并补全所有指代（如“这个节点”、“它”等）,使其成为无歧义的完整问题。
   - 如果是“陈述/补充信息/名词短语”,请结合最近的AI追问和更早的用户提问,将补充信息合并,还原为原始意图的完整新问题。
2. 输出时,禁止无端联想,参考上下文提供的信息,不要修改问题本身的意义。


当前最新用户输入：
{user_query}

最近3次用户消息（HumanMessage）：
{[msg.content for msg in recent_human_msgs] if recent_human_msgs else '无'}

最近一次AI回复（AIMessage）：
{recent_ai_msg.content if recent_ai_msg else '无'}

请严格按上述要求输出补全后的问题（如无补全则原样输出）：
【举例】
- 上下文：
        用户：创建节点J100
        AI：请提供经度、纬度、高程、初始水深、最大水深
        用户：经纬度为130 29
    输出：我要创建节点J100,经度为130,纬度为29

- 上下文：
        用户：创建渠道
        AI：请提供名称、起点、终点
        用户：名称为C100 起始点 J1 终点 J3
    输出：我要创建渠道C100,起点为J1,终点为J3

- 上下文：
        用户：查询节点J1
    输出：查询节点J1

- 上下文：
        AI：(历史有“J1节点”)
        用户：这个节点的流量是多少？
    输出：J1节点的流量是多少？
"""
    # 用 LLM 生成改写后的问题
    rewrite_messages = [HumanMessage(content=rewrite_prompt)]
    rewrite_response = await question_rewrite_llm.ainvoke(rewrite_messages)
    new_query = rewrite_response.content.strip()
    agent_logger.info(f"{state.get('client_id')} - 问题改写节点LLM响应: {new_query}")

    # 更新 state 的 query 字段
    return {"query": new_query, "retry_count": 0}
