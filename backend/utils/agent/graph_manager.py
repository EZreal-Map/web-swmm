import os
import json
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
from utils.agent.websocket_manager import ChatMessageSendHandler
from langgraph.types import Send

from tools.webgis import fly_to_entity_by_name_tool, init_entities_tool
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
            # 如果没有传入LLM,使用默认的OpenAI模型
            if llm is None:
                llm = create_openai_llm()

            # 构建graph
            graph_builder = StateGraph(State)

            # 定义工具
            # 1.1 普通后端工具
            normal_backend_tools = [
                get_junctions_tool,
                create_junction_tool,
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
            # 1.2 Human in the loop后端工具(人类反馈工具)
            HIL_backend_tools = [
                delete_junction_tool,
                delete_outfall_tool,
                delete_conduit_tool,
            ]
            HIL_backend_tools_name = [
                tool.name for tool in HIL_backend_tools
            ]  # HIL后端工具名字变量
            # 1.3 后端工具集合
            backend_tools = normal_backend_tools + HIL_backend_tools

            # 2.1 普通前端工具
            normal_frontend_tools = []
            # 2.2 Human in the loop前端工具(人类反馈工具)
            HIL_frontend_tools = [
                init_entities_tool,
                fly_to_entity_by_name_tool,
            ]
            HIL_frontend_tools_name = [
                tool.name for tool in HIL_frontend_tools
            ]  # HIL前端工具名字变量
            # 2.3 前端工具集合
            frontend_tools = normal_frontend_tools + HIL_frontend_tools

            # 创建LLM实例
            intent_llm = llm  # TODO:有可能加上 with_structured_output,但是就会失去流式输出,但是结果更加优雅,现在用 in 判断也没有出过问题
            backend_llm = llm.bind_tools(tools=backend_tools)
            frontend_llm = llm.bind_tools(tools=frontend_tools)
            chatbot_llm = llm  # 纯聊天用的LLM

            # 1. 意图识别节点:分析并标记需要的工具类型
            async def intent_classifier_node(state: State) -> dict:
                """意图识别节点:分析问题并标记需要后端/前端工具"""
                user_message = GraphInstance.get_recent_messages_by_type(
                    state.get("messages", []), n=1, msg_type=HumanMessage
                )
                if not user_message:
                    return {"query": "", "need_backend": False, "need_frontend": False}
                # 提取用户查询
                user_query = user_message.content
                agent_logger.info(
                    f"{state.get('client_id')} - 进入意图识别节点: user_query: {user_query}"
                )
                # 使用提示词进行意图识别(可能包含多种需求)
                # 新增:将state上下文也加入prompt
                # TODO:promt需要放在其他文件,不要硬编码到核心代码里面
                intent_prompt = f"""
                                请阅读用户的问题:<<** {user_query} **>>,并根据需求判断需要调用哪些处理工具(可以同时需要多种)。  

                                处理工具说明:  
                                1. backend_tools  
                                - 用于 **SWMM 模型数据操作**(例如:节点/管道/子汇水区等数据的查询、创建、更新、删除)。  
                                - 如果问题涉及数据的增删改查,或者需要从数据库读取模型信息,都应选择该工具。  

                                2. frontend_tools  
                                - 用于 **前端界面交互**(例如:地图跳转、实体高亮、界面刷新等)。  
                                - 如果问题需要让用户在界面上看到变化(如定位到某个节点、在地图上显示结果等),则需要该工具。  
                                - 注意:如果只是查询数据并将结果直接返回给用户(不要求地图或界面变化),则**不需要** frontend_tools。
                                - 但凡涉及到数据的**更新,删除,增加**操作,都需要 frontend_tools,因为前端界面也要响应的变化更新。

                                3. chatbot  
                                - 用于 **普通对话、解释说明、总结回答** 等不需要操作数据或界面的场景。  
                                - 当用户只提问概念性问题、流程指导,或不涉及数据和界面操作时,选该工具。  

                                ---

                                ### 输出要求  
                                只按以下格式回答(不要多余内容):  

                                backend_tools: [true/false]  
                                frontend_tools: [true/false]  
                                说明: [简短说明需要这些工具的原因]  

                                ---

                                ### 示例  

                                ##### 1 查询多个问题
                                用户问题:帮我查询所有节点的信息  
                                回答:  
                                backend_tools: true  
                                frontend_tools: false  
                                说明: 查询节点信息只需调用 backend_tools 获取数据表,数据太多无法在前端上一一显示,所以不需要 frontend_tools。

                                ##### 2 查询一个问题
                                用户问题:帮我查询一个节点的信息,节点ID为J1  
                                回答:  
                                backend_tools: true  
                                frontend_tools: true
                                说明: 查询节点信息需调用 backend_tools 获取数据信息,因为数据只有1个,所以可以很方便的在前端界面显示,所以需要 frontend_tools。

                                #### 3 创建问题
                                用户问题:帮我创建一个节点,节点信息如下名字为J1,纬度为110,纬度为30  
                                回答:  
                                backend_tools: true
                                frontend_tools: true  
                                说明: 创建节点需要调用 backend_tools 保存数据,因为数据只有1个,所以可以很方便的在前端界面显示,所以需要 frontend_tools。

                                #### 4 删除问题
                                用户问题:帮我删除一个节点,节点ID为J1  
                                回答:  
                                backend_tools: true
                                frontend_tools: true  
                                说明: 删除节点需调用 backend_tools 删除数据,同时需要 frontend_tools 在界面显示更新后的节点信息。  

                                ##### 5 更新问题
                                用户问题:帮我把节点J1的名字设置为J1_new  
                                回答:  
                                backend_tools: true
                                frontend_tools: true  
                                说明: 更新节点需要调用 backend_tools 保存数据,同时需要 frontend_tools 在界面显示更新后的节点信息。

                                ##### 6 前端问题
                                用户问题:跳转到J1
                                回答:
                                backend_tools: true
                                frontend_tools: true
                                说明: 跳转到J1不需要查询后端数据,所有不需要backend_tools,前端工具可以直接处理跳转。
"""
                # TODO:这里需要更改,根据之后处理 memory 引入数据库后,更加优雅的处理
                # 将历史消息与意图prompt结合  (参考下面的frontend_messages节点的分析)
                intent_messages = [HumanMessage(content=intent_prompt)]
                # 获取意图识别结果
                intent_response = await intent_llm.ainvoke(intent_messages)
                response_content = intent_response.content.strip()
                # 解析回答
                need_backend = "backend_tools: true" in response_content
                need_frontend = "frontend_tools: true" in response_content
                agent_logger.info(
                    f"{state.get('client_id')} - 意图识别节点LLM响应: {response_content}"
                )

                return {
                    "query": user_query,
                    "need_backend": need_backend,
                    "need_frontend": need_frontend,
                }

            # 2. 后端工具节点:根据标记决定是否执行
            async def backend_tools_node(state: State) -> dict:
                """后端工具节点:根据need_backend标记决定是否执行"""
                need_backend = state.get("need_backend", False)
                user_query = state.get("query", "")
                agent_logger.info(
                    f"{state.get('client_id')} - 进入后端工具节点: need_backend:{need_backend}, user_query: {user_query}"
                )
                # 如果不需要后端工具,直接返回原状态
                if not need_backend:
                    agent_logger.info(
                        f"{state.get('client_id')} - 不需要后端工具,跳过后端工具节点"
                    )
                    return {}

                if not user_query:
                    agent_logger.warning(
                        f"{state.get('client_id')} - 用户问题为空,后端工具节点没有收到用户问题"
                    )
                    return {}

                # TODO:这里需要更改,根据之后处理 memory 引入数据库后,更加优雅的处理
                # 将历史消息与意图prompt结合
                # 构建后端专用的消息,让后端LLM分析问题 (参考下面的frontend_messages节点的分析)
                backend_messages = [
                    HumanMessage(
                        content=f"""请根据以下问题一次性调用合适的后端工具调用:{user_query}"""
                    )
                ]

                # 后端LLM生成工具调用
                backend_response = await backend_llm.ainvoke(backend_messages)
                agent_logger.info(
                    f"{state.get('client_id')} - 后端工具节点LLM响应: {backend_response}"
                )
                # 返回包含工具调用的AI消息
                return {"messages": [backend_response]}

            # 2.1 路由函数:决定是否执行后端工具
            def route_backend_tools(
                state: State,
            ) -> Literal["backend_tool_execution", "frontend_tools"]:
                """
                决定是否执行后端工具
                如果最后一条消息有tool_calls,则执行工具；否则跳过
                """
                if isinstance(state, list):
                    ai_message = state[-1]
                elif messages := state.get("messages", []):
                    ai_message = messages[-1]
                else:
                    agent_logger.warning(
                        f"{state.get('client_id')} - state格式为空或者不正确,没有找到消息用于工具路由: state={state}"
                    )
                    return Send("frontend_tools", state)

                if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                    agent_logger.debug(
                        f"{state.get('client_id')} - 检测到后端工具调用,执行后端工具"
                    )
                    # 2.后端有工具调用
                    # 记录 Send 返回结果
                    send_list = []
                    split_messages = GraphInstance.split_ai_message_by_tool_names(
                        ai_message, HIL_backend_tools_name
                    )
                    # 2.1 分割后第一个消息为普通工具调用消息
                    if split_messages[0]:
                        send_list.append(
                            Send(
                                "backend_tool_execution",
                                {
                                    "messages": [split_messages[0]],
                                    "client_id": state["client_id"],
                                    "human_in_the_loop": False,
                                },
                            )
                        )
                    # 2.2 分割后第二个消息为人类参与的工具调用消息
                    if split_messages[1]:
                        send_list.append(
                            Send(
                                "backend_tool_execution",
                                {
                                    "messages": [split_messages[1]],
                                    "client_id": state["client_id"],
                                    "human_in_the_loop": True,
                                },
                            )
                        )
                    # 返回调用下一个节点执行工具
                    return send_list
                else:
                    # 后端LLM没有生成工具调用,跳转到前端工具节点
                    return Send("frontend_tools", state)

            # 2.2 后端工具执行节点
            # Send 到这个节点,分为并行(toolnode)(自动执行)和 (serialtoolnode)(人类参与)
            async def backend_tool_execution_node(send_state: State) -> dict:
                """后端工具执行节点:实际执行后端工具"""
                if send_state.get("human_in_the_loop", False):
                    agent_logger.debug(
                        f"{send_state.get('client_id')} - 开始执行后端工具(人类参与): messages: {send_state.get('messages', [])}"
                    )
                    backend_tool_node = SerialToolNode(tools=backend_tools)
                    result = backend_tool_node.invoke(send_state)
                    agent_logger.debug(
                        f"{send_state.get('client_id')} - 后端工具(人类参与)执行结果: {result}"
                    )
                    return result
                else:
                    agent_logger.debug(
                        f"{send_state.get('client_id')} -  开始执行后端工具(自动执行): messages: {send_state.get('messages', [])}"
                    )
                    backend_tool_node = ToolNode(tools=backend_tools)
                    result = await backend_tool_node.ainvoke(send_state)
                    agent_logger.debug(
                        f"{send_state.get('client_id')} - 后端工具(自动执行)执行结果: {result}"
                    )
                    return result

            # 3. 前端工具节点:根据标记决定是否生成工具调用
            async def frontend_tools_node(state: State) -> dict:
                """前端工具节点:根据need_frontend标记决定是否生成工具调用"""
                need_frontend = state.get("need_frontend", False)
                user_query = state.get("query", "")
                agent_logger.info(
                    f"{state.get('client_id')} - 进入前端工具节点: need_frontend: {need_frontend}, user_query: {user_query}"
                )

                # 如果不需要前端工具,直接返回原状态
                if not need_frontend:
                    agent_logger.info(
                        f"{state.get('client_id')} - 不需要前端工具,跳过前端工具节点"
                    )
                    return {}

                if not user_query:
                    agent_logger.warning(
                        f"{state.get('client_id')} - 用户问题为空,前端工具节点没有收到用户问题"
                    )
                    return {}

                # TODO:这里需要更改,根据之后处理 memory 引入数据库后,更加优雅的处理
                # 将历史消息与意图prompt结合 ,不能直接把 human_messages + frontend_messages
                # 因为会让这个并列,有时候就会回答之前的问题去了,要把放进promt里面,包裹关系
                # 还有一种办法,在graph最开始,有一个拼接上下文的llm,丰富问题上下文(这个更好)

                # human_messages = GraphInstance.get_recent_messages_by_type(
                #     state, n=3, msg_type=HumanMessage
                # )

                # 构建前端专用的消息,让前端LLM分析问题
                frontend_messages = [
                    HumanMessage(
                        content=f"""请根据以下问题一次性调用合适的前端工具:{user_query}
                        前端工具调用**注意事项**:
                        1.如果要调用**更新所有实体工具**,需要最先调用。
                        2.如果涉及到**一次性更新单个实体**实体数据和**增加**实体数据,一定需要调用**更新所有实体工具**,最好再调用**跳转功能**。
                        3.如果涉及一次性更新单个实体实体的**名字属性**的时候,尤其需要调用**跳转功能**,跳转到新的名字实体上。""",
                    )
                ]
                # 前端LLM生成工具调用
                frontend_response = await frontend_llm.ainvoke(frontend_messages)
                agent_logger.info(
                    f"{state.get('client_id')} - 前端工具LLM响应: {frontend_response}"
                )

                return {"messages": [frontend_response]}

            # 3.1 路由函数:决定是否执行前端工具
            def route_frontend_tools(
                state: State,
            ) -> Literal["frontend_tool_execution", "chatbot_response"]:
                """
                根据最后上一个节点的消息决定是否执行工具:执行工具或跳转到下一个节点(chatbot_response)
                """
                if isinstance(state, list):
                    ai_message = state[-1]
                elif messages := state.get("messages", []):
                    ai_message = messages[-1]
                else:
                    agent_logger.warning("没有找到消息用于工具路由")
                    return Send("chatbot_response", state)

                if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                    agent_logger.debug(
                        f"{state.get('client_id')} - 检测到前端工具调用,执行前端工具"
                    )
                    # 2.前端有工具调用
                    # 记录 Send 返回结果
                    send_list = []
                    split_messages = GraphInstance.split_ai_message_by_tool_names(
                        ai_message, HIL_frontend_tools_name
                    )
                    # 2.1 分割后第一个消息为普通工具调用消息
                    if split_messages[0]:
                        send_list.append(
                            Send(
                                "frontend_tool_execution",
                                {
                                    "messages": [split_messages[0]],
                                    "client_id": state["client_id"],
                                    "human_in_the_loop": False,
                                },
                            )
                        )
                    # 2.2 分割后第二个消息为人类参与的工具调用消息
                    if split_messages[1]:
                        send_list.append(
                            Send(
                                "frontend_tool_execution",
                                {
                                    "messages": [split_messages[1]],
                                    "client_id": state["client_id"],
                                    "human_in_the_loop": True,
                                },
                            )
                        )
                    # 返回调用下一个节点执行工具
                    return send_list
                else:
                    # 前端LLM没有生成工具调用,跳转到总结节点
                    return Send("chatbot_response", state)

            # 3.2 前端工具执行节点
            # Send 到这个节点,分为并行(toolnode)(自动执行)和 (serialtoolnode)(人类参与)
            # (重点:这里用同步,异步会导致human in the loop问题)
            async def frontend_tool_execution_node(send_state: State) -> dict:
                """前端工具执行节点:实际执行前端工具"""
                if send_state.get("human_in_the_loop", False):
                    agent_logger.debug(
                        f"{send_state.get('client_id')} - 开始执行前端工具(人类参与): messages: {send_state.get('messages', [])}"
                    )
                    frontend_tool_node = SerialToolNode(tools=frontend_tools)
                    result = frontend_tool_node.invoke(send_state)
                    agent_logger.debug(
                        f"{send_state.get('client_id')} - 前端工具(人类参与)执行结果: {result}"
                    )
                    return result
                else:
                    agent_logger.debug(
                        f"{send_state.get('client_id')} -  开始执行前端工具(自动执行): messages: {send_state.get('messages', [])}"
                    )
                    frontend_tool_node = ToolNode(tools=frontend_tools)
                    result = await frontend_tool_node.ainvoke(send_state)
                    agent_logger.debug(
                        f"{send_state.get('client_id')} - 前端工具(自动执行)执行结果: {result}"
                    )
                    return result

            # 4. 最终总结节点
            async def chatbot_response(state: State) -> dict:
                """最终总结节点:基于所有执行结果生成总结回答"""
                agent_logger.info(f"{state.get('client_id')} - 进入总结节点")
                user_query = state.get("query", "")
                if not user_query:
                    agent_logger.warning(
                        f"{state.get('client_id')} - 总结节点没有收到用户问题"
                    )
                    return {"messages": []}

                # 基于最近一轮消息生成总结 (包含用户问题和所有工具执行结果)
                recent_dialogue_round = GraphInstance.get_split_dialogue_rounds(
                    state.get("messages", []), 1
                )
                # 添加总结提示
                summary_prompt = f"""
                请基于以上的工具执行结果,为用户问题"{user_query}"生成一个清晰、完整的回答。
                要求:
                1. 总结所有工具的执行结果
                2. 回答用户的原始问题
                3. 如果有数据查询结果,请清晰展示,如果数据过长请进行适当的截断，除非用户要求保留完整和精确的数据。
                4. 浮点数小数位如果过长，可以适当截取，比如经纬度，适当截取保留5位就差不多了，除非用户要求保留完整和精确的数据。
                5. 尽量使用markdown格式回答，如果有多组同样格式数据，可以适当使用表格，确保信息清晰可读。
                """
                # TODO: 优化总结上下文管理
                summary_messages = recent_dialogue_round + [
                    HumanMessage(content=summary_prompt)
                ]

                # 使用纯聊天LLM生成总结
                response = await chatbot_llm.ainvoke(summary_messages)
                agent_logger.info(
                    f"{state.get('client_id')} - 总结节点LLM响应: {response}"
                )
                await ChatMessageSendHandler.send_complete(state["client_id"])
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

            # 添加边 - 串行执行,每个工具分为决策和执行两步
            graph_builder.add_edge(START, "intent_classifier")
            graph_builder.add_edge("intent_classifier", "backend_tools")
            graph_builder.add_conditional_edges("backend_tools", route_backend_tools)
            graph_builder.add_edge("backend_tool_execution", "frontend_tools")
            graph_builder.add_conditional_edges(
                "frontend_tools", route_frontend_tools, ["frontend_tool_execution"]
            )
            graph_builder.add_edge("frontend_tool_execution", "chatbot_response")
            graph_builder.add_edge("chatbot_response", END)

            # === 持久化存储 ===
            checkpointer = AsyncStoreManager.checkpointer
            store = AsyncStoreManager.store
            cls._graph = graph_builder.compile(checkpointer=checkpointer, store=store)
            agent_logger.info(
                "Graph创建成功 - 拆分架构: 意图识别 -> 后端决策/执行 -> 前端决策/执行 -> 最终总结"
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

    @staticmethod
    def get_recent_messages_by_type(
        messages, n=1, msg_type: Union[Type[HumanMessage], Type[AIMessage]] = AIMessage
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

    # TODO:也许这里2个方法要被移出去,看以后会不会有很多处理messages消息的类
    @staticmethod
    def get_split_dialogue_rounds(messages, n=None):
        """
        将消息列表按 HumanMessage 分为多轮,每轮以 HumanMessage 开头。
        如果 n 不传递,返回全部轮次；
        如果 n=1,返回最近 1 轮(最新的在最后)；
        如果 n>1,返回最近 n 轮,顺序与原始消息一致。
        返回:List[List[Message]]
        """
        from langchain.schema import HumanMessage

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

    @staticmethod
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
