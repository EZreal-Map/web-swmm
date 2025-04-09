from pydantic import BaseModel, field_validator, model_validator
from fastapi import HTTPException

# TODO：理解一下 swmm 计算逻辑，一些节点参数的选择（比如：节点的最大深度，初始深度，溢流深度，蓄水面积），还有没有涉及的功能，是否需要添加此次任务（河道径流模拟）中


class JunctionModel(BaseModel):
    type: str = "junction"
    name: str
    lon: float
    lat: float
    elevation: float = 0.0
    depth_max: float = 0.0
    depth_init: float = 0.0
    depth_surcharge: float = 0.0
    area_ponded: float = 0.0
    has_inflow: bool = False  # 是否有入流
    timeseries_name: str = ""  # 入流时间序列名称

    @field_validator("name", mode="before")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise HTTPException(
                status_code=400,
                detail="节点名称不能为空",
            )
        return v

    # 检测数值类型和正数
    @field_validator(
        "lon",
        "lat",
        "elevation",
        "depth_max",
        "depth_init",
        "depth_surcharge",
        "area_ponded",
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
        elif info.field_name == "depth_max":
            field_name_alias = "最大水深"
        elif info.field_name == "depth_init":
            field_name_alias = "初始水深"
        elif info.field_name == "depth_surcharge":
            field_name_alias = "超额水深"
        elif info.field_name == "area_ponded":
            field_name_alias = "积水面积"
        else:
            field_name_alias = info.field_name

        # 这里检测数值类型和正数，主要只是检查 length 和 roughness，并且结构化报错，其实不用检查，也会被 float 检查
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

    @model_validator(mode="before")
    def check_timeseries_name(cls, values):
        # 如果 has_inflow 为 True，timeseries_name 不能为空
        if values.get("has_inflow") and not values.get("timeseries_name"):
            raise HTTPException(
                status_code=400,
                detail="节点有入流时，必须提供入流时间序列名称",
            )
        return values
