from pydantic import BaseModel
from datetime import datetime, time
from typing import Literal


class CalculateModel(BaseModel):
    flow_units: Literal["CFS", "GPM", "MGD", "CMS", "LPS", "MLD"] = (
        "CMS"  # 流量单位  (默认是 CMS,不用传这个字段)
    )
    start_datetime: datetime  # 开始时间
    end_datetime: datetime  # 结束时间
    report_step: time  # 时间步长 (格式:hr:min:sec)默认是 00:15:00
    flow_routing: Literal["STEADY", "KINWAVE", "DYNWAVE"] = "KINWAVE"  # 流量计算方法
