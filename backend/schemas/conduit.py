from fastapi import HTTPException
from pydantic import BaseModel, field_validator, model_validator
from typing import Literal, Union
import numpy as np


class ConduitResponseModel(BaseModel):
    type: str = "conduit"
    name: str
    from_node: str
    to_node: str
    length: float  # 渠道长度
    roughness: float  # 渠道粗糙度
    # 断面引用,只有在断面类型为"IRREGULAR"时才有意义
    transect: Union[str, None] = None
    shape: Literal["TRAPEZOIDAL", "IRREGULAR", "CIRCULAR"] = "TRAPEZOIDAL"  #  断面形状
    height: Union[float, None]  # 断面高度
    parameter_2: Union[float, None]  # 断面低宽
    parameter_3: Union[float, None]  # 断面左侧边坡
    parameter_4: Union[float, None]  # 断面右侧边坡

    # 响应数据的时:将 np.nan 转换为 None
    # (因为用swmm创建渠道时,断面参数会被swmm-api读取为 np.nan,避免第一次读取时出错
    # 后续空值在这个系统里面的 Conduit 和 Xsection 都是用 None 统一处理)
    @field_validator(
        "transect", "height", "parameter_2", "parameter_3", "parameter_4", mode="before"
    )
    def convert_none_or_empty_to_nan(cls, value):
        #  np.nan -> None
        # 如果是 np.nan,返回 None,避免序列化错误
        if isinstance(value, float) and np.isnan(value):
            return None
        return value


class ConduitRequestModel(BaseModel):
    type: str = "conduit"
    name: str
    from_node: str
    to_node: str
    length: float = 100  # 渠道长度
    roughness: float = 0.01  # 渠道粗糙度
    # 断面引用,只有在断面类型为"IRREGULAR"时才有意义
    transect: Union[str, None] = None
    shape: Literal["TRAPEZOIDAL", "IRREGULAR", "CIRCULAR"] = "TRAPEZOIDAL"  #  断面形状
    height: float = 10  # 断面高度
    parameter_2: float = 20  # 断面低宽
    parameter_3: float = 0.5  # 断面左侧边坡
    parameter_4: float = 0.5  # 断面右侧边坡

    # 接收数据时:将 None 转换为 np.nan 或空字符串转换为 None
    @field_validator("transect", mode="before")
    def convert_none_or_empty_to_nan(cls, value):
        # 空字符串 -> None
        if value == "":
            return None
        return value

    # 检查断面形状是否符合要求
    @model_validator(mode="before")
    def check_shape_value(cls, values):
        """检查断面形状是否符合要求"""
        if values.get("shape") == "IRREGULAR":
            if not values.get("transect"):
                raise HTTPException(
                    status_code=400,
                    detail="保存失败,断面类型为 '不规则断面' 时候,断面选择不能为空！",
                )
            values["height"] = 0
            values["parameter_2"] = 0
            values["parameter_3"] = 0
            values["parameter_4"] = 0

        if values.get("shape") != "IRREGULAR":
            # 其他形状的断面,transect 为空
            values["transect"] = None

        if values.get("shape") == "CIRCULAR":
            # 圆形断面,参数2、3、4 为空
            values["parameter_2"] = 0
            values["parameter_3"] = 0
            values["parameter_4"] = 0
            if not values.get("height"):
                raise HTTPException(
                    status_code=400,
                    detail="保存失败,圆形断面时,断面高度不能为空或0！",
                )

        if values.get("shape") == "TRAPEZOIDAL":
            # 梯形断面,参数2、3、4 不能为空
            if not (
                values.get("height")
                and values.get("parameter_2")
                and values.get("parameter_3")
                and values.get("parameter_4")
            ):
                raise HTTPException(
                    status_code=400,
                    detail="保存失败,梯形断面时,断面高度、断面低宽、左侧边坡、右侧边坡不能有空或0！",
                )
        return values

    # 检测数值类型和正数
    @field_validator(
        "length",
        "roughness",
        "height",
        "parameter_2",
        "parameter_3",
        "parameter_4",
        mode="before",
    )
    def check_positive(cls, value, info):
        # field_name 的别名
        if info.field_name == "length":
            field_name_alias = "长度"
        elif info.field_name == "roughness":
            field_name_alias = "粗糙度"
        elif info.field_name == "height":
            field_name_alias = "断面高度"
        elif info.field_name == "parameter_2":
            field_name_alias = "断面底宽"
        elif info.field_name == "parameter_3":
            field_name_alias = "左侧边坡"
        elif info.field_name == "parameter_4":
            field_name_alias = "右侧边坡"
        else:
            field_name_alias = info.field_name

        # 这里检测数值类型和正数,主要只是检查 length 和 roughness,并且结构化报错,其实不用检查,也会被 float 检查
        if not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_alias  } 必须是数值类型",
            )
        if value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_alias } 必须是非负数",
            )
        return value

    @field_validator("name", mode="before")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise HTTPException(
                status_code=400,
                detail="渠道名称不能为空",
            )
        return v
