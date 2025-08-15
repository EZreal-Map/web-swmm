from fastapi import APIRouter, HTTPException, Query
from swmm_api import SwmmInput
from swmm_api.input_file.sections.others import TimeseriesData
from swmm_api.input_file.sections.node_component import Inflow
from schemas.timeseries import (
    TimeSeriesModel,
    TimeSeriesTypeModel,
    TIMESERIES_PREFIXES_MAP,
)
from schemas.result import Result
from datetime import datetime
from utils.swmm_constant import SWMM_FILE_INP_PATH, ENCODING
from utils.utils import with_exception_handler, remove_timeseries_prefix
from typing import Annotated
from apis.raingage import create_raingage, delete_raingage, update_raingage
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger("timeseries")

timeseriesRouter = APIRouter()


# 获取所有时间序列信息的name集合
@timeseriesRouter.get(
    "/timeseries/name",
    summary="获取所有时间序列的名称列表(不包含数据)",
    description="获取所有时间序列的名称列表集合(不包含数据)",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_timeseries_names(
    type: Annotated[
        TimeSeriesTypeModel,
        Query(description="时间序列类型,必须是 INFLOW 或 RAINGAGE"),
    ] = TimeSeriesTypeModel.INFLOW,
):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_timeseries = INP.check_for_section(TimeseriesData)
    timeseries_names = list(inp_timeseries.keys())
    # 筛选出符合前缀的,并移除前缀
    filtered_names = [
        remove_timeseries_prefix(name, custom_prefix=TIMESERIES_PREFIXES_MAP[type])
        for name in timeseries_names
        if name.startswith(TIMESERIES_PREFIXES_MAP[type])
    ]

    return Result.success(
        message=f"成功获取所有时间序列名称,共({len(filtered_names)}个)",
        data=filtered_names,
    )


def parse_datetime_safe(t):
    """
    安全解析时间字符串为 datetime 对象
    支持格式:MM/DD/YYYY HH:MM:SS
    因为:window读取swmm文件得到的是 timeseries.data [(datetime.datetime(2025, 5, 14, 12, 0), 10.0)]
    而linux读取swmm文件得到的是 timeseries.data [('04/07/2025 00:00:00', 1000.0)]
    这里需要将字符串转换为 datetime 对象
    """
    if isinstance(t, datetime):
        return t
    if isinstance(t, str):
        try:
            return datetime.strptime(t.strip(), "%m/%d/%Y %H:%M:%S")
        except ValueError:
            logger.error(f"无法解析时间字符串: {t}")
            return None
    return None


# 通过时间序列名称获取时间序列信息
@timeseriesRouter.get(
    "/timeseries/{timeseries_id:path}",
    summary="获取指定时间序列信息",
    description="通过指定时间序列名字,获取该时间序列的相关的所有信息",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_timeseries_by_id(
    timeseries_id: str,
    type: Annotated[
        TimeSeriesTypeModel,
        Query(description="时间序列类型,必须是 INFLOW 或 RAINGAGE"),
    ] = TimeSeriesTypeModel.INFLOW,
):
    # 加上时间序列类型前缀
    timeseries_id = TIMESERIES_PREFIXES_MAP[type] + timeseries_id

    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_timeseries = INP.check_for_section(TimeseriesData)
    timeseries = inp_timeseries.get(timeseries_id)
    if not timeseries:
        raise HTTPException(
            status_code=404, detail=f"时间序列 [ {timeseries_id} ] 不存在"
        )
    # 解析时间字符串为 datetime 对象,处理不同操作系统的时间格式
    data = []
    for t, v in timeseries.data:
        t = parse_datetime_safe(t)
        data.append((t, v))

    # 移除时间序列类型前缀
    name = remove_timeseries_prefix(
        timeseries.name, custom_prefix=TIMESERIES_PREFIXES_MAP[type]
    )

    time_series_model = TimeSeriesModel(
        name=name,
        data=data,
    )
    return Result.success(message="成功获取时间序列信息", data=time_series_model)


# 通过时间序列id更新时间序列信息
@timeseriesRouter.put(
    "/timeseries/{timeseries_id:path}",
    summary="更新指定时间序列信息",
    description="通过指定时间序列ID,更新时间序列的相关信息",
)
@with_exception_handler(default_message="更新失败,文件有误,发生未知错误")
async def update_timeseries_by_id(
    timeseries_id: str,
    timeseries: TimeSeriesModel,
    type: Annotated[
        TimeSeriesTypeModel,
        Query(description="时间序列类型,必须是 INFLOW 或 RAINGAGE"),
    ] = TimeSeriesTypeModel.INFLOW,
):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_timeseries = INP.check_for_section(TimeseriesData)
    inp_inflows = INP.check_for_section(Inflow)

    # 加上时间序列类型前缀
    timeseries_id = TIMESERIES_PREFIXES_MAP[type] + timeseries_id
    timeseries.name = TIMESERIES_PREFIXES_MAP[type] + timeseries.name

    # 检查时间序列ID是否存在
    if timeseries_id not in inp_timeseries:
        raise HTTPException(
            status_code=404,
            detail=f"保存失败,需要修改的时间序列名称 [ {timeseries_id} ] 不存在,请检查时间序列名称是否正确",
        )
    if timeseries.name in inp_timeseries and timeseries.name != timeseries_id:
        raise HTTPException(
            status_code=400,
            detail=f"保存失败,时间序列名称 [ {timeseries.name} ] 已存在,请使用不同的时间序列名称",
        )

    # 1.更新时间序列信息
    del inp_timeseries[timeseries_id]
    new_timeseries = TimeseriesData(
        name=timeseries.name,
        data=timeseries.data,
    )
    inp_timeseries[timeseries_id] = new_timeseries
    # 2.更新时间序列相关的数据
    related_entity_ids = []
    # 2.1 如果是 INFLOW 类型,则更新对应的 Inflow
    if type == TimeSeriesTypeModel.INFLOW:
        if timeseries_id != timeseries.name:
            for inflow in inp_inflows.values():
                if inflow.time_series == timeseries_id:
                    inflow.time_series = timeseries.name
                    related_entity_ids.append(inflow.node)

    # 2.2.如果是 RAINGAGE 类型,则更新对应的 RainGage
    if type == TimeSeriesTypeModel.RAINGAGE:
        related_entity_ids = update_raingage(
            INP,
            timeseries_name=timeseries_id,
            new_timeseries_name=timeseries.name,
            interval=timeseries.get_interval(),
        )

    # 3.message的构建
    if type == TimeSeriesTypeModel.INFLOW:
        message = f"流量序列更新成功"
    elif type == TimeSeriesTypeModel.RAINGAGE:
        message = f"雨量序列更新成功"
    else:
        message = f"时间序列更新成功"
    # 构建响应信息
    if len(related_entity_ids) > 0:
        message += f",同时更新了 {len(related_entity_ids)} 条引用"

    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success(
        message=message,
        data={"id": timeseries.name, "related_entity_ids": related_entity_ids},
    )


# 新建时间序列
@timeseriesRouter.post(
    "/timeseries",
    summary="创建新的时间序列",
    description="创建一个新的时间序列,并写入 SWMM 文件",
)
@with_exception_handler(default_message="创建失败,文件有误,发生未知错误")
async def create_timeseries(
    timeseries_data: TimeSeriesModel,
    type: Annotated[
        TimeSeriesTypeModel,
        Query(description="时间序列类型,必须是 INFLOW 或 RAINGAGE"),
    ] = TimeSeriesTypeModel.INFLOW,
):
    """
    创建时间序列信息
    """
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_timeseries = INP.check_for_section(TimeseriesData)

    # 补充时间序列名称前缀
    name = TIMESERIES_PREFIXES_MAP[type] + timeseries_data.name
    # 检查时间序列名称是否已存在
    if name in inp_timeseries:
        raise HTTPException(
            status_code=400,
            detail=f"创建失败,时间序列名称 [ {timeseries_data.name} ] 已存在,请使用不同的时间序列名称",
        )

    # 1.创建新的时间序列信息
    new_timeseries = TimeseriesData(
        name=name,
        data=timeseries_data.data,
    )
    inp_timeseries[name] = new_timeseries

    # 2.如果是 RAINGAGE 类型,则创建对应的 RainGage
    if type == TimeSeriesTypeModel.RAINGAGE:
        create_raingage(INP, timeseries_name=name)

    # 3.message的构建
    if type == TimeSeriesTypeModel.INFLOW:
        message = f"流量序列创建成功"
    elif type == TimeSeriesTypeModel.RAINGAGE:
        message = f"雨量序列创建成功"
    else:
        message = f"时间序列创建成功"

    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success(message=message, data={"name": timeseries_data.name})


# 通过 timeseries_id 删除时间序列
@timeseriesRouter.delete(
    "/timeseries/{timeseries_id:path}",
    summary="删除指定时间序列",
    description="通过时间序列ID删除时间序列,并清理关联的节点数据",
)
async def delete_timeseries(
    timeseries_id: str,
    type: Annotated[
        TimeSeriesTypeModel,
        Query(description="时间序列类型,必须是 INFLOW 或 RAINGAGE"),
    ] = TimeSeriesTypeModel.INFLOW,
):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_timeseries = INP.check_for_section(TimeseriesData)
    inp_inflows = INP.check_for_section(Inflow)

    # 加上时间序列类型前缀
    id = TIMESERIES_PREFIXES_MAP[type] + timeseries_id

    # 检查时间序列是否存在
    if id not in inp_timeseries:
        raise HTTPException(
            status_code=404,
            detail=f"删除失败,时间序列 [ {timeseries_id} ] 不存在",
        )
    # 1.检查关联的节点并记录
    related_inflows = [
        inflow.node for inflow in inp_inflows.values() if inflow.time_series == id
    ]
    if related_inflows:
        # 无法删除时间序列,因为有节点引用了它
        raise HTTPException(
            status_code=400,
            detail=f"删除失败,时间序列 [ {timeseries_id} ] 被 {len(related_inflows)} 条节点引用,请先取消引用再删除,节点名称为:{related_inflows}",
        )
    # 2.删除时间序列数据
    del inp_timeseries[id]

    # 3.如果是 RAINGAGE 类型,则删除对应的 RainGage
    if type == TimeSeriesTypeModel.RAINGAGE:
        delete_raingage(INP, timeseries_name=remove_timeseries_prefix(id))

    # 4.message的构建
    if type == TimeSeriesTypeModel.INFLOW:
        message = f"流量序列删除成功"
    elif type == TimeSeriesTypeModel.RAINGAGE:
        message = f"雨量序列删除成功"
    else:
        message = f"时间序列删除成功"
    # 保存修改
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success(message=message, data={"id": timeseries_id})
