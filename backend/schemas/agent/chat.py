import uuid
from pydantic import BaseModel, Field, field_validator, ValidationError


class ChatRequest(BaseModel):
    """聊天请求模型"""

    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    feedback: bool = Field(default=False, description="用户反馈，可选")
    success: bool = Field(default=True, description="用于HIL反馈函数执行成功与否")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        """验证消息内容"""
        if not v.strip():
            raise ValueError("消息内容不能为空")
        return v.strip()

    @staticmethod
    def get_user_friendly_error(validation_error: ValidationError) -> str:
        """
        将 Pydantic 验证错误转换为用户友好的错误信息

        Args:
            validation_error: Pydantic ValidationError 实例

        Returns:
            用户友好的错误信息字符串
        """
        # 错误信息映射
        error_messages = {
            "message": "消息内容不能为空或过长（最多10000字符）",
        }

        # 获取第一个错误的字段名
        for error in validation_error.errors():
            field = error["loc"][-1] if error["loc"] else "unknown"
            if field in error_messages:
                return error_messages[field]

        # 默认错误信息
        return "请求参数有误"


# TODO:没有用到，可以在graph更加规范的使用
class ChatResponse(BaseModel):
    """聊天响应模型"""

    id: str = Field(default_factory=lambda: f"chat-{uuid.uuid4().hex}")
    message: str = Field(..., description="回复内容")
    conversation_id: str = Field(..., description="对话ID")
    user_id: str = Field(..., description="用户ID")
    is_complete: bool = Field(default=False, description="响应是否完整")


class ChatFeedback(BaseModel):
    success: bool = Field(default=True, description="反馈是否成功")
    feedback_message: str = Field(..., description="用户反馈消息")


class MessageType:
    """消息类型常量"""

    PING = "ping"
    PONG = "pong"
    START = "start"
    AI_MESSAGE = "AIMessage"
    TOOL_MESSAGE = "ToolMessage"
    FUNCTION_CALL = "FunctionCall"
    COMPLETE = "complete"
    ERROR = "error"
