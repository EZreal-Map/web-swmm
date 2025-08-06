import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from utils.logger import websocket_logger
from utils.agent.graph_manager import graph_instance
from utils.agent.websocket_manager import websocket_manager
from schemas.agent.chat import ChatRequest


# 创建路由器
chatRouter = APIRouter()


@chatRouter.websocket("/ws/chat/{client_id}")
async def websocket_chat(websocket: WebSocket, client_id: str):
    """WebSocket聊天端点"""
    await websocket_manager.connect(websocket, client_id)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            websocket_logger.info(f"收到来自 {client_id} 的消息: {data}")

            try:
                # 解析请求数据
                request_data = json.loads(data)

                # 处理 ping 请求
                if request_data.get("type") == "ping":
                    await websocket_manager.send_message(
                        client_id,
                        {
                            "type": "pong",
                        },
                    )
                    continue

                chat_request = ChatRequest(**request_data)

                # 记录请求信息（不记录敏感消息内容）
                websocket_logger.info(
                    f"处理会话请求 - 用户: {chat_request.user_id}, 会话: {chat_request.conversation_id}"
                )

                # 处理聊天请求
                await process_chat_request(client_id, chat_request)

            except json.JSONDecodeError as e:
                websocket_logger.error(f"JSON解析错误: {e}")
                await websocket_manager.send_message(
                    client_id,
                    {
                        "error": "INVALID_JSON",
                        "message": "请求数据格式错误，请确保发送有效的JSON数据",
                    },
                )
            except ValidationError as e:
                websocket_logger.error(f"数据验证错误: {e}")

                # 使用模型中定义的用户友好错误信息
                error_message = ChatRequest.get_user_friendly_error(e)

                await websocket_manager.send_message(
                    client_id,
                    {
                        "error": "VALIDATION_ERROR",
                        "message": error_message,
                    },
                )
            except Exception as e:
                websocket_logger.error(f"处理消息时出错: {e}")
                await websocket_manager.send_message(
                    client_id,
                    {
                        "error": "PROCESSING_ERROR",
                        "message": "服务器处理请求时发生错误",
                    },
                )

    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
    except Exception as e:
        websocket_logger.error(f"WebSocket错误: {e}")
        websocket_manager.disconnect(client_id)


async def process_chat_request(client_id: str, chat_request: ChatRequest):
    """处理聊天请求"""
    try:
        # 确保Graph已初始化
        if not graph_instance.is_initialized():
            websocket_logger.info("初始化Graph...")
            graph_instance.create_graph()

        graph = graph_instance.get_graph()

        # 配置对话上下文
        config = {
            "configurable": {
                "thread_id": f"{chat_request.user_id}@@{chat_request.conversation_id}"
            }
        }

        # 构建消息
        messages = [{"role": "user", "content": chat_request.message}]

        websocket_logger.info(f"开始处理用户消息: {chat_request.message}")
        websocket_logger.info(f"对话配置: {config}")

        # 流式响应
        await handle_stream_response(client_id, graph, messages, config, chat_request)

    except Exception as e:
        websocket_logger.error(f"处理聊天请求失败: {e}")
        await websocket_manager.send_message(
            client_id,
            {
                "error": "Chat processing failed",
                "message": str(e),
                "conversation_id": chat_request.conversation_id,
                "user_id": chat_request.user_id,
            },
        )


async def handle_stream_response(
    client_id: str, graph, messages: list, config: dict, chat_request: ChatRequest
):
    """处理流式响应"""
    try:
        response_id = f"chat-{uuid.uuid4().hex}"
        accumulated_content = ""

        # 发送开始响应
        await websocket_manager.send_message(
            client_id,
            {
                "id": response_id,
                "type": "start",
                "conversation_id": chat_request.conversation_id,
                "user_id": chat_request.user_id,
            },
        )

        # 流式处理
        try:
            async for message_chunk, metadata in graph.astream(
                {"messages": messages}, config, stream_mode="messages"
            ):
                # 检查连接是否还活跃
                if not websocket_manager.is_connected(client_id):
                    websocket_logger.info(f"客户端 {client_id} 已断开，停止流式响应")
                    break

                if hasattr(message_chunk, "content") and message_chunk.content:
                    chunk_content = message_chunk.content
                    accumulated_content += chunk_content

                    # 发送流式数据块
                    await websocket_manager.send_message(
                        client_id,
                        {
                            "id": response_id,
                            "type": "chunk",
                            "content": chunk_content,
                            "accumulated_content": accumulated_content,
                            "conversation_id": chat_request.conversation_id,
                            "user_id": chat_request.user_id,
                            "is_complete": False,
                        },
                    )

                    websocket_logger.debug(f"发送流式块: {chunk_content}")

            # 发送完成响应（仅在连接仍活跃时）
            if websocket_manager.is_connected(client_id):
                await websocket_manager.send_message(
                    client_id,
                    {
                        "id": response_id,
                        "type": "complete",
                        "message": accumulated_content,
                        "conversation_id": chat_request.conversation_id,
                        "user_id": chat_request.user_id,
                        "is_complete": True,
                    },
                )

            websocket_logger.info(f"流式响应完成，总长度: {len(accumulated_content)}")

        except Exception as stream_error:
            websocket_logger.error(f"流式处理过程中出错: {stream_error}")
            # 发送错误信息（仅在连接仍活跃时）
            if websocket_manager.is_connected(client_id):
                await websocket_manager.send_message(
                    client_id,
                    {
                        "id": response_id,
                        "type": "error",
                        "error": "Stream processing failed",
                        "message": str(stream_error),
                        "conversation_id": chat_request.conversation_id,
                        "user_id": chat_request.user_id,
                    },
                )

    except Exception as e:
        websocket_logger.error(f"流式响应处理失败: {e}")
        await websocket_manager.send_message(
            client_id,
            {
                "error": "Stream response failed",
                "message": str(e),
                "conversation_id": chat_request.conversation_id,
                "user_id": chat_request.user_id,
            },
        )


@chatRouter.get("/chat/health")
async def chat_health_check():
    """聊天服务健康检查"""
    return {
        "status": "healthy",
        "graph_initialized": graph_instance.is_initialized(),
        "active_connections": websocket_manager.get_connection_count(),
        "connected_clients": len(websocket_manager.get_connected_clients()),
    }
