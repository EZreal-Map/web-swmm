import json
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from utils.logger import websocket_logger
from utils.agent.graph_manager import GraphInstance
from utils.agent.websocket_manager import websocket_manager
from schemas.agent.chat import ChatRequest, ChatFeedback
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langgraph.types import Command


# 创建路由器
chatRouter = APIRouter()


class MessageType:
    """消息类型常量"""

    PING = "ping"
    PONG = "pong"
    START = "start"
    AI_MESSAGE = "AIMessage"
    HUMAN_FEEDBACK = "HumanFeedback"
    TOOL_MESSAGE = "ToolMessage"
    FUNCTION_CALL = "FunctionCall"
    COMPLETE = "complete"
    ERROR = "error"
    CHAT_ERROR = "Chat processing failed"
    STREAM_ERROR = "Stream processing failed"
    INVALID_JSON = "INVALID_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"


class ChatMessageHandler:
    """聊天消息处理器"""

    @staticmethod
    async def send_response(
        client_id: str,
        response_type: str,
        chat_request: Optional[ChatRequest] = None,
        **kwargs,
    ) -> None:
        """统一的响应发送方法"""
        base_data = {
            "type": response_type,
            "timestamp": int(time.time() * 1000),
        }

        if chat_request:
            base_data.update(
                {
                    "conversation_id": chat_request.conversation_id,
                    "user_id": chat_request.user_id,
                }
            )

        base_data.update(kwargs)
        await websocket_manager.send_message(client_id, base_data)
        websocket_logger.debug(f"发送消息 [{response_type}] 到客户端 {client_id}")

    @staticmethod
    async def send_pong(client_id: str) -> None:
        """发送心跳响应"""
        await ChatMessageHandler.send_response(client_id, MessageType.PONG)

    @staticmethod
    async def send_start(client_id: str, chat_request: ChatRequest) -> None:
        """发送开始响应"""
        await ChatMessageHandler.send_response(
            client_id, MessageType.START, chat_request, message="开始处理您的请求..."
        )

    @staticmethod
    async def handle_tool_message(
        client_id: str, message: ToolMessage, chat_request: ChatRequest
    ) -> None:
        """处理工具消息"""
        await ChatMessageHandler.send_response(
            client_id,
            MessageType.TOOL_MESSAGE,
            chat_request,
            tool_call_id=message.tool_call_id,
            content=message.content,
            tool_name=message.name,
        )
        websocket_logger.debug(f"发送工具消息: {message.name} - {message.content}")

    @staticmethod
    async def handle_ai_message(
        client_id: str,
        message: AIMessage,
        chat_request: ChatRequest,
    ) -> None:
        """处理AI普通消息，直接渲染content"""
        chunk_content = message.content or ""
        if chunk_content:
            await ChatMessageHandler.send_response(
                client_id,
                MessageType.AI_MESSAGE,
                chat_request,
                content=chunk_content,
                is_complete=False,
                chunk_length=len(chunk_content),
            )

    @staticmethod
    async def handle_human_feedback_message(
        client_id: str,
        message: AIMessage,
        chat_request: ChatRequest,
    ) -> None:
        """处理用户反馈消息，直接渲染content"""
        chunk_content = message.content or ""
        if chunk_content:
            await ChatMessageHandler.send_response(
                client_id,
                MessageType.HUMAN_FEEDBACK,
                chat_request,
                content=chunk_content,
                is_complete=False,
                chunk_length=len(chunk_content),
            )

    @staticmethod
    async def handle_function_call(
        client_id: str, function_name: str, args: dict, chat_request: ChatRequest
    ) -> None:
        """处理函数调用"""
        await ChatMessageHandler.send_response(
            client_id,
            MessageType.FUNCTION_CALL,
            chat_request,
            function_name=function_name,
            args=args,
            execution_id=f"exec_{int(time.time() * 1000)}",
        )
        websocket_logger.info(f"发送函数调用: {function_name} with args: {args}")

    @staticmethod
    async def send_completion(
        client_id: str, chat_request: ChatRequest, message: str = "complete"
    ) -> None:
        """发送完成响应"""
        await ChatMessageHandler.send_response(
            client_id,
            MessageType.COMPLETE,
            chat_request,
            message=message,
            is_complete=True,
        )
        websocket_logger.info(f"astream - 响应完成 - 总长度:")

    @staticmethod
    async def send_error(
        client_id: str,
        chat_request: Optional[ChatRequest],
        error_msg: str,
        error_type: str = MessageType.ERROR,
    ) -> None:
        """发送错误响应"""
        await ChatMessageHandler.send_response(
            client_id, error_type, chat_request, error=error_msg, message=error_msg
        )
        websocket_logger.error(f"发送错误响应: {error_type} - {error_msg}")


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
                await ChatMessageHandler.send_pong(client_id)
                return

            # 处理聊天请求
            chat_request = ChatRequest(**request_data)
            websocket_logger.info(
                f"处理聊天请求 - 用户: {chat_request.user_id}, "
                f"会话: {chat_request.conversation_id}, "
                f"反馈: {chat_request.feedback}"
            )
            await ChatProcessor.process_chat_request(client_id, chat_request)

        except json.JSONDecodeError as e:
            websocket_logger.error(f"JSON解析错误: {e}")
            await ChatMessageHandler.send_error(
                client_id,
                None,
                "请求数据格式错误，请确保发送有效的JSON数据",
                MessageType.INVALID_JSON,
            )
        except ValidationError as e:
            error_message = ChatRequest.get_user_friendly_error(e)
            websocket_logger.error(f"验证错误: {error_message}")
            await ChatMessageHandler.send_error(
                client_id, None, error_message, MessageType.VALIDATION_ERROR
            )
        except Exception as e:
            websocket_logger.error(f"处理消息异常: {e}")
            await ChatMessageHandler.send_error(
                client_id,
                None,
                "服务器处理请求时发生错误",
                MessageType.PROCESSING_ERROR,
            )


