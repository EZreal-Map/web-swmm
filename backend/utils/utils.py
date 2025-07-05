from functools import wraps
from fastapi import HTTPException


def with_exception_handler(default_message="操作失败，发生未知错误"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise HTTPException(
                    status_code=getattr(e, "status_code", 500),
                    detail=getattr(e, "detail", default_message),
                )

        return wrapper

    return decorator
