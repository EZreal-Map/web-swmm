import json
import time
from typing import Dict, Any
from fastapi import WebSocket
from utils.logger import websocket_logger
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from schemas.agent.chat import ChatRequest, ChatFeedback, MessageType
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
                websocket_logger.warning(f"发送消息失败，移除连接 {client_id}: {e}")
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
            websocket_logger.debug(
                f"解析消息成功: {request_data.get('type', 'unknown')}"
            )

            # 处理ping请求
            if request_data.get("type") == MessageType.PING:
                await ChatMessageSendHandler.send_pong(client_id)
                return

            # 处理聊天请求
            chat_request = ChatRequest(**request_data)
            await ChatProcessor.process_chat_request(client_id, chat_request)

        except json.JSONDecodeError as e:
            websocket_logger.error(f"JSON解析错误: {e}")
            await ChatMessageSendHandler.send_error(
                client_id,
                "请求数据格式错误，请确保发送有效的JSON数据",
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

            # 确保Graph已初始化
            if not GraphInstance.is_initialized():
                websocket_logger.info("初始化Graph...")
                GraphInstance.init()

            graph = GraphInstance.get_graph()
            config = {"configurable": {"thread_id": client_id}}

            # states_message = graph.aget_state(config)

            if chat_request.feedback:
                await ChatProcessor.handle_feedback_request(
                    client_id, chat_request, graph, config
                )
            else:
                await ChatProcessor.handle_normal_request(
                    client_id, chat_request, graph, config
                )

        except Exception as e:
            websocket_logger.error(f"处理聊天请求失败: {e}")
            await ChatMessageSendHandler.send_error(client_id, str(e))

    @staticmethod
    async def handle_normal_request(
        client_id: str, chat_request: ChatRequest, graph, config: Dict[str, Any]
    ) -> None:
        """处理普通聊天请求"""
        state = {
            "messages": [HumanMessage(content=chat_request.message)],
            "client_id": client_id,
        }

        websocket_logger.info(f"开始处理用户消息: {chat_request.message}")
        # 发送开始响应头，提醒前端（可以新建一个对话窗口）
        await ChatMessageSendHandler.send_start(client_id)
        await StreamProcessor.send_stream_graph_messages(
            client_id, graph, state, config
        )

    @staticmethod
    async def handle_feedback_request(
        client_id: str, chat_request: ChatRequest, graph, config: Dict[str, Any]
    ) -> None:
        """处理反馈请求（流式处理）"""
        websocket_logger.info(f"收到反馈，继续执行graph: {chat_request.message}")
        try:
            feedback_state = ChatFeedback(
                success=chat_request.success, feedback_message=chat_request.message
            ).model_dump()
            # 发送人类反馈消息，把feedback_state 发送给 interrupt
            # 然后interrupt函数按照return的逻辑，被ToolMessage封装
            # 然后继续执行 graph
            human_command = Command(resume=feedback_state)
            await StreamProcessor.send_stream_graph_messages(
                client_id, graph, human_command, config
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
    ):
        """统一处理 graph.astream 下的流式消息分发和连接检查"""
        # 检查连接状态
        if not websocket_manager.is_connected(client_id):
            websocket_logger.warning(f"客户端 {client_id} 已断开，跳过处理")
            return
        # 处理流式消息
        async for message_chunk, metadata in graph.astream(
            state_or_command, config, stream_mode="messages"
        ):
            if not websocket_manager.is_connected(client_id):
                websocket_logger.info(f"客户端 {client_id} 已断开，停止流式响应")
                break
            if isinstance(message_chunk, AIMessage):
                await ChatMessageSendHandler.send_ai_message(client_id, message_chunk)
            elif isinstance(message_chunk, ToolMessage):
                await ChatMessageSendHandler.send_tool_message(client_id, message_chunk)
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
        """统一的响应发送方法（私有，仅供本类内部调用）"""
        base_data = {
            "type": response_type,
            "timestamp": int(time.time() * 1000),
        }
        base_data.update(kwargs)
        await websocket_manager.send_message(client_id, base_data)
        websocket_logger.debug(f"发送消息 [{response_type}] 到客户端 {client_id}")

    @staticmethod
    async def send_pong(client_id: str) -> None:
        """发送心跳响应"""
        await ChatMessageSendHandler._send_response(client_id, MessageType.PONG)

    @staticmethod
    async def send_start(client_id: str) -> None:
        """发送开始响应"""
        await ChatMessageSendHandler._send_response(client_id, MessageType.START)

    @staticmethod
    async def send_tool_message(client_id: str, message: ToolMessage) -> None:
        """处理工具消息"""
        await ChatMessageSendHandler._send_response(
            client_id,
            MessageType.TOOL_MESSAGE,
            tool_call_id=message.tool_call_id,
            content=message.content,
            tool_name=message.name,
        )
        websocket_logger.debug(f"发送工具消息: {message.name} - {message.content}")

    @staticmethod
    async def send_ai_message(
        client_id: str,
        message: AIMessage,
    ) -> None:
        """处理AI普通消息，直接渲染content"""
        chunk_content = message.content or ""
        if chunk_content:
            await ChatMessageSendHandler._send_response(
                client_id,
                MessageType.AI_MESSAGE,
                content=chunk_content,
                chunk_length=len(chunk_content),
            )

    @staticmethod
    async def send_function_call(
        client_id: str,
        function_name: str,
        args: dict,
        is_direct_feedback: bool,
        success_message: str = None,
    ) -> None:
        """处理函数调用"""
        await ChatMessageSendHandler._send_response(
            client_id,
            MessageType.FUNCTION_CALL,
            function_name=function_name,
            args=args,
            is_direct_feedback=is_direct_feedback,
            success_message=success_message,
        )
        websocket_logger.info(f"发送函数调用: {function_name} with args: {args}")

    @staticmethod
    async def send_complete(client_id: str) -> None:
        """发送完成响应"""
        await ChatMessageSendHandler._send_response(
            client_id,
            MessageType.COMPLETE,
        )
        websocket_logger.info(f"astream - 响应完成 - 总长度:")

    @staticmethod
    async def send_error(
        client_id: str,
        error_msg: str,
    ) -> None:
        """发送错误响应"""
        await ChatMessageSendHandler._send_response(
            client_id, MessageType.ERROR, message=error_msg
        )
        websocket_logger.error(f"发送错误响应: {MessageType.ERROR} - {error_msg}")
