from fastapi import APIRouter
from pydantic import BaseModel
from schemas.result import Result

# 岷江项目,与此项目无关
mjRouter = APIRouter()


class ShortTermInput(BaseModel):
    start_time: str
    end_time: str
    station_name: str


# 这个接口与此 web-swmm 项目无关
@mjRouter.post(
    "/short_term_calculate",
    summary="岷江项目短期计算按钮",
    description="岷江项目短期计算按钮",
)
async def short_term_calculate(short_term_input: ShortTermInput):
    print("start_time:", short_term_input.start_time)
    print("end_time:", short_term_input.end_time)
    print("station_name:", short_term_input.station_name)
    # 查询数据库，获取对应的计算结果
    # 1. 查询实测数据库
    real_data = [
        ["2023-10-01 08:00", 120],
        ["2023-10-01 09:00", 120],
        ["2023-10-01 10:00", 123.5],
        ["2023-10-01 11:00", 200],
        ["2023-10-01 12:00", 210],
        ["2023-10-01 13:00", 400.8],
    ]
    # 2. 查询预测数据库
    # （这里预测数据时间长度，要包括实测数据时间长度，因为前端x轴是以预测长度为准的）
    forecast_data = [
        ["2023-10-01 08:00", 100],
        ["2023-10-01 09:00", 130],
        ["2023-10-01 10:00", 120],
        ["2023-10-01 11:00", 160],
        ["2023-10-01 12:00", 200],
        ["2023-10-01 13:00", 500],
        ["2023-10-01 14:00", 300],
        ["2023-10-01 15:00", 100],
        ["2023-10-01 16:00", 152.8],
    ]
    return Result.success(
        data={
            "real_data": real_data,
            "forecast_data": forecast_data,
        },
        message="短期计算成功",
    )
