from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections.others import TimeseriesData
from swmm_api.input_file.sections.node_component import Inflow
from schemas.timeseries import TimeSeriesModel
from schemas.result import Result
from datetime import timezone, timedelta, datetime

from utils.swmm_constant import (
    SWMM_FILE_INP_PATH,
    ENCODING,
)


timeseriesRouter = APIRouter()


@timeseriesRouter.get(
    "/timeseries",
    summary="获取所有时间序列信息",
    description="获取所有时间序列信息（废弃）",
    deprecated=True,
)
async def get_timeseries():
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_timeseries = INP.check_for_section(TimeseriesData)
        timeseries = []
        for ts in inp_timeseries.values():
            timeseries.append(
                {
                    "name": ts.name,
                    "data": ts.data,
                }
            )
        return timeseries
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，文件有误，发生未知错误'}",
        )


# 获取所有时间序列信息的name集合
@timeseriesRouter.get(
    "/timeseries/name",
    summary="获取所有时间序列的名称列表（不包含数据）",
    description="获取所有时间序列的名称列表集合（不包含数据）",
)
async def get_timeseries_names():
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_timeseries = INP.check_for_section(TimeseriesData)
        timeseries_names = list(inp_timeseries.keys())
        return Result.success(message="成功获取所有时间序列名称", data=timeseries_names)
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，文件有误，发生未知错误'}",
        )


# 通过时间序列名称获取时间序列信息
@timeseriesRouter.get(
    "/timeseries/{timeseries_id:path}",
    summary="获取指定时间序列信息",
    description="通过指定时间序列名字，获取该时间序列的相关的所有信息",
)
async def get_timeseries_by_id(timeseries_id: str):
    try:
        print("timeseries_id", timeseries_id)
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_timeseries = INP.check_for_section(TimeseriesData)
        timeseries = inp_timeseries.get(timeseries_id)
        if not timeseries:
            raise HTTPException(
                status_code=404, detail=f"时间序列 [ {timeseries_id} ] 不存在"
            )

        time_series_model = TimeSeriesModel(
            name=timeseries.name,
            data=timeseries.data,
        )
        return Result.success(message="成功获取时间序列信息", data=time_series_model)
    except Exception as e:
        print(e)
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，文件有误，发生未知错误'}",
        )


# 通过时间序列id更新时间序列信息
@timeseriesRouter.put(
    "/timeseries/{timeseries_id:path}",
    summary="更新指定时间序列信息",
    description="通过指定时间序列ID，更新时间序列的相关信息",
)
async def update_timeseries_by_id(timeseries_id: str, timeseries: TimeSeriesModel):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_timeseries = INP.check_for_section(TimeseriesData)
        inp_inflows = INP.check_for_section(Inflow)

        # 检查时间序列ID是否存在
        if timeseries_id not in inp_timeseries:
            raise HTTPException(
                status_code=404,
                detail=f"保存失败，需要修改的时间序列名称 [ {timeseries_id} ] 不存在，请检查时间序列名称是否正确",
            )
        if timeseries.name in inp_timeseries and timeseries.name != timeseries_id:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，时间序列名称 [ {timeseries.name} ] 已存在，请使用不同的时间序列名称",
            )

        # 1.更新时间序列信息
        del inp_timeseries[timeseries_id]
        new_timeseries = TimeseriesData(
            name=timeseries.name,
            data=timeseries.data,
        )
        inp_timeseries[timeseries_id] = new_timeseries
        # 2.更新时间序列相关的数据，比如Inflow
        related_inflows = []
        if timeseries_id != timeseries.name:
            for inflow in inp_inflows.values():
                if inflow.time_series == timeseries_id:
                    inflow.time_series = timeseries.name
                    related_inflows.append(inflow.node)

        # 构建响应信息
        message = f"时间序列更新成功"
        if len(related_inflows) > 0:
            message += f"，同时更新了 {len(related_inflows)} 条引用该时间序列的节点的时间序列名称"

        INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        return Result.success(
            message=message,
            data={"id": timeseries.name, "related_inflows": related_inflows},
        )
    except Exception as e:
        print(e)
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '更新失败，文件有误，发生未知错误'}",
        )


# 新建时间序列
@timeseriesRouter.post(
    "/timeseries",
    summary="创建新的时间序列",
    description="创建一个新的时间序列，并写入 SWMM 文件",
)
async def create_timeseries(timeseries_data: TimeSeriesModel):
    """
    创建时间序列信息
    """
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_timeseries = INP.check_for_section(TimeseriesData)

        # 检查时间序列名称是否已存在
        if timeseries_data.name in inp_timeseries:
            raise HTTPException(
                status_code=400,
                detail=f"创建失败，时间序列名称 [ {timeseries_data.name} ] 已存在，请使用不同的时间序列名称",
            )

        # 1.创建新的时间序列信息
        new_timeseries = TimeseriesData(
            name=timeseries_data.name,
            data=timeseries_data.data,
        )
        inp_timeseries[timeseries_data.name] = new_timeseries

        INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        return Result.success(
            message="时间序列创建成功", data={"name": timeseries_data.name}
        )
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '创建失败，文件有误，发生未知错误'}",
        )


# 通过 timeseries_id 删除时间序列
@timeseriesRouter.delete(
    "/timeseries/{timeseries_id:path}",
    summary="删除指定时间序列",
    description="通过时间序列ID删除时间序列，并清理关联的节点数据",
)
async def delete_timeseries(timeseries_id: str):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_timeseries = INP.check_for_section(TimeseriesData)
        inp_inflows = INP.check_for_section(Inflow)

        # 检查时间序列是否存在
        if timeseries_id not in inp_timeseries:
            raise HTTPException(
                status_code=404,
                detail=f"删除失败，时间序列 [ {timeseries_id} ] 不存在",
            )
        # 1.检查关联的节点并记录
        related_inflows = [
            inflow.node
            for inflow in inp_inflows.values()
            if inflow.time_series == timeseries_id
        ]
        if related_inflows:
            # 无法删除时间序列，因为有节点引用了它
            raise HTTPException(
                status_code=400,
                detail=f"删除失败，时间序列 [ {timeseries_id} ] 被 {len(related_inflows)} 条节点引用，请先取消引用再删除，节点名称为：{related_inflows}",
            )
        # 2.删除时间序列数据
        del inp_timeseries[timeseries_id]

        # 保存修改
        INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        return Result.success(message="时间序列删除成功", data={"id": timeseries_id})
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '创建失败，文件有误，发生未知错误'}",
        )
