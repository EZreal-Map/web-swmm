from langgraph.graph import StateGraph, START, END
from utils.logger import agent_logger
from utils.agent.async_store_manager import AsyncStoreManager
from schemas.agent.state import State


def build_tool_graph() -> StateGraph:
    # 0. 问题改写节点:结合记忆补全用户问题
    from utils.agent.node.question_rewrite import question_rewrite_node

    # 1. 意图识别节点:分析并标记需要的工具类型
    from utils.agent.node.intent_classifier import intent_classifier_node

    # 2. 后端工具节点:根据标记决定是否执行
    from utils.agent.node.backend_tools import backend_tools_node

    # 2.1 路由函数:决定是否执行后端工具
    from utils.agent.route.backend_tools import backend_tools_route

    # 2.2 后端工具执行节点
    # Send 到这个节点,分为并行(toolnode)(自动执行)和 (serialtoolnode)(人类参与)
    from utils.agent.node.backend_tool_execution import (
        backend_tool_execution_node,
    )

    # 2.3 后端工具检查节点
    from utils.agent.node.backend_tool_check import (
        backend_tool_check_node,
    )

    # 2.4 后端检查点路由
    from utils.agent.route.backend_tool_check import (
        backend_tool_check_route,
    )

    # 3. 前端工具节点:根据标记决定是否生成工具调用
    from utils.agent.node.frontend_tools import frontend_tools_node

    # 3.1 路由函数:决定是否执行前端工具
    from utils.agent.route.frontend_tools import frontend_tools_route

    # 3.2 前端工具执行节点
    from utils.agent.node.frontend_tool_execution import (
        frontend_tool_execution_node,
    )

    # 4. 最终总结节点
    from utils.agent.node.summary_response import summary_response_node

    # 构建graph
    graph_builder = StateGraph(State)
    # 构建图结构 - 拆分工具调用和执行
    graph_builder.add_node("question_rewrite", question_rewrite_node)
    graph_builder.add_node("intent_classifier", intent_classifier_node)
    graph_builder.add_node("backend_tools", backend_tools_node)
    graph_builder.add_node("backend_tool_execution", backend_tool_execution_node)
    graph_builder.add_node("check_node", backend_tool_check_node)
    graph_builder.add_node("frontend_tools", frontend_tools_node)
    graph_builder.add_node("frontend_tool_execution", frontend_tool_execution_node)
    graph_builder.add_node("summary_response", summary_response_node)

    # 添加边 - 串行执行,每个工具分为决策和执行两步
    graph_builder.add_edge(START, "question_rewrite")
    graph_builder.add_edge("question_rewrite", "intent_classifier")
    graph_builder.add_edge("intent_classifier", "backend_tools")
    graph_builder.add_conditional_edges("backend_tools", backend_tools_route)
    graph_builder.add_edge("backend_tool_execution", "check_node")
    graph_builder.add_conditional_edges("check_node", backend_tool_check_route)
    graph_builder.add_conditional_edges("frontend_tools", frontend_tools_route)
    graph_builder.add_edge("frontend_tool_execution", "summary_response")
    graph_builder.add_edge("summary_response", END)

    # === 持久化存储 ===
    checkpointer = AsyncStoreManager.checkpointer
    store = AsyncStoreManager.store
    agent_logger.info(
        "Graph创建成功 - 拆分架构: 问题重写 -> 意图识别 -> 后端决策/执行 -> 前端决策/执行 -> 最终总结"
    )
    return graph_builder.compile(checkpointer=checkpointer, store=store)
