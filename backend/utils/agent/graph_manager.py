from langgraph.graph import StateGraph
from utils.logger import agent_logger
from schemas.agent.chat import AgentMode


class GraphRegistry:
    _graphs: dict[str, StateGraph] = {}

    @classmethod
    def register(cls, mode: str, graph: StateGraph):
        cls._graphs[mode] = graph
        agent_logger.info(f"Graph 注册成功: mode={mode.value}")

    @classmethod
    def get(cls, mode: str) -> StateGraph:
        if mode not in cls._graphs:
            raise ValueError(f"未找到 graph, mode={mode}")
        return cls._graphs[mode]

    @classmethod
    def exists(cls, mode: str) -> bool:
        return mode in cls._graphs

    @classmethod
    def clear(cls):
        cls._graphs.clear()


class GraphInstance:
    @classmethod
    def init(cls):
        from utils.agent.graph.tool_graph import build_tool_graph
        from utils.agent.graph.plan_graph import build_plan_graph

        GraphRegistry.register(AgentMode.TOOL, build_tool_graph())
        GraphRegistry.register(AgentMode.PLAN, build_plan_graph())

    @classmethod
    def get_graph(cls, mode: str):
        return GraphRegistry.get(mode)
