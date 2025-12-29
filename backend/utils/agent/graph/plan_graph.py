from langgraph.graph import StateGraph, START, END
from utils.logger import agent_logger
from utils.agent.async_store_manager import AsyncStoreManager

from schemas.agent.state import PlanModeState


def build_plan_graph() -> StateGraph:
    # 0. 计划节点: 生成工具执行计划
    from utils.agent.node.plan.planner import planner_node

    # 1. 工具执行节点: 将计划翻译成单步工具调用
    from utils.agent.node.plan.tool_execution import tool_execution_node

    # 1.1 执行器节点: 负责真正调用工具
    from utils.agent.node.plan.executor import executor_node

    # 2. 观察者节点: 复盘执行结果, 决定下一步
    from utils.agent.node.plan.observer import observer_node

    # 3. 总结节点: 汇总整个计划过程并返回给用户
    from utils.agent.node.plan.summary import summary_node

    # 构建graph
    graph_builder = StateGraph(PlanModeState)
    # 构建图结构 - 规划/执行/观察/总结四段流程
    graph_builder.add_node("planner", planner_node)
    graph_builder.add_node("tool_execution", tool_execution_node)
    graph_builder.add_node("executor", executor_node)
    graph_builder.add_node("observer", observer_node)
    graph_builder.add_node("summary", summary_node)

    # 添加边 - 规划 -> 步骤执行 -> 执行器 -> 观察 -> 总结
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "tool_execution")
    graph_builder.add_edge("executor", "observer")
    graph_builder.add_edge("summary", END)

    # === 持久化存储 ===
    checkpointer = AsyncStoreManager.checkpointer
    store = AsyncStoreManager.store
    agent_logger.info(
        "Graph 创建成功 - 计划模式: 规划 -> 步骤执行 -> 执行器 -> 观察者 -> 总结"
    )
    return graph_builder.compile(checkpointer=checkpointer, store=store)
