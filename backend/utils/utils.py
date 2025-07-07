from functools import wraps
from fastapi import HTTPException
from schemas.timeseries import TIMESERIES_PREFIXES_MAP


def with_exception_handler(default_message="操作失败，发生未知错误"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                print(f"Exception in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=getattr(e, "status_code", 500),
                    detail=getattr(e, "detail", default_message),
                )

        return wrapper

    return decorator


def remove_timeseries_prefix(name: str, custom_prefix: str = None) -> str:
    """
    从 name 中移除指定或已知的时间序列前缀。

    参数：
    - name: 原始名称字符串
    - custom_prefix: 自定义前缀（优先使用），如果为 None，则使用已知的时间序列前缀集合 TIMESERIES_PREFIXES_MAP

    返回：
    - 移除前缀后的字符串
    """
    if custom_prefix:
        if name.startswith(custom_prefix):
            return name[len(custom_prefix) :]
        raise ValueError(f"名称 [ {name} ] 不符合自定义前缀 [ {custom_prefix} ] 的格式")

    for prefix in TIMESERIES_PREFIXES_MAP.values():
        if name.startswith(prefix):
            return name[len(prefix) :]

    return name
