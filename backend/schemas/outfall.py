from pydantic import BaseModel, model_validator
from typing import Literal, Union
import numpy as np


class OutfallModel(BaseModel):
    type: str = "outfall"
    name: str
    lon: float
    lat: float
    elevation: float = 0.0
    kind: Literal["FREE", "NORMAL", "FIXED"] = "FREE"  # 简化了 TIDAL TIMESERIES 出流
    # 仅在 kind 为 FIXED 时有效，才有一个水位值，否则都是np.nan
    data: Union[float, None] = None  # 水位值，默认是 None
    # route_to # 简化处理，默认出口不再继续指向下一个节点，出口为整个计算的终点

    @model_validator(mode="after")
    def check_data_required_for_FIXED(cls, values):
        """当 shape 为 IRREGULAR 时，transect 不能为空"""
        if values.kind == "FIXED" and (values.data is None or values.data is np.nan):
            values.data = 0.0
        return values
