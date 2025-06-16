from pydantic import BaseModel, root_validator, field_validator
from datetime import datetime
from fastapi import HTTPException


class TimeSeriesModel(BaseModel):
    name: str
    data: list[tuple[datetime, float]]

    # 定义根验证器，确保data字段为空时设置为默认值
    @root_validator(pre=True)
    def set_default_data(cls, values):
        data = values.get("data")
        if not data:  # 如果data为空，包括None、""、[]等
            default_time = datetime.now()
            values["data"] = [(default_time, 10.0)]  # 设置默认数据
        return values

    @field_validator(
        "name",
        mode="before",
    )
    def check_none(cls, value):
        if not value:
            raise HTTPException(
                status_code=400,
                detail="时间序列名称不能为空",
            )
        return value
