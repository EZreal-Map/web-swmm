from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from typing import Optional, Type, Union
import json


def get_recent_messages_by_type(
    messages,
    n=1,
    msg_type: Union[Type[HumanMessage], Type[AIMessage], Type[ToolMessage]] = AIMessage,
):
    """
    获取 messages 最近 n 条 HumanMessage 或 AIMessage,按原始顺序返回。
    msg_type: HumanMessage 或 AIMessage
    如果不足 n 条,则尽可能多取。
    """
    result_messages = []

    # 倒序遍历,找到最近的 n 条
    for message in reversed(messages):
        if isinstance(message, msg_type):
            result_messages.append(message)
            if len(result_messages) >= n:
                break

    # 要保持原始顺序,就在返回前反转
    result_messages.reverse()

    if n == 1:
        # 如果 n 为 1 返回单条消息,否则返回列表 (如果 n 为 1 不返回[],返回 BaseMessage)
        return result_messages[-1] if result_messages else None
    return result_messages


def get_split_dialogue_rounds(messages, n=None):
    """
    将消息列表按 HumanMessage 分为多轮,每轮以 HumanMessage 开头。
    如果 n 不传递,返回全部轮次；
    如果 n=1,返回最近 1 轮；
    如果 n>1,返回最近 n 轮,顺序与原始消息一致。
    返回:List[List[Message]]
    """
    rounds = []
    current_round = []

    for msg in messages:
        if isinstance(msg, HumanMessage):
            if current_round:
                rounds.append(current_round)
                current_round = []
        current_round.append(msg)
    if current_round:
        rounds.append(current_round)
    if n == 1:
        # 如果 n 为 1 返回单轮消息,否则返回列表 (不返回[[]], 之间返回[])
        return rounds[-1] if rounds else []
    if n is not None:
        return rounds[-n:]  # 取最近 n 轮,顺序不变
    return rounds


def split_ai_message_by_tool_names(
    ai_msg: AIMessage, tool_names: list[str] = []
) -> list[Optional[AIMessage]]:
    """
    拆分AIMessage,将tool_calls中tool_name在tool_names列表中的全部合并为一个AIMessage,其余的合并为另一个AIMessage。
    返回长度为2的list:
        - 第一个为去除所有需要独立运行tool_calls后的AIMessage(如无则为None)
        - 第二个为所有需要独立运行的tool_calls合并成的AIMessage(如无则为None)

    参数:
        ai_msg: 原始AIMessage对象
        tool_names: 需要单独拆分的tool_name列表

    返回:
        list[Optional[AIMessage]]: [剩余AIMessage, 独立AIMessage]
    """
    tool_calls = ai_msg.tool_calls or []
    matched = [tc for tc in tool_calls if tc["name"] in tool_names]
    unmatched = [tc for tc in tool_calls if tc["name"] not in tool_names]

    def make_message(calls):
        if not calls:
            return None
        return AIMessage(
            content=ai_msg.content,
            additional_kwargs={
                "tool_calls": [
                    {
                        "index": i,
                        "id": tc["id"],
                        "function": {
                            "arguments": json.dumps(tc["args"]),
                            "name": tc["name"],
                        },
                        "type": "function",
                    }
                    for i, tc in enumerate(calls)
                ]
            },
            response_metadata=ai_msg.response_metadata,
            id=ai_msg.id,
            tool_calls=calls,
            usage_metadata=ai_msg.usage_metadata,
        )

    remain_msg = make_message(unmatched)
    matched_msg = make_message(matched)
    return [remain_msg, matched_msg]
