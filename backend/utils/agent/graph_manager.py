import os
from typing import Optional, Annotated, Literal, Type, Union
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm
from utils.agent.serial_tool_node import SerialToolNode
from utils.agent.async_store_manager import AsyncStoreManager

from tools.web_ui import fly_to_entity_by_name_tool, init_entities_tool
from tools.junction import (
    get_junctions_tool,
    batch_get_junctions_by_ids_tool,
    create_junction_tool,
    delete_junction_tool,
    update_junction_tool,
)
from tools.outfall import (
    get_outfalls_tool,
    update_outfall_tool,
    create_outfall_tool,
    delete_outfall_tool,
)
from tools.conduit import (
    get_conduits_tool,
    update_conduit_tool,
    create_conduit_tool,
    delete_conduit_tool,
    batch_get_conduits_by_ids_tool,
)

static_dir = os.path.join("static", "agent_graph")


# 定义聊天机器人的状态
class State(TypedDict):
    messages: Annotated[list, add_messages]
    client_id: Optional[str]  # 客户端连接ID
    query: Optional[str]  # 当前要解决的问题
    need_backend: Optional[bool]  # 是否需要执行后端工具
    need_frontend: Optional[bool]  # 是否需要执行前端工具


class GraphInstance:
    """LangGraph 管理器 - 全静态方法"""

    _graph: Optional[StateGraph] = None

    @classmethod
    def init(cls, llm=None) -> StateGraph:
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
                get_outfalls_tool,
                update_outfall_tool,
                create_outfall_tool,
                delete_outfall_tool,
                get_conduits_tool,
                update_conduit_tool,
                create_conduit_tool,
                delete_conduit_tool,
                batch_get_conduits_by_ids_tool,
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
            async def intent_classifier_node(state: State) -> dict:
                """意图判断节点：分析问题并标记需要后端/前端工具"""
                user_message = GraphInstance.get_recent_messages_by_type(
                    state, n=1, msg_type=HumanMessage
                )
                if not user_message:
                    return {"query": "", "need_backend": False, "need_frontend": False}
                # 提取用户查询
                user_query = user_message.content
                agent_logger.info(f"意图判断 - 用户问题: {user_query}")

                # 使用提示词进行意图分析（可能包含多种需求）
                # 新增：将state上下文也加入prompt
                # TODO：promt需要放在其他文件，不要硬编码到核心代码里面
                intent_prompt = f"""
                                请阅读用户的问题:<<** {user_query} **>>，并根据需求判断需要调用哪些处理工具（可以同时需要多种）。  

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
                # TODO:这里需要更改，根据之后处理 memory 引入数据库后，更加优雅的处理
                # 将历史消息与意图prompt结合  (参考下面的frontend_messages节点的分析)
                intent_messages = [HumanMessage(content=intent_prompt)]
                # 获取意图分析结果
                intent_response = await chatbot_llm.ainvoke(intent_messages)
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
            async def backend_tools_node(state: State) -> dict:
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

                # TODO:这里需要更改，根据之后处理 memory 引入数据库后，更加优雅的处理
                # 将历史消息与意图prompt结合
                # 构建后端专用的消息，让后端LLM分析问题 (参考下面的frontend_messages节点的分析)
                backend_messages = [
                    HumanMessage(
                        content=f"""请根据以下问题调用合适的后端工具调用：{user_query}"""
                    )
                ]

                # 后端LLM生成工具调用
                backend_response = await backend_llm.ainvoke(backend_messages)
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
            async def backend_tool_execution_node(state: State) -> dict:
                """后端工具执行节点：实际执行后端工具"""
                agent_logger.info("执行后端工具")

                # 直接使用ToolNode执行后端工具
                backend_tool_node = ToolNode(tools=backend_tools)
                result = await backend_tool_node.ainvoke(state)
                agent_logger.info(f"后端工具执行完成, 结果: {result}")

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
            async def frontend_tools_node(state: State) -> dict:
                """前端工具节点：根据need_frontend标记决定是否生成工具调用"""
                need_frontend = state.get("need_frontend", False)
                user_query = state.get("query", "")

                agent_logger.info(
                    f"前端工具节点 - 需要执行: {need_frontend}, 问题: {user_query} "
                )

                # 如果不需要前端工具，直接返回原状态
                if not need_frontend:
                    agent_logger.info("跳过前端工具执行")
                    return {}

                if not user_query:
                    agent_logger.warning("前端节点没有收到用户问题")
                    return {}

                # TODO:这里需要更改，根据之后处理 memory 引入数据库后，更加优雅的处理
                # 将历史消息与意图prompt结合 ，不能直接把 human_messages + frontend_messages
                # 因为会让这个并列，有时候就会回答之前的问题去了，要把放进promt里面，包裹关系
                # 还有一种办法，在graph最开始，有一个拼接上下文的llm，丰富问题上下文（这个更好）

                # human_messages = GraphInstance.get_recent_messages_by_type(
                #     state, n=3, msg_type=HumanMessage
                # )

                # 构建前端专用的消息，让前端LLM分析问题
                frontend_messages = [
                    HumanMessage(
                        content=f"""请根据以下问题调用合适的前端工具：{user_query}
                        前端工具调用**注意事项**：
                        1.如果要调用**更新所有实体工具**，需要最先调用。
                        2.如果涉及到**一次性更新单个实体**实体数据和**增加**实体数据，一定需要调用**更新所有实体工具**，最好再调用**跳转功能**。
                        3.如果涉及一次性更新单个实体实体的**名字属性**的时候，尤其需要调用**跳转功能**，跳转到新的名字实体上。""",
                    )
                ]
                # frontend_messages = message

                # 前端LLM生成工具调用
                frontend_response = await frontend_llm.ainvoke(frontend_messages)
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
            # (重点：这里用同步，异步会导致human in the loop问题)
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
            async def chatbot_response(state: State) -> dict:
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
                    chat_messages = [HumanMessage(content=user_query)]
                    response = await chatbot_llm.ainvoke(chat_messages)
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
                # TODO: 优化总结上下文管理
                summary_messages = all_messages + [HumanMessage(content=summary_prompt)]

                # 使用纯聊天LLM生成总结
                response = await chatbot_llm.ainvoke(summary_messages)
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

            # === 持久化存储 ===
            checkpointer = AsyncStoreManager.checkpointer
            print("checkpointer:", checkpointer)
            store = AsyncStoreManager.store
            print("store:", store)
            cls._graph = graph_builder.compile(checkpointer=checkpointer, store=store)
            agent_logger.info(
                "Graph创建成功 - 拆分架构: 意图判断 -> 后端决策/执行 -> 前端决策/执行 -> 最终总结"
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
            raise RuntimeError("Graph未初始化，请先调用init()")
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

    @staticmethod
    def get_recent_messages_by_type(
        state, n=1, msg_type: Union[Type[HumanMessage], Type[AIMessage]] = AIMessage
    ):
        """
        获取 state 最近 n 条 HumanMessage 或 AIMessage，按原始顺序返回。
        msg_type: HumanMessage 或 AIMessage
        如果不足 n 条，则尽可能多取。
        """
        messages = state.get("messages", [])
        result_messages = []

        # 倒序遍历，找到最近的 n 条
        for message in reversed(messages):
            if isinstance(message, msg_type):
                result_messages.append(message)
                if len(result_messages) >= n:
                    break

        # 要保持原始顺序，就在返回前反转
        result_messages.reverse()

        if n == 1:
            return result_messages[-1] if result_messages else None
        return result_messages


if __name__ == "__main__":
    # → 保存成 test_graph.png
    # python -m utils.agent.graph_manager test_graph.png
    # → 自动保存成 graph_20250809_153200.png
    # python -m utils.agent.graph_manager

    import sys
    import time
    import asyncio

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
