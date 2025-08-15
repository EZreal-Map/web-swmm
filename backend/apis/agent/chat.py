from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.agent.graph_manager import GraphInstance
from utils.agent.websocket_manager import websocket_manager, WebSocketProcessor
from utils.logger import websocket_logger

# 创建路由器
chatRouter = APIRouter()


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
