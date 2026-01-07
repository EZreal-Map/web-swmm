from schemas.agent.state import PlanModeState
from utils.agent.llm_manager import LLMRegistry
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.logger import agent_logger


async def summary_node(state: PlanModeState) -> dict:
    """总结节点: 汇总整个过程，生成最终回复"""
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""),
        "[总结回答中] 正在根据问题和执行过程总结回答中...",
        state.get("mode"),
    )

    summary_llm = LLMRegistry.get("llm")

    summary_prompt = f"""
你是一个智能助手。你的任务是基于用户的问题和整个工具执行过程，生成一个清晰、完整的最终回复。
问题：{state.get("query")}
计划：{state.get("plans")}
最近5次执行记录：{state.get("executed_tools", [])[-5:]}
要求：
1. 总结工具调用的执行过程和执行结果，聚焦信息的总结，不要回复过多其他的内容。
2. 回答用户的原始问题,如果需要更多信息才能完成任务,一定在最后提出来,需要哪些数据和信息。
3. 如果有数据查询结果,请清晰展示,如果数据过长请进行适当的截断,除非用户要求保留完整和精确的数据。
4. 浮点数小数位如果过长,可以适当截取,比如经纬度,适当截取保留5位就差不多了,除非用户要求保留完整和精确的数据。
5. 如果执行结果中(success_message)有表明以用前端组件展示数据,请相信这个结果,不用再用文字输出该已展示的数据了。
6. 尽量使用markdown格式回答,如果有多组同样格式数据,可以适当使用表格,确保信息清晰可读。
7. **表格显示规则**：当使用表格展示多条数据时,不要显示sysid、swmm_project_id等UUID字段(它们占用大量空间且对用户无意义)。但如果是单个数据的详细查询,可以保留这些字段。
8. 回答要简洁明了，避免冗长，确保用户能快速获取关键信息，突出回答的重点。
"""
    response = await summary_llm.ainvoke(summary_prompt)
    agent_logger.debug(f"{state.get('client_id')} - 总结节点生成的回复: {response}")
    await ChatMessageSendHandler.send_complete(state["client_id"])
    return {}
