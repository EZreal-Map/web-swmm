import os
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from utils.logger import agent_logger
from utils.agent.async_store_manager import AsyncStoreManager
from schemas.agent.state import State


static_dir = os.path.join("static", "agent_graph")


class GraphInstance:
    """LangGraph 管理器 - 全静态方法"""

    _graph: Optional[StateGraph] = None

    @classmethod
    def init(cls) -> StateGraph:
        """创建和配置聊天机器人的状态图"""
        try:

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
            graph_builder.add_node(
                "backend_tool_execution", backend_tool_execution_node
            )
            graph_builder.add_node("check_node", backend_tool_check_node)
            graph_builder.add_node("frontend_tools", frontend_tools_node)
            graph_builder.add_node(
                "frontend_tool_execution", frontend_tool_execution_node
            )
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
            cls._graph = graph_builder.compile(checkpointer=checkpointer, store=store)
            agent_logger.info(
                "Graph创建成功 - 拆分架构: 问题重写 -> 意图识别 -> 后端决策/执行 -> 前端决策/执行 -> 最终总结"
            )
            return cls._graph
        except Exception as e:
            agent_logger.error(
                f"创建Graph失败: {str(e)} | type: {type(e).__name__} | repr: {repr(e)}"
            )
            return None

    @classmethod
    def get_graph(cls) -> StateGraph:
        if cls._graph is None:
            raise RuntimeError("Graph未初始化,请先调用init()")
        return cls._graph

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._graph is not None

    @classmethod
    def save_visualization(cls, filename: str = "graph.png") -> None:
        if not cls.is_initialized():
            raise RuntimeError("Graph未初始化")
        try:
            os.makedirs(static_dir, exist_ok=True)
            full_path = os.path.join(static_dir, filename)
            with open(full_path, "wb") as f:
                f.write(cls._graph.get_graph().draw_mermaid_png())
            agent_logger.info(f"Graph可视化已保存为 {full_path}")
        except IOError as e:
            agent_logger.warning(f"保存Graph可视化失败: {str(e)}")

    @classmethod
    def reset(cls) -> None:
        cls._graph = None
        agent_logger.info("Graph管理器已重置")


if __name__ == "__main__":
    # → 保存成 test_graph.png
    # python -m utils.agent.graph_manager test_graph.png
    # → 自动保存成 graph_20250809_153200.png
    # python -m utils.agent.graph_manager

    import sys
    import time
    import asyncio
    import traceback

    # 测试创建Graph
    try:
        # 创建文件名
        if len(sys.argv) > 1:
            filename = sys.argv[1]
        else:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"graph_{timestamp}.png"
        # 初始化Graph
        GraphInstance.init()
        # 保存可视化
        GraphInstance.save_visualization(filename)
        print(f"图已保存为: {filename}")

        # 测试简单对话
        config = {"configurable": {"thread_id": "test_conversation"}}
        chat_messages = [HumanMessage(content="帮我查询节点信息")]

        graph = GraphInstance.get_graph()
        result = asyncio.run(graph.ainvoke({"messages": chat_messages}, config))
        print(f"对话结果: {result}")

    except Exception as e:
        print(f"测试失败: {e}")
        print(f"异常类型: {type(e).__name__}")
        print("详细堆栈信息:")
        traceback.print_exc()
