from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int
    message: str
    data: Optional[T] = None

    # 增加类似于字典的get方法
    def get(self, key: str, default=None):
        # 如果是字段名,就返回对应值,否则返回默认值
        return getattr(self, key, default)

    @staticmethod
    def success(data: Optional[T] = None, message: str = "成功") -> "Result[T]":
        return Result(code=200, message=message, data=data)

    @staticmethod
    def error(
        code: int = 500, message: str = "发生错误", data: Optional[T] = None
    ) -> "Result[T]":
        return Result(code=code, message=message, data=data)

    @staticmethod
    def not_found(message: str = "资源未找到") -> "Result[T]":
        return Result(code=404, message=message)

    @staticmethod
    def bad_request(message: str = "请求参数错误") -> "Result[T]":
        return Result(code=400, message=message)

    @staticmethod
    def unauthorized(message: str = "未授权") -> "Result[T]":
        return Result(code=401, message=message)
