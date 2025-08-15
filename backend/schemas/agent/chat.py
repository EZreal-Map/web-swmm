import uuid
from pydantic import BaseModel, Field, field_validator, ValidationError
from enum import Enum


# 前端请求消息类型
class RequestMessageType(str, Enum):
    """请求消息类型常量"""

    PING = "ping"
    CHAT = "chat"
    FEEDBACK = "feedback"


# 后端响应消息类型
class ResponseMessageType(str, Enum):
    """响应消息类型常量"""

    PONG = "pong"
    START = "start"
    AI_MESSAGE = "AIMessage"
    TOOL_MESSAGE = "ToolMessage"
    FUNCTION_CALL = "FunctionCall"
    COMPLETE = "complete"
    ERROR = "error"


class ChatRequest(BaseModel):
    """聊天请求模型"""

    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    type: RequestMessageType = Field(
        default=RequestMessageType.CHAT, description="请求类型"
    )
    success: bool = Field(
        default=True,
        description="用于HIL反馈函数执行成功与否,当type为RequestMessageType.FEEDBACK时有效,其余默认为True",
    )

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
        # 获取所有请求类型的字符串表示
        type_choices = ", ".join([e.value for e in RequestMessageType])
        error_messages = {
            "message": "消息内容不能为空或过长(最多10000字符)",
            "type": f"请求类型非法(只能为 {type_choices})",
        }

        # 获取第一个错误的字段名
        for error in validation_error.errors():
            field = error["loc"][-1] if error["loc"] else "unknown"
            if field in error_messages:
                return error_messages[field]

        # 默认错误信息
        return "请求参数有误"


class ChatFeedbackRequest(BaseModel):
    """反馈请求模型"""

    success: bool = Field(default=True, description="反馈是否成功")
    feedback_message: str = Field(..., description="用户反馈消息")


# TODO:没有用到,可以在graph更加规范的使用
# class ChatResponse(BaseModel):
#     """聊天响应模型"""

#     id: str = Field(default_factory=lambda: f"chat-{uuid.uuid4().hex}")
#     message: str = Field(..., description="回复内容")
#     conversation_id: str = Field(..., description="对话ID")
#     user_id: str = Field(..., description="用户ID")
#     is_complete: bool = Field(default=False, description="响应是否完整")
