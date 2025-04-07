from pydantic import BaseModel, field_validator
from fastapi import HTTPException

# TODO: 完成 提取断面功能，前端界面点击2个点，获取2个点之间的断面高程过程线（已完成，下次提交删除）
# TODO：校验问题，可以前端加入校验（使用表达rules），也可以后端加入校验（已校验，但是错误信息不友好） 这里包括除渠道弹窗以外的（节点，出口，不规则断面） （已完成，已在后端校验，并且返回友好的错误信息）
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
