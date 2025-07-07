from pydantic import BaseModel, root_validator, field_validator
from datetime import datetime
from fastapi import HTTPException
from enum import Enum
from utils.swmm_constant import RAINGAGE_DEFAULT_INTERVAL


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

    # 根据 data 判断获取等间隔时间（如不是等间隔使用默认值 1:00），用作raingage的interval使用
    def get_interval(self, default=RAINGAGE_DEFAULT_INTERVAL) -> str:
        """
        根据 data 判断是否为等间隔。如果是，返回实际间隔（hh:mm格式），否则返回默认值。
        """
        if len(self.data) < 2:
            return default

        intervals = {
            (self.data[i + 1][0] - self.data[i][0]).total_seconds()
            for i in range(len(self.data) - 1)
        }

        if len(intervals) == 1:
            total_seconds = intervals.pop()
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            return f"{int(hours)}:{int(minutes):02d}"
        else:
            return default


class TimeSeriesTypeModel(str, Enum):
    INFLOW = "INFLOW"
    RAINGAGE = "RAINGAGE"


TIMESERIES_PREFIXES_MAP = {item.value: f"{item.value}_" for item in TimeSeriesTypeModel}
