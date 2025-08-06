import os
from typing import Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from utils.logger import agent_logger
from .llm_manager import create_openai_llm

static_dir = os.path.join("static", "agent_graph")


# 定义聊天机器人的状态
class State(TypedDict):
    messages: Annotated[list, add_messages]


class GraphInstance:
    """LangGraph 管理器 - 单例模式"""

    _instance: Optional["GraphInstance"] = None
    _graph: Optional[StateGraph] = None

    def __new__(cls, llm=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.create_graph(llm)  # 自动初始化
        return cls._instance

    def create_graph(self, llm=None) -> StateGraph:
        """创建和配置聊天机器人的状态图"""
        try:
            # 如果没有传入LLM，使用默认的OpenAI模型
            if llm is None:
                llm = create_openai_llm()

            # 构建graph
            graph_builder = StateGraph(State)

            # 定义chatbot的node
            def chatbot(state: State) -> dict:
                """处理当前状态并返回 LLM 响应"""
                agent_logger.info(
                    f"Processing messages: {len(state['messages'])} messages"
                )
                response = llm.invoke(state["messages"])
                return {"messages": [response]}

            # 配置graph
            graph_builder.add_node("chatbot", chatbot)
            graph_builder.add_edge(START, "chatbot")
            graph_builder.add_edge("chatbot", END)

            # 使用内存存储（也可以持久化到数据库）
            memory = MemorySaver()

            # 编译生成graph
            self._graph = graph_builder.compile(checkpointer=memory)

            agent_logger.info("Graph创建成功")
            return self._graph

        except Exception as e:
            agent_logger.error(f"创建Graph失败: {str(e)}")
            raise RuntimeError(f"Failed to create graph: {str(e)}")

    def get_graph(self) -> StateGraph:
        """获取Graph实例"""
        if self._graph is None:
            raise RuntimeError("Graph未初始化，请先调用create_graph()")
        return self._graph

    def is_initialized(self) -> bool:
        """检查Graph是否已初始化"""
        return self._graph is not None

    def save_visualization(self, filename: str = "graph.png") -> None:
        """将构建的graph可视化保存为PNG文件"""
        if not self.is_initialized():
            raise RuntimeError("Graph未初始化")

        try:
            # 确保目录存在
            os.makedirs(static_dir, exist_ok=True)

            # 构建完整路径
            full_path = os.path.join(static_dir, filename)

            with open(full_path, "wb") as f:
                f.write(self._graph.get_graph().draw_mermaid_png())
            agent_logger.info(f"Graph可视化已保存为 {full_path}")
        except IOError as e:
            agent_logger.warning(f"保存Graph可视化失败: {str(e)}")

    def reset(self) -> None:
        """重置Graph管理器"""
        self._graph = None
        agent_logger.info("Graph管理器已重置")


# 全局实例
graph_instance = GraphInstance()


if __name__ == "__main__":
    # 测试创建Graph
    try:
        # 创建Graph
        # graph = graph.create_graph(llm=create_openai_llm())
        # 保存可视化
        graph_instance.save_visualization("test_graph.png")

        # 测试简单对话
        config = {"configurable": {"thread_id": "test_conversation"}}
        messages = [{"role": "user", "content": "你好"}]

        result = graph_instance.invoke({"messages": messages}, config)
        print(f"对话结果: {result}")

    except Exception as e:
        print(f"测试失败: {e}")
