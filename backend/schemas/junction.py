from pydantic import BaseModel, field_validator, model_validator, Field
from pydantic.fields import FieldInfo
from fastapi import HTTPException


class JunctionModel(BaseModel):
    type: str = "junction"
    name: str = Field(description="节点名称")
    lon: float = Field(description="经度")
    lat: float = Field(description="纬度")
    elevation: float = Field(default=0.0, description="高程")
    depth_init: float = Field(default=0.0, description="初始水深")
    depth_max: float = Field(default=9999.0, description="最大水深")
    depth_surcharge: float = Field(default=9999.0, description="超额水深")
    area_ponded: float = Field(default=0.0, description="积水面积")
    has_inflow: bool = Field(default=False, description="是否有入流")
    timeseries_name: str = Field(default="", description="入流时间序列")


    @model_validator(mode="before")
    def handle_fieldinfo_all(cls, values):
        # 把所有 FieldInfo 替换为 default
        for k, v in values.items():
            if isinstance(v, FieldInfo):
                values[k] = v.default
        return values

    @field_validator("name", mode="before")
    def name_must_not_be_empty(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise HTTPException(
                status_code=400,
                detail="节点名称不能为空",
            )
        return v

    @field_validator("lon", mode="before")
    def check_longitude(cls, value):
        if not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail="经度必须是数值类型")
        if not -180 <= value <= 180:
            raise HTTPException(status_code=400, detail="经度必须在 -180 到 180 之间")
        return value

    @field_validator("lat", mode="before")
    def check_latitude(cls, value):
        if not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail="纬度必须是数值类型")
        if not -90 <= value <= 90:
            raise HTTPException(status_code=400, detail="纬度必须在 -90 到 90 之间")
        return value

    @field_validator(
        "elevation",
        "depth_max",
        "depth_init",
        "depth_surcharge",
        "area_ponded",
        mode="before",
    )
    def check_positive(cls, value, info):
        alias_map = {
            "elevation": "高程",
            "depth_max": "最大水深",
            "depth_init": "初始水深",
            "depth_surcharge": "超额水深",
            "area_ponded": "积水面积",
        }
        field_name_alias = alias_map.get(info.field_name, info.field_name)

        if not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_alias} 必须是数值类型",
            )
        if value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name_alias} 必须是非负数",
            )
        return value

    @model_validator(mode="before")
    def check_timeseries_name(cls, values):
        if values.get("has_inflow") and not values.get("timeseries_name"):
            raise HTTPException(
                status_code=400,
                detail="节点有入流时,必须提供入流时间序列名称",
            )
        return values
