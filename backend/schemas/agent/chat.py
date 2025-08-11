import uuid
from pydantic import BaseModel, Field, field_validator, ValidationError


# TODO:没有用到，可以在graph更加规范的使用
class ChatMessage(BaseModel):
    """聊天消息模型"""

    role: str = Field(..., description="消息角色: user 或 assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求模型"""

    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    conversation_id: str = Field(..., description="对话ID，用于多轮对话")
    user_id: str = Field(default="default_user", description="用户ID")
    feedback: bool = Field(default=False, description="用户反馈，可选")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        """验证消息内容"""
        if not v.strip():
            raise ValueError("消息内容不能为空")
        return v.strip()

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v):
        """验证会话ID格式"""
        if not v or not v.strip():
            raise ValueError("会话ID不能为空")
        # 验证会话ID格式（可以是 conv-xxx 或 temp-xxx 格式）
        if not (v.startswith("conv-") or v.startswith("temp-")):
            raise ValueError("会话ID格式无效，必须以 'conv-' 或 'temp-' 开头")
        return v.strip()

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """验证用户ID格式"""
        if not v or not v.strip():
            raise ValueError("用户ID不能为空")
        # 简单的用户ID格式验证
        if len(v.strip()) < 3:
            raise ValueError("用户ID长度至少为3个字符")
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
            "conversation_id": "会话ID无效",
            "user_id": "用户ID无效",
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
