from pydantic import BaseModel, field_validator
from fastapi import HTTPException


class TransectModel(BaseModel):
    name: str
    roughness_left: float = 0.1
    roughness_right: float = 0.1
    roughness_channel: float = 0.1
    bank_station_left: float = 0
    bank_station_right: float = 0
    station_elevations: list[list[float, float]] = []
    # from_node: Optional[str] = None
    # to_node: Optional[str] = None

    @field_validator("station_elevations", mode="before")
    def validate_station_elevations(cls, values):
        if not isinstance(values, list):
            raise HTTPException(
                status_code=400,
                detail="断面高程数据格式错误，必须是列表",
            )

        # 过滤掉 None 和负值，并按 X 坐标升序排序
        filtered_sorted = sorted(
            (
                pair
                for pair in values
                if pair[0] is not None
                and pair[1] is not None
                and pair[0] >= 0
                and pair[1] >= 0
            ),
            key=lambda x: x[1],
        )

        if len(filtered_sorted) != len(values):
            raise HTTPException(
                status_code=400,
                detail="坐标中存在无效的值，必须是非负数",
            )

        return filtered_sorted

    # 检测数值类型和正数
    @field_validator(
        "roughness_left",
        "roughness_right",
        "roughness_channel",
        "bank_station_left",
        "bank_station_right",
        mode="before",
    )
    def check_positive(cls, value, info):
        # field_name 的别名
        if info.field_name == "roughness_left":
            field_name_alias = "左岸糙率"
        elif info.field_name == "roughness_right":
            field_name_alias = "右岸糙率"
        elif info.field_name == "roughness_channel":
            field_name_alias = "渠道糙率"
        elif info.field_name == "bank_station_left":
            field_name_alias = "左岸编号"
        elif info.field_name == "bank_station_right":
            field_name_alias = "右岸编号"
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
