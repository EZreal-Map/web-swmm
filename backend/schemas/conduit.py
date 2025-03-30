from pydantic import BaseModel, field_validator, model_validator
from typing import Literal, Union
import numpy as np


class ConduitResponseModel(BaseModel):
    type: str = "conduit"
    name: str
    from_node: str
    to_node: str
    length: float  # 管道长度
    roughness: float  # 管道粗糙度
    # 断面引用，只有在断面类型为"IRREGULAR"时才有意义
    transect: Union[str, float, None] = None
    shape: Literal["TRAPEZOIDAL", "IRREGULAR", "CIRCULAR"] = "TRAPEZOIDAL"  #  断面形状
    height: Union[float, str]  # 断面高度
    parameter_2: Union[float, str]  # 断面低宽
    parameter_3: Union[float, str]  # 断面左侧边坡
    parameter_4: Union[float, str]  # 断面右侧边坡

    # 接收数据时：将 None 转换为 np.nan 或空字符串转换为 None
    @field_validator("transect", mode="before")
    def convert_none_or_empty_to_nan(cls, value):
        #  np.nan -> None
        # 如果是 np.nan，返回 None，避免序列化错误
        if isinstance(value, float) and np.isnan(value):
            print(f"is np.nan, converting to None")
            return None
        return value

    @field_validator(
        "height", "parameter_2", "parameter_3", "parameter_4", mode="before"
    )
    def convert_none_or_empty_to_blank_string(cls, value):
        #  np.nan -> None
        # 如果是 np.nan，返回 None，避免序列化错误
        if isinstance(value, float) and np.isnan(value):
            return ""
        return value


class ConduitRequestModel(BaseModel):
    type: str = "conduit"
    name: str
    from_node: str
    to_node: str
    length: float = 100  # 管道长度
    roughness: float = 0.01  # 管道粗糙度
    # 断面引用，只有在断面类型为"IRREGULAR"时才有意义
    transect: Union[str, float, None] = None
    shape: Literal["TRAPEZOIDAL", "IRREGULAR", "CIRCULAR"] = "TRAPEZOIDAL"  #  断面形状
    height: float = 10  # 断面高度
    parameter_2: float = 20  # 断面低宽
    parameter_3: float = 0.5  # 断面左侧边坡
    parameter_4: float = 0.5  # 断面右侧边坡

    # 接收数据时：将 None 转换为 np.nan 或空字符串转换为 None
    @field_validator("transect", mode="before")
    def convert_none_or_empty_to_nan(cls, value):
        # 处理 None 或空字符串 -> np.nan
        if value is None or value == "":
            # TODO: 调试功能无误之后，删除一些不必要的打印
            print(f"is None or empty, converting to np.nan")
            return np.nan
        return value

    @model_validator(mode="after")
    def check_transect_required_for_irregular(cls, values):
        """当 shape 为 IRREGULAR 时，transect 不能为空"""
        if values.shape == "IRREGULAR" and (
            values.transect is None or values.transect is np.nan
        ):
            raise ValueError("当 shape 为 'IRREGULAR' 时，transect 不能为空！")
        return values
