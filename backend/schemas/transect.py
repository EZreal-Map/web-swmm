from pydantic import BaseModel, field_validator
from typing import Optional
from fastapi import HTTPException


class TransectModel(BaseModel):
    type: str = "transect"
    name: str
    roughness_left: float = 0.1
    roughness_right: float = 0.1
    roughness_channel: float = 0.1
    bank_station_left: int = 0
    bank_station_right: int = 0
    station_elevations: list[list[float, float]] = []
    # from_node: Optional[str] = None
    # to_node: Optional[str] = None

    @field_validator("station_elevations", mode="before")
    def validate_station_elevations(cls, values):
        if not isinstance(values, list):
            raise ValueError("station_elevations 必须是列表")

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
