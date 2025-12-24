from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.agent.graph_manager import GraphInstance
from utils.agent.websocket_manager import websocket_manager, WebSocketProcessor
from utils.logger import websocket_logger

# 创建路由器
chatRouter = APIRouter()


@chatRouter.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket端点"""
    # 接受连接并注册客户端
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await WebSocketProcessor.process_message(client_id, data)

    except WebSocketDisconnect:
        websocket_logger.info(f"WebSocket连接正常断开: {client_id}")
    except Exception as e:
        websocket_logger.error(f"WebSocket连接异常断开: {client_id},错误信息: {e}")
    finally:
        websocket_manager.disconnect(client_id)


@chatRouter.get("/chat/health")
async def chat_health_check():
    """聊天服务健康检查"""
    return {
        "status": "healthy",
        "active_connections": websocket_manager.get_connection_count(),
        "connected_clients": len(websocket_manager.get_connected_clients()),
    }
