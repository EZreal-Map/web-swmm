import os
from typing import Optional, Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm
from utils.agent.serial_tool_node import SerialToolNode

from langgraph.prebuilt import ToolNode
from tools.junction import (
    get_junctions_tool,
    batch_get_junctions_by_ids_tool,
    create_junction_tool,
    delete_junction_tool,
    update_junction_tool,
)
from tools.web_ui import fly_to_entity_by_name_tool, init_entities_tool

static_dir = os.path.join("static", "agent_graph")


# 定义聊天机器人的状态
class State(TypedDict):
    messages: Annotated[list, add_messages]
    client_id: Optional[str]  # 客户端连接ID
    query: Optional[str]  # 当前要解决的问题
    need_backend: Optional[bool]  # 是否需要执行后端工具
    need_frontend: Optional[bool]  # 是否需要执行前端工具


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

            # 定义工具
            backend_tools = [
                get_junctions_tool,
                create_junction_tool,
                delete_junction_tool,
                batch_get_junctions_by_ids_tool,
                update_junction_tool,
            ]

            frontend_tools = [
                init_entities_tool,
                fly_to_entity_by_name_tool,
            ]
            # 创建LLM实例
            backend_llm = llm.bind_tools(tools=backend_tools)
            frontend_llm = llm.bind_tools(tools=frontend_tools)
            chatbot_llm = llm  # 纯聊天用的LLM

            # 1. 意图判断节点：分析并标记需要的工具类型
            def intent_classifier_node(state: State) -> dict:
                """意图判断节点：分析问题并标记需要后端/前端工具"""
                user_message = state["messages"][-1] if state["messages"] else None
                if not user_message:
                    return {"query": "", "need_backend": False, "need_frontend": False}

                # 提取用户查询
                user_query = (
                    user_message.get("content", "")
                    if isinstance(user_message, dict)
                    else str(user_message)
                )
                agent_logger.info(f"意图判断 - 用户问题: {user_query}")

                # 使用提示词进行意图分析（可能包含多种需求）
                intent_prompt = f"""
请阅读用户的问题 {user_query}，并根据需求判断需要调用哪些处理工具（可以同时需要多种）。  

处理工具说明：  
1. backend_tools  
   - 用于 **SWMM 模型数据操作**（例如：节点/管道/子汇水区等数据的查询、创建、更新、删除）。  
   - 如果问题涉及数据的增删改查，或者需要从数据库读取模型信息，都应选择该工具。  

2. frontend_tools  
   - 用于 **前端界面交互**（例如：地图跳转、实体高亮、界面刷新等）。  
   - 如果问题需要让用户在界面上看到变化（如定位到某个节点、在地图上显示结果等），则需要该工具。  
   - 注意：如果只是查询数据并将结果直接返回给用户（不要求地图或界面变化），则**不需要** frontend_tools。
   - 但凡涉及到数据的**更新，删除，增加**操作，都需要 frontend_tools，因为前端界面也要响应的变化更新。

3. chatbot  
   - 用于 **普通对话、解释说明、总结回答** 等不需要操作数据或界面的场景。  
   - 当用户只提问概念性问题、流程指导，或不涉及数据和界面操作时，选该工具。  

---

### 输出要求  
只按以下格式回答（不要多余内容）：  

backend_tools: [true/false]  
frontend_tools: [true/false]  
说明: [简短说明需要这些工具的原因]  

---

### 示例  

##### 1 查询多个问题
用户问题：帮我查询所有节点的信息  
回答：  
backend_tools: true  
frontend_tools: false  
说明: 查询节点信息只需调用 backend_tools 获取数据表，数据太多无法在前端上一一显示，所以不需要 frontend_tools。

##### 2 查询一个问题
用户问题：帮我查询一个节点的信息，节点ID为J1  
回答：  
backend_tools: true  
frontend_tools: true
说明: 查询节点信息需调用 backend_tools 获取数据信息，因为数据只有1个，所以可以很方便的在前端界面显示，所以需要 frontend_tools。

#### 3 创建问题
用户问题：帮我创建一个节点，节点信息如下名字为J1，纬度为110，纬度为30  
回答：  
backend_tools: true
frontend_tools: true  
说明: 创建节点需要调用 backend_tools 保存数据，因为数据只有1个，所以可以很方便的在前端界面显示，所以需要 frontend_tools。

#### 4 删除问题
用户问题：帮我删除一个节点，节点ID为J1  
回答：  
backend_tools: true
frontend_tools: true  
说明: 删除节点需调用 backend_tools 删除数据，同时需要 frontend_tools 在界面显示更新后的节点信息。  

##### 5 更新问题
用户问题：帮我把节点J1的名字设置为J1_new  
回答：  
backend_tools: true
frontend_tools: true  
说明: 更新节点需要调用 backend_tools 保存数据，同时需要 frontend_tools 在界面显示更新后的节点信息。
"""

                # 获取意图分析结果
                intent_messages = [{"role": "user", "content": intent_prompt}]
                intent_response = chatbot_llm.invoke(intent_messages)
                response_content = intent_response.content.strip()

                agent_logger.info(f"意图分析结果: {response_content}")

                # 解析回答
                need_backend = "backend_tools: true" in response_content.lower()
                need_frontend = "frontend_tools: true" in response_content.lower()

                agent_logger.info(
                    f"需求分析 - 后端: {need_backend}, 前端: {need_frontend}"
                )

                return {
                    "query": user_query,
                    "need_backend": need_backend,
                    "need_frontend": need_frontend,
                }

            # 2. 后端工具节点：根据标记决定是否执行
            def backend_tools_node(state: State) -> dict:
                """后端工具节点：根据need_backend标记决定是否执行"""
                need_backend = state.get("need_backend", False)
                user_query = state.get("query", "")

                agent_logger.info(
                    f"后端工具节点 - 需要执行: {need_backend}, 问题: {user_query}"
                )

                # 如果不需要后端工具，直接返回原状态
                if not need_backend:
                    agent_logger.info("跳过后端工具执行")
                    return {}

                if not user_query:
                    agent_logger.warning("后端节点没有收到用户问题")
                    return {}

                # 构建后端专用的消息，让后端LLM分析问题
                backend_messages = [
                    {
                        "role": "user",
                        "content": f"请根据以下问题调用合适的后端工具调用：{user_query}",
                    }
                ]

                # 后端LLM生成工具调用
                backend_response = backend_llm.invoke(backend_messages)
                agent_logger.info(f"后端LLM响应: {backend_response}")

                if not (
                    hasattr(backend_response, "tool_calls")
                    and backend_response.tool_calls
                ):
                    agent_logger.info("后端LLM没有生成工具调用")
                    return {}

                # 返回包含工具调用的AI消息
                return {"messages": [backend_response]}

            # 2a. 后端工具执行节点
            def backend_tool_execution_node(state: State) -> dict:
                """后端工具执行节点：实际执行后端工具"""
                agent_logger.info("执行后端工具")

                # 直接使用ToolNode执行后端工具
                backend_tool_node = ToolNode(tools=backend_tools)
                result = backend_tool_node.invoke(state)
                agent_logger.info("后端工具执行完成")

                return result

            # 路由函数：决定是否执行后端工具
            def route_backend_tools(
                state: State,
            ) -> Literal["backend_tool_execution", "frontend_tools"]:
                """
                决定是否执行后端工具
                如果最后一条消息有tool_calls，则执行工具；否则跳过
                """
                if isinstance(state, list):
                    ai_message = state[-1]
                elif messages := state.get("messages", []):
                    ai_message = messages[-1]
                else:
                    agent_logger.warning("没有找到消息用于工具路由")
                    return "frontend_tools"

                if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                    agent_logger.info("检测到后端工具调用，执行工具")
                    return "backend_tool_execution"

                agent_logger.info("没有后端工具调用，跳转到前端")
                return "frontend_tools"

            # 3. 前端工具节点：根据标记决定是否生成工具调用
            def frontend_tools_node(state: State) -> dict:
                """前端工具节点：根据need_frontend标记决定是否生成工具调用"""
                need_frontend = state.get("need_frontend", False)
                user_query = state.get("query", "")

                agent_logger.info(
                    f"前端工具节点 - 需要执行: {need_frontend}, 问题: {user_query} 注意事项：1.如果要调用**更新所有实体工具**，需要最先调用。2.所有前端功能不能重复调用。3.如果设计到更新实体数据和增加实体数据，需要先调用**更新所有实体工具**,再调用**跳转工具**"
                )

                # 如果不需要前端工具，直接返回原状态
                if not need_frontend:
                    agent_logger.info("跳过前端工具执行")
                    return {}

                if not user_query:
                    agent_logger.warning("前端节点没有收到用户问题")
                    return {}

                # 构建前端专用的消息，让前端LLM分析问题
                frontend_messages = [
                    {
                        "role": "user",
                        "content": f"请根据以下问题调用合适的前端工具：{user_query}",
                    }
                ]

                # 前端LLM生成工具调用
                frontend_response = frontend_llm.invoke(frontend_messages)
                agent_logger.info(f"前端LLM响应: {frontend_response}")

                if not (
                    hasattr(frontend_response, "tool_calls")
                    and frontend_response.tool_calls
                ):
                    agent_logger.info("前端LLM没有生成工具调用")
                    return {}

                # 返回包含工具调用的AI消息
                return {"messages": [frontend_response]}

            # 3a. 前端工具执行节点
            def frontend_tool_execution_node(state: State) -> dict:
                """前端工具执行节点：实际执行前端工具"""
                agent_logger.info("执行前端工具")

                # 直接使用ToolNode执行前端工具
                frontend_tool_node = SerialToolNode(tools=frontend_tools)
                result = frontend_tool_node.invoke(state)
                agent_logger.info("前端工具执行完成")

                return result

            # 路由函数：决定是否执行前端工具
            def route_frontend_tools(
                state: State,
            ) -> Literal["frontend_tool_execution", "chatbot_response"]:
                """
                决定是否执行前端工具
                如果最后一条消息有tool_calls，则执行工具；否则跳过
                """
                if isinstance(state, list):
                    ai_message = state[-1]
                elif messages := state.get("messages", []):
                    ai_message = messages[-1]
                else:
                    agent_logger.warning("没有找到消息用于工具路由")
                    return "chatbot_response"

                if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                    agent_logger.info("检测到前端工具调用，执行工具")
                    return "frontend_tool_execution"

                agent_logger.info("没有前端工具调用，跳转到总结")
                return "chatbot_response"

            # 4. 最终总结节点
            def chatbot_response(state: State) -> dict:
                """最终总结节点：基于所有执行结果生成总结回答"""
                user_query = state.get("query", "")
                need_backend = state.get("need_backend", False)
                need_frontend = state.get("need_frontend", False)

                agent_logger.info(
                    f"生成最终总结 - 问题: {user_query}, 后端: {need_backend}, 前端: {need_frontend}"
                )

                if not user_query:
                    agent_logger.warning("总结节点没有收到用户问题")
                    return {"messages": []}

                # 如果没有任何工具需求，直接进行普通对话
                if not need_backend and not need_frontend:
                    chat_messages = [{"role": "user", "content": user_query}]
                    response = chatbot_llm.invoke(chat_messages)
                    agent_logger.info(f"纯聊天回答: {response}")
                    return {"messages": [response]}

                # 基于所有历史消息生成总结
                # 包含用户问题和所有工具执行结果
                all_messages = state.get("messages", [])

                # 添加总结提示
                summary_prompt = f"""
请基于以上的工具执行结果，为用户问题"{user_query}"生成一个清晰、完整的回答。

要求：
1. 总结所有工具的执行结果
2. 回答用户的原始问题
3. 如果有数据查询结果，请清晰展示
4. 如果有界面操作，请确认操作已完成
5. 语言要自然、友好
"""

                summary_messages = all_messages + [
                    {"role": "user", "content": summary_prompt}
                ]

                # 使用纯聊天LLM生成总结
                response = chatbot_llm.invoke(summary_messages)
                agent_logger.info(f"最终总结: {response}")

                return {"messages": [response]}

            # 构建图结构 - 拆分工具调用和执行
            graph_builder.add_node("intent_classifier", intent_classifier_node)
            graph_builder.add_node("backend_tools", backend_tools_node)
            graph_builder.add_node(
                "backend_tool_execution", backend_tool_execution_node
            )
            graph_builder.add_node("frontend_tools", frontend_tools_node)
            graph_builder.add_node(
                "frontend_tool_execution", frontend_tool_execution_node
            )
            graph_builder.add_node("chatbot_response", chatbot_response)

            # 添加边 - 串行执行，每个工具分为决策和执行两步
            graph_builder.add_edge(START, "intent_classifier")
            graph_builder.add_edge("intent_classifier", "backend_tools")
            graph_builder.add_conditional_edges("backend_tools", route_backend_tools)
            graph_builder.add_edge("backend_tool_execution", "frontend_tools")
            graph_builder.add_conditional_edges("frontend_tools", route_frontend_tools)
            graph_builder.add_edge("frontend_tool_execution", "chatbot_response")
            graph_builder.add_edge("chatbot_response", END)

            # 使用内存存储
            memory = MemorySaver()
            self._graph = graph_builder.compile(checkpointer=memory)

            agent_logger.info(
                "Graph创建成功 - 拆分架构: 意图判断 -> 后端决策/执行 -> 前端决策/执行 -> 最终总结"
            )
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
    # → 保存成 test_graph.png
    # python -m utils.agent.graph_manager test_graph.png
    # → 自动保存成 graph_20250809_153200.png
    # python -m utils.agent.graph_manager

    import sys
    import time

    # 测试创建Graph
    try:
        # 创建文件名
        if len(sys.argv) > 1:
            filename = sys.argv[1]
        else:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"graph_{timestamp}.png"
        # 保存可视化
        graph_instance.save_visualization(filename)
        print(f"图已保存为: {filename}")

        # 测试简单对话
        config = {"configurable": {"thread_id": "test_conversation"}}
        messages = [{"role": "user", "content": "帮我查询节点信息"}]

        graph = graph_instance.get_graph()
        result = graph.invoke({"messages": messages}, config)
        print(f"对话结果: {result}")

    except Exception as e:
        print(f"测试失败: {e}")
