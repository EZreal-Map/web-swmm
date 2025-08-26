from pydantic import BaseModel, model_validator, field_validator
from pydantic.fields import FieldInfo
from typing import Literal, Union
from fastapi import HTTPException
import numpy as np


class OutfallModel(BaseModel):
    type: str = "outfall"
    name: str
    lon: float
    lat: float
    elevation: float = 0.0
    kind: Literal["FREE", "NORMAL", "FIXED"] = "FREE"  # 简化了 TIDAL TIMESERIES 出流
    # 仅在 kind 为 FIXED 时有效,才有一个水位值,否则都是np.nan
    data: Union[float, None] = None  # 水位值,默认是 None
    # route_to # 简化处理,默认出口不再继续指向下一个节点,出口为整个计算的终点

    @model_validator(mode="before")
    def handle_fieldinfo_all(cls, values):
        # 把所有 FieldInfo 替换为 default
        for k, v in values.items():
            if isinstance(v, FieldInfo):
                values[k] = v.default
        return values

    @model_validator(mode="before")
    def check_data_required_for_FIXED(cls, values):
        # 如果 kind 为 FIXED,data 不能为空
        if values.get("kind") == "FIXED" and not values.get("data"):
            raise HTTPException(
                status_code=400,
                detail="出口类型为固定水位时,必须提供出口水位值",
            )
        return values

    @field_validator("name", mode="before")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise HTTPException(
                status_code=400,
                detail="出口名称不能为空",
            )
        return v

    @field_validator(
        "lon",
        "lat",
        "elevation",
        mode="before",
    )
    def check_positive(cls, value, info):
        # field_name 的别名
        if info.field_name == "lon":
            field_name_alias = "经度"
        elif info.field_name == "lat":
            field_name_alias = "纬度"
        elif info.field_name == "elevation":
            field_name_alias = "高程"
        else:
            field_name_alias = info.field_name

        # 这里检测数值类型和正数,主要只是检查 length 和 roughness,并且结构化报错,其实不用检查,也会被 float 检查
        if not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_alias} 必须是数字",
            )
        if value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_alias} 必须是非负数",
            )
        return value
