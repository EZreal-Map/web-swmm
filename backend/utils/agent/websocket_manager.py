import json
from typing import Dict, Any
from fastapi import WebSocket
from utils.logger import websocket_logger


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
