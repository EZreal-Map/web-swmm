from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import ToolMessage
from utils.logger import agent_logger


# 为什么会有SerialToolNode，因为需要一个能够串行执行工具调用的节点类，ToolNode 默认是并行执行的
# 这里没有考虑 ToolNode 的 messages_key ,默认使用的是 messages
class SerialToolNode(ToolNode):
    """继承ToolNode,将并行执行改为串行执行,支持interrupt机制"""

    def __init__(self, tools: list):
        super().__init__(tools)

    def invoke(self, state, config=None, **kwargs):
        """串行执行工具调用,按tool_calls顺序执行,支持interrupt"""
        # 如果工具需要发送信息给前端，一定要用dict包裹messages，并且包含client_id字段
        if isinstance(state, list):
            message = state[-1]
        elif messages := state.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in state")

        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return state

        outputs = []
        # 按照tool_calls的顺序串行执行每个工具
        for i, tool_call in enumerate(message.tool_calls):
            try:
                # 为每个工具调用创建单独的消息和状态
                single_call_message = type(message)(
                    content=message.content,
                    additional_kwargs=message.additional_kwargs,
                    response_metadata=message.response_metadata,
                    id=message.id,
                    tool_calls=[tool_call],  # 只包含当前要执行的工具调用
                )

                # 构造单个工具调用的输入
                single_tool_state = {
                    **state,
                    "messages": [single_call_message],
                }

                # 使用父类的invoke方法执行单个工具
                result = super().invoke(single_tool_state, config, **kwargs)

                # 收集结果
                if "messages" in result:
                    outputs.extend(result["messages"])

                agent_logger.info(
                    f"串行执行工具 {tool_call['name']} 完成 ({i+1}/{len(message.tool_calls)}, result={result})"
                )

            except Exception as e:
                # 检查是否是Interrupt异常(前端工具的正常行为)
                if "Interrupt" in str(type(e)) or "interrupt" in str(e).lower():
                    agent_logger.info(
                        f"工具 {tool_call['name']} ({i+1}/{len(message.tool_calls)}) 触发interrupt,等待人类反馈"
                    )
                    # 对于interrupt,直接重新抛出,让LangGraph处理
                    raise e
                else:
                    agent_logger.error(
                        f"串行执行工具 {tool_call['name']} ({i+1}/{len(message.tool_calls)}) 失败: {e}"
                    )
                    # 创建错误消息
                    error_message = ToolMessage(
                        content=f"工具执行失败: {str(e)}",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                    outputs.append(error_message)
        return {"messages": outputs}

    async def ainvoke(self, state, config=None, **kwargs):
        """串行执行工具调用,按tool_calls顺序执行,支持interrupt"""
        # 如果工具需要发送信息给前端，一定要用dict包裹messages，并且包含client_id字段
        if isinstance(state, list):
            message = state[-1]
        elif messages := state.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in state")

        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return state

        outputs = []
        # 按照tool_calls的顺序串行执行每个工具
        for i, tool_call in enumerate(message.tool_calls):
            try:
                # 为每个工具调用创建单独的消息和状态
                single_call_message = type(message)(
                    content=message.content,
                    additional_kwargs=message.additional_kwargs,
                    response_metadata=message.response_metadata,
                    id=message.id,
                    tool_calls=[tool_call],  # 只包含当前要执行的工具调用
                )

                # 构造单个工具调用的输入
                single_tool_state = {
                    **state,
                    "messages": [single_call_message],
                }

                # 使用父类的invoke方法执行单个工具
                result = await super().ainvoke(single_tool_state, config, **kwargs)

                # 收集结果
                if "messages" in result:
                    outputs.extend(result["messages"])

                agent_logger.info(
                    f"串行执行工具 {tool_call['name']} 完成 ({i+1}/{len(message.tool_calls)}, result={result})"
                )

            except Exception as e:
                # 检查是否是Interrupt异常(前端工具的正常行为)
                if "Interrupt" in str(type(e)) or "interrupt" in str(e).lower():
                    agent_logger.info(
                        f"工具 {tool_call['name']} ({i+1}/{len(message.tool_calls)}) 触发interrupt,等待人类反馈"
                    )
                    # 对于interrupt,直接重新抛出,让LangGraph处理
                    raise e
                else:
                    agent_logger.error(
                        f"串行执行工具 {tool_call['name']} ({i+1}/{len(message.tool_calls)}) 失败: {e}"
                    )
                    # 创建错误消息
                    error_message = ToolMessage(
                        content=f"工具执行失败: {str(e)}",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                    outputs.append(error_message)
        return {"messages": outputs}


# 注意:
# 1. LLM.invoke 返回的是 返单个 AIMessage 对象(或 BaseMessage 子类)
# 2. ToolNode.invoke 返回的是 {"messages": [ToolMessage, ...]} 格式 (这样ToolNode 为了保存State的兼容性)
