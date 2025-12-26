import json
import time
from typing import Dict, Any
from fastapi import WebSocket
from utils.logger import websocket_logger
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from schemas.agent.chat import (
    ChatRequest,
    ResponseMessageType,
    RequestMessageType,
)
from langgraph.types import Command
from pydantic import ValidationError
from typing import Dict, Any


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        websocket_logger.info(f"WebSocket连接已建立: {client_id}")

    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            websocket_logger.info(f"WebSocket连接已断开: {client_id}")

    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """发送消息到指定客户端"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                websocket_logger.warning(f"发送消息失败,移除连接 {client_id}: {e}")
                self.disconnect(client_id)

    def is_connected(self, client_id: str) -> bool:
        """检查客户端是否仍然连接"""
        return client_id in self.active_connections

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)

    def get_connected_clients(self) -> list[str]:
        """获取所有连接的客户端ID列表"""
        return list(self.active_connections.keys())


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()


# 调用流程 WebSocketProcessor -> ChatProcessor -> StreamProcessor -> ChatMessageSendHandler -> WebSocketManager
class WebSocketProcessor:
    """WebSocket消息处理器"""

    @staticmethod
    async def process_message(client_id: str, data: str) -> None:
        """处理WebSocket消息"""
        try:
            request_data = json.loads(data)
            websocket_logger.debug(f"{client_id} - 解析消息成功: {request_data}")

            # 处理ping请求
            if request_data.get("type") == RequestMessageType.PING:
                await ChatMessageSendHandler.send_pong(client_id)
                return

            # 处理聊天请求
            chat_request = ChatRequest(**request_data)
            await ChatProcessor.process_chat_request(client_id, chat_request)

        except json.JSONDecodeError as e:
            websocket_logger.error(f"JSON解析错误: {e}")
            await ChatMessageSendHandler.send_error(
                client_id,
                "请求数据格式错误,请确保发送有效的JSON数据",
            )
        except ValidationError as e:
            error_message = ChatRequest.get_user_friendly_error(e)
            websocket_logger.error(f"验证错误: {error_message}")
            await ChatMessageSendHandler.send_error(client_id, error_message)
        except Exception as e:
            websocket_logger.error(f"处理消息异常: {e}")
            await ChatMessageSendHandler.send_error(
                client_id,
                "服务器处理请求时发生错误",
            )


class ChatProcessor:
    """聊天处理器"""

    @staticmethod
    async def process_chat_request(client_id: str, chat_request: ChatRequest):
        """处理聊天请求"""
        try:
            # 延迟导入
            from utils.agent.graph_manager import GraphInstance

            graph = GraphInstance.get_graph(chat_request.mode)
            config = {"configurable": {"thread_id": client_id}}

            # states_message = graph.aget_state(config)

            if chat_request.type == RequestMessageType.FEEDBACK:
                await ChatProcessor.handle_feedback_request(
                    client_id, chat_request, graph, config
                )

            elif chat_request.type == RequestMessageType.CHAT:
                await ChatProcessor.handle_normal_request(
                    client_id, chat_request, graph, config
                )
            else:
                websocket_logger.error(
                    f"{client_id} - 未知请求类型: {chat_request.type}"
                )

        except Exception as e:
            websocket_logger.error(f"{client_id} - 处理聊天请求失败: {e}")
            await ChatMessageSendHandler.send_error(client_id, str(e))

    @staticmethod
    async def handle_normal_request(
        client_id: str,
        chat_request: ChatRequest,
        graph,
        config: Dict[str, Any],
    ) -> None:
        """处理普通聊天请求"""
        state = {
            "messages": [HumanMessage(content=chat_request.message)],
            "client_id": client_id,
            "mode": chat_request.mode,
        }

        websocket_logger.info(
            f"{client_id} - 开始处理用户正常聊天请求: {chat_request.message}"
        )
        # 发送开始响应头,提醒前端(可以新建一个对话窗口)
        await ChatMessageSendHandler.send_start(client_id)
        await StreamProcessor.send_stream_graph_messages(
            client_id, graph, state, config, chat_request.mode
        )

    @staticmethod
    async def handle_feedback_request(
        client_id: str,
        chat_request: ChatRequest,
        graph,
        config: Dict[str, Any],
    ) -> None:
        """处理反馈请求(流式处理)"""
        try:
            websocket_logger.info(
                f"{client_id} - 收到前端反馈请求,继续执行graph: Command:{chat_request}"
            )
            # 发送人类反馈消息,把chat_request 发送给 interrupt
            # 然后interrupt函数按照return的逻辑,被ToolMessage封装
            # 然后继续执行 graph
            human_command = Command(resume=chat_request.model_dump())
            await StreamProcessor.send_stream_graph_messages(
                client_id, graph, human_command, config, chat_request.mode
            )
        except Exception as e:
            websocket_logger.error(f"处理反馈请求失败: {e}")
            await ChatMessageSendHandler.send_error(client_id, str(e))


class StreamProcessor:
    """流式响应处理器"""

    # 通用流式消息发送函数
    @staticmethod
    async def send_stream_graph_messages(
        client_id: str,
        graph,
        state_or_command,
        config,
        mode: str,  # 这里必须传 mode 参数，因为 Command 和 state 这里不是统一的 .get("mode")或者 .mode能取到 mode的值，为了统一处理，直接传 mode 参数
    ):
        """统一处理 graph.astream 下的流式消息分发和连接检查"""
        # 检查连接状态
        if not websocket_manager.is_connected(client_id):
            websocket_logger.warning(f"客户端 {client_id} 已断开,跳过处理")
            return
        # 处理流式消息
        async for message_chunk, metadata in graph.astream(
            state_or_command, config, stream_mode="messages"
        ):
            if not websocket_manager.is_connected(client_id):
                websocket_logger.info(f"客户端 {client_id} 已断开,停止流式响应")
                break
            if isinstance(message_chunk, AIMessage):
                # llm异步流式返回的 AIMessages，就会被这里捕获
                await ChatMessageSendHandler.send_ai_message(
                    client_id, message_chunk, mode
                )
            elif isinstance(message_chunk, ToolMessage):
                # 节点 return 执行结果（ToolMessage）的时候，会被这里捕获
                await ChatMessageSendHandler.send_tool_message(
                    client_id, message_chunk, mode
                )
            else:
                websocket_logger.warning(f"未知消息类型: {type(message_chunk)}")


class ChatMessageSendHandler:
    """聊天消息发送处理器"""

    @staticmethod
    async def _send_response(
        client_id: str,
        response_type: str,
        **kwargs,
    ) -> None:
        """统一的响应发送方法(私有,仅供本类内部调用)"""
        if client_id is None:
            websocket_logger.error("客户端ID为空,无法发送响应")
            return
        if not websocket_manager.is_connected(client_id):
            websocket_logger.warning(
                f"客户端 {client_id} 已断开,跳过发送响应: {response_type}"
            )
            return
        base_data = {
            "type": response_type,
            "timestamp": int(time.time() * 1000),
        }
        base_data.update(kwargs)
        await websocket_manager.send_message(client_id, base_data)

    @staticmethod
    async def send_pong(client_id: str) -> None:
        """发送心跳响应"""
        await ChatMessageSendHandler._send_response(client_id, ResponseMessageType.PONG)

    @staticmethod
    async def send_start(client_id: str) -> None:
        """发送开始响应"""
        await ChatMessageSendHandler._send_response(
            client_id, ResponseMessageType.START
        )
        websocket_logger.info(f"{client_id} - 发送开始消息: start")

    @staticmethod
    async def send_ai_message(
        client_id: str, message: AIMessage, mode: str, force_send: bool = False
    ) -> None:
        """处理AI普通消息,直接渲染content"""
        # force_send 解决 astream 会自动捕捉 aimessage 的 tool_calls,但是此时的tool_calls 有个bug args为空（content='' 拦截）
        # 所有增加一个 forcesend 参数，除了astream发送aimessage，当工具节点生成调用的时候，手动发送完整的aimessage
        content = message.content or ""
        tool_calls = message.tool_calls
        if not force_send and not content:
            # AI消息内容为空,且不是强制发送，跳过发送
            return
        await ChatMessageSendHandler._send_response(
            client_id,
            ResponseMessageType.AI_MESSAGE,
            content=content,
            tool_calls=tool_calls,
            mode=mode,
        )
        # 分段发送,打印太多了,注释掉
        # websocket_logger.debug(
        #     f"{client_id} -  发送AI消息: {content} -- {client_id}"
        # )

    @staticmethod
    async def send_tool_message(
        client_id: str, message: ToolMessage, mode: str
    ) -> None:
        """处理工具消息"""
        await ChatMessageSendHandler._send_response(
            client_id,
            ResponseMessageType.TOOL_MESSAGE,
            content=message.content,
            name=message.name,
            mode=mode,
        )
        websocket_logger.debug(
            f"{client_id} - 发送工具消息: name: {message.name} -- content: {message.content}"
        )

    @staticmethod
    async def send_function_call(
        client_id: str,
        function_name: str,
        args: dict,
        is_direct_feedback: bool,
        mode: str,
        success_message: str = None,
    ) -> None:
        """处理函数调用"""
        await ChatMessageSendHandler._send_response(
            client_id,
            ResponseMessageType.FUNCTION_CALL,
            function_name=function_name,
            args=args,
            is_direct_feedback=is_direct_feedback,
            success_message=success_message,
            mode=mode,
        )
        websocket_logger.debug(
            f"{client_id} - 发送函数调用消息: function_name: {function_name} -- args: {args} -- is_direct_feedback: {is_direct_feedback} -- success_message: {success_message}"
        )

    @staticmethod
    async def send_complete(client_id: str) -> None:
        """发送完成响应"""
        await ChatMessageSendHandler._send_response(
            client_id,
            ResponseMessageType.COMPLETE,
        )
        websocket_logger.debug(f"{client_id} - 发送完成消息:complete")

    @staticmethod
    async def send_error(
        client_id: str,
        error_msg: str,
    ) -> None:
        """发送错误响应"""
        await ChatMessageSendHandler._send_response(
            client_id, ResponseMessageType.ERROR, message=error_msg
        )
        websocket_logger.error(
            f"{client_id} - 发送错误消息: {client_id} -- {error_msg}"
        )

    @staticmethod
    async def send_step(client_id: str, content: str, mode: str) -> None:
        """发送步骤信息"""
        await ChatMessageSendHandler._send_response(
            client_id, ResponseMessageType.STEP, content=content, mode=mode
        )
        websocket_logger.info(f"{client_id} - 发送步骤信息: {content}")
