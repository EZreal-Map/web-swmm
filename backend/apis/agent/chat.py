from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from utils.agent.graph_manager import GraphInstance
from utils.agent.websocket_manager import websocket_manager, WebSocketProcessor
from utils.logger import websocket_logger
from utils.agent.llm_manager import get_available_models, create_openai_llm, LLMRegistry
from schemas.result import Result

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
    data = {
        "status": "healthy",
        "active_connections": websocket_manager.get_connection_count(),
        "connected_clients": len(websocket_manager.get_connected_clients()),
    }
    return Result.success_result(data=data)


class SetModelRequest(BaseModel):
    model: str


@chatRouter.get("/chat/models")
async def get_chat_models():
    """获取可用的模型列表"""
    selected_model = LLMRegistry.get_selected_model_name()
    models = get_available_models()

    data = {"selected_model": selected_model, "models": models}
    return Result.success_result(data=data)


@chatRouter.put("/chat/model")
async def set_chat_model(req: SetModelRequest):
    """设置当前使用的模型并重建 LLM 实例"""

    models = get_available_models()
    if req.model not in models:
        raise HTTPException(status_code=400, detail=f"不支持的模型: {req.model}")

    llm = create_openai_llm(model=req.model)
    LLMRegistry.clear()
    LLMRegistry.register("llm", llm)
    return Result.success_result(message=f"模型已切换为 {req.model}")