class ChatProcessor:
    """聊天处理器"""

    @staticmethod
    async def process_chat_request(client_id: str, chat_request: ChatRequest):
        """处理聊天请求"""
        try:
            # 确保Graph已初始化
            if not GraphInstance.is_initialized():
                websocket_logger.info("初始化Graph...")
                GraphInstance.init()

            graph = GraphInstance.get_graph()
            config = {
                "configurable": {
                    "thread_id": f"{chat_request.user_id}@@{chat_request.conversation_id}"
                }
            }

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
            await ChatMessageHandler.send_error(
                client_id, chat_request, str(e), MessageType.CHAT_ERROR
            )

    @staticmethod
    async def handle_normal_request(
        client_id: str, chat_request: ChatRequest, graph, config: Dict[str, Any]
    ) -> None:
        """处理普通聊天请求"""
        state = {
            "messages": [HumanMessage(content=chat_request.message)],
            "client_id": client_id,
            # "query": chat_request.message,  # 新增：保存用户问题到query字段 (可不填写，graph的第一个节点一开始会自动提取，并保存)
        }

        websocket_logger.info(f"开始处理用户消息: {chat_request.message}")
        await StreamProcessor.handle_stream_response(
            client_id, graph, state, config, chat_request
        )

    @staticmethod
    async def handle_feedback_request(
        client_id: str, chat_request: ChatRequest, graph, config: Dict[str, Any]
    ) -> None:
        """处理反馈请求（流式处理）"""
        websocket_logger.info(f"处理人类反馈: {chat_request.message}")
        try:
            feedback_state = ChatFeedback(
                success=chat_request.success, feedback_message=chat_request.message
            ).model_dump()
            human_command = Command(resume=feedback_state)
            await StreamProcessor.send_stream_graph_messages(
                client_id,
                chat_request,
                graph,
                human_command,
                config,
                ai_handler=ChatMessageHandler.handle_human_feedback_message,
                tool_handler=ChatMessageHandler.handle_tool_message,
            )
        except Exception as e:
            websocket_logger.error(f"处理反馈请求失败: {e}")
            await ChatMessageHandler.send_error(client_id, chat_request, str(e))


class StreamProcessor:
    """流式响应处理器"""

    # 流式消息处理函数
    @staticmethod
    async def handle_stream_response(
        client_id: str, graph, state: dict, config: dict, chat_request: ChatRequest
    ):
        """处理流式响应"""
        try:
            # 发送开始响应
            await ChatMessageHandler.send_start(client_id, chat_request)
            await StreamProcessor.send_stream_graph_messages(
                client_id,
                chat_request,
                graph,
                state,
                config,
                ai_handler=ChatMessageHandler.handle_ai_message,
                tool_handler=ChatMessageHandler.handle_tool_message,
            )
        except Exception as e:
            websocket_logger.error(f"流式处理异常: {e}")
            if websocket_manager.is_connected(client_id):
                await ChatMessageHandler.send_error(
                    client_id, chat_request, str(e), MessageType.STREAM_ERROR
                )

    # 通用流式消息发送函数
    @staticmethod
    async def send_stream_graph_messages(
        client_id: str,
        chat_request: ChatRequest,
        graph,
        state_or_command,
        config,
        ai_handler=ChatMessageHandler.handle_ai_message,  # ai_handler 可能发送AIMessage或者HumanFeedbackMessage
        tool_handler=ChatMessageHandler.handle_tool_message,
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
                await ai_handler(client_id, message_chunk, chat_request)
            elif isinstance(message_chunk, ToolMessage):
                await tool_handler(client_id, message_chunk, chat_request)
            else:
                websocket_logger.warning(f"未知消息类型: {type(message_chunk)}")

        # TODO: 暂时保留 astream 流式输出 complete处理，实际上它只能算作一次流式输出的结束，并不是整个对话的complete
        # 发送完成响应
        if websocket_manager.is_connected(client_id):
            await ChatMessageHandler.send_completion(client_id, chat_request)


@chatRouter.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket端点"""
    websocket_logger.info(f"WebSocket连接请求 - 客户端ID: {client_id}")

    # 接受连接并注册客户端
    await websocket_manager.connect(websocket, client_id)
    websocket_logger.info(f"客户端 {client_id} 连接成功")

    try:
        while True:
            data = await websocket.receive_text()
            await WebSocketProcessor.process_message(client_id, data)

    except WebSocketDisconnect:
        websocket_logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        websocket_logger.error(f"WebSocket连接异常: {e}")
    finally:
        websocket_manager.disconnect(client_id)
        websocket_logger.info(f"客户端 {client_id} 连接清理完成")


@chatRouter.get("/chat/health")
async def chat_health_check():
    """聊天服务健康检查"""
    return {
        "status": "healthy",
        "graph_initialized": GraphInstance.is_initialized(),
        "active_connections": websocket_manager.get_connection_count(),
        "connected_clients": len(websocket_manager.get_connected_clients()),
    }
